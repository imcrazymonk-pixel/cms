"""Backup recipes: declarative knowledge about services on a host.

Recipes live in ``recipes/*.yaml`` and are the single source of truth for:
- how to detect a service in an agent inventory;
- which artifacts to collect (database/files/logs);
- which env keys are secret;
- how to restore and health-check.

The module has no CMS dependencies so it can be reused by the orchestrator and
tested standalone.
"""
import logging
import re
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_RECIPES_DIR = Path(__file__).resolve().parent / "recipes"

# recipe file mtime signature -> parsed recipes
_CACHE: Optional[tuple[str, dict[str, "Recipe"]]] = None


# --------------------------------------------------------------------------- models

class DetectCondition(BaseModel):
    docker_image: Optional[str] = None
    docker_container: Optional[str] = None
    port: Optional[int] = None


class DetectSpec(BaseModel):
    any: list[DetectCondition] = Field(default_factory=list)
    require_any: list[str] = Field(default_factory=list)
    min_confidence: str = "high"


class ArtifactDatabase(BaseModel):
    kind: str = "postgres"
    container: Optional[str] = None
    env_from_container: list[str] = Field(default_factory=list)
    password_from: Optional[str] = None
    method: str = "pg_dump"
    format: str = "custom"
    consistency: str = "online"


class ArtifactFile(BaseModel):
    path: str
    volume: Optional[str] = None
    exclude: list[str] = Field(default_factory=list)
    required: list[str] = Field(default_factory=list)
    secret: bool = False


class ArtifactLogs(BaseModel):
    enabled: bool = False
    paths: list[str] = Field(default_factory=list)
    max_size_mb: int = 500


class ArtifactsSpec(BaseModel):
    database: Optional[ArtifactDatabase] = None
    files: list[ArtifactFile] = Field(default_factory=list)
    logs: Optional[ArtifactLogs] = None
    redis: Optional[dict[str, Any]] = None


class ManifestSpec(BaseModel):
    capture: list[str] = Field(default_factory=list)


class HealthcheckSpec(BaseModel):
    command: str
    timeout: int = 30


class RestoreSpec(BaseModel):
    order: int = 0
    stop: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    destructive: bool = False
    requires_versions_match: bool = True


class Recipe(BaseModel):
    id: str
    title: str
    version: int = 1
    description: Optional[str] = None
    transport: str = "agent"
    detect: DetectSpec = Field(default_factory=DetectSpec)
    artifacts: ArtifactsSpec = Field(default_factory=ArtifactsSpec)
    manifest: ManifestSpec = Field(default_factory=ManifestSpec)
    secret_env_keys: list[str] = Field(default_factory=list)
    healthcheck: Optional[HealthcheckSpec] = None
    restore: Optional[RestoreSpec] = None


class MatchedComponent(BaseModel):
    recipe_id: str
    name: str
    container_name: Optional[str] = None
    image: Optional[str] = None
    image_digest: Optional[str] = None
    version: Optional[str] = None
    confidence: str = "high"
    matched_by: str
    detect_meta: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- loader

def _signature() -> str:
    return ",".join(
        f"{p.name}:{p.stat().st_mtime_ns}" for p in sorted(_RECIPES_DIR.glob("*.yaml"))
    )


def load_recipes() -> dict[str, Recipe]:
    """Parse all recipes, re-reading only when files change."""
    global _CACHE
    signature = _signature()
    if _CACHE is not None and _CACHE[0] == signature:
        return _CACHE[1]

    recipes: dict[str, Recipe] = {}
    for path in sorted(_RECIPES_DIR.glob("*.yaml")):
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            recipe = Recipe(**raw)
        except Exception as exc:  # noqa: BLE001 - a broken recipe must not kill startup
            logger.error("Backup recipe %s is invalid: %s", path.name, exc)
            continue
        if recipe.id in recipes:
            logger.warning("Duplicate backup recipe id %s in %s", recipe.id, path.name)
            continue
        recipes[recipe.id] = recipe

    _CACHE = (signature, recipes)
    return recipes


def list_recipes() -> list[Recipe]:
    return list(load_recipes().values())


def get_recipe(recipe_id: str) -> Optional[Recipe]:
    return load_recipes().get(recipe_id)


def reload_recipes() -> dict[str, Recipe]:
    """Force re-read (used by admin endpoints/tests)."""
    global _CACHE
    _CACHE = None
    return load_recipes()


# -------------------------------------------------------------------------- matcher

def _image_version(image: str) -> Optional[str]:
    if not image or ":" not in image:
        return None
    tag = image.rsplit(":", 1)[1]
    return None if tag in ("latest", "") else tag


def _containers(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    items = inventory.get("containers") or []
    return [c for c in items if isinstance(c, dict)]


def _matches(regex: Optional[str], value: Optional[str]) -> bool:
    if not regex or not value:
        return False
    try:
        return re.search(regex, str(value)) is not None
    except re.error:
        return False


def match_components(
    recipe: Recipe, inventory: dict[str, Any], host_role: str = "server"
) -> list[MatchedComponent]:
    """Return one component per matched container (or a single host-level one)."""
    # Recipes executed by the CMS process itself (`transport: inline`) only make
    # sense on the `self` host; scanning a remote server must not match them.
    if recipe.transport == "inline" and host_role != "self":
        return []

    containers = _containers(inventory)
    matched: dict[str, MatchedComponent] = {}

    for cond in recipe.detect.any:
        for container in containers:
            name = container.get("name")
            image = container.get("image")
            confidence: Optional[str] = None
            matched_by: Optional[str] = None

            if cond.docker_container and _matches(cond.docker_container, name):
                confidence, matched_by = "high", "docker_container"
            elif cond.docker_image and _matches(cond.docker_image, image):
                confidence, matched_by = "high", "docker_image"
            elif cond.port and cond.port in (container.get("ports") or []):
                confidence, matched_by = "medium", "port"

            if not confidence or not name:
                continue
            if name in matched:
                continue

            matched[name] = MatchedComponent(
                recipe_id=recipe.id,
                name=name,
                container_name=name,
                image=image,
                image_digest=container.get("image_digest"),
                version=container.get("version") or _image_version(image or ""),
                confidence=confidence,
                matched_by=matched_by,
                detect_meta={
                    "status": container.get("status"),
                    "ports": container.get("ports") or [],
                },
            )

    if matched:
        return list(matched.values())

    # Host-level recipes (e.g. the CMS itself) declare no docker hints.
    if not recipe.detect.any:
        return [
            MatchedComponent(
                recipe_id=recipe.id,
                name=recipe.title,
                confidence="high",
                matched_by="host",
            )
        ]

    return []


def match_all(inventory: dict[str, Any], host_role: str = "server") -> list[MatchedComponent]:
    result: list[MatchedComponent] = []
    for recipe in load_recipes().values():
        result.extend(match_components(recipe, inventory, host_role=host_role))
    return result

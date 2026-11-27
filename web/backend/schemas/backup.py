"""Backup schemas — Pydantic v2 models for the backup module.

Secrets never appear in response models: storages/channels expose only
``has_secret``. Nested values (config/advanced/threshold/manifest) are opaque
JSON owned by the backend.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- hosts

class Host(_Base):
    id: str
    name: str
    role: str = "server"
    address: str
    transport: str = "agent"
    ssh_port: int = 22
    ssh_user: Optional[str] = None
    credential_ref: Optional[str] = None
    has_ssh_key: bool = False
    tags: list[str] = Field(default_factory=list)
    status: str = "unknown"
    last_seen_at: Optional[datetime] = None
    last_scan_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class HostCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    address: str = Field(min_length=1, max_length=255)
    role: str = "server"
    transport: str = "agent"
    ssh_port: int = 22
    ssh_user: Optional[str] = None
    ssh_private_key: Optional[str] = None
    credential_ref: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class HostUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    role: Optional[str] = None
    transport: Optional[str] = None
    ssh_port: Optional[int] = None
    ssh_user: Optional[str] = None
    ssh_private_key: Optional[str] = None
    credential_ref: Optional[str] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None


class HostTestResult(BaseModel):
    ok: bool
    ssh: Optional[bool] = None
    docker: Optional[bool] = None
    message: str = ""
    disk_free_bytes: Optional[int] = None
    docker_version: Optional[str] = None


# --------------------------------------------------------------------------- agents

class Agent(_Base):
    id: str
    host_id: str
    agent_version: Optional[str] = None
    desired_version: Optional[str] = None
    protocol_version: int = 1
    status: str = "pending"
    spool_bytes: int = 0
    disk_free: Optional[int] = None
    last_heartbeat: Optional[datetime] = None
    installed_at: Optional[datetime] = None


class AgentInstall(BaseModel):
    host_id: str
    token: str
    install_command: str
    expires_at: Optional[datetime] = None


# ----------------------------------------------------------------------- components

class Component(_Base):
    id: str
    host_id: str
    recipe_id: str
    name: str
    container_name: Optional[str] = None
    image: Optional[str] = None
    image_digest: Optional[str] = None
    version: Optional[str] = None
    confidence: str = "high"
    enabled: bool = True
    detect_meta: dict[str, Any] = Field(default_factory=dict)
    updated_at: Optional[datetime] = None


class ComponentUpdate(BaseModel):
    enabled: Optional[bool] = None
    confidence: Optional[str] = None


class RecipeInfo(BaseModel):
    id: str
    title: str
    version: int = 1
    transport: str = "agent"
    description: Optional[str] = None


# ------------------------------------------------------------------------- policies

class Policy(_Base):
    id: str
    name: str
    host_id: str
    timezone: str = "Europe/Moscow"
    enabled: bool = True
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


class PolicyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    host_id: str
    timezone: str = "Europe/Moscow"
    enabled: bool = True


class PolicyUpdate(BaseModel):
    name: Optional[str] = None
    timezone: Optional[str] = None
    enabled: Optional[bool] = None


# ---------------------------------------------------------------------------- tiers

class Tier(_Base):
    id: str
    policy_id: str
    name: str
    position: int = 0
    scope: str = "full"
    component_ids: list[str] = Field(default_factory=list)
    schedule_kind: str = "cron"
    cron: Optional[str] = None
    interval_minutes: Optional[int] = None
    retention_mode: str = "auto"
    retention_copies: Optional[int] = None
    retention_days: int = 14
    min_copies: int = 3
    storage_ids: list[str] = Field(default_factory=list)
    encrypt: bool = True
    include_logs: bool = False
    consistency: str = "online"
    enabled: bool = True
    next_run_at: Optional[datetime] = None


class TierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    position: int = 0
    scope: str = "full"
    component_ids: list[str] = Field(default_factory=list)
    schedule_kind: str = "cron"
    cron: Optional[str] = None
    interval_minutes: Optional[int] = None
    retention_mode: str = "auto"
    retention_copies: Optional[int] = None
    retention_days: int = 14
    min_copies: int = 3
    storage_ids: list[str] = Field(default_factory=list)
    encrypt: bool = True
    include_logs: bool = False
    consistency: str = "online"
    enabled: bool = True


class TierUpdate(BaseModel):
    name: Optional[str] = None
    position: Optional[int] = None
    scope: Optional[str] = None
    component_ids: Optional[list[str]] = None
    schedule_kind: Optional[str] = None
    cron: Optional[str] = None
    interval_minutes: Optional[int] = None
    retention_mode: Optional[str] = None
    retention_copies: Optional[int] = None
    retention_days: Optional[int] = None
    min_copies: Optional[int] = None
    storage_ids: Optional[list[str]] = None
    encrypt: Optional[bool] = None
    include_logs: Optional[bool] = None
    consistency: Optional[str] = None
    enabled: Optional[bool] = None


# ----------------------------------------------------------------------------- runs

class RunStep(BaseModel):
    id: str
    title: str
    status: str = "pending"
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    detail: Optional[str] = None


class Run(_Base):
    id: str
    policy_id: Optional[str] = None
    tier_id: Optional[str] = None
    host_id: Optional[str] = None
    agent_id: Optional[str] = None
    kind: str = "backup"
    trigger: str = "manual"
    client_run_id: Optional[str] = None
    status: str = "queued"
    progress: int = 0
    steps: list[RunStep] = Field(default_factory=list)
    log: str = ""
    error: Optional[str] = None
    cancel_requested: bool = False
    size_bytes: Optional[int] = None
    artifact_scope: Optional[str] = None
    consistency_group: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class RunCreate(BaseModel):
    host_id: str
    tier_id: Optional[str] = None
    kind: str = "backup"
    scope: Optional[str] = None
    component_ids: list[str] = Field(default_factory=list)
    include_logs: bool = False


# ------------------------------------------------------------------------ artifacts

class Artifact(_Base):
    id: str
    run_id: str
    component_id: Optional[str] = None
    storage_id: Optional[str] = None
    artifact_type: str
    object_key: str
    size_bytes: Optional[int] = None
    sha256: Optional[str] = None
    encrypted: bool = True
    manifest: dict[str, Any] = Field(default_factory=dict)
    orphaned: bool = False
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ArtifactVerifyResult(BaseModel):
    artifact_id: str
    sha256_ok: bool
    pg_restore_list_ok: Optional[bool] = None
    message: str = ""


# ------------------------------------------------------------------------- storages

class Storage(_Base):
    id: str
    name: str
    kind: str
    config: dict[str, Any] = Field(default_factory=dict)
    advanced: dict[str, Any] = Field(default_factory=dict)
    has_secret: bool = False
    enabled: bool = True
    is_default: bool = False
    quota_bytes: Optional[int] = None
    used_bytes: int = 0
    last_check_at: Optional[datetime] = None
    last_check_ok: Optional[bool] = None
    created_at: Optional[datetime] = None


class StorageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str
    config: dict[str, Any] = Field(default_factory=dict)
    advanced: dict[str, Any] = Field(default_factory=dict)
    secret: Optional[str] = None
    enabled: bool = True
    is_default: bool = False
    quota_bytes: Optional[int] = None


class StorageUpdate(BaseModel):
    name: Optional[str] = None
    kind: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    advanced: Optional[dict[str, Any]] = None
    secret: Optional[str] = None
    enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    quota_bytes: Optional[int] = None


class StorageTestResult(BaseModel):
    ok: bool
    message: str = ""
    latency_ms: Optional[int] = None


# -------------------------------------------------------------------------- restores

class RestorePlanStep(BaseModel):
    title: str
    description: Optional[str] = None
    duration_hint: Optional[str] = None


class RestorePlan(BaseModel):
    group_key: str
    target_host_id: Optional[str] = None
    target_kind: str = "same"
    plan_token: str
    steps: list[RestorePlanStep] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocking: bool = False


class RestoreCreate(BaseModel):
    plan_token: str
    confirm: bool = False


class Restore(_Base):
    id: str
    group_key: Optional[str] = None
    target_host_id: Optional[str] = None
    target_kind: str = "same"
    plan: dict[str, Any] = Field(default_factory=dict)
    status: str = "planned"
    pre_snapshot_run_id: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


# --------------------------------------------------------------------- notifications

class NotificationChannel(_Base):
    id: str
    name: str
    kind: str
    config: dict[str, Any] = Field(default_factory=dict)
    has_secret: bool = False
    enabled: bool = True
    last_check_at: Optional[datetime] = None
    last_check_ok: Optional[bool] = None
    created_at: Optional[datetime] = None


class NotificationChannelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str
    config: dict[str, Any] = Field(default_factory=dict)
    secret: Optional[str] = None
    enabled: bool = True


class NotificationChannelUpdate(BaseModel):
    name: Optional[str] = None
    kind: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    secret: Optional[str] = None
    enabled: Optional[bool] = None


class NotificationRule(_Base):
    id: str
    name: str
    event: str
    host_id: Optional[str] = None
    policy_id: Optional[str] = None
    channel_ids: list[str] = Field(default_factory=list)
    threshold: dict[str, Any] = Field(default_factory=dict)
    quiet_hours: Optional[str] = None
    repeat_every_min: Optional[int] = None
    severity: str = "warning"
    enabled: bool = True
    created_at: Optional[datetime] = None


class NotificationRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    event: str
    host_id: Optional[str] = None
    policy_id: Optional[str] = None
    channel_ids: list[str] = Field(default_factory=list)
    threshold: dict[str, Any] = Field(default_factory=dict)
    quiet_hours: Optional[str] = None
    repeat_every_min: Optional[int] = None
    severity: str = "warning"
    enabled: bool = True


class NotificationRuleUpdate(BaseModel):
    name: Optional[str] = None
    event: Optional[str] = None
    host_id: Optional[str] = None
    policy_id: Optional[str] = None
    channel_ids: Optional[list[str]] = None
    threshold: Optional[dict[str, Any]] = None
    quiet_hours: Optional[str] = None
    repeat_every_min: Optional[int] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None


class NotificationEvent(BaseModel):
    event: str
    title: str
    description: str
    severity: str = "warning"


# -------------------------------------------------------------------------- overview

class BackupOverview(BaseModel):
    hosts_total: int = 0
    hosts_unreachable: int = 0
    agents_online: int = 0
    agents_offline: int = 0
    storages_total: int = 0
    storages_error: int = 0
    policies_total: int = 0
    last_success_at: Optional[datetime] = None
    last_db_backup_at: Optional[datetime] = None
    last_full_backup_at: Optional[datetime] = None
    overdue: list[dict[str, Any]] = Field(default_factory=list)
    attention: list[dict[str, Any]] = Field(default_factory=list)
    total_bytes: int = 0


class BackupSettings(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


class BackupSettingsUpdate(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------- agent protocol

class AgentRegister(BaseModel):
    host_id: str
    token: str
    agent_version: str
    protocol_version: int = 1


class AgentRegisterResult(BaseModel):
    agent_id: str
    host_id: str
    heartbeat_interval: int = 30
    poll_interval: int = 15


class AgentHeartbeat(BaseModel):
    agent_version: Optional[str] = None
    spool_bytes: int = 0
    disk_free: Optional[int] = None
    uptime_seconds: Optional[int] = None


class AgentInventory(BaseModel):
    docker_version: Optional[str] = None
    compose_projects: list[dict[str, Any]] = Field(default_factory=list)
    containers: list[dict[str, Any]] = Field(default_factory=list)
    ports: list[dict[str, Any]] = Field(default_factory=list)
    disk: dict[str, Any] = Field(default_factory=dict)
    collected_at: Optional[datetime] = None


class AgentState(BaseModel):
    version: str
    desired_version: Optional[str] = None
    recipes: list[dict[str, Any]] = Field(default_factory=list)
    policies: list[dict[str, Any]] = Field(default_factory=list)
    agent_settings: dict[str, Any] = Field(default_factory=dict)


class AgentRunUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[int] = None
    steps: Optional[list[dict[str, Any]]] = None
    log_append: Optional[str] = None
    error: Optional[str] = None
    finished: bool = False

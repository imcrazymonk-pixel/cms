"""Agent configuration (env prefix ``AGENT_``)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENT_", env_file=".env", extra="ignore")

    url: str
    host_id: str
    token: str

    spool_dir: str = "/var/lib/hexaveil-agent"
    concurrency: int = 1
    tz: str = "UTC"
    host_mode: bool = False
    log_level: str = "info"

    # Where the host filesystem is mounted inside the container.
    host_prefix: str = "/host"

    # age keys. The recipient (public key) is used for encryption; identity is
    # needed only to restore (optional, may be provided by the CMS at restore).
    age_recipient: str = ""
    age_identity: str = ""

    version: str = "0.1.0"
    protocol_version: int = 1

    heartbeat_interval: int = 30
    poll_interval: int = 15
    state_interval: int = 60
    schedule_interval: int = 15

    request_timeout: int = 120
    upload_timeout: int = 3600


def load_config() -> AgentConfig:
    return AgentConfig()  # type: ignore[call-arg]

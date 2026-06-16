"""Bootstrap helpers for service-backed backend tests."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from test.cn_model_hub.support.bootstrap import (
    ADMIN_TOKEN,
    DEFAULT_PASSWORD,
    ensure_python_paths,
)

SERVICE_ROOT = Path(__file__).resolve().parents[3] / "hub-meta" / "test" / "backend-service"
LAKEFS_CREDENTIALS_FILE = SERVICE_ROOT / "lakefs-credentials.env"
DEV_LAKEFS_CREDENTIALS_FILE = (
    Path(__file__).resolve().parents[3] / "hub-meta" / "dev" / "lakefs" / "credentials.env"
)

_ENV_APPLIED = False


@dataclass(frozen=True, slots=True)
class ServiceTestConfig:
    """Configuration for the service-backed backend test profile."""

    database_url: str
    s3_endpoint: str
    s3_public_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    s3_region: str
    lakefs_endpoint: str
    lakefs_repo_namespace: str
    lakefs_credentials_file: Path


def ensure_service_paths() -> None:
    """Create local directories used by the service-backed test profile."""
    SERVICE_ROOT.mkdir(parents=True, exist_ok=True)


def get_service_test_config() -> ServiceTestConfig:
    """Return the effective config for the service-backed test profile."""
    return ServiceTestConfig(
        database_url=os.environ.get(
            "CN_MODEL_HUB_DATABASE_URL",
            "postgresql://hub_dev:hub_dev_password@127.0.0.1:25432/cn_model_hub_test",
        ),
        s3_endpoint=os.environ.get(
            "CN_MODEL_HUB_S3_ENDPOINT",
            "http://127.0.0.1:29001",
        ),
        s3_public_endpoint=os.environ.get(
            "CN_MODEL_HUB_S3_PUBLIC_ENDPOINT",
            os.environ.get("CN_MODEL_HUB_S3_ENDPOINT", "http://127.0.0.1:29001"),
        ),
        s3_access_key=os.environ.get("CN_MODEL_HUB_S3_ACCESS_KEY", "minioadmin"),
        s3_secret_key=os.environ.get("CN_MODEL_HUB_S3_SECRET_KEY", "minioadmin"),
        s3_bucket=os.environ.get("CN_MODEL_HUB_S3_BUCKET", "hub-storage"),
        s3_region=os.environ.get("CN_MODEL_HUB_S3_REGION", "us-east-1"),
        lakefs_endpoint=os.environ.get(
            "CN_MODEL_HUB_LAKEFS_ENDPOINT",
            "http://127.0.0.1:28000",
        ),
        lakefs_repo_namespace=os.environ.get(
            "CN_MODEL_HUB_LAKEFS_REPO_NAMESPACE",
            "hf",
        ),
        lakefs_credentials_file=Path(
            os.environ.get(
                "CN_MODEL_HUB_LAKEFS_CREDENTIALS_FILE",
                str(LAKEFS_CREDENTIALS_FILE),
            )
        ),
    )


def _read_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key] = value
    return data


def apply_service_test_env() -> None:
    """Apply deterministic environment overrides for the service-backed test suite."""
    global _ENV_APPLIED
    if _ENV_APPLIED:
        return

    ensure_service_paths()
    ensure_python_paths()

    cfg = get_service_test_config()
    lakefs_credentials = _read_env_file(cfg.lakefs_credentials_file)
    if not lakefs_credentials:
        lakefs_credentials = _read_env_file(DEV_LAKEFS_CREDENTIALS_FILE)

    forced_env = {
        "CN_MODEL_HUB_BASE_URL": "http://testserver",
        "CN_MODEL_HUB_INTERNAL_BASE_URL": "http://testserver",
        "CN_MODEL_HUB_API_BASE": "/api",
        "CN_MODEL_HUB_SESSION_SECRET": "test-session-secret",
        "CN_MODEL_HUB_SESSION_EXPIRE_HOURS": "168",
        "CN_MODEL_HUB_TOKEN_EXPIRE_DAYS": "365",
        "CN_MODEL_HUB_REQUIRE_EMAIL_VERIFICATION": "false",
        "CN_MODEL_HUB_INVITATION_ONLY": "false",
        "CN_MODEL_HUB_ADMIN_ENABLED": "true",
        "CN_MODEL_HUB_ADMIN_SECRET_TOKEN": ADMIN_TOKEN,
        "CN_MODEL_HUB_FALLBACK_ENABLED": "false",
        "CN_MODEL_HUB_DISABLE_DATASET_VIEWER": "true",
        "CN_MODEL_HUB_LOG_LEVEL": "ERROR",
        "CN_MODEL_HUB_LOG_FORMAT": "terminal",
        "CN_MODEL_HUB_LFS_THRESHOLD_BYTES": "1024",
        "CN_MODEL_HUB_LFS_MULTIPART_THRESHOLD_BYTES": "1000000",
        "CN_MODEL_HUB_LFS_MULTIPART_CHUNK_SIZE_BYTES": "500000",
        "CN_MODEL_HUB_LFS_KEEP_VERSIONS": "5",
        "CN_MODEL_HUB_LFS_AUTO_GC": "true",
    }

    default_env = {
        "CN_MODEL_HUB_DB_BACKEND": "postgres",
        "CN_MODEL_HUB_DATABASE_URL": cfg.database_url,
        "CN_MODEL_HUB_DATABASE_KEY": "test-database-key",
        "CN_MODEL_HUB_S3_ENDPOINT": cfg.s3_endpoint,
        "CN_MODEL_HUB_S3_PUBLIC_ENDPOINT": cfg.s3_public_endpoint,
        "CN_MODEL_HUB_S3_ACCESS_KEY": cfg.s3_access_key,
        "CN_MODEL_HUB_S3_SECRET_KEY": cfg.s3_secret_key,
        "CN_MODEL_HUB_S3_BUCKET": cfg.s3_bucket,
        "CN_MODEL_HUB_S3_REGION": cfg.s3_region,
        "CN_MODEL_HUB_LAKEFS_ENDPOINT": cfg.lakefs_endpoint,
        "CN_MODEL_HUB_LAKEFS_REPO_NAMESPACE": cfg.lakefs_repo_namespace,
        "CN_MODEL_HUB_LAKEFS_CREDENTIALS_FILE": str(cfg.lakefs_credentials_file),
    }

    os.environ.update(forced_env)
    for key, value in default_env.items():
        os.environ.setdefault(key, value)

    if lakefs_credentials:
        for key, value in lakefs_credentials.items():
            os.environ.setdefault(key, value)

    _ENV_APPLIED = True

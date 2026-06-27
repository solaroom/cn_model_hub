"""Configuration management for cn_model_hub."""

import os
from functools import lru_cache

from pydantic import BaseModel

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

# Default configuration values
_DEFAULT_S3_ENDPOINT = "http://localhost:9000"


class S3Config(BaseModel):
    public_endpoint: str = _DEFAULT_S3_ENDPOINT
    endpoint: str = _DEFAULT_S3_ENDPOINT
    access_key: str = "test-access-key"
    secret_key: str = "test-secret-key"
    bucket: str = "test-bucket"
    region: str = "us-east-1"  # auto (recommended), us-east-1, or specific AWS region
    force_path_style: bool = True
    signature_version: str | None = None  # s3v4 (R2, AWS S3) or None/s3v2 (MinIO)


class LakeFSConfig(BaseModel):
    endpoint: str = "http://localhost:8000"
    access_key: str = "test-access-key"
    secret_key: str = "test-secret-key"
    repo_namespace: str = "hf"


class SMTPConfig(BaseModel):
    enabled: bool = False
    host: str = "localhost"
    port: int = 587
    username: str = ""
    password: str = ""
    from_email: str = "noreply@localhost"
    use_tls: bool = True


class AuthConfig(BaseModel):
    require_email_verification: bool = False
    invitation_only: bool = False  # Disable public registration, require invitation
    session_secret: str = "change-me-in-production"
    session_expire_hours: int = 168  # 7 days
    token_expire_days: int = 365


class QuotaConfig(BaseModel):
    """Storage quota configuration."""

    default_user_private_quota_bytes: int | None = None  # None = unlimited
    default_user_public_quota_bytes: int | None = None  # None = unlimited
    default_org_private_quota_bytes: int | None = None  # None = unlimited
    default_org_public_quota_bytes: int | None = None  # None = unlimited


class FallbackConfig(BaseModel):
    """Fallback source configuration."""

    enabled: bool = True  # Enable fallback system
    cache_ttl_seconds: int = 30  # Cache TTL for repo→source mappings (default 30s post-#78)
    timeout_seconds: int = 10  # HTTP request timeout for external sources
    max_concurrent_requests: int = 5  # Max concurrent requests to external sources
    require_auth: bool = False  # Require authenticated user for fallback access
    # Global fallback sources (JSON list)
    # Format: [{"url": "https://huggingface.co", "token": "", "priority": 1, "name": "HF", "source_type": "huggingface"}]
    sources: list[dict] = []


class CacheConfig(BaseModel):
    """L2 cache (Valkey/Redis) configuration.

    Pure cache, no business state. When ``enabled`` is False the cache layer
    silently degrades and every call falls back to its source. See
    ``docs/development/cache.md`` for the full design.
    """

    # Disabled by default so existing deployments don't acquire a hard
    # dependency on Valkey unintentionally. Local-dev .env.dev.example flips
    # this to True so contributors surface cache bugs early.
    enabled: bool = False
    url: str = "redis://localhost:6379/0"
    # Namespace prefix isolates cache keys when multiple deployments share a
    # single Valkey instance (rare in production, common in CI runners that
    # reuse a managed Redis between jobs).
    namespace: str = "kh"
    # Default TTL applied by ``cache_set_json`` when callers don't pass one.
    default_ttl_seconds: int = 300
    # ±jitter fraction applied to every TTL inside the helper. Set to 0 to
    # disable jitter (only useful for deterministic tests).
    jitter_fraction: float = 0.15
    # Connection pool size; tuned for ~4 uvicorn workers each running a
    # handful of concurrent requests. Bump if a deployment scales beyond.
    max_connections: int = 50
    # Socket timeouts. Cache must never become a latency cliff — short
    # timeouts so a flaky Valkey degrades to "cache miss" within ms, not s.
    socket_timeout_seconds: float = 0.5
    socket_connect_timeout_seconds: float = 0.5


class SearchConfig(BaseModel):
    """Repository search backend configuration."""

    meilisearch_enabled: bool = False
    meilisearch_url: str = ""
    meilisearch_api_key: str = ""
    meilisearch_timeout_seconds: int = 3
    meilisearch_task_timeout_ms: int = 5000


class AssistantConfig(BaseModel):
    """Smart assistant configuration."""

    llm_api_key: str = ""
    llm_provider: str = "llm"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: int = 30
    embedding_enabled: bool = True
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    max_knowledge_chunks: int = 5


class AppConfig(BaseModel):
    base_url: str = "http://localhost:48888"
    # Allows local dev to expose frontend-facing URLs while backend self-calls stay direct.
    internal_base_url: str | None = None
    api_base: str = "/api"
    db_backend: str = "sqlite"
    # Optional features
    disable_dataset_viewer: bool = False
    database_url: str = "sqlite:///./hub.db"
    database_key: str = (
        ""  # Encryption key for external tokens (generate with: openssl rand -hex 32)
    )
    # Lower threshold to 5MB to account for base64 encoding overhead (~33%)
    # 5MB file -> ~6.7MB base64, leaving room for multiple files in one commit
    lfs_threshold_bytes: int = 5 * 1000 * 1000
    debug_log_payloads: bool = False
    # LFS Multipart Upload settings
    lfs_multipart_threshold_bytes: int = (
        2 * 1000 * 1000 * 1000
    )  # 2 GB - keep common demo models on the simpler single PUT path
    lfs_multipart_chunk_size_bytes: int = (
        50 * 1000 * 1000
    )  # 50 MB - size of each part (S3 minimum is 5MB except last part)
    # LFS Garbage Collection settings
    lfs_keep_versions: int = 5  # Keep last K versions of each file
    lfs_auto_gc: bool = False  # Auto-delete old LFS objects on commit
    # Download tracking settings
    download_time_bucket_seconds: int = 900  # 15 minutes - session deduplication window
    download_session_cleanup_threshold: int = (
        100  # Trigger cleanup when sessions > this
    )
    download_keep_sessions_days: int = 30  # Keep sessions from last N days
    # LFS Suffix Rules - File extensions that should ALWAYS use LFS
    # These are server-wide defaults that apply to ALL repositories
    # Repositories can add their own additional suffix rules
    lfs_suffix_rules_default: list[str] = [
        # ML Model Formats
        ".safetensors",  # SafeTensors (most common for HF models)
        ".bin",  # PyTorch binary weights
        ".pt",  # PyTorch checkpoint
        ".pth",  # PyTorch checkpoint
        ".ckpt",  # PyTorch Lightning checkpoint
        ".onnx",  # ONNX model
        ".pb",  # TensorFlow protobuf
        ".h5",  # Keras/HDF5 model
        ".tflite",  # TensorFlow Lite
        ".gguf",  # GGUF quantized models (llama.cpp)
        ".ggml",  # GGML models
        ".msgpack",  # MessagePack serialization
        # Compressed Archives
        ".zip",  # ZIP archive
        ".tar",  # TAR archive
        ".gz",  # GZIP compressed
        ".bz2",  # BZIP2 compressed
        ".xz",  # XZ compressed
        ".7z",  # 7-Zip archive
        ".rar",  # RAR archive
        # Data Files
        ".npy",  # NumPy array
        ".npz",  # NumPy compressed archive
        ".arrow",  # Apache Arrow
        ".parquet",  # Apache Parquet
        # Media Files
        ".mp4",  # Video
        ".avi",  # Video
        ".mkv",  # Video
        ".mov",  # Video
        ".wav",  # Audio
        ".mp3",  # Audio
        ".flac",  # Audio
        # Images (large formats)
        ".tiff",  # TIFF image
        ".tif",  # TIFF image
    ]
    # Site identification
    site_name: str = "cn_model_hub"  # Configurable site name (e.g., "MyCompany Hub")
    # Simplified local Space runtime.
    space_runtime_backend: str = "local"
    space_runtime_dir: str = ".space-runtimes"
    space_runtime_install_requirements: bool = True
    space_runtime_remote_base_url: str = ""
    space_runtime_remote_api_key: str = ""
    space_runtime_remote_upload_method: str = "ssh"
    space_runtime_remote_ssh_alias: str = ""
    space_runtime_remote_root: str = ""
    # MLflow tracking endpoint. Also exported to Space runtimes as MLFLOW_TRACKING_URI.
    mlflow_tracking_uri: str = ""
    # Log settings
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_format: str = (
        "file"  # Output logs to "file" or "terminal" (maybe sql in future)
    )
    log_dir: str = "logs/"  # Path to log file (if log_format is "file")


class Config(BaseModel):
    s3: S3Config
    lakefs: LakeFSConfig
    smtp: SMTPConfig = SMTPConfig()
    auth: AuthConfig = AuthConfig()
    quota: QuotaConfig = QuotaConfig()
    fallback: FallbackConfig = FallbackConfig()
    cache: CacheConfig = CacheConfig()
    search: SearchConfig = SearchConfig()
    assistant: AssistantConfig = AssistantConfig()
    app: AppConfig

    def validate_production_safety(self) -> list[str]:
        """Check if configuration uses unsafe default values.

        Returns:
            List of warning messages for unsafe defaults
        """
        warnings = []

        # S3 credentials
        if self.s3.access_key == "test-access-key":
            warnings.append("S3 access_key is using test default value")
        if self.s3.secret_key == "test-secret-key":
            warnings.append("S3 secret_key is using test default value")
        if self.s3.bucket == "test-bucket":
            warnings.append("S3 bucket is using test default value")

        # LakeFS credentials
        if self.lakefs.access_key == "test-access-key":
            warnings.append("LakeFS access_key is using test default value")
        if self.lakefs.secret_key == "test-secret-key":
            warnings.append("LakeFS secret_key is using test default value")

        # Auth secrets
        if self.auth.session_secret == "change-me-in-production":
            warnings.append("Session secret is using default value - SECURITY RISK!")
        # LFS GC settings validation
        if self.app.lfs_keep_versions < 2:
            warnings.append(
                f"LFS keep_versions={self.app.lfs_keep_versions} is too low! "
                f"Minimum recommended: 5. Revert/reset operations will likely fail. "
                f"Set CN_MODEL_HUB_LFS_KEEP_VERSIONS=5 or higher."
            )

        # LFS threshold validation
        if self.app.lfs_threshold_bytes < 1000 * 1000:  # Less than 1MB
            warnings.append(
                f"LFS threshold is very low ({self.app.lfs_threshold_bytes} bytes). "
                f"Consider setting to at least 5MB (5242880 bytes)."
            )

        return warnings


def update_recursive(d: dict, u: dict) -> dict:
    """Recursively update a dictionary."""
    for k, v in u.items():
        if isinstance(v, dict):
            # get node or create one
            d[k] = update_recursive(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def _parse_quota(value: str | None) -> int | None:
    """Parse quota value from environment variable."""
    if value is None or value.lower() in ("", "none", "unlimited"):
        return None
    return int(value)


def _parse_fallback_sources(value: str | None) -> list[dict]:
    """Parse fallback sources from JSON environment variable."""
    import json

    if not value:
        return []
    try:
        sources = json.loads(value)
        if not isinstance(sources, list):
            return []
        return sources
    except json.JSONDecodeError:
        return []


@lru_cache(maxsize=1)
def load_config(path: str = None) -> Config:
    # 1. Determine config file path: explicit path, HUB_CONFIG env, or default "config.toml"
    config_path = path or os.environ.get("HUB_CONFIG") or "config.toml"

    # 2. Load from TOML file if it exists
    config_from_file = {}
    if os.path.exists(config_path):
        with open(config_path, "rb") as f:
            config_from_file = tomllib.load(f)

    # 3. Load from environment variables, building a nested dict
    config_from_env = {}

    # S3
    s3_env = {}
    if "CN_MODEL_HUB_S3_PUBLIC_ENDPOINT" in os.environ:
        s3_env["public_endpoint"] = os.environ["CN_MODEL_HUB_S3_PUBLIC_ENDPOINT"]
    if "CN_MODEL_HUB_S3_ENDPOINT" in os.environ:
        s3_env["endpoint"] = os.environ["CN_MODEL_HUB_S3_ENDPOINT"]
    if "CN_MODEL_HUB_S3_ACCESS_KEY" in os.environ:
        s3_env["access_key"] = os.environ["CN_MODEL_HUB_S3_ACCESS_KEY"]
    if "CN_MODEL_HUB_S3_SECRET_KEY" in os.environ:
        s3_env["secret_key"] = os.environ["CN_MODEL_HUB_S3_SECRET_KEY"]
    if "CN_MODEL_HUB_S3_BUCKET" in os.environ:
        s3_env["bucket"] = os.environ["CN_MODEL_HUB_S3_BUCKET"]
    if "CN_MODEL_HUB_S3_REGION" in os.environ:
        s3_env["region"] = os.environ["CN_MODEL_HUB_S3_REGION"]
    if "CN_MODEL_HUB_S3_SIGNATURE_VERSION" in os.environ:
        s3_env["signature_version"] = os.environ["CN_MODEL_HUB_S3_SIGNATURE_VERSION"]
    if s3_env:
        config_from_env["s3"] = s3_env

    # LakeFS
    lakefs_env = {}
    if "CN_MODEL_HUB_LAKEFS_ENDPOINT" in os.environ:
        lakefs_env["endpoint"] = os.environ["CN_MODEL_HUB_LAKEFS_ENDPOINT"]
    if "CN_MODEL_HUB_LAKEFS_ACCESS_KEY" in os.environ:
        lakefs_env["access_key"] = os.environ["CN_MODEL_HUB_LAKEFS_ACCESS_KEY"]
    if "CN_MODEL_HUB_LAKEFS_SECRET_KEY" in os.environ:
        lakefs_env["secret_key"] = os.environ["CN_MODEL_HUB_LAKEFS_SECRET_KEY"]
    if "CN_MODEL_HUB_LAKEFS_REPO_NAMESPACE" in os.environ:
        lakefs_env["repo_namespace"] = os.environ["CN_MODEL_HUB_LAKEFS_REPO_NAMESPACE"]
    if lakefs_env:
        config_from_env["lakefs"] = lakefs_env

    # SMTP
    smtp_env = {}
    if "CN_MODEL_HUB_SMTP_ENABLED" in os.environ:
        smtp_env["enabled"] = os.environ["CN_MODEL_HUB_SMTP_ENABLED"].lower() == "true"
    if "CN_MODEL_HUB_SMTP_HOST" in os.environ:
        smtp_env["host"] = os.environ["CN_MODEL_HUB_SMTP_HOST"]
    if "CN_MODEL_HUB_SMTP_PORT" in os.environ:
        smtp_env["port"] = int(os.environ["CN_MODEL_HUB_SMTP_PORT"])
    if "CN_MODEL_HUB_SMTP_USERNAME" in os.environ:
        smtp_env["username"] = os.environ["CN_MODEL_HUB_SMTP_USERNAME"]
    if "CN_MODEL_HUB_SMTP_PASSWORD" in os.environ:
        smtp_env["password"] = os.environ["CN_MODEL_HUB_SMTP_PASSWORD"]
    if "CN_MODEL_HUB_SMTP_FROM" in os.environ:
        smtp_env["from_email"] = os.environ["CN_MODEL_HUB_SMTP_FROM"]
    if "CN_MODEL_HUB_SMTP_TLS" in os.environ:
        smtp_env["use_tls"] = os.environ["CN_MODEL_HUB_SMTP_TLS"].lower() == "true"
    if smtp_env:
        config_from_env["smtp"] = smtp_env

    # Auth
    auth_env = {}
    if "CN_MODEL_HUB_REQUIRE_EMAIL_VERIFICATION" in os.environ:
        auth_env["require_email_verification"] = (
            os.environ["CN_MODEL_HUB_REQUIRE_EMAIL_VERIFICATION"].lower() == "true"
        )
    if "CN_MODEL_HUB_INVITATION_ONLY" in os.environ:
        auth_env["invitation_only"] = (
            os.environ["CN_MODEL_HUB_INVITATION_ONLY"].lower() == "true"
        )
    if "CN_MODEL_HUB_SESSION_SECRET" in os.environ:
        auth_env["session_secret"] = os.environ["CN_MODEL_HUB_SESSION_SECRET"]
    if "CN_MODEL_HUB_SESSION_EXPIRE_HOURS" in os.environ:
        auth_env["session_expire_hours"] = int(
            os.environ["CN_MODEL_HUB_SESSION_EXPIRE_HOURS"]
        )
    if "CN_MODEL_HUB_TOKEN_EXPIRE_DAYS" in os.environ:
        auth_env["token_expire_days"] = int(os.environ["CN_MODEL_HUB_TOKEN_EXPIRE_DAYS"])
    if auth_env:
        config_from_env["auth"] = auth_env

    # Quota
    quota_env = {}
    if "CN_MODEL_HUB_DEFAULT_USER_PRIVATE_QUOTA_BYTES" in os.environ:
        quota_env["default_user_private_quota_bytes"] = _parse_quota(
            os.environ.get("CN_MODEL_HUB_DEFAULT_USER_PRIVATE_QUOTA_BYTES")
        )
    if "CN_MODEL_HUB_DEFAULT_USER_PUBLIC_QUOTA_BYTES" in os.environ:
        quota_env["default_user_public_quota_bytes"] = _parse_quota(
            os.environ.get("CN_MODEL_HUB_DEFAULT_USER_PUBLIC_QUOTA_BYTES")
        )
    if "CN_MODEL_HUB_DEFAULT_ORG_PRIVATE_QUOTA_BYTES" in os.environ:
        quota_env["default_org_private_quota_bytes"] = _parse_quota(
            os.environ.get("CN_MODEL_HUB_DEFAULT_ORG_PRIVATE_QUOTA_BYTES")
        )
    if "CN_MODEL_HUB_DEFAULT_ORG_PUBLIC_QUOTA_BYTES" in os.environ:
        quota_env["default_org_public_quota_bytes"] = _parse_quota(
            os.environ.get("CN_MODEL_HUB_DEFAULT_ORG_PUBLIC_QUOTA_BYTES")
        )
    if quota_env:
        config_from_env["quota"] = quota_env

    # Cache (L2 / Valkey)
    cache_env = {}
    if "CN_MODEL_HUB_CACHE_ENABLED" in os.environ:
        cache_env["enabled"] = (
            os.environ["CN_MODEL_HUB_CACHE_ENABLED"].lower() == "true"
        )
    if "CN_MODEL_HUB_CACHE_URL" in os.environ:
        cache_env["url"] = os.environ["CN_MODEL_HUB_CACHE_URL"]
        # Implicit-enable: if the operator set a CACHE_URL but did not
        # set CACHE_ENABLED, treat the URL as opt-in. This matters for
        # dev environments whose .env.dev predates the cache feature —
        # they get a fresh CN_MODEL_HUB_CACHE_URL line (e.g. via
        # ``cp .env.dev.example .env.dev``) without remembering to also
        # set ENABLED. Explicit ``CN_MODEL_HUB_CACHE_ENABLED=false`` still
        # wins over this default.
        if "CN_MODEL_HUB_CACHE_ENABLED" not in os.environ:
            cache_env["enabled"] = True
    if "CN_MODEL_HUB_CACHE_NAMESPACE" in os.environ:
        cache_env["namespace"] = os.environ["CN_MODEL_HUB_CACHE_NAMESPACE"]
    if "CN_MODEL_HUB_CACHE_DEFAULT_TTL" in os.environ:
        cache_env["default_ttl_seconds"] = int(
            os.environ["CN_MODEL_HUB_CACHE_DEFAULT_TTL"]
        )
    if "CN_MODEL_HUB_CACHE_JITTER_FRACTION" in os.environ:
        cache_env["jitter_fraction"] = float(
            os.environ["CN_MODEL_HUB_CACHE_JITTER_FRACTION"]
        )
    if "CN_MODEL_HUB_CACHE_MAX_CONNECTIONS" in os.environ:
        cache_env["max_connections"] = int(
            os.environ["CN_MODEL_HUB_CACHE_MAX_CONNECTIONS"]
        )
    if "CN_MODEL_HUB_CACHE_SOCKET_TIMEOUT" in os.environ:
        cache_env["socket_timeout_seconds"] = float(
            os.environ["CN_MODEL_HUB_CACHE_SOCKET_TIMEOUT"]
        )
    if "CN_MODEL_HUB_CACHE_SOCKET_CONNECT_TIMEOUT" in os.environ:
        cache_env["socket_connect_timeout_seconds"] = float(
            os.environ["CN_MODEL_HUB_CACHE_SOCKET_CONNECT_TIMEOUT"]
        )
    if cache_env:
        config_from_env["cache"] = cache_env

    # Search (Meilisearch)
    search_env = {}
    if "CN_MODEL_HUB_MEILISEARCH_ENABLED" in os.environ:
        search_env["meilisearch_enabled"] = (
            os.environ["CN_MODEL_HUB_MEILISEARCH_ENABLED"].lower() == "true"
        )
    if "CN_MODEL_HUB_MEILISEARCH_URL" in os.environ:
        search_env["meilisearch_url"] = os.environ["CN_MODEL_HUB_MEILISEARCH_URL"]
        if "CN_MODEL_HUB_MEILISEARCH_ENABLED" not in os.environ:
            search_env["meilisearch_enabled"] = True
    if "CN_MODEL_HUB_MEILISEARCH_API_KEY" in os.environ:
        search_env["meilisearch_api_key"] = os.environ[
            "CN_MODEL_HUB_MEILISEARCH_API_KEY"
        ]
    if "CN_MODEL_HUB_MEILISEARCH_TIMEOUT" in os.environ:
        search_env["meilisearch_timeout_seconds"] = int(
            os.environ["CN_MODEL_HUB_MEILISEARCH_TIMEOUT"]
        )
    if "CN_MODEL_HUB_MEILISEARCH_TASK_TIMEOUT_MS" in os.environ:
        search_env["meilisearch_task_timeout_ms"] = int(
            os.environ["CN_MODEL_HUB_MEILISEARCH_TASK_TIMEOUT_MS"]
        )
    if search_env:
        config_from_env["search"] = search_env

    # Assistant
    assistant_env = {}
    if "CN_MODEL_HUB_ASSISTANT_LLM_API_KEY" in os.environ:
        assistant_env["llm_api_key"] = os.environ[
            "CN_MODEL_HUB_ASSISTANT_LLM_API_KEY"
        ]
    if "CN_MODEL_HUB_ASSISTANT_LLM_PROVIDER" in os.environ:
        assistant_env["llm_provider"] = os.environ[
            "CN_MODEL_HUB_ASSISTANT_LLM_PROVIDER"
        ]
    if "CN_MODEL_HUB_ASSISTANT_LLM_BASE_URL" in os.environ:
        assistant_env["llm_base_url"] = os.environ[
            "CN_MODEL_HUB_ASSISTANT_LLM_BASE_URL"
        ]
    if "CN_MODEL_HUB_ASSISTANT_LLM_MODEL" in os.environ:
        assistant_env["llm_model"] = os.environ["CN_MODEL_HUB_ASSISTANT_LLM_MODEL"]
    if "CN_MODEL_HUB_ASSISTANT_LLM_TIMEOUT" in os.environ:
        assistant_env["llm_timeout_seconds"] = int(
            os.environ["CN_MODEL_HUB_ASSISTANT_LLM_TIMEOUT"]
        )
    if "CN_MODEL_HUB_ASSISTANT_EMBEDDING_ENABLED" in os.environ:
        assistant_env["embedding_enabled"] = (
            os.environ["CN_MODEL_HUB_ASSISTANT_EMBEDDING_ENABLED"].lower() == "true"
        )
    if "CN_MODEL_HUB_ASSISTANT_EMBEDDING_MODEL" in os.environ:
        assistant_env["embedding_model"] = os.environ[
            "CN_MODEL_HUB_ASSISTANT_EMBEDDING_MODEL"
        ]
    if "CN_MODEL_HUB_ASSISTANT_MAX_KNOWLEDGE_CHUNKS" in os.environ:
        assistant_env["max_knowledge_chunks"] = int(
            os.environ["CN_MODEL_HUB_ASSISTANT_MAX_KNOWLEDGE_CHUNKS"]
        )
    if assistant_env:
        config_from_env["assistant"] = assistant_env

    # Fallback
    fallback_env = {}
    if "CN_MODEL_HUB_FALLBACK_ENABLED" in os.environ:
        fallback_env["enabled"] = (
            os.environ["CN_MODEL_HUB_FALLBACK_ENABLED"].lower() == "true"
        )
    if "CN_MODEL_HUB_FALLBACK_CACHE_TTL" in os.environ:
        fallback_env["cache_ttl_seconds"] = int(
            os.environ["CN_MODEL_HUB_FALLBACK_CACHE_TTL"]
        )
    if "CN_MODEL_HUB_FALLBACK_TIMEOUT" in os.environ:
        fallback_env["timeout_seconds"] = int(os.environ["CN_MODEL_HUB_FALLBACK_TIMEOUT"])
    if "CN_MODEL_HUB_FALLBACK_MAX_CONCURRENT" in os.environ:
        fallback_env["max_concurrent_requests"] = int(
            os.environ["CN_MODEL_HUB_FALLBACK_MAX_CONCURRENT"]
        )
    if "CN_MODEL_HUB_FALLBACK_REQUIRE_AUTH" in os.environ:
        fallback_env["require_auth"] = (
            os.environ["CN_MODEL_HUB_FALLBACK_REQUIRE_AUTH"].lower() == "true"
        )
    if "CN_MODEL_HUB_FALLBACK_SOURCES" in os.environ:
        fallback_env["sources"] = _parse_fallback_sources(
            os.environ.get("CN_MODEL_HUB_FALLBACK_SOURCES")
        )
    if fallback_env:
        config_from_env["fallback"] = fallback_env

    # App
    app_env = {}
    if "CN_MODEL_HUB_BASE_URL" in os.environ:
        app_env["base_url"] = os.environ["CN_MODEL_HUB_BASE_URL"]
    if "CN_MODEL_HUB_INTERNAL_BASE_URL" in os.environ:
        app_env["internal_base_url"] = os.environ["CN_MODEL_HUB_INTERNAL_BASE_URL"]
    if "CN_MODEL_HUB_API_BASE" in os.environ:
        app_env["api_base"] = os.environ["CN_MODEL_HUB_API_BASE"]
    if "CN_MODEL_HUB_DISABLE_DATASET_VIEWER" in os.environ:
        app_env["disable_dataset_viewer"] = (
            os.environ["CN_MODEL_HUB_DISABLE_DATASET_VIEWER"].lower() == "true"
        )
    if "CN_MODEL_HUB_DB_BACKEND" in os.environ:
        app_env["db_backend"] = os.environ["CN_MODEL_HUB_DB_BACKEND"]
    if "CN_MODEL_HUB_DATABASE_URL" in os.environ:
        app_env["database_url"] = os.environ["CN_MODEL_HUB_DATABASE_URL"]
    if "CN_MODEL_HUB_DATABASE_KEY" in os.environ:
        app_env["database_key"] = os.environ["CN_MODEL_HUB_DATABASE_KEY"]
    if "CN_MODEL_HUB_LFS_THRESHOLD_BYTES" in os.environ:
        app_env["lfs_threshold_bytes"] = int(
            os.environ["CN_MODEL_HUB_LFS_THRESHOLD_BYTES"]
        )
    if "CN_MODEL_HUB_LFS_MULTIPART_THRESHOLD_BYTES" in os.environ:
        app_env["lfs_multipart_threshold_bytes"] = int(
            os.environ["CN_MODEL_HUB_LFS_MULTIPART_THRESHOLD_BYTES"]
        )
    if "CN_MODEL_HUB_LFS_MULTIPART_CHUNK_SIZE_BYTES" in os.environ:
        app_env["lfs_multipart_chunk_size_bytes"] = int(
            os.environ["CN_MODEL_HUB_LFS_MULTIPART_CHUNK_SIZE_BYTES"]
        )
    if "CN_MODEL_HUB_LFS_KEEP_VERSIONS" in os.environ:
        app_env["lfs_keep_versions"] = int(os.environ["CN_MODEL_HUB_LFS_KEEP_VERSIONS"])
    if "CN_MODEL_HUB_LFS_AUTO_GC" in os.environ:
        app_env["lfs_auto_gc"] = os.environ["CN_MODEL_HUB_LFS_AUTO_GC"].lower() == "true"
    if "CN_MODEL_HUB_SITE_NAME" in os.environ:
        app_env["site_name"] = os.environ["CN_MODEL_HUB_SITE_NAME"]
    if "CN_MODEL_HUB_SPACE_RUNTIME_DIR" in os.environ:
        app_env["space_runtime_dir"] = os.environ["CN_MODEL_HUB_SPACE_RUNTIME_DIR"]
    if "CN_MODEL_HUB_SPACE_RUNTIME_BACKEND" in os.environ:
        app_env["space_runtime_backend"] = os.environ[
            "CN_MODEL_HUB_SPACE_RUNTIME_BACKEND"
        ]
    if "CN_MODEL_HUB_SPACE_RUNTIME_INSTALL_REQUIREMENTS" in os.environ:
        app_env["space_runtime_install_requirements"] = (
            os.environ["CN_MODEL_HUB_SPACE_RUNTIME_INSTALL_REQUIREMENTS"].lower()
            == "true"
        )
    if "CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_BASE_URL" in os.environ:
        app_env["space_runtime_remote_base_url"] = os.environ[
            "CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_BASE_URL"
        ]
    if "CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_API_KEY" in os.environ:
        app_env["space_runtime_remote_api_key"] = os.environ[
            "CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_API_KEY"
        ]
    if "CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_UPLOAD_METHOD" in os.environ:
        app_env["space_runtime_remote_upload_method"] = os.environ[
            "CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_UPLOAD_METHOD"
        ]
    if "CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_SSH_ALIAS" in os.environ:
        app_env["space_runtime_remote_ssh_alias"] = os.environ[
            "CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_SSH_ALIAS"
        ]
    if "CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_ROOT" in os.environ:
        app_env["space_runtime_remote_root"] = os.environ[
            "CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_ROOT"
        ]
    if "CN_MODEL_HUB_MLFLOW_TRACKING_URI" in os.environ:
        app_env["mlflow_tracking_uri"] = os.environ[
            "CN_MODEL_HUB_MLFLOW_TRACKING_URI"
        ]
    if "MLFLOW_TRACKING_URI" in os.environ:
        app_env["mlflow_tracking_uri"] = os.environ["MLFLOW_TRACKING_URI"]
    if "CN_MODEL_HUB_DEBUG_LOG_PAYLOADS" in os.environ:
        app_env["debug_log_payloads"] = (
            os.environ["CN_MODEL_HUB_DEBUG_LOG_PAYLOADS"].lower() == "true"
        )
    if "CN_MODEL_HUB_LOG_LEVEL" in os.environ:
        app_env["log_level"] = os.environ["CN_MODEL_HUB_LOG_LEVEL"]
    if "CN_MODEL_HUB_LOG_FORMAT" in os.environ:
        app_env["log_format"] = os.environ["CN_MODEL_HUB_LOG_FORMAT"]
    if "CN_MODEL_HUB_LOG_DIR" in os.environ:
        app_env["log_dir"] = os.environ["CN_MODEL_HUB_LOG_DIR"]
    if app_env:
        config_from_env["app"] = app_env

    # 4. Merge: Start with file config, then recursively update with env config
    merged_config = update_recursive(config_from_file, config_from_env)

    # 5. Instantiate config models, allowing Pydantic to handle defaults
    s3_config = S3Config(**merged_config.get("s3", {}))
    lakefs_config = LakeFSConfig(**merged_config.get("lakefs", {}))
    smtp_config = SMTPConfig(**merged_config.get("smtp", {}))
    auth_config = AuthConfig(**merged_config.get("auth", {}))
    quota_config = QuotaConfig(**merged_config.get("quota", {}))
    fallback_config = FallbackConfig(**merged_config.get("fallback", {}))
    cache_config = CacheConfig(**merged_config.get("cache", {}))
    search_config = SearchConfig(**merged_config.get("search", {}))
    assistant_config = AssistantConfig(**merged_config.get("assistant", {}))
    app_config = AppConfig(**merged_config.get("app", {}))

    return Config(
        s3=s3_config,
        lakefs=lakefs_config,
        smtp=smtp_config,
        auth=auth_config,
        quota=quota_config,
        fallback=fallback_config,
        cache=cache_config,
        search=search_config,
        assistant=assistant_config,
        app=app_config,
    )


cfg = load_config()

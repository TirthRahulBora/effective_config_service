import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent

DEFAULTS: dict[str, Any] = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

INT_KEYS = {"port", "workers"}
BOOL_KEYS = {"debug"}
KNOWN_KEYS = set(DEFAULTS)


def coerce(key: str, value: Any) -> Any:
    if key in INT_KEYS:
        return int(value)
    if key in BOOL_KEYS:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"true", "1", "yes", "on"}
    if value is None:
        return ""
    return str(value)


def normalize_key(key: str) -> str:
    key = key.strip()
    if key.upper() == "NUM_WORKERS":
        return "workers"
    return key.lower()


def apply_layer(target: dict[str, Any], values: dict[str, Any]) -> None:
    for raw_key, value in values.items():
        if value is None:
            continue
        key = normalize_key(str(raw_key))
        if key in KNOWN_KEYS:
            target[key] = coerce(key, value)


def load_effective_config(overrides: list[str] | None) -> dict[str, Any]:
    config = dict(DEFAULTS)

    # Layer 2: environment-specific YAML. The assigned development YAML is empty.
    env_name = os.getenv("APP_ENV", "development")
    yaml_path = BASE_DIR / f"config.{env_name}.yaml"
    if yaml_path.exists():
        with yaml_path.open("r", encoding="utf-8") as handle:
            yaml_values = yaml.safe_load(handle) or {}
        if isinstance(yaml_values, dict):
            apply_layer(config, yaml_values)

    # Layer 3: .env file, independently read so OS variables don't alter this layer.
    env_file_values = dotenv_values(BASE_DIR / ".env")
    apply_layer(config, dict(env_file_values))

    # Layer 4: OS environment variables with APP_ prefix.
    os_values: dict[str, Any] = {}
    for env_key, value in os.environ.items():
        if env_key.startswith("APP_") and env_key != "APP_ENV":
            os_values[env_key[4:].lower()] = value
    apply_layer(config, os_values)

    # Highest precedence: repeated CLI-style query parameters ?set=key=value
    for item in overrides or []:
        if "=" not in item:
            continue
        raw_key, value = item.split("=", 1)
        key = normalize_key(raw_key)
        if key in KNOWN_KEYS:
            config[key] = coerce(key, value)

    # Never expose the configured secret.
    config["api_key"] = "****"
    return config


app = FastAPI(title="Effective Configuration Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health() -> dict[str, str]:
    return {"service": "effective-config", "status": "ok"}


@app.get("/effective-config")
def effective_config(set: list[str] | None = Query(default=None)) -> dict[str, Any]:
    try:
        return load_effective_config(set)
    except (ValueError, TypeError):
        # Invalid numeric overrides should not crash the process.
        # Use the normal layer values if a supplied override cannot be coerced.
        safe_overrides = []
        for item in set or []:
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            try:
                coerce(normalize_key(key), value)
                safe_overrides.append(item)
            except (ValueError, TypeError):
                continue
        return load_effective_config(safe_overrides)

"""SINU Auto-Enrollment — configuration loading."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SinusSettings:
    """Typed settings for the SINU automation."""

    # SINU connection
    url: str = "https://sinu.usc.edu.co:8443/sinugwt/"
    username: str = ""
    password: str = ""

    # Target course
    course_code: str = "ISI51"
    group_prefix: str = "PIG"
    require_no_conflict: bool = True

    # Fixed schedule (conflict sources): list of {name, days[], time}
    fixed_schedule: list = field(default_factory=list)

    # Enrollment behavior
    auto_enroll: bool = True
    max_attempts: int = 3
    watch_interval: int = 1800  # seconds


def _load_env(env_path: str) -> dict:
    """Load KEY=VALUE pairs from a .env file (simple parser, no deps)."""
    env: dict = {}
    p = Path(env_path)
    if not p.exists():
        return env
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def load_settings(config_path: str = "config/settings.yaml", env_path: str = ".env") -> SinusSettings:
    """Load settings from YAML + .env + real environment (env wins)."""
    raw: dict = {}
    p = Path(config_path)
    if p.exists():
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    env = _load_env(env_path)
    s = SinusSettings()

    # SINU section
    sinu_cfg = raw.get("sinu", {})
    s.url = env.get("SINU_URL") or os.getenv("SINU_URL") or sinu_cfg.get("url", s.url)
    s.username = env.get("SINU_USERNAME") or os.getenv("SINU_USERNAME") or ""
    s.password = env.get("SINU_PASSWORD") or os.getenv("SINU_PASSWORD") or ""

    # Target section
    target = raw.get("target", {})
    s.course_code = target.get("course_code", s.course_code)
    s.group_prefix = target.get("group_prefix", s.group_prefix)
    s.require_no_conflict = target.get("require_no_conflict", s.require_no_conflict)
    s.fixed_schedule = target.get("fixed_schedule", [])

    # Enroll section
    enroll = raw.get("enroll", {})
    s.auto_enroll = enroll.get("auto", s.auto_enroll)
    s.max_attempts = enroll.get("max_attempts", s.max_attempts)
    s.watch_interval = enroll.get("wait_between_checks", s.watch_interval)

    if not s.username or not s.password:
        raise ValueError(
            "Missing SINU credentials. Set SINU_USERNAME and SINU_PASSWORD "
            "in your .env file (see config/example.env)."
        )

    return s

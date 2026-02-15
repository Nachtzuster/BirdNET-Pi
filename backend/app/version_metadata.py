"""Version metadata loader for BirdNET-Pibird.

Reads machine-friendly release metadata from versions.md.
"""
from __future__ import annotations

import os
import re
from typing import Dict

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
HASH_RE = re.compile(r"^[0-9a-f]{7,40}$", re.IGNORECASE)


def _default_metadata() -> Dict[str, str]:
    return {
        "service_version": "unknown",
        "git_hash": "unknown",
        "git_branch": "unknown",
        "api_version": "1.0.0",
        "build_date_utc": "unknown",
        "changelog_file": "version.md",
    }


def read_version_metadata(base_path: str) -> Dict[str, str]:
    """Load version metadata from versions.md.

    Expected format (line-based):
      key: value
    Comment lines starting with '#' are ignored.
    """
    metadata = _default_metadata()
    versions_path = os.path.join(base_path, "versions.md")

    if not os.path.exists(versions_path):
        return metadata

    try:
        with open(versions_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key in metadata and value:
                    metadata[key] = value
    except Exception:
        return metadata

    return metadata


def normalized_service_version(metadata: Dict[str, str]) -> str:
    """Return a concise, display-safe service version."""
    value = metadata.get("service_version", "unknown")
    return value if SEMVER_RE.match(value) else "unknown"


def normalized_git_hash(metadata: Dict[str, str]) -> str:
    """Return normalized short hash or unknown."""
    value = metadata.get("git_hash", "unknown")
    if HASH_RE.match(value):
        return value[:12]
    return "unknown"

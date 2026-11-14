"""Project profiles: small, declarative defaults per technology family.

A profile is a YAML file under ``harness/assets/profiles``. It contributes
detection markers, candidate verification commands (only kept when their
marker files exist), short agent guidance and ignore patterns. Profiles
never copy files into a consumer repository.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from harness.core.assets import asset_path, list_assets


@dataclass
class VerificationCandidate:
    name: str
    run: str
    when: list[str] = field(default_factory=list)   # any of these path globs / "file:substring" markers must match
    description: str = ""


@dataclass
class Profile:
    name: str
    title: str
    description: str
    detect: list[dict] = field(default_factory=list)      # [{glob: ..., weight: n}]
    guidance: str = ""
    testing: str = ""
    verification: list[VerificationCandidate] = field(default_factory=list)
    doc_types: list[str] = field(default_factory=list)
    reference_categories: list[str] = field(default_factory=list)
    ignore: list[str] = field(default_factory=list)
    structure: list[str] = field(default_factory=list)


def _load_profile(path: Path) -> Profile:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Profile(
        name=data["name"],
        title=data.get("title", data["name"]),
        description=data.get("description", ""),
        detect=data.get("detect", []) or [],
        guidance=(data.get("guidance") or "").strip(),
        testing=(data.get("testing") or "").strip(),
        verification=[VerificationCandidate(**v) for v in data.get("verification", []) or []],
        doc_types=data.get("doc_types", []) or [],
        reference_categories=data.get("reference_categories", []) or [],
        ignore=data.get("ignore", []) or [],
        structure=data.get("structure", []) or [],
    )


@lru_cache(maxsize=1)
def load_profiles() -> dict[str, Profile]:
    profiles: dict[str, Profile] = {}
    for p in list_assets("profiles", pattern="*.yaml"):
        prof = _load_profile(p)
        profiles[prof.name] = prof
    return profiles


def available_profiles() -> list[str]:
    return sorted(load_profiles())


def get_profile(name: str) -> Profile:
    profiles = load_profiles()
    if name not in profiles:
        raise KeyError(f"unknown profile {name!r}; available: {', '.join(sorted(profiles))}")
    return profiles[name]


def profile_dir() -> Path:
    return asset_path("profiles")

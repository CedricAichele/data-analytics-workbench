"""Reusable mapping profile helpers for recurring source files."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import MutableMapping
from datetime import datetime, timezone
from io import BytesIO
import hashlib
import json
import re
from typing import Any

import streamlit as st


MAPPING_PROFILES_KEY = "mapping_profiles"


@dataclass(frozen=True)
class MappingProfileValidation:
    is_valid: bool
    missing_columns: list[str]
    messages: list[str]


def initialize_mapping_profiles(state: MutableMapping[str, Any] | None = None) -> None:
    """Initialize session storage for reusable mapping profiles."""
    current = _state(state)
    current.setdefault(MAPPING_PROFILES_KEY, {})


def save_mapping_profile(
    *,
    profile_name: str,
    template_id: str,
    mapping: dict[str, str | None],
    notes: str = "",
    state: MutableMapping[str, Any] | None = None,
) -> tuple[str, bool]:
    """Save or activate a mapping profile in the current session."""
    current = _state(state)
    initialize_mapping_profiles(current)
    cleaned_name = profile_name.strip() or "Mapping Profile"
    cleaned_mapping = {field: column for field, column in mapping.items() if column}
    if not cleaned_mapping:
        raise ValueError("Save a valid mapping before creating a Mapping Profile.")

    signature = _profile_signature(template_id, cleaned_mapping)
    for profile_id, profile in current[MAPPING_PROFILES_KEY].items():
        if profile.get("signature") == signature and profile.get("profile_name") == cleaned_name:
            return profile_id, False

    profile_id = _new_profile_id(cleaned_name, current[MAPPING_PROFILES_KEY])
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    current[MAPPING_PROFILES_KEY][profile_id] = {
        "profile_id": profile_id,
        "profile_name": cleaned_name,
        "template_id": template_id,
        "mapping": cleaned_mapping,
        "notes": notes.strip(),
        "created_at": timestamp,
        "signature": signature,
    }
    return profile_id, True


def list_mapping_profiles(
    template_id: str | None = None,
    state: MutableMapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return saved mapping profiles, optionally filtered by template."""
    current = _state(state)
    initialize_mapping_profiles(current)
    profiles = list(current[MAPPING_PROFILES_KEY].values())
    if template_id:
        profiles = [profile for profile in profiles if profile.get("template_id") == template_id]
    return sorted(profiles, key=lambda profile: profile.get("profile_name", ""))


def get_mapping_profile(profile_id: str, state: MutableMapping[str, Any] | None = None) -> dict[str, Any] | None:
    """Return one mapping profile by id."""
    current = _state(state)
    initialize_mapping_profiles(current)
    profile = current[MAPPING_PROFILES_KEY].get(profile_id)
    return None if profile is None else dict(profile)


def validate_mapping_profile(profile: dict[str, Any], columns: list[str]) -> MappingProfileValidation:
    """Validate whether a profile can be applied to the active working dataset."""
    mapping = dict(profile.get("mapping", {}))
    available = set(columns)
    missing = sorted({column for column in mapping.values() if column and column not in available})
    if missing:
        return MappingProfileValidation(
            is_valid=False,
            missing_columns=missing,
            messages=[f"Missing source columns: {', '.join(missing)}."],
        )
    return MappingProfileValidation(
        is_valid=True,
        missing_columns=[],
        messages=["Mapping Profile is compatible with the active dataset."],
    )


def apply_mapping_profile(profile: dict[str, Any], columns: list[str]) -> dict[str, str | None]:
    """Return a profile mapping after validating active dataset compatibility."""
    validation = validate_mapping_profile(profile, columns)
    if not validation.is_valid:
        raise ValueError(validation.messages[0])
    return dict(profile.get("mapping", {}))


def build_mapping_profile_backup(profile: dict[str, Any]) -> bytes:
    """Serialize a Mapping Profile Backup as bytes."""
    payload = {
        "profile_name": profile.get("profile_name", "Mapping Profile"),
        "template_id": profile.get("template_id"),
        "mapping": profile.get("mapping", {}),
        "notes": profile.get("notes", ""),
        "created_at": profile.get("created_at", ""),
    }
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")


def load_mapping_profile_backup(uploaded_file: bytes | bytearray | BytesIO | Any) -> dict[str, Any]:
    """Load a Mapping Profile Backup created by the Workbench."""
    if isinstance(uploaded_file, bytes | bytearray):
        raw = bytes(uploaded_file)
    elif hasattr(uploaded_file, "getvalue"):
        raw = uploaded_file.getvalue()
    else:
        raw = uploaded_file.read()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError("Mapping Profile Backup could not be read.") from exc
    required = {"profile_name", "template_id", "mapping"}
    if not required.issubset(payload):
        raise ValueError("Mapping Profile Backup is missing required profile details.")
    return {
        "profile_name": str(payload.get("profile_name") or "Mapping Profile"),
        "template_id": str(payload.get("template_id") or ""),
        "mapping": dict(payload.get("mapping") or {}),
        "notes": str(payload.get("notes") or ""),
        "created_at": str(payload.get("created_at") or ""),
    }


def import_mapping_profile(
    profile: dict[str, Any],
    state: MutableMapping[str, Any] | None = None,
) -> tuple[str, bool]:
    """Store a loaded Mapping Profile Backup in the current session."""
    return save_mapping_profile(
        profile_name=profile.get("profile_name", "Mapping Profile"),
        template_id=profile.get("template_id", ""),
        mapping=dict(profile.get("mapping") or {}),
        notes=profile.get("notes", ""),
        state=state,
    )


def _state(state: MutableMapping[str, Any] | None = None) -> MutableMapping[str, Any]:
    return st.session_state if state is None else state


def _profile_signature(template_id: str, mapping: dict[str, str | None]) -> str:
    payload = json.dumps({"template_id": template_id, "mapping": mapping}, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _new_profile_id(profile_name: str, profiles: dict[str, Any]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", profile_name.lower()).strip("-") or "mapping-profile"
    candidate = base
    suffix = 2
    while candidate in profiles:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate

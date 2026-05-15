"""Lineage, intended-use, and reproducibility records for Axiom runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import platform
from typing import Any

import pandas as pd


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return sorted((_json_safe(item) for item in value), key=str)
    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def dataframe_fingerprint(df: pd.DataFrame) -> str:
    schema = [(str(c), str(df[c].dtype)) for c in df.columns]
    row_hashes = pd.util.hash_pandas_object(df, index=True).to_numpy().tobytes()
    digest = hashlib.sha256()
    digest.update(_stable_json(schema).encode("utf-8"))
    digest.update(row_hashes)
    return digest.hexdigest()


@dataclass(frozen=True)
class IntendedUse:
    purpose: str
    users: list[str] = field(default_factory=list)
    prohibited_uses: list[str] = field(default_factory=list)
    recipient: str | None = None
    jurisdiction: list[str] = field(default_factory=list)
    retention_days: int | None = None


@dataclass
class RunManifest:
    run_id: str
    created_at: str
    package_version: str
    generator: str
    random_state: int | None
    input_fingerprint: str
    output_fingerprint: str
    configuration: dict[str, Any]
    configuration_fingerprint: str
    input_rows: int
    output_rows: int
    columns: list[str]
    intended_use: IntendedUse
    release: dict[str, Any]
    environment: dict[str, str]
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["intended_use"] = asdict(self.intended_use)
        return payload

    @classmethod
    def build(
        cls,
        *,
        package_version: str,
        generator: str,
        random_state: int | None,
        input_data: pd.DataFrame,
        output_data: pd.DataFrame,
        configuration: dict[str, Any],
        intended_use: IntendedUse,
        release: dict[str, Any],
        limitations: list[str] | None = None,
    ) -> "RunManifest":
        input_hash = dataframe_fingerprint(input_data)
        output_hash = dataframe_fingerprint(output_data)
        safe_configuration = _json_safe(configuration)
        config_hash = hashlib.sha256(_stable_json(safe_configuration).encode("utf-8")).hexdigest()
        run_id = hashlib.sha256(f"{input_hash}:{output_hash}:{config_hash}".encode("utf-8")).hexdigest()[:24]
        return cls(
            run_id=run_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            package_version=package_version,
            generator=generator,
            random_state=random_state,
            input_fingerprint=input_hash,
            output_fingerprint=output_hash,
            configuration=safe_configuration,
            configuration_fingerprint=config_hash,
            input_rows=len(input_data),
            output_rows=len(output_data),
            columns=[str(c) for c in output_data.columns],
            intended_use=intended_use,
            release=release,
            environment={"python": platform.python_version(), "pandas": pd.__version__, "platform": platform.platform()},
            limitations=list(limitations or []),
        )

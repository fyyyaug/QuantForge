"""Stable scientific artifacts independent of run UUIDs and wall-clock time."""

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


def plain(value):
    if isinstance(value, BaseModel):
        return plain(value.model_dump())
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Nonfinite decimal cannot be serialized")
        # Do not use Decimal.normalize(): it depends on ambient precision.
        text = format(value, "f")
        text = text.rstrip("0").rstrip(".") if "." in text else text
        return "0" if value == 0 else text
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def canonical(value) -> str:
    return json.dumps(plain(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

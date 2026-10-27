"""Lossless JSON representations for MySQL values and reproducible hashing."""

from __future__ import annotations

import base64
import math
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any


def encode_value(value: Any) -> list:
    if value is None:
        return ["null"]
    if isinstance(value, bool):
        return ["number", "1" if value else "0"]
    if isinstance(value, (int, Decimal)):
        number = Decimal(value)
        if not number.is_finite():
            raise ValueError("Non-finite database numeric value")
        text = format(number, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return ["number", "0" if number == 0 else text]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite database floating value")
        return ["float", value.hex()]
    if isinstance(value, str):
        return ["text", value]
    if isinstance(value, bytes):
        return ["bytes", base64.b64encode(value).decode("ascii")]
    if isinstance(value, datetime):
        return ["datetime", value.isoformat(timespec="microseconds")]
    if isinstance(value, date):
        return ["date", value.isoformat()]
    if isinstance(value, time):
        return ["time", value.isoformat(timespec="microseconds")]
    if isinstance(value, timedelta):
        return ["duration_microseconds", (value.days * 86400 + value.seconds) * 1000000 + value.microseconds]
    raise TypeError("Unsupported database value type")


def encode_row(row: tuple) -> list:
    return [encode_value(value) for value in row]


def decode_value(value: list):
    """Inverse of the audited tagged representation; never eval/pickle."""
    if not isinstance(value, list) or not value or not isinstance(value[0], str):
        raise ValueError("Invalid tagged result value")
    tag = value[0]
    if tag == "null" and len(value) == 1:
        return None
    if len(value) != 2:
        raise ValueError("Invalid tagged result arity")
    data = value[1]
    if tag == "number" and isinstance(data, str):
        result = Decimal(data)
        if result.is_finite(): return result
    elif tag == "float" and isinstance(data, str):
        result = float.fromhex(data)
        if math.isfinite(result): return result
    elif tag == "text" and isinstance(data, str): return data
    elif tag == "bytes" and isinstance(data, str): return base64.b64decode(data, validate=True)
    elif tag == "datetime" and isinstance(data, str): return datetime.fromisoformat(data)
    elif tag == "date" and isinstance(data, str): return date.fromisoformat(data)
    elif tag == "time" and isinstance(data, str): return time.fromisoformat(data)
    elif tag == "duration_microseconds" and type(data) is int: return timedelta(microseconds=data)
    raise ValueError("Unsupported or non-finite tagged result value")


"""Private serialization helpers for the catalog domain."""

import json
from typing import Any, List, Optional


def encode_list(value: Any) -> Optional[str]:
    """Encode a Python list into a JSON string, keeping strings or None as-is."""
    if isinstance(value, list):
        return json.dumps(value)
    return value


def decode_list(value: Any) -> List[str]:
    """Decode a JSON string or return list directly, defaulting to empty list on error."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            res = json.loads(value)
            if isinstance(res, list):
                return res
            return [res] if res else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def encode_record_lists(data: dict) -> dict:
    """Encode record JSON lists (authors, illustrators, keywords) for DB storage."""
    res = data.copy()
    for field in ["authors", "illustrators", "keywords"]:
        if field in res:
            res[field] = encode_list(res[field])
    return res

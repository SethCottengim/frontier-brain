"""Stdlib-only YAML frontmatter parser for flat decision records."""

from __future__ import annotations

import re


def parse(text: str) -> tuple[dict, str]:
    """Parse ``---`` fenced YAML frontmatter + body from *text*.

    Returns (metadata_dict, body_string). Raises ValueError on bad fences.
    """
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("missing --- fenced frontmatter")
    meta = _parse_yaml_flat(parts[1])
    body = parts[2].strip()
    return meta, body


def _parse_yaml_flat(raw: str) -> dict:
    result: dict = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)", line)
        if not m:
            continue
        key = m.group(1)
        val = m.group(2).strip()
        result[key] = _parse_value(val)
    return result


def _parse_value(val: str):
    if not val or val in ("null", "~"):
        return None

    if val.startswith("[") and val.endswith("]"):
        return _parse_inline_list(val)

    if val in ("true", "True", "yes", "on"):
        return True
    if val in ("false", "False", "no", "off"):
        return False

    try:
        return int(val)
    except ValueError:
        pass

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", val):
        return val

    if len(val) >= 2 and val[0] in ('"', "'") and val[-1] == val[0]:
        return val[1:-1]

    return val


def _parse_inline_list(val: str) -> list:
    inner = val[1:-1].strip()
    if not inner:
        return []
    items = []
    for item in inner.split(","):
        item = item.strip()
        if len(item) >= 2 and item[0] in ('"', "'") and item[-1] == item[0]:
            item = item[1:-1]
        else:
            try:
                item = int(item)
            except ValueError:
                pass
        items.append(item)
    return items

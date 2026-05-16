"""Utility helpers."""

from formatters import ALL_FORMATS
from parsers import CitationData


FORMAT_KEYS = list(ALL_FORMATS.keys())


def detect_existing_format(cd: CitationData, pasted_text: str) -> str | None:
    """Return format name if the pasted text already matches that style."""
    return cd.detected_format


def convert_all(cd: CitationData) -> dict[str, str]:
    """Return a dict of {format_name: formatted_string} for all formats."""
    results = {}
    for name, fn in ALL_FORMATS.items():
        try:
            results[name] = fn(cd)
        except Exception as e:
            results[name] = f"[Hata: {e}]"
    return results

"""JSON persistence utilities for OCR outputs."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

DATE_PATTERN = "%Y%m%d_%H%M%S"

def build_output_path(output_dir: Path, name_hint: str) -> Path:
	"""Compose a timestamped output path within the output directory."""
	timestamp = datetime.utcnow().strftime(DATE_PATTERN)
	filename = f"{name_hint}_{timestamp}.json"
	return output_dir.joinpath(filename)

def dump_json(data: dict[str, Any], output_dir: Path, name_hint: str) -> Path:
	"""Persist a dictionary as formatted JSON in the output directory."""
	output_dir.mkdir(parents=True, exist_ok=True)
	path = build_output_path(output_dir, name_hint)
	path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
	return path

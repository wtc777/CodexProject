"""Utility helpers for working with input images."""

import base64
from pathlib import Path

def ensure_image_path(image: str | Path) -> Path:
	"""Validate that the provided path exists and points to a file."""
	path = Path(image).expanduser().resolve()
	if not path.exists():
		raise FileNotFoundError(f"Image path not found: {path}")
	if not path.is_file():
		raise ValueError(f"Image path is not a file: {path}")
	return path

def read_image_base64(path: Path) -> str:
	"""Read image bytes and encode them as base64 for HTTP payloads."""
	data = path.read_bytes()
	return base64.b64encode(data).decode("utf-8")

def read_image_bytes(path: Path) -> bytes:
	"""Read the raw bytes of an image."""
	return path.read_bytes()

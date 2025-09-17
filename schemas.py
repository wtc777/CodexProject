"""Pydantic schemas for normalized OCR responses."""


from typing import Literal

from pydantic import BaseModel

class OcrTextSpan(BaseModel):
	"""Represents a single OCR text segment from any provider."""
	text: str
	confidence: float | None = None
	polygon: list[tuple[float, float]] | None = None
	line_index: int | None = None

class OcrResult(BaseModel):
	"""Normalized OCR output for console display and persistence."""
	backend: Literal["aliyun", "qwen"]
	task: str | None
	image_path: str
	blocks: list[OcrTextSpan]
	full_text: str
	raw: dict

"""Smoke tests for OCR CLI scaffolding."""
from __future__ import annotations

from main import parse_arguments
from schemas import OcrResult, OcrTextSpan


def test_schema_construction() -> None:
	"""Ensure schemas can be instantiated with expected fields."""
	span = OcrTextSpan(text="hello", confidence=0.9, polygon=[(0.0, 1.0)], line_index=0)
	result = OcrResult(
		backend="aliyun",
		task="advanced",
		image_path="/tmp/image.png",
		blocks=[span],
		full_text="hello",
		raw={"sample": True},
	)
	assert result.full_text == "hello"
	assert result.blocks[0].text == "hello"


def test_cli_parser_defaults() -> None:
	"""Validate argument parser accepts expected switches."""
	args = parse_arguments(
		[
			"--backend",
			"qwen",
			"--image",
			"samples/sample.png",
			"--task",
			"table",
			"--min_conf",
			"0.7",
			"--outdir",
			"outputs",
			"--alltext_type",
			"general",
		]
	)
	assert args.backend == "qwen"
	assert args.task == "table"
	assert args.min_conf == 0.7
	assert args.alltext_type == "general"

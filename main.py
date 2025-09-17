"""Command-line interface for comparing OCR backends."""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from config import AppConfig, configure_logging, load_config
from providers.aliyun_ocr import AliyunOcrClient
from providers.qwen_ocr import QwenOcrClient
from utils.image_io import ensure_image_path
from utils.io_json import dump_json


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(description="Aliyun and Qwen OCR comparison CLI")
	parser.add_argument("--backend", choices=["aliyun", "qwen"], required=True, help="OCR backend to use")
	parser.add_argument("--image", required=True, help="Path to the image file")
	parser.add_argument("--task", choices=["document", "table", "general"], default="document", help="Qwen OCR task type")
	parser.add_argument("--min_conf", type=float, default=0.5, help="Minimum confidence threshold for text spans")
	parser.add_argument("--outdir", default="outputs", help="Directory to store JSON outputs")
	parser.add_argument(
		"--alltext_type",
		default="",
		help="Aliyun RecognizeAllText type (use to switch from RecognizeAdvanced)",
	)
	return parser.parse_args(argv)


def run(args: argparse.Namespace, config: AppConfig) -> dict[str, Any]:
	"""Execute OCR processing for the provided arguments."""
	image_path = ensure_image_path(args.image)
	output_dir = Path(args.outdir).expanduser().resolve()
	output_dir.mkdir(parents=True, exist_ok=True)

	if args.backend == "aliyun":
		if not config.aliyun:
			raise RuntimeError("Aliyun credentials are not configured.")
		client = AliyunOcrClient(config.aliyun)
		result = client.recognize(image_path=image_path, alltext_type=args.alltext_type or None, min_conf=args.min_conf)
		label = args.alltext_type or "advanced"
	else:
		if not config.dashscope:
			raise RuntimeError("DashScope API key is not configured.")
		client = QwenOcrClient(config.dashscope)
		task = args.task or "document"
		result = client.recognize(image_path=image_path, task=task, min_conf=args.min_conf)
		label = task

	json_payload = result.dict()
	json_payload["raw"] = result.raw

	filename_hint = f"{args.backend}_{label}"
	output_path = dump_json(json_payload, output_dir, filename_hint)
	logging.info("Saved OCR output to %s", output_path)
	print(json.dumps(json_payload, ensure_ascii=False, indent=2))
	return json_payload


def main(argv: list[str] | None = None) -> int:
	"""Entry point for the CLI application."""
	configure_logging()
	config = load_config()
	try:
		args = parse_arguments(argv)
		run(args, config)
	except Exception as exc:  # noqa: BLE001
		logging.exception("OCR processing failed: %s", exc)
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

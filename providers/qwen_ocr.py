"""DashScope Qwen OCR provider implementation."""


import base64
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from config import DashScopeCredentials
from schemas import OcrResult, OcrTextSpan
from utils.image_io import read_image_bytes

try:
	from dashscope.client.base_api import BaseApi
except ImportError:
	BaseApi = None  # type: ignore[assignment]

TASK_MODEL_MAP: dict[str, str] = {
	"document": "qwen-ocr-document",
	"table": "qwen-ocr-table",
	"general": "qwen-ocr-general",
}


@dataclass
class QwenOcrClient:
	"""Client wrapper around DashScope Qwen OCR tasks."""

	credentials: DashScopeCredentials
	retries: int = 3
	backoff: float = 1.5

	def __post_init__(self) -> None:
		self._logger = logging.getLogger(self.__class__.__name__)

	def recognize(self, image_path: Path, task: str, min_conf: float) -> OcrResult:
		if BaseApi is None:
			raise ImportError("DashScope SDK is not installed. Please install dashscope.")
		model = TASK_MODEL_MAP.get(task, TASK_MODEL_MAP["document"])
		payload = self._build_payload(image_path)
		response = self._execute(lambda: self._call_service(model, payload, task))
		raw = self._serialize_response(response)
		blocks = self._parse_blocks(raw)
		filtered = [block for block in blocks if block.confidence is None or block.confidence >= min_conf]
		full_text = "\n".join(block.text for block in filtered)
		return OcrResult(
			backend="qwen",
			task=task,
			image_path=str(image_path),
			blocks=filtered,
			full_text=full_text,
			raw=raw,
		)

	def _call_service(self, model: str, payload: dict[str, Any], task: str):
		if BaseApi is None:
			raise ImportError("DashScope SDK is not installed. Please install dashscope.")
		return BaseApi.call(
			model=model,
			input=payload,
			task_group="ocr",
			task=task,
			api_key=self.credentials.api_key,
			stream=False,
		)

	def _build_payload(self, path: Path) -> dict[str, Any]:
		image_bytes = read_image_bytes(path)
		image_b64 = base64.b64encode(image_bytes).decode("utf-8")
		return {
			"image": [
				{
					"data": image_b64,
					"format": path.suffix.lstrip(".") or "png",
				}
			]
		}

	def _execute(self, call: Callable[[], Any]):
		for attempt in range(1, self.retries + 1):
			try:
				response = call()
				if getattr(response, "status_code", 500) != 200:
					raise RuntimeError(getattr(response, "message", "Qwen OCR request failed."))
				return response
			except Exception as exc:  # noqa: BLE001
				wait = self.backoff ** attempt
				self._logger.warning("Qwen OCR call failed (attempt %s/%s): %s", attempt, self.retries, exc)
				if attempt == self.retries:
					raise
				time.sleep(wait)

	def _serialize_response(self, response: Any) -> dict[str, Any]:
		raw = {
			"status_code": getattr(response, "status_code", None),
			"request_id": getattr(response, "request_id", None),
			"code": getattr(response, "code", None),
			"message": getattr(response, "message", None),
			"output": getattr(response, "output", None),
			"usage": getattr(response, "usage", None),
		}
		if hasattr(response, "to_dict"):
			raw.update(response.to_dict())  # type: ignore[arg-type]
		return raw

	def _parse_blocks(self, raw: dict[str, Any]) -> list[OcrTextSpan]:
		output = raw.get("output")
		nodes = self._collect_text_nodes(output)
		blocks: list[OcrTextSpan] = []
		for index, node in enumerate(nodes):
			text = self._extract_text(node)
			if not text:
				continue
			confidence = self._extract_confidence(node)
			polygon = self._extract_polygon(node)
			blocks.append(OcrTextSpan(text=text, confidence=confidence, polygon=polygon, line_index=index))
		return blocks

	def _collect_text_nodes(self, data: Any) -> list[dict[str, Any]]:
		collected: list[dict[str, Any]] = []
		self._walk_nodes(data, collected)
		return collected

	def _walk_nodes(self, data: Any, collected: list[dict[str, Any]]) -> None:
		if isinstance(data, dict):
			if any(key in data for key in ("text", "content", "value")):
				collected.append(data)
			for value in data.values():
				self._walk_nodes(value, collected)
		elif isinstance(data, list):
			for item in data:
				self._walk_nodes(item, collected)

	def _extract_text(self, node: dict[str, Any]) -> str:
		for key in ("text", "content", "value"):
			value = node.get(key)
			if isinstance(value, str) and value.strip():
				return value.strip()
		return ""

	def _extract_confidence(self, node: dict[str, Any]) -> float | None:
		for key in ("confidence", "score", "probability", "prob"):
			value = node.get(key)
			if isinstance(value, (int, float)):
				return float(value)
		return None

	def _extract_polygon(self, node: dict[str, Any]) -> list[tuple[float, float]] | None:
		polygon = node.get("polygon") or node.get("points") or node.get("quad")
		if isinstance(polygon, list) and polygon and isinstance(polygon[0], (list, tuple)):
			return [tuple(float(coord) for coord in point[:2]) for point in polygon]
		bbox = node.get("bbox") or node.get("bounding_box") or node.get("box")
		if isinstance(bbox, dict):
			return self._polygon_from_bbox(bbox)
		if isinstance(polygon, list) and all(isinstance(num, (int, float)) for num in polygon):
			iterator = iter(polygon)
			return [tuple(float(a) for a in pair) for pair in zip(iterator, iterator)]
		return None

	def _polygon_from_bbox(self, bbox: dict[str, Any]) -> list[tuple[float, float]] | None:
		x = float(bbox.get("x", 0.0))
		y = float(bbox.get("y", 0.0))
		w = float(bbox.get("w") or bbox.get("width") or 0.0)
		h = float(bbox.get("h") or bbox.get("height") or 0.0)
		if w <= 0.0 or h <= 0.0:
			return None
		return [
			(x, y),
			(x + w, y),
			(x + w, y + h),
			(x, y + h),
		]

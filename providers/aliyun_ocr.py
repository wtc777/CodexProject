"""Aliyun OCR provider implementation."""


import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from config import AliyunCredentials
from schemas import OcrResult, OcrTextSpan
from utils.image_io import read_image_base64

try:
	from alibabacloud_ocr_api20210707.client import Client as OcrClient
	from alibabacloud_ocr_api20210707 import models as ocr_models
	from alibabacloud_tea_openapi import models as open_api_models
	from alibabacloud_tea_util import models as util_models
except ImportError:
	OcrClient = None  # type: ignore[assignment]
	ocr_models = None  # type: ignore[assignment]
	open_api_models = None  # type: ignore[assignment]
	util_models = None  # type: ignore[assignment]

JsonDict = dict[str, Any]


@dataclass
class AliyunOcrClient:
	"""Client wrapper around the Aliyun OCR API."""

	credentials: AliyunCredentials
	retries: int = 3
	backoff: float = 1.5

	def __post_init__(self) -> None:
		self._logger = logging.getLogger(self.__class__.__name__)
		self._client = self._create_client()

	def recognize(self, image_path: Path, alltext_type: str | None, min_conf: float) -> OcrResult:
		payload = read_image_base64(image_path)
		if alltext_type:
			request = self._build_all_text_request(payload, alltext_type)
			response = self._execute(lambda: self._invoke_client("recognize_all_text", request))
			label = alltext_type
		else:
			request = self._build_advanced_request(payload)
			response = self._execute(lambda: self._invoke_client("recognize_advanced", request))
			label = "advanced"

		raw = self._to_dict(response)
		blocks = self._parse_blocks(raw)
		filtered = [block for block in blocks if block.confidence is None or block.confidence >= min_conf]
		full_text = "\n".join(block.text for block in filtered)
		return OcrResult(
			backend="aliyun",
			task=label,
			image_path=str(image_path),
			blocks=filtered,
			full_text=full_text,
			raw=raw,
		)

	def _create_client(self) -> Any:
		if not all([OcrClient, open_api_models]):
			raise ImportError("Aliyun OCR SDK is not installed. Please install alibabacloud-ocr_api20210707.")
		config = open_api_models.Config(
			access_key_id=self.credentials.access_key_id,
			access_key_secret=self.credentials.access_key_secret,
			region_id=self.credentials.region_id,
		)
		return OcrClient(config)

	def _build_advanced_request(self, body: str):
		if not ocr_models:
			raise ImportError("Aliyun OCR models unavailable. Install alibabacloud-ocr_api20210707.")
		return ocr_models.RecognizeAdvancedRequest(body=body)

	def _build_all_text_request(self, body: str, alltext_type: str):
		if not ocr_models:
			raise ImportError("Aliyun OCR models unavailable. Install alibabacloud-ocr_api20210707.")
		return ocr_models.RecognizeAllTextRequest(body=body, type=alltext_type)

	def _invoke_client(self, method_base: str, request: Any):
		method = getattr(self._client, method_base, None)
		if callable(method):
			return method(request)
		with_options = getattr(self._client, f"{method_base}_with_options", None)
		if callable(with_options):
			runtime = util_models.RuntimeOptions() if util_models else None
			return with_options(request, runtime, {})
		raise AttributeError(f"Aliyun client missing method for {method_base}")

	def _execute(self, call: Callable[[], Any]):
		for attempt in range(1, self.retries + 1):
			try:
				return call()
			except Exception as exc:  # noqa: BLE001
				wait = self.backoff ** attempt
				self._logger.warning("Aliyun OCR call failed (attempt %s/%s): %s", attempt, self.retries, exc)
				if attempt == self.retries:
					raise
				time.sleep(wait)

	def _to_dict(self, response: Any) -> JsonDict:
		if hasattr(response, "to_map"):
			return response.to_map()
		if hasattr(response, "body") and hasattr(response.body, "to_map"):
			return {"body": response.body.to_map()}
		if isinstance(response, dict):
			return response
		return {"body": response} if response is not None else {}

	def _parse_blocks(self, payload: JsonDict) -> list[OcrTextSpan]:
		body = self._extract_body(payload)
		candidates = self._collect_candidates(body)
		blocks: list[OcrTextSpan] = []
		for index, item in enumerate(candidates):
			text = self._extract_text(item)
			if not text:
				continue
			confidence = self._extract_confidence(item)
			polygon = self._extract_polygon(item)
			blocks.append(OcrTextSpan(text=text, confidence=confidence, polygon=polygon, line_index=index))
		return blocks

	def _extract_body(self, payload: JsonDict) -> JsonDict:
		body = payload.get("body") if isinstance(payload, dict) else None
		if isinstance(body, dict):
			return body.get("Data", body)
		return payload

	def _collect_candidates(self, data: Any) -> list[JsonDict]:
		if not isinstance(data, dict):
			return []
		candidates: list[JsonDict] = []
		for key in ("Results", "PrismWordsInfo", "Lines", "Blocks"):
			items = data.get(key)
			if isinstance(items, list):
				candidates.extend(item for item in items if isinstance(item, dict))
		return candidates

	def _extract_text(self, item: JsonDict) -> str:
		for key in ("Text", "Word", "Content", "text"):
			value = item.get(key)
			if isinstance(value, str) and value.strip():
				return value.strip()
		return ""

	def _extract_confidence(self, item: JsonDict) -> float | None:
		for key in ("Score", "Confidence", "Prob"):
			value = item.get(key)
			if isinstance(value, (int, float)):
				return float(value)
		return None

	def _extract_polygon(self, item: JsonDict) -> list[tuple[float, float]] | None:
		points = item.get("Polygon") or item.get("Quad") or item.get("Points")
		if isinstance(points, list) and points and isinstance(points[0], (list, tuple)):
			return [tuple(float(coord) for coord in point[:2]) for point in points]
		if isinstance(points, list) and all(isinstance(val, (int, float)) for val in points):
			iterator = iter(points)
			return [tuple(float(a) for a in pair) for pair in zip(iterator, iterator)]
		return None

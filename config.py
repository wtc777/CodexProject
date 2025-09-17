"""Application configuration management for OCR CLI."""


import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

ENV_FILE: Final[str] = "\.env"
DEFAULT_REGION: Final[str] = "cn-hangzhou"
DEFAULT_LOG_LEVEL: Final[int] = logging.INFO


@dataclass(frozen=True)
class AliyunCredentials:
	"""Container for Aliyun credential details."""
	access_key_id: str
	access_key_secret: str
	region_id: str = DEFAULT_REGION


@dataclass(frozen=True)
class DashScopeCredentials:
	"""Container for DashScope credential details."""
	api_key: str


@dataclass(frozen=True)
class AppConfig:
	"""Aggregate configuration for the CLI runtime."""
	aliyun: AliyunCredentials | None
	dashscope: DashScopeCredentials | None
	output_dir: Path
	log_level: int = DEFAULT_LOG_LEVEL


def load_config() -> AppConfig:
	"""Load environment-based configuration values.

	Returns:
		AppConfig: Parsed configuration with credentials when available.
	"""
	load_dotenv(ENV_FILE)
	output_dir = Path(os.getenv("OCR_OUTPUT_DIR", "outputs")).resolve()
	output_dir.mkdir(parents=True, exist_ok=True)

	aliyun_config = _load_aliyun_credentials()
	dashscope_config = _load_dashscope_credentials()

	return AppConfig(
		aliyun=aliyun_config,
		dashscope=dashscope_config,
		output_dir=output_dir,
		log_level=DEFAULT_LOG_LEVEL,
	)


def configure_logging(level: int = DEFAULT_LOG_LEVEL) -> None:
	"""Configure the root logger for the application."""
	logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def _load_aliyun_credentials() -> AliyunCredentials | None:
	"""Load Aliyun credentials from the environment if available."""
	access_key_id = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID")
	access_key_secret = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
	region_id = os.getenv("ALIBABA_CLOUD_REGION", DEFAULT_REGION)
	if access_key_id and access_key_secret:
		return AliyunCredentials(
			access_key_id=access_key_id,
			access_key_secret=access_key_secret,
			region_id=region_id,
		)
	return None


def _load_dashscope_credentials() -> DashScopeCredentials | None:
	"""Load DashScope credentials from the environment if available."""
	api_key = os.getenv("DASHSCOPE_API_KEY")
	if api_key:
		return DashScopeCredentials(api_key=api_key)
	return None

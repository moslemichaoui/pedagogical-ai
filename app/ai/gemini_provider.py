"""Google Gemini client with multi-key / multi-model fallback.

The provider is deliberately small: it owns credentials, retries and error
classification, and nothing about pedagogy. Callers receive either text or a
parsed JSON object, and every failure raises :class:`GeminiError` carrying an
Arabic message the UI can show directly.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.utils.config_values import config_value
from app.utils.text import extract_json

logger = logging.getLogger(__name__)


class GeminiErrorType(str, Enum):
    NOT_CONFIGURED = "not_configured"
    QUOTA_EXCEEDED = "quota_exceeded"
    INVALID_API_KEY = "invalid_api_key"
    INVALID_MODEL = "invalid_model"
    MALFORMED_REQUEST = "malformed_request"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    EMPTY_RESPONSE = "empty_response"
    INVALID_JSON = "invalid_json"
    UNKNOWN = "unknown"


ARABIC_ERRORS = {
    GeminiErrorType.NOT_CONFIGURED: (
        "لم يتم إعداد مفتاح Gemini بعد. أضف GEMINI_API_KEY في ملف .env ثم أعد تشغيل التطبيق."
    ),
    GeminiErrorType.QUOTA_EXCEEDED: (
        "تم بلوغ الحد الأقصى لاستخدام Gemini مؤقتاً. أعد المحاولة بعد قليل أو أضف مفتاحاً آخر."
    ),
    GeminiErrorType.INVALID_API_KEY: (
        "مفتاح Gemini غير صالح. تحقّق من قيمة GEMINI_API_KEY في ملف .env."
    ),
    GeminiErrorType.INVALID_MODEL: (
        "النموذج المطلوب غير متاح لهذا المفتاح. جرّب gemini-2.5-flash أو gemini-2.0-flash."
    ),
    GeminiErrorType.MALFORMED_REQUEST: "تعذّر إرسال الطلب إلى Gemini بسبب بيانات غير صالحة.",
    GeminiErrorType.SERVER_ERROR: "خدمة Gemini غير متاحة حالياً. أعد المحاولة بعد لحظات.",
    GeminiErrorType.NETWORK_ERROR: (
        "تعذّر الاتصال بخدمة Gemini. تحقّق من اتصال الإنترنت ثم أعد المحاولة."
    ),
    GeminiErrorType.EMPTY_RESPONSE: "أعاد Gemini رداً فارغاً. أعد المحاولة.",
    GeminiErrorType.INVALID_JSON: "أعاد Gemini محتوى غير صالح. أعد المحاولة.",
    GeminiErrorType.UNKNOWN: "تعذّر إكمال التوليد. أعد المحاولة.",
}


class GeminiError(RuntimeError):
    """A generation failure with a stable type and an Arabic message."""

    def __init__(self, error_type: GeminiErrorType, detail: str = "", retry_after: Optional[int] = None):
        self.error_type = error_type
        self.detail = detail
        self.retry_after = retry_after
        super().__init__(ARABIC_ERRORS.get(error_type, ARABIC_ERRORS[GeminiErrorType.UNKNOWN]))

    @property
    def code(self) -> str:
        return self.error_type.value

    @property
    def message(self) -> str:
        return str(self)


@dataclass
class GeminiConfig:
    key: str
    key_label: str
    model: str
    model_label: str


@dataclass
class GenerationResult:
    text: str
    model_used: str
    key_label: str
    latency_ms: int
    attempts: int = 1
    raw: Any = field(default=None, repr=False)


def _classify_error(error: Exception) -> Tuple[GeminiErrorType, Optional[int]]:
    text = f"{type(error).__name__} {error}".lower()
    retry_after = None
    match = re.search(r"retry[-_ ]?after[^0-9]{0,12}(\d+)", text)
    if match:
        try:
            retry_after = int(match.group(1))
        except ValueError:
            retry_after = None

    if any(x in text for x in ("429", "resource_exhausted", "quota", "rate limit", "rate_limit")):
        return GeminiErrorType.QUOTA_EXCEEDED, retry_after
    if any(x in text for x in ("api key not valid", "api_key_invalid", "invalid api key", "unauthenticated", "401", "permission_denied", "403")):
        return GeminiErrorType.INVALID_API_KEY, None
    if any(x in text for x in ("model not found", "not_found", "not found for api version", "invalid model", "404")):
        return GeminiErrorType.INVALID_MODEL, None
    if any(x in text for x in ("timeout", "timed out", "deadline", "connection", "network", "dns", "ssl", "connect")):
        return GeminiErrorType.NETWORK_ERROR, None
    if any(x in text for x in ("500", "502", "503", "504", "internal", "unavailable", "overloaded")):
        return GeminiErrorType.SERVER_ERROR, None
    if any(x in text for x in ("400", "bad request", "invalid argument", "malformed")):
        return GeminiErrorType.MALFORMED_REQUEST, None
    return GeminiErrorType.UNKNOWN, None


class GeminiProvider:
    """Generate content with automatic fallback across configured keys/models."""

    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        models: Optional[List[str]] = None,
        timeout: Optional[int] = None,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
    ) -> None:
        if any(
            value is None
            for value in (api_keys, models, timeout, temperature, max_output_tokens)
        ):
            api_keys = config_value("GEMINI_API_KEYS") if api_keys is None else api_keys
            models = config_value("GEMINI_MODELS") if models is None else models
            timeout = config_value("GEMINI_TIMEOUT_SECONDS") if timeout is None else timeout
            temperature = config_value("GEMINI_TEMPERATURE") if temperature is None else temperature
            max_output_tokens = (
                config_value("GEMINI_MAX_OUTPUT_TOKENS")
                if max_output_tokens is None
                else max_output_tokens
            )

        self.api_keys = [key for key in (api_keys or []) if key]
        self.models = [model for model in (models or []) if model]
        self.timeout = timeout or 90
        self.temperature = 0.25 if temperature is None else temperature
        self.max_output_tokens = max_output_tokens or 8192
        self._clients: Dict[str, Any] = {}
        self.last_model_used: Optional[str] = None
        self.configurations = [
            GeminiConfig(key=key, key_label=f"KEY_{ki}", model=model, model_label=f"MODEL_{mi}")
            for ki, key in enumerate(self.api_keys, 1)
            for mi, model in enumerate(self.models, 1)
        ]

    # -- availability -------------------------------------------------
    def is_available(self) -> bool:
        return bool(self.configurations)

    def _require_available(self) -> None:
        if not self.is_available():
            raise GeminiError(
                GeminiErrorType.NOT_CONFIGURED,
                "GEMINI_API_KEY is not set",
            )

    def _get_client(self, api_key: str):
        client = self._clients.get(api_key)
        if client is not None:
            return client
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise GeminiError(
                GeminiErrorType.UNKNOWN,
                "google-genai is not installed",
            ) from exc

        options = None
        try:
            options = types.HttpOptions(timeout=self.timeout * 1000)
        except Exception:  # older SDKs
            options = None
        try:
            client = genai.Client(api_key=api_key, http_options=options) if options else genai.Client(api_key=api_key)
        except TypeError:
            client = genai.Client(api_key=api_key)
        self._clients[api_key] = client
        return client

    @staticmethod
    def _config_types():
        from google.genai import types

        return types

    def _build_config(self, *, system_instruction: Optional[str], json_mode: bool, temperature: Optional[float]):
        types = self._config_types()
        kwargs: Dict[str, Any] = {
            "temperature": self.temperature if temperature is None else temperature,
            "max_output_tokens": self.max_output_tokens,
        }
        if system_instruction:
            kwargs["system_instruction"] = system_instruction
        if json_mode:
            kwargs["response_mime_type"] = "application/json"
        try:
            return types.GenerateContentConfig(**kwargs)
        except TypeError:
            kwargs.pop("max_output_tokens", None)
            return types.GenerateContentConfig(**kwargs)

    def generate(
        self,
        prompt: str,
        *,
        system_instruction: Optional[str] = None,
        json_mode: bool = False,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_attempts: Optional[int] = None,
    ) -> GenerationResult:
        """Generate text, trying every key/model combination before failing."""
        self._require_available()

        configs = self.configurations
        if model:
            configs = [c for c in configs if c.model == model]
            if not configs:
                raise GeminiError(GeminiErrorType.INVALID_MODEL, f"model {model} not configured")
        if max_attempts:
            configs = configs[: max(1, max_attempts)]

        skipped_models: set[str] = set()
        last_error: Optional[GeminiError] = None
        attempt = 0

        for config in configs:
            if config.model in skipped_models:
                continue
            attempt += 1
            started = time.perf_counter()
            try:
                client = self._get_client(config.key)
                response = client.models.generate_content(
                    model=config.model,
                    contents=prompt,
                    config=self._build_config(
                        system_instruction=system_instruction,
                        json_mode=json_mode,
                        temperature=temperature,
                    ),
                )
                text = (getattr(response, "text", None) or "").strip()
                if not text:
                    raise GeminiError(GeminiErrorType.EMPTY_RESPONSE, "empty response")
                self.last_model_used = config.model
                return GenerationResult(
                    text=text,
                    model_used=config.model,
                    key_label=config.key_label,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    attempts=attempt,
                    raw=response,
                )
            except GeminiError as exc:
                last_error = exc
                if exc.error_type == GeminiErrorType.EMPTY_RESPONSE:
                    continue
                raise
            except Exception as exc:  # noqa: BLE001 - classified below
                error_type, retry_after = _classify_error(exc)
                last_error = GeminiError(error_type, str(exc)[:400], retry_after)
                logger.warning(
                    "Gemini attempt %s failed (%s / %s): %s",
                    attempt,
                    config.key_label,
                    config.model,
                    str(exc)[:200],
                )
                if error_type == GeminiErrorType.INVALID_MODEL:
                    skipped_models.add(config.model)
                    continue
                if error_type == GeminiErrorType.MALFORMED_REQUEST:
                    raise last_error from exc
                continue

        raise last_error or GeminiError(GeminiErrorType.UNKNOWN, "no configuration attempted")

    def generate_json(
        self,
        prompt: str,
        *,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        result = self.generate(
            prompt,
            system_instruction=system_instruction,
            json_mode=True,
            model=model,
            temperature=temperature,
        )
        parsed = extract_json(result.text)
        if not isinstance(parsed, dict):
            raise GeminiError(GeminiErrorType.INVALID_JSON, result.text[:400])
        return parsed

    def health_check(self) -> Dict[str, Any]:
        if not self.is_available():
            return {
                "status": "not_configured",
                "message": ARABIC_ERRORS[GeminiErrorType.NOT_CONFIGURED],
                "configurations": 0,
            }
        return {
            "status": "configured",
            "configurations": len(self.configurations),
            "models": self.models,
            "keys": len(self.api_keys),
        }

    def describe(self) -> List[Dict[str, str]]:
        return [
            {"key": cfg.key_label, "model": cfg.model_label, "model_name": cfg.model}
            for cfg in self.configurations
        ]

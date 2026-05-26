"""OCR provider boundary, validation, normalization, and retention helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Protocol
from urllib.parse import urlparse
from uuid import uuid4


class OcrValidationError(ValueError):
    pass


@dataclass(frozen=True)
class FieldSchema:
    key: str
    label: str
    min_confidence: float = 0.8
    normalizer: str = "strip"


@dataclass(frozen=True)
class DocumentSchema:
    document_type: str
    fields: dict[str, FieldSchema]


@dataclass(frozen=True)
class TrustedOcrProviderConfig:
    alias: str
    provider_type: str
    endpoint_url: str
    cloud_approved: bool = False

    @property
    def is_on_prem_capable(self) -> bool:
        return self.provider_type in {"rapidocr", "paddleocr", "internal-http", "fixture"}

    def validate(self, environment: str) -> "TrustedOcrProviderConfig":
        prod = environment.lower() in {"prod", "production", "formal"}
        host = (urlparse(self.endpoint_url).hostname or "").lower()
        if prod and (host in {"localhost", "127.0.0.1", "::1"} or host.startswith("127.")):
            raise ValueError("production OCR provider cannot point at localhost")
        if self.provider_type == "cloud" and not self.cloud_approved:
            raise ValueError("cloud OCR provider requires explicit approval")
        if not self.is_on_prem_capable and self.provider_type != "cloud":
            raise ValueError(f"unsupported OCR provider type: {self.provider_type}")
        return self


@dataclass(frozen=True)
class OcrSource:
    source_type: str
    file_name: str = ""
    size_bytes: int = 0
    page_count: int = 1
    content_type: str = ""
    attachment_id: str = ""


@dataclass(frozen=True)
class OcrFieldResult:
    raw: str
    normalized: str
    confidence: float
    requires_manual_review: bool = False


@dataclass(frozen=True)
class OcrJobResult:
    job_id: str
    status: str
    document_type: str
    fields: dict[str, OcrFieldResult]
    warnings: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class OcrProvider(Protocol):
    def recognize(self, source: OcrSource, document_type: str) -> tuple[str, dict[str, tuple[str, float]]]:
        ...


class FixtureOcrProvider:
    """Deterministic provider used for local tests and stub flows."""

    def __init__(self, document_type: str, fields: dict[str, tuple[str, float]]) -> None:
        self._document_type = document_type
        self._fields = fields

    def recognize(self, source: OcrSource, document_type: str) -> tuple[str, dict[str, tuple[str, float]]]:
        return self._document_type, dict(self._fields)


class OcrJobService:
    def __init__(
        self,
        provider: OcrProvider,
        schemas: dict[str, DocumentSchema],
        *,
        max_size_bytes: int = 10 * 1024 * 1024,
        max_pages: int = 5,
        allowed_extensions: set[str] | None = None,
    ) -> None:
        self._provider = provider
        self._schemas = schemas
        self._max_size_bytes = max_size_bytes
        self._max_pages = max_pages
        self._allowed_extensions = allowed_extensions or {".jpg", ".jpeg", ".png", ".pdf"}
        self.jobs: dict[str, OcrJobResult] = {}

    def create_job(self, source: OcrSource, requested_document_type: str) -> OcrJobResult:
        self._validate_source(source)
        if requested_document_type not in self._schemas:
            raise OcrValidationError(f"unsupported document type: {requested_document_type}")

        actual_type, raw_fields = self._provider.recognize(source, requested_document_type)
        if actual_type not in self._schemas:
            return OcrJobResult(uuid4().hex, "needs_document_type", actual_type, {}, ["document_type_uncertain"])

        schema = self._schemas[actual_type]
        fields: dict[str, OcrFieldResult] = {}
        warnings: list[str] = []
        for key, field_schema in schema.fields.items():
            if key not in raw_fields:
                warnings.append(f"missing_field:{key}")
                continue
            raw, confidence = raw_fields[key]
            normalized = _normalize(str(raw), field_schema.normalizer)
            low_confidence = confidence < field_schema.min_confidence
            if low_confidence:
                warnings.append(f"low_confidence:{key}")
            fields[key] = OcrFieldResult(raw=str(raw), normalized=normalized, confidence=confidence, requires_manual_review=low_confidence)

        result = OcrJobResult(uuid4().hex, "completed", actual_type, fields, warnings)
        self.jobs[result.job_id] = result
        return result

    def purge_expired_artifacts(self, max_age: timedelta, *, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        before = len(self.jobs)
        self.jobs = {job_id: job for job_id, job in self.jobs.items() if now - job.created_at <= max_age}
        return before - len(self.jobs)

    def _validate_source(self, source: OcrSource) -> None:
        if source.source_type not in {"file", "attachment"}:
            raise OcrValidationError("source_type must be file or attachment")
        if source.source_type == "attachment":
            if not source.attachment_id:
                raise OcrValidationError("attachment source requires attachment_id")
            return
        if source.size_bytes <= 0 or source.size_bytes > self._max_size_bytes:
            raise OcrValidationError("file size is outside allowed bounds")
        if source.page_count <= 0 or source.page_count > self._max_pages:
            raise OcrValidationError("page count is outside allowed bounds")
        ext = _extension(source.file_name)
        if ext not in self._allowed_extensions:
            raise OcrValidationError(f"unsupported file extension: {ext or '<none>'}")


def _extension(file_name: str) -> str:
    match = re.search(r"(\.[A-Za-z0-9]+)$", file_name or "")
    return match.group(1).lower() if match else ""


def _normalize(value: str, normalizer: str) -> str:
    if normalizer == "compact":
        return re.sub(r"\s+", "", value)
    return value.strip()

"""Vendor-neutral knowledge assistant adapter boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4

from .audit import InMemoryAuditLog
from .config import PageScope


@dataclass(frozen=True)
class SourceReference:
    source_id: str
    title: str
    section: str = ""
    url: str = ""
    snippet: str = ""
    score: float | None = None


@dataclass(frozen=True)
class KnowledgeAdapterResult:
    status: str
    answer: str
    sources: list[SourceReference] = field(default_factory=list)
    trace_id: str = ""


@dataclass(frozen=True)
class KnowledgeAskRequest:
    question: str
    scope: PageScope
    page_context: dict[str, object] = field(default_factory=dict)
    conversation_id: str = ""


@dataclass(frozen=True)
class KnowledgeResponse:
    status: str
    answer: str
    sources: list[SourceReference]
    trace_id: str


class KnowledgeAdapter(Protocol):
    def ask(self, request: KnowledgeAskRequest) -> KnowledgeAdapterResult:
        ...


class StubKnowledgeAdapter:
    """Keyword-driven adapter for UI and permission-flow tests."""

    def __init__(self, fixtures: dict[str, KnowledgeAdapterResult]) -> None:
        self._fixtures = fixtures

    def ask(self, request: KnowledgeAskRequest) -> KnowledgeAdapterResult:
        for keyword, result in self._fixtures.items():
            if keyword in request.question:
                return result
        return KnowledgeAdapterResult(
            status="unsupported",
            answer="知识库中没有找到足够依据回答这个问题。",
            sources=[],
        )


class DisabledKnowledgeAdapter:
    def ask(self, request: KnowledgeAskRequest) -> KnowledgeAdapterResult:
        return KnowledgeAdapterResult(
            status="adapter_unavailable",
            answer="知识助手当前未启用。",
            sources=[],
        )


class KnowledgeService:
    """Grounded answer service that refuses answers without sources."""

    def __init__(self, adapter: KnowledgeAdapter, audit_log: InMemoryAuditLog | None = None) -> None:
        self._adapter = adapter
        self._audit = audit_log or InMemoryAuditLog()

    def ask(self, request: KnowledgeAskRequest) -> KnowledgeResponse:
        trace_id = uuid4().hex
        try:
            result = self._adapter.ask(request)
        except Exception as exc:  # pragma: no cover - defensive boundary
            result = KnowledgeAdapterResult(
                status="adapter_unavailable",
                answer="知识库服务暂时不可用，请稍后重试。",
                sources=[],
                trace_id=trace_id,
            )
            self._audit.record("assistant.error", {"error": str(exc), "scope": request.scope.__dict__})

        if result.status == "answered" and not result.sources:
            result = KnowledgeAdapterResult(
                status="unsupported",
                answer="知识库中没有找到足够依据回答这个问题。",
                sources=[],
                trace_id=result.trace_id or trace_id,
            )

        response = KnowledgeResponse(
            status=result.status,
            answer=result.answer,
            sources=result.sources,
            trace_id=result.trace_id or trace_id,
        )
        self._audit.record(
            "assistant.answer",
            {
                "status": response.status,
                "traceId": response.trace_id,
                "sourceIds": [source.source_id for source in response.sources],
                "scope": request.scope.__dict__,
                "pageContext": request.page_context,
            },
        )
        return response

    def feedback(self, trace_id: str, rating: str, comment: str = "") -> None:
        self._audit.record("assistant.feedback", {"traceId": trace_id, "rating": rating, "comment": comment})


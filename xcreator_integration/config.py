"""Configuration models for page-scoped XCreator features."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


PRODUCTION_ENVS = {"prod", "production", "formal"}


@dataclass(frozen=True)
class PageScope:
    tenant_code: str
    app_code: str
    page_code: str
    page_id: str
    environment: str
    roles: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class AssistantFeature:
    enabled: bool = False
    mode: str = "disabled"
    entry: str = "floating"
    endpoint_alias: str | None = None
    title: str = "知识助手"
    placeholder: str = "请输入你想查询的问题"
    source_scope_hints: tuple[str, ...] = ()


@dataclass(frozen=True)
class OcrSlotConfig:
    upload_slot_id: str
    enabled: bool
    document_types: set[str]
    field_mappings: dict[str, Any]
    attachment_source: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FeatureConfig:
    tenant_code: str
    app_code: str
    page_code: str
    page_id: str
    environment: str
    roles: set[str] = field(default_factory=set)
    assistant: AssistantFeature = field(default_factory=AssistantFeature)
    ocr_slots: list[OcrSlotConfig] = field(default_factory=list)

    @staticmethod
    def disabled(scope: PageScope) -> "FeatureConfig":
        return FeatureConfig(
            tenant_code=scope.tenant_code,
            app_code=scope.app_code,
            page_code=scope.page_code,
            page_id=scope.page_id,
            environment=scope.environment,
        )


class EndpointRegistry:
    """Environment-specific endpoint aliases with production safety checks."""

    def __init__(self, endpoints: dict[str, dict[str, str]]) -> None:
        self._endpoints = endpoints

    def endpoint_url(self, alias: str, environment: str) -> str:
        by_env = self._endpoints.get(alias)
        if not by_env:
            raise KeyError(f"unknown endpoint alias: {alias}")
        url = by_env.get(environment) or by_env.get("default")
        if not url:
            raise KeyError(f"endpoint alias {alias!r} has no URL for {environment!r}")
        if environment.lower() in PRODUCTION_ENVS and _is_local_url(url):
            raise ValueError(f"production endpoint alias {alias!r} cannot point at localhost")
        return url


class FeatureConfigResolver:
    """Resolve the most specific enabled config for a page scope."""

    def __init__(self, configs: list[FeatureConfig], endpoints: EndpointRegistry) -> None:
        self._configs = configs
        self._endpoints = endpoints

    def resolve(self, scope: PageScope) -> FeatureConfig:
        matches = [config for config in self._configs if _matches(config, scope)]
        if not matches:
            return FeatureConfig.disabled(scope)
        return max(matches, key=_specificity)

    def endpoint_url(self, alias: str, environment: str) -> str:
        return self._endpoints.endpoint_url(alias, environment)


def _matches(config: FeatureConfig, scope: PageScope) -> bool:
    if config.tenant_code != scope.tenant_code:
        return False
    if config.environment != scope.environment:
        return False
    if config.app_code and config.app_code != scope.app_code:
        return False
    if config.page_code and config.page_code != scope.page_code:
        return False
    if config.page_id and config.page_id != scope.page_id:
        return False
    if config.roles and not (config.roles & scope.roles):
        return False
    return True


def _specificity(config: FeatureConfig) -> int:
    score = 0
    score += 4 if config.page_id else 0
    score += 2 if config.page_code else 0
    score += 1 if config.roles else 0
    return score


def _is_local_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"} or host.startswith("127.")


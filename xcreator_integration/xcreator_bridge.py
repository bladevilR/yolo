"""Dry-run upload discovery and safe confirmed field-fill bridge."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


BUSINESS_ACTION_RE = re.compile(
    r"保存|提交|删除|批量删除|归档|下载|导入|导出|审批|通过|驳回|save|submit|delete|archive|download|import|export|approve",
    re.IGNORECASE,
)
UPLOAD_RE = re.compile(r"upload|file|attach|attachment|image|photo|pic|附件|上传|文件|照片|图片|扫描|证件|材料|教育文件", re.IGNORECASE)
ATTACHMENT_IFRAME_RE = re.compile(r"attachmentIframeSrc|sysAttachmentList", re.IGNORECASE)


@dataclass(frozen=True)
class PageField:
    widget_id: str = ""
    selector: str = ""
    stable_name: str = ""
    label: str = ""
    widget_type: str = "input"


@dataclass(frozen=True)
class FieldMapping:
    target_type: str
    target: str


@dataclass(frozen=True)
class MappingReport:
    resolved: dict[str, PageField] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    duplicate_targets: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)


class MappingResolver:
    def __init__(self, fields: list[PageField]) -> None:
        self._by_widget = {field.widget_id: field for field in fields if field.widget_id}
        self._by_selector = {field.selector: field for field in fields if field.selector}
        self._by_stable = {field.stable_name: field for field in fields if field.stable_name}

    def resolve(self, mapping: FieldMapping) -> PageField | None:
        if mapping.target_type == "widgetId":
            return self._by_widget.get(mapping.target)
        if mapping.target_type == "selector":
            return self._by_selector.get(mapping.target)
        if mapping.target_type == "stableName":
            return self._by_stable.get(mapping.target)
        return None

    def dry_run(self, mappings: dict[str, FieldMapping]) -> MappingReport:
        resolved: dict[str, PageField] = {}
        missing: list[str] = []
        unsupported: list[str] = []
        target_to_key: dict[str, str] = {}
        duplicates: list[str] = []
        for key, mapping in mappings.items():
            field = self.resolve(mapping)
            if mapping.target_type not in {"widgetId", "selector", "stableName"}:
                unsupported.append(key)
                continue
            if not field:
                missing.append(key)
                continue
            target_key = field.selector or field.widget_id or field.stable_name
            if target_key in target_to_key:
                duplicates.append(key)
            else:
                target_to_key[target_key] = key
            resolved[key] = field
        return MappingReport(resolved=resolved, missing=missing, duplicate_targets=duplicates, unsupported=unsupported)


@dataclass(frozen=True)
class FillOutcome:
    applied: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    duplicate_targets: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)


class SafeFillBridge:
    """Apply values via a supplied setter; never touches business actions."""

    def __init__(
        self,
        resolver: MappingResolver,
        *,
        setter: Callable[[PageField, str], None],
        action_guard: Callable[[str], None] | None = None,
    ) -> None:
        self._resolver = resolver
        self._setter = setter
        self._action_guard = action_guard

    def apply_confirmed(self, values: dict[str, str], mappings: dict[str, FieldMapping]) -> FillOutcome:
        report = self._resolver.dry_run({key: mappings[key] for key in values if key in mappings})
        applied: dict[str, str] = {}
        for key, field in report.resolved.items():
            self._setter(field, values[key])
            applied[key] = field.widget_id or field.selector or field.stable_name
        return FillOutcome(applied=applied, missing=report.missing, duplicate_targets=report.duplicate_targets, unsupported=report.unsupported)


@dataclass(frozen=True)
class UploadSlotInventory:
    upload_like_ids: list[str]
    attachment_iframe_count: int

    @classmethod
    def from_page_config(cls, page_config: dict[str, Any]) -> "UploadSlotInventory":
        upload_ids: list[str] = []
        attachment_count = 0

        def walk(value: Any) -> None:
            nonlocal attachment_count
            if isinstance(value, list):
                for item in value:
                    walk(item)
                return
            if isinstance(value, dict):
                text = " ".join(f"{key}:{item}" for key, item in value.items() if isinstance(item, (str, int, float, bool)))
                if ATTACHMENT_IFRAME_RE.search(text):
                    attachment_count += 1
                if UPLOAD_RE.search(text):
                    upload_id = str(value.get("id") or value.get("name") or value.get("label") or "")
                    if upload_id and upload_id not in upload_ids:
                        upload_ids.append(upload_id)
                for item in value.values():
                    walk(item)

        walk(page_config)
        return cls(upload_like_ids=upload_ids, attachment_iframe_count=attachment_count)


def is_business_action(label_or_action: str) -> bool:
    return bool(BUSINESS_ACTION_RE.search(label_or_action or ""))

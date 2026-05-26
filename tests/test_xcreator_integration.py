from datetime import datetime, timedelta, timezone

import pytest

from xcreator_integration.audit import InMemoryAuditLog
from xcreator_integration.config import (
    AssistantFeature,
    EndpointRegistry,
    FeatureConfig,
    FeatureConfigResolver,
    OcrSlotConfig,
    PageScope,
)
from xcreator_integration.knowledge import (
    KnowledgeAdapterResult,
    KnowledgeAskRequest,
    KnowledgeService,
    SourceReference,
    StubKnowledgeAdapter,
)
from xcreator_integration.ocr import (
    DocumentSchema,
    FieldSchema,
    FixtureOcrProvider,
    OcrJobService,
    OcrSource,
    OcrValidationError,
    TrustedOcrProviderConfig,
)
from xcreator_integration.redaction import redact
from xcreator_integration.xcreator_bridge import (
    FieldMapping,
    MappingResolver,
    PageField,
    SafeFillBridge,
    UploadSlotInventory,
    is_business_action,
)


def test_redact_removes_xcreator_tokens_from_urls_and_nested_payloads():
    payload = {
        "url": "http://xcreator/a?cwUserToken=abc&cwAppToken=app&ok=1",
        "headers": {"Authorization": "Bearer secret", "Cookie": "sid=abc"},
        "nested": {"sessionToken": "raw", "safe": "value"},
    }

    cleaned = redact(payload)

    assert "abc" not in str(cleaned)
    assert "secret" not in str(cleaned)
    assert cleaned["url"].endswith("cwUserToken=[REDACTED]&cwAppToken=[REDACTED]&ok=1")
    assert cleaned["nested"]["safe"] == "value"


def test_feature_config_resolves_by_scope_role_and_rejects_localhost_in_production():
    registry = EndpointRegistry(
        {
            "kb-test": {"stub": "https://kb.test.internal"},
            "bad-prod": {"prod": "http://localhost:8000"},
        }
    )
    resolver = FeatureConfigResolver(
        [
            FeatureConfig(
                tenant_code="platform",
                app_code="aji0nnjl",
                page_code="certificateInfotest1Form",
                page_id="2f596471-0d6a-463f-a394-385b260a4ee8",
                environment="stub",
                roles={"tester"},
                assistant=AssistantFeature(enabled=True, mode="stub", endpoint_alias="kb-test"),
                ocr_slots=[
                    OcrSlotConfig(
                        upload_slot_id="certificateAttachment",
                        enabled=True,
                        document_types={"certificate"},
                        field_mappings={"number": FieldMapping("widgetId", "certificateNum")},
                    )
                ],
            )
        ],
        registry,
    )

    config = resolver.resolve(
        PageScope(
            tenant_code="platform",
            app_code="aji0nnjl",
            page_code="certificateInfotest1Form",
            page_id="2f596471-0d6a-463f-a394-385b260a4ee8",
            environment="stub",
            roles={"tester"},
        )
    )

    assert config.assistant.enabled is True
    assert resolver.endpoint_url("kb-test", "stub") == "https://kb.test.internal"
    with pytest.raises(ValueError, match="localhost"):
        registry.endpoint_url("bad-prod", "prod")


def test_knowledge_service_supports_stub_mode_and_refuses_ungrounded_answers():
    audit = InMemoryAuditLog()
    service = KnowledgeService(
        adapter=StubKnowledgeAdapter(
            {
                "归档": KnowledgeAdapterResult(
                    status="answered",
                    answer="归档状态表示档案包处理进度。",
                    sources=[SourceReference(source_id="doc-1", title="操作手册", section="归档")],
                ),
                "无来源": KnowledgeAdapterResult(status="answered", answer="不能直接相信。", sources=[]),
            }
        ),
        audit_log=audit,
    )
    scope = PageScope("platform", "acbbhqib", "dzda", "page-1", "stub", {"tester"})

    answered = service.ask(KnowledgeAskRequest("归档状态是什么？", scope))
    unsupported = service.ask(KnowledgeAskRequest("无来源也回答？", scope))

    assert answered.status == "answered"
    assert answered.sources[0].source_id == "doc-1"
    assert unsupported.status == "unsupported"
    assert "没有找到足够依据" in unsupported.answer
    assert "cwUserToken" not in str(audit.events)


def test_ocr_job_service_validates_source_normalizes_fields_and_flags_low_confidence():
    service = OcrJobService(
        provider=FixtureOcrProvider(
            document_type="id-card-front",
            fields={
                "name": (" 张三 ", 0.96),
                "idNumber": ("110101199003070011", 0.91),
                "address": ("某路 1 号", 0.52),
            },
        ),
        schemas={
            "id-card-front": DocumentSchema(
                document_type="id-card-front",
                fields={
                    "name": FieldSchema("name", "姓名", min_confidence=0.8),
                    "idNumber": FieldSchema("idNumber", "身份证号", min_confidence=0.9, normalizer="compact"),
                    "address": FieldSchema("address", "地址", min_confidence=0.75),
                },
            )
        },
    )

    result = service.create_job(
        OcrSource(
            source_type="file",
            file_name="id-card.png",
            size_bytes=1024,
            page_count=1,
            content_type="image/png",
        ),
        requested_document_type="id-card-front",
    )

    assert result.status == "completed"
    assert result.fields["name"].normalized == "张三"
    assert result.fields["idNumber"].normalized == "110101199003070011"
    assert result.fields["address"].requires_manual_review is True
    with pytest.raises(OcrValidationError):
        service.create_job(
            OcrSource("file", file_name="bad.exe", size_bytes=10, page_count=1),
            requested_document_type="id-card-front",
        )


def test_trusted_ocr_provider_config_blocks_unapproved_cloud_and_localhost_prod():
    internal = TrustedOcrProviderConfig(
        alias="rapidocr-internal",
        provider_type="rapidocr",
        endpoint_url="https://ocr.internal.example/api",
    )

    assert internal.is_on_prem_capable is True
    assert internal.validate("prod") is internal

    with pytest.raises(ValueError, match="cloud"):
        TrustedOcrProviderConfig(
            alias="cloud-ocr",
            provider_type="cloud",
            endpoint_url="https://ocr.vendor.example/api",
            cloud_approved=False,
        ).validate("prod")

    with pytest.raises(ValueError, match="localhost"):
        TrustedOcrProviderConfig(
            alias="local-ocr",
            provider_type="rapidocr",
            endpoint_url="http://127.0.0.1:9000/ocr",
        ).validate("prod")


def test_mapping_resolver_dry_run_and_safe_fill_never_triggers_business_actions():
    fields = [
        PageField(widget_id="certificateName", selector="#certificateName", stable_name="certificateName"),
        PageField(widget_id="certificateNum", selector="#certificateNum", stable_name="certificateNum"),
    ]
    resolver = MappingResolver(fields)
    mappings = {
        "name": FieldMapping("widgetId", "certificateName"),
        "number": FieldMapping("selector", "#certificateNum"),
        "missing": FieldMapping("widgetId", "notThere"),
        "duplicate": FieldMapping("selector", "#certificateNum"),
    }

    report = resolver.dry_run(mappings)

    assert report.resolved["name"].widget_id == "certificateName"
    assert "missing" in report.missing
    assert "duplicate" in report.duplicate_targets
    assert is_business_action("保存") is True
    assert is_business_action("OCR 识别") is False

    calls = []
    bridge = SafeFillBridge(
        resolver,
        setter=lambda field, value: calls.append((field.widget_id, value)),
        action_guard=lambda action: pytest.fail(f"business action triggered: {action}"),
    )

    outcome = bridge.apply_confirmed({"name": "证件 A", "number": "ZJ-001"}, mappings)

    assert outcome.applied == {"name": "certificateName", "number": "certificateNum"}
    assert calls == [("certificateName", "证件 A"), ("certificateNum", "ZJ-001")]


def test_upload_slot_inventory_finds_attachment_and_upload_patterns():
    inventory = UploadSlotInventory.from_page_config(
        {
            "configObject": {
                "tabFragment": [
                    {
                        "childrens": [
                            {"id": "eduFileCell", "label": "教育文件", "type": "cell"},
                            {
                                "id": "attachmentFrame",
                                "pageCode_attachmentIframeSrc": "common/sysAttachmentList",
                            },
                        ]
                    }
                ]
            }
        }
    )

    assert inventory.upload_like_ids == ["eduFileCell", "attachmentFrame"]
    assert inventory.attachment_iframe_count == 1


def test_audit_retention_redacts_payloads_and_expires_ocr_artifacts():
    audit = InMemoryAuditLog()
    audit.record(
        "ocr.completed",
        {"cwUserToken": "secret", "jobId": "j1"},
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    audit.record("assistant.feedback", {"message": "ok"})

    expired = audit.purge_older_than(timedelta(days=1))

    assert expired == 1
    assert len(audit.events) == 1
    assert "secret" not in str(audit.events)

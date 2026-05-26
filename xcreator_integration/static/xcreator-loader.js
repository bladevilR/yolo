(function () {
  "use strict";

  var REDACTED = "[REDACTED]";
  var TOKEN_KEYS = /token|session|authorization|cookie|password|secret|auth/i;
  var BUSINESS_ACTIONS = /保存|提交|删除|批量删除|归档|下载|导入|导出|审批|通过|驳回|save|submit|delete|archive|download|import|export|approve/i;

  function redactValue(value) {
    if (Array.isArray(value)) {
      return value.map(redactValue);
    }
    if (value && typeof value === "object") {
      var output = {};
      Object.keys(value).forEach(function (key) {
        output[key] = TOKEN_KEYS.test(key) ? REDACTED : redactValue(value[key]);
      });
      return output;
    }
    if (typeof value === "string") {
      return value.replace(/([?&](?:cwUserToken|cwAppToken|userToken|token|session|auth)=)([^&#]*)/gi, "$1" + REDACTED);
    }
    return value;
  }

  function collectPageContext() {
    var params = new URLSearchParams(window.location.search || "");
    var globalContext = window.Global || {};
    return redactValue({
      tenantCode: params.get("cwTenantCode") || globalContext.tenantCode || "platform",
      appCode: params.get("appCode") || params.get("cwAppToken") || globalContext.appCode || "",
      pageCode: params.get("pageCode") || globalContext.pageCode || "",
      pageId: params.get("pageId") || globalContext.pageId || "",
      title: document.title || "",
      url: window.location.href
    });
  }

  function resolveTarget(mapping, root) {
    root = root || document;
    if (!mapping) return null;
    if (mapping.targetType === "selector") return root.querySelector(mapping.target);
    if (mapping.targetType === "widgetId") return root.getElementById(mapping.target) || root.querySelector("[name='" + cssEscape(mapping.target) + "']");
    if (mapping.targetType === "stableName") return root.querySelector("[name='" + cssEscape(mapping.target) + "'],[data-field='" + cssEscape(mapping.target) + "']");
    return null;
  }

  function cssEscape(value) {
    if (window.CSS && typeof window.CSS.escape === "function") return window.CSS.escape(value);
    return String(value).replace(/['"\\]/g, "\\$&");
  }

  function discoverUploads(root) {
    root = root || document;
    return Array.prototype.slice.call(
      root.querySelectorAll("input[type='file'],[data-xc-upload],iframe[src*='sysAttachmentList'],textarea[id*='File'],textarea[name*='File'],[id*='Attachment'],[name*='Attachment']")
    ).map(function (node, index) {
      return {
        index: index,
        id: node.id || "",
        name: node.getAttribute("name") || "",
        selector: node.id ? "#" + cssEscape(node.id) : "",
        tagName: node.tagName.toLowerCase(),
        label: findLabel(node)
      };
    });
  }

  function discoverFields(root) {
    root = root || document;
    return Array.prototype.slice.call(root.querySelectorAll("input,textarea,select,[contenteditable='true']"))
      .filter(function (node) {
        return !node.matches("input[type='hidden'],input[type='file']");
      })
      .map(function (node) {
        return {
          id: node.id || "",
          name: node.getAttribute("name") || "",
          selector: node.id ? "#" + cssEscape(node.id) : "",
          label: findLabel(node),
          tagName: node.tagName.toLowerCase()
        };
      });
  }

  function findLabel(node) {
    if (!node) return "";
    if (node.id) {
      var explicit = document.querySelector("label[for='" + cssEscape(node.id) + "']");
      if (explicit) return explicit.textContent.trim();
    }
    var labelled = node.closest("[data-label]");
    if (labelled) return labelled.getAttribute("data-label") || "";
    var row = node.closest(".form-row,.xcreator-field,tr,li,div");
    return row ? (row.getAttribute("aria-label") || "").trim() : "";
  }

  function fillFields(values, mappings, options) {
    options = options || {};
    if (!options.confirmed) {
      return { applied: {}, errors: ["confirmation_required"] };
    }
    var applied = {};
    var errors = [];
    Object.keys(values || {}).forEach(function (key) {
      var mapping = mappings ? mappings[key] : null;
      var target = resolveTarget(mapping, options.root || document);
      if (!target) {
        errors.push("missing:" + key);
        return;
      }
      if (target.matches && target.matches("button,[type='button'],[type='reset'],a")) {
        errors.push("unsupported:" + key);
        return;
      }
      setFieldValue(target, values[key]);
      applied[key] = target.id || target.getAttribute("name") || mapping.target;
    });
    return { applied: applied, errors: errors };
  }

  function setFieldValue(target, value) {
    if ("value" in target) {
      target.value = value == null ? "" : String(value);
    } else {
      target.textContent = value == null ? "" : String(value);
    }
    target.dispatchEvent(new Event("input", { bubbles: true }));
    target.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function renderAssistant(config, context) {
    if (!config || !config.enabled || config.entry === "none") return null;
    if (document.getElementById("xc-assistant-root")) return document.getElementById("xc-assistant-root");

    var root = document.createElement("div");
    root.id = "xc-assistant-root";
    root.style.cssText = "position:fixed;right:22px;bottom:22px;z-index:99999;font-family:Arial,'Microsoft YaHei',sans-serif;";

    var button = document.createElement("button");
    button.type = "button";
    button.textContent = config.title || "知识助手";
    button.setAttribute("aria-label", config.title || "知识助手");
    button.style.cssText = "border:0;border-radius:999px;padding:12px 16px;background:#14532d;color:#fff;box-shadow:0 8px 20px rgba(0,0,0,.22);cursor:pointer;";

    var panel = document.createElement("section");
    panel.hidden = true;
    panel.style.cssText = "width:360px;max-width:calc(100vw - 32px);height:460px;max-height:calc(100vh - 96px);margin-bottom:10px;background:#fff;border:1px solid #d5d9e2;box-shadow:0 14px 40px rgba(15,23,42,.22);display:flex;flex-direction:column;";
    panel.innerHTML = [
      "<header style='padding:12px 14px;border-bottom:1px solid #e5e7eb;font-weight:700;'>", escapeHtml(config.title || "知识助手"), "</header>",
      "<div data-xc-assistant-log style='flex:1;overflow:auto;padding:12px;font-size:14px;line-height:1.5;'></div>",
      "<form data-xc-assistant-form style='display:flex;gap:8px;padding:10px;border-top:1px solid #e5e7eb;'>",
      "<input data-xc-assistant-question style='flex:1;padding:8px;border:1px solid #cbd5e1;' placeholder='", escapeHtml(config.placeholder || "请输入问题"), "'>",
      "<button type='submit' style='padding:8px 12px;border:1px solid #14532d;background:#14532d;color:#fff;'>询问</button>",
      "</form>"
    ].join("");

    button.addEventListener("click", function () {
      panel.hidden = !panel.hidden;
      if (!panel.hidden) renderAssistantState(panel, config.mode === "disabled" ? "disabled" : "ready", config);
    });
    panel.querySelector("[data-xc-assistant-form]").addEventListener("submit", function (event) {
      event.preventDefault();
      askAssistant(panel, config, context);
    });

    root.appendChild(panel);
    root.appendChild(button);
    document.body.appendChild(root);
    return root;
  }

  function renderAssistantState(panel, state, config, payload) {
    var log = panel.querySelector("[data-xc-assistant-log]");
    if (!log) return;
    if (state === "disabled") log.innerHTML = "<p>知识助手当前未启用。</p>";
    if (state === "ready") log.innerHTML = "<p>可以询问当前页面相关的制度、流程或字段含义。</p>";
    if (state === "loading") log.innerHTML = "<p>正在查询知识库...</p>";
    if (state === "unsupported") log.innerHTML = "<p>知识库中没有找到足够依据回答这个问题。</p>";
    if (state === "error") log.innerHTML = "<p>知识助手暂时不可用，请稍后重试。</p>";
    if (state === "answered") {
      var sources = (payload.sources || []).map(function (source) {
        return "<li><button type='button' data-source-id='" + escapeHtml(source.sourceId || source.source_id || "") + "'>" + escapeHtml(source.title || "来源") + "</button></li>";
      }).join("");
      log.innerHTML = "<p>" + escapeHtml(payload.answer || "") + "</p><ul>" + sources + "</ul><div><button type='button' data-feedback='helpful'>有帮助</button> <button type='button' data-feedback='bad'>不准确</button></div>";
    }
  }

  function askAssistant(panel, config, context) {
    var input = panel.querySelector("[data-xc-assistant-question]");
    var question = input ? input.value.trim() : "";
    if (!question) return;
    renderAssistantState(panel, "loading", config);
    if (config.mode === "stub" || !config.askUrl) {
      renderAssistantState(panel, "answered", config, {
        answer: "这是 stub 模式回答：真实知识库接通前，仅用于验证入口、权限上下文和引用展示。",
        sources: [{ sourceId: "stub-source", title: "本地测试知识源" }]
      });
      return;
    }
    window.fetch(config.askUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(redactValue({ question: question, scope: context }))
    })
      .then(function (response) { return response.json(); })
      .then(function (payload) {
        renderAssistantState(panel, payload.status === "answered" ? "answered" : "unsupported", config, payload);
      })
      .catch(function () { renderAssistantState(panel, "error", config); });
  }

  function renderFallbackEntry(config, context, container) {
    if (!config || !config.enabled) return null;
    var button = document.createElement("button");
    button.type = "button";
    button.textContent = config.title || "知识助手";
    button.addEventListener("click", function () {
      var root = renderAssistant(Object.assign({}, config, { entry: "floating" }), context);
      var panel = root ? root.querySelector("section") : null;
      if (panel) panel.hidden = false;
    });
    (container || document.body).appendChild(button);
    return button;
  }

  function renderOcrReview(container, result, mappings, onApply) {
    if (!container) return null;
    var fields = result && result.fields ? result.fields : {};
    var panel = document.createElement("section");
    panel.setAttribute("data-xc-ocr-review", "true");
    panel.style.cssText = "border:1px solid #cbd5e1;padding:10px;margin-top:8px;background:#fff;";
    var rows = Object.keys(fields).map(function (key) {
      var field = fields[key];
      var checked = field.requiresManualReview || field.requires_manual_review ? "" : " checked";
      var mapped = mappings && mappings[key] ? "已映射" : "未映射";
      return "<label style='display:block;margin:6px 0;'><input type='checkbox' data-field-key='" + escapeHtml(key) + "'" + checked + "> " + escapeHtml(key) + ": <input data-value-key='" + escapeHtml(key) + "' value='" + escapeHtml(field.normalized || field.raw || "") + "'> <small>" + mapped + "</small></label>";
    }).join("");
    panel.innerHTML = "<strong>OCR 识别草稿</strong>" + rows + "<div><button type='button' data-apply>应用选中字段</button> <button type='button' data-cancel>取消</button></div>";
    panel.querySelector("[data-apply]").addEventListener("click", function () {
      var values = {};
      Array.prototype.slice.call(panel.querySelectorAll("[data-field-key]:checked")).forEach(function (checkbox) {
        var key = checkbox.getAttribute("data-field-key");
        var valueInput = panel.querySelector("[data-value-key='" + cssEscape(key) + "']");
        if (valueInput) values[key] = valueInput.value;
      });
      var outcome = fillFields(values, mappings, { confirmed: true });
      if (onApply) onApply(outcome);
    });
    panel.querySelector("[data-cancel]").addEventListener("click", function () {
      panel.remove();
    });
    container.appendChild(panel);
    return panel;
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function init(options) {
    options = options || {};
    var context = collectPageContext();
    var config = options.config || {};
    if (config.assistant && config.assistant.enabled) {
      if (config.assistant.entry === "fallback") renderFallbackEntry(config.assistant, context, options.fallbackContainer);
      else renderAssistant(config.assistant, context);
    }
    return {
      context: context,
      uploads: discoverUploads(),
      fields: discoverFields()
    };
  }

  window.XCreatorAssistantOcrLoader = {
    init: init,
    collectPageContext: collectPageContext,
    discoverUploads: discoverUploads,
    discoverFields: discoverFields,
    fillFields: fillFields,
    renderAssistant: renderAssistant,
    renderFallbackEntry: renderFallbackEntry,
    renderOcrReview: renderOcrReview,
    redactValue: redactValue,
    isBusinessAction: function (value) { return BUSINESS_ACTIONS.test(value || ""); }
  };
})();

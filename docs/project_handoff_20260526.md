# 项目交接文档：AI 质检与 XCreator 接入

更新时间：2026-05-26  
工作目录：`E:\yolo`  
当前分支：`codex/add-ai-qc-field-inspection`

## 1. 总体状态

这段时间主要做了两条线：

1. AI 质检现场素材与 PPE/构件质检 Demo 交付。
2. XCreator 低代码平台的知识库助手和 OCR 自动填充接入方案与第一版代码骨架。

当前可以交接的核心判断：

- PPE / AI 质检链路已经能做技术演示和复核闭环，但不能当作业务验收准确率承诺。
- 钢筋点数不能说“模型已训练完成”；`field-qc-0026` 的 `118` 是端面候选圈，不是验收数量，旧版 `5` 已撤销。
- XCreator 生产环境只做过只读探查；已经形成 loader + adapter + OCR bridge 的低风险接入骨架，但真实上线前必须先在测试/克隆页验证。

## 2. 019e43f2 线程工作总结

线程 ID：`019e43f2-5108-7150-ad50-6be845cfc7cd`  
本地会话文件：`C:\Users\R\.codex\sessions\2026\05\20\rollout-2026-05-20T13-53-34-019e43f2-5108-7150-ad50-6be845cfc7cd.jsonl`

这条线程主要产出了 AI 质监现场汇报材料和复核资料，最终落在：

- `AI_QC_Human_Delivery_20260525/00_README_FIRST.md`
- `AI_QC_Human_Delivery_20260525/01_AI_QC_Demo_Leader_Brief_CN.docx`
- `AI_QC_Human_Delivery_20260525/03_AI_QC_Result_Gallery_CN.html`
- `AI_QC_Human_Delivery_20260525/03_AI_QC_Result_Gallery_CN.docx`
- `AI_QC_Human_Delivery_20260525/04_AI_QC_Clear_Review_CN.html`
- `AI_QC_Human_Delivery_20260525/04_AI_QC_Clear_Review_CN.docx`
- `AI_QC_Human_Delivery_20260525/05_AI_QC_Training_Process_Reassessment_CN.md`
- `AI_QC_Human_Delivery_20260525/06_AI_QC_Leader_Report_Updated_CN.docx`
- `AI_QC_Human_Delivery_20260525/06_AI_QC_Leader_Report_Updated_CN.md`

关键口径已经调整：

- 当前可以说“AI 质监辅助评估 Demo 已完成一轮现场素材验证”。
- 不能说“钢筋点数模型已经训练完成”。
- `field-qc-0026` 是唯一可用端面图，`118` 是候选检测圈，需要人工点核。
- 旧版 `5` 是漏检结果，已撤销。
- 钢筋点数要补拍端面样本、人工标注真值、重新训练、独立测试，再按计数误差验收。
- 套筒和混凝土可以优先作为“辅助复核 Demo”，不要说成自动正式验收。

对应经验：

- 对外材料必须区分“候选检测”“人工复核”“正式验收数量”。
- 模型演示要有边界，不要把规则兜底或候选框包装成已训练能力。
- 现场图像质量决定上限：端面、近景、比例尺、构件编号、真值标注比调阈值更重要。
- 给领导看的资料要用粗框、局部放大和中文结论，底层 CSV/JSON 只做追溯。

## 3. PPE 与现场质检代码工作

已有工作包括：

- 视频/图片样本整理。
- 抽帧、伪标注、多模态质检、复核队列。
- PPE strict demo 输出。
- 现场构件质检规则和脚本，包括钢筋材料点数、套筒连接、混凝土面异常提示等。
- 多个测试文件覆盖数据工厂、复核队列、预标注、字段规则、构件质检脚本。

重要文档：

- `docs/station_ppe_current_work_summary_20260521.md`
- `docs/station_ppe_multimodal_qc_20260519.md`
- `docs/station_ppe_v2_baseline_report_20260521.md`
- `docs/station_ppe_v3_class_map_and_annotation_rules_20260521.md`
- `docs/station_ppe_v3_data_input_audit_20260521.md`

当前边界：

- 可演示：人员/安全帽/反光衣疑似状态、事件表、标注图、复核队列、下一轮训练数据闭环。
- 不可承诺：业务级自动告警准确率、身份级人脸识别、复杂遮挡下稳定 PPE 判断、钢筋侧面图精确点数。

下一步：

1. 人工确认复核队列。
2. 修正 `labels_reviewed`。
3. 补硬负样本。
4. 重训模型。
5. 用 strict demo 再验收。
6. 补近中景摄像头样本作为身份入口。

## 4. XCreator 低代码平台工作

已经完成只读探查和 OpenSpec：

- `docs/xcreator-lowcode-platform-handbook.md`
- `docs/xcreator-project-memo.md`
- `docs/xcreator-ocr-and-assistant-discovery-20260525.md`
- `docs/xcreator-target-page-baseline-20260525.md`
- `docs/xcreator-integration-deployment-runbook.md`
- `openspec/changes/add-xcreator-assistant-and-ocr-autofill/`

核心结论：

- XCreator 运行态是低代码 JSON 配置驱动，不是普通 Vue/React 前端工程。
- 页面主要是 WUI / jQuery / jqGrid / iframe / actionOptions / serviceCode。
- 知识库助手应该通过轻量 loader 挂入口，复杂逻辑放后端 adapter。
- OCR 应该挂在已有上传/附件控件旁边，走“上传后识别 -> 草稿确认 -> 回填字段”，不能自动保存。
- 生产系统只读探查；没有执行保存、提交、删除、导入导出、下载、归档、审批。

已经实现的代码骨架：

- `xcreator_integration/config.py`：feature flag、endpoint alias、生产 localhost 阻断。
- `xcreator_integration/redaction.py`：`cwUserToken`、`cwAppToken`、session/auth/cookie 脱敏。
- `xcreator_integration/knowledge.py`：知识库 adapter、stub/disabled 模式、有来源才回答。
- `xcreator_integration/ocr.py`：OCR provider、job、字段标准化、低置信度人工复核、保留期清理。
- `xcreator_integration/xcreator_bridge.py`：上传控件发现、字段映射 dry-run、确认后回填。
- `xcreator_integration/static/xcreator-loader.js`：悬浮小球、fallback、OCR review panel、字段回填。
- `xcreator_integration/examples/cloned-page-smoke.html`：本地克隆测试页。

OpenSpec 当前状态：

- 已完成 33/37。
- 未完成项是外部依赖项：真实浏览器/测试页验证、知识库负责人确认、完整集成测试、业务/安全审批。

XCreator 下一步：

1. 找一个非生产/克隆 XCreator 页面。
2. 挂 `xcreator-loader.js`。
3. 在真实 Chrome/测试环境验证小球、OCR 面板、字段回填和按钮避让。
4. 找 `智能小助手后台` 负责人确认真实问答 API、鉴权、引用来源。
5. 确认 OCR provider，优先内网/本地服务。
6. 做首个页面字段映射表。
7. 安全/业务审批后灰度生产。

## 5. VPN / 代理经验

XCreator 域名要绕过系统代理/VPN：

```text
xcreator.sz-mtrtest.com
sz-mtrtest.com
*.sz-mtrtest.com
xsso.sz-mtrtest.com
```

如果平台突然打不开，先查 Windows 代理例外，而不是先怀疑页面代码。

PowerShell 检查：

```powershell
$path = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
Get-ItemProperty -Path $path -Name ProxyEnable,ProxyServer,ProxyOverride
```

## 6. 验证记录

本轮验证通过：

```powershell
python -m pytest tests -q
```

结果：`96 passed`

```powershell
python -m pytest tests/test_xcreator_integration.py tests/test_xcreator_loader_assets.py -q
```

结果：`10 passed`

```powershell
openspec validate add-xcreator-assistant-and-ocr-autofill --strict
```

结果：`Change 'add-xcreator-assistant-and-ocr-autofill' is valid`

全仓库裸跑 `python -m pytest -q` 会被 `PPE/` 里的外部样例测试挡住，原因是缺旧权重 `best.pt` 和 `gluoncv`，不是本次变更造成的。

## 7. Git 注意事项

- `.local/` 是本机外部克隆/缓存目录，已加入 `.gitignore`，不应提交。
- 大模型、图片、视频、压缩包、运行输出目录已有 ignore 规则。
- 本次用户明确要求 `commit all`，所以本次提交会纳入所有仓库相关未提交产物。

## 8. 最短接手路线

1. 先读 `AI_QC_Human_Delivery_20260525/00_README_FIRST.md`，明确对外汇报口径。
2. 再读 `docs/project_handoff_20260526.md`，掌握全局。
3. AI 质检继续推进时，优先做人工复核和补样训练。
4. XCreator 继续推进时，先找测试页，不碰生产写操作。
5. 任何对外演示都先确认“候选、辅助、正式验收”三类口径没有混在一起。

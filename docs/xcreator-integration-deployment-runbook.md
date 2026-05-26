# XCreator 知识助手与 OCR 接入部署/回滚手册

更新时间：2026-05-25

## 1. 产物

- Python 集成核心：`xcreator_integration/`
- 页面 loader：`xcreator_integration/static/xcreator-loader.js`
- 本地克隆冒烟页：`xcreator_integration/examples/cloned-page-smoke.html`
- 单元测试：`tests/test_xcreator_integration.py`、`tests/test_xcreator_loader_assets.py`

## 2. 配置原则

- 不在生产页写死 `localhost`。
- 所有服务地址通过 endpoint alias 配置。
- 功能开关按 `tenantCode + appCode + pageCode/pageId + environment + role` 解析。
- 生产页默认 disabled，只有审批通过的页面/角色才打开。
- 日志和诊断必须先做 token 脱敏。

## 3. 推荐启用顺序

1. 本地克隆页：开启助手 stub + OCR fixture。
2. 测试 XCreator 克隆页：只加载 loader，确认布局、搜索、分页、上传、操作列无回归。
3. 测试页开启助手 stub：确认悬浮入口、禁用态、加载态、引用态、反馈态。
4. 测试页开启 OCR dry-run：确认上传槽、字段映射、缺失字段、重复目标。
5. 测试页开启 OCR confirmed-fill：只回填字段，不保存。
6. 接入真实知识库 test endpoint。
7. 接入可信内网 OCR provider。
8. 安全/业务审批后小范围生产灰度。

## 4. 回滚方式

- 首选：关闭对应页面 feature flag。
- 次选：把助手模式改成 `disabled`，OCR slot 改成 `enabled=false`。
- 紧急：移除页面自定义脚本或菜单入口里的 loader 引用。
- 后端服务可独立下线，不影响原 XCreator 页面原有保存、上传、列表和流程。

## 5. 生产安全检查

必须确认：

- OCR 回填不调用保存/提交/删除/归档/下载/导入/导出/审批。
- 知识助手无来源时拒答，不编造答案。
- 审计只存 page/user 标识、sourceId、结果状态和置信度摘要，不存 token。
- OCR 临时文件或中间结果按 retention policy 清理，不删除原业务附件。
- `xcreator.sz-mtrtest.com`、`sz-mtrtest.com`、`*.sz-mtrtest.com` 走系统代理例外。

## 6. 验证命令

```powershell
python -m pytest tests/test_xcreator_integration.py tests/test_xcreator_loader_assets.py -q
openspec validate add-xcreator-assistant-and-ocr-autofill --strict
```


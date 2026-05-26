# XCreator OCR 与知识助手只读探查记录

更新时间：2026-05-25  
范围：生产环境只读探查，不执行保存、提交、删除、导入导出、下载、归档、审批等业务动作。  
敏感信息处理：不记录 `cwUserToken`、账号、姓名、真实业务数据或配置值。

## 1. 本次确认的事实

- 当前平台运行页：`汇擎智建-工程建设管理平台`
- 当前主应用编码：`acbbhqib`
- 只读页配置接口可读到约 551 个页面配置。
- 应用树接口可读到约 155 个应用/节点。
- 平台不是常规单体前端工程，而是低代码 JSON 配置驱动的运行态页面；主要形态包括 `grid`、`table`、`tab`、`flowForm`、按钮 `actionOptions`、服务 `serviceCode`、iframe/附件页等。
- 列表页里大量出现通用上传/编辑配置痕迹，但这类通常只是 jqGrid/editoptions 的通用能力，不应直接当作 OCR 入口。

## 2. 知识库/知识问答现状

应用树里已经存在一个明确节点：

| 名称 | appId | 备注 |
| --- | --- | --- |
| 智能小助手后台 | `1b25ad02-8d7b-b725-cbc7-989734d84966` | 说明平台里已有助手后台痕迹 |

继续只读查看页面配置后，能看到它关联出的后台页：

| 页面 | appCode | pageCode | pageId | 发现 |
| --- | --- | --- | --- | --- |
| 首页 | `x84s4xlb` | `index` | `489d5a08-f684-4a34-a37b-6f2b3b847dd2` | 助手后台入口页 |
| 访问记录 | `ba6vmywc` | `recordsList` | `147d30b3-0f21-41d4-91ad-e75c41335aa5` | 有 `recordsPageQuery`，字段含登录次数、提问次数等 |
| 系统配置管理 | `ba6vmywc` | `sysConfigList` | `933db43a-6457-4b9b-8e6e-0e34c3de3df8` | 有 `sysConfigPageQuery`、`sysConfigDelete` |
| 系统配置信息 | `ba6vmywc` | `sysConfigForm` | `bf7eee8a-e711-438b-a13d-e248d4825b38` | 字段含配置编码、配置值、配置名称、启用；保存服务为 `sysConfigInsertOrUpdate` |
| 报表统计 | `ba6vmywc` | `bbtj` | `c4ab585a-e37d-4f67-b9f6-6073539956ba` | 有统计组件 |
| 反馈记录管理 | `ba6vmywc` | `feedbackList` | `e0336e3c-14b0-40fc-b02a-8bfa8dfa4931` | 字段含问题内容、模型答案、反馈内容、反馈时间 |

结论：

- 知识问答不像是完全从零做，平台内已经有“智能小助手后台”的管理痕迹。
- 当前还没有确认前台悬浮小球是否已经挂到工程建设平台主应用。
- 下一步不应在生产里点配置、保存或读真实配置值，而应让系统负责人提供测试环境或说明这个后台的真实问答 API。

建议集成方式：

```text
XCreator 页面
  -> 悬浮小球 loader
  -> assistant backend
  -> knowledge adapter
  -> 既有智能小助手/知识库系统
```

前端低代码页只做入口和上下文采集；真正问答、鉴权、引用来源、权限过滤、日志脱敏都放在后端 adapter。

## 3. OCR 候选页扫描结果

### 3.1 强候选：已有附件 iframe 的流程表单

| 页面 | appCode | pageCode | pageId | 发现 | 判断 |
| --- | --- | --- | --- | --- | --- |
| 安全教育流程表单页面(废弃) | `acbbhqib` | `uapSafetyEduFlowForm` | `961be927-9412-3ba5-b8e0-6c4afb1c856b` | 有 `eduFileCell`/`eduFile`，并出现附件 iframe / `common/sysAttachmentList` 形态 | 技术形态最清楚，但标记为废弃，不能直接作为业务试点 |
| 证件借用流程表单页面 | `pao1l0xs` | `certificateBorrowtest1FlowForm` | `018d69e7-a8b3-46e4-993a-c600ca75f678` | 有流程表单和附件 iframe 形态 | 可作为“附件识别后回填”的参考形态，需确认是否测试/克隆应用 |
| 证件及借用关联表流程表单页面 | `pao1l0xs` | `borrowReftesttestFlowForm` | `f79f05b9-832e-488d-bc35-0be837eb29d3` | 有流程表单和附件 iframe 形态 | 更像测试/关联表，不适合首个业务试点 |

这类页面说明 OCR 最适合挂在“已有附件/文件 iframe 上传组件旁边”，识别后只生成草稿字段。

### 3.2 字段映射候选：有证件字段但未发现真实上传控件

| 页面 | appCode | pageCode | pageId | 可回填字段线索 | 判断 |
| --- | --- | --- | --- | --- | --- |
| 证件信息详情表单页面 | `aji0nnjl` | `certificateInfotest1Form` | `2f596471-0d6a-463f-a394-385b260a4ee8` | `certificateName`、`certificateNum`、`issueDate`、`status`、`descn` 等 | 适合做证件 OCR 字段映射，但当前配置未看到附件 iframe，需要另找上传入口或加上传控件 |
| 用户管理表单 | `uuapv2` | `secUserManageForm` | `3ffb6e3d-829f-4018-aafc-63edf932994a` | 用户姓名、账号、工号、身份证等 | 身份证 OCR 字段很匹配，但当前未看到照片/附件上传入口 |
| 证件借用 | `aji0nnjl` | `zjjy` | `bb68d173-f61c-4d3a-957d-797350ced71e` | 借用单相关字段 | 未看到上传入口，优先级低 |

### 3.3 技术测试页

| 页面 | appCode | pageCode | pageId | 判断 |
| --- | --- | --- | --- | --- |
| 上传文件测试 | `axgkpgau` | `scwjcs` | `85f0db65-f3f5-44e2-8a11-57b57893c759` | 可用于研究上传控件形态，但不应在生产业务数据上试 |
| 批次号附件信息 | `axgkpgau` | `pchfjxx` | `4cb5b0e0-dd2d-4321-9b01-f53017012e53` | 附件/批次号相关，适合看技术结构，不适合直接落生产 |

### 3.4 暂不适合作 OCR 首点的页面

- `证件信息列表页面`、`证件借用列表页面` 等列表页：多为 grid 和操作列，适合跳转到表单，不适合直接挂 OCR。
- `安全教育列表页面`：能看到 `eduFile` 列，但列表页不是首选；真正要看的是当前详情/流程表单。
- `安全教育详情表单页面` `uapSafetyEduForm`：当前通过旧配置接口没有看到附件控件细节，可能是新版 AntD 母版/另一套渲染配置，需要打开具体运行态表单或找新版配置接口继续确认。

## 4. OCR 推荐接入方式

推荐使用“上传后识别”，不要改原上传链路：

```text
用户照常上传证件/照片/附件
  -> 上传成功后在控件旁显示“识别”
  -> OCR 后端读取 attachmentId 或临时文件
  -> 返回结构化字段 + 置信度
  -> 弹出草稿确认
  -> 用户确认后仅填入当前表单字段
  -> 用户自己点保存/提交
```

关键边界：

- OCR 不自动保存。
- OCR 不自动提交。
- OCR 不删除、归档、下载、导入、导出。
- OCR 只在用户确认后写入前端表单值。
- 所有页面启用都通过 feature flag 控制。
- 字段映射配置应该外置，例如：

```json
{
  "appCode": "aji0nnjl",
  "pageCode": "certificateInfotest1Form",
  "uploadField": "certificateAttachment",
  "ocrType": "certificate",
  "fieldMap": {
    "name": "certificateName",
    "number": "certificateNum",
    "issueDate": "issueDate",
    "status": "status"
  }
}
```

## 5. 低代码平台里怎么挂

优先顺序：

1. 页面级自定义脚本：适合先做单页试点。
2. 公共 layout/header 注入 loader：适合知识助手悬浮球全局启用。
3. iframe/openWindow：适合把外部助手或 OCR 确认面板作为独立模块嵌入。
4. 后端 adapter/service：承接真正的知识库问答、OCR、日志、权限和脱敏。

知识助手和 OCR 都不要把复杂逻辑写死在低代码配置里。低代码配置只负责“挂入口”和“传上下文”。

## 6. 下一步建议

1. 让负责人确认 `智能小助手后台` 的实际问答 API、鉴权方式、测试环境地址。
2. 选一个非生产/克隆页面作为 OCR 试点，优先选择已有附件 iframe 的流程表单。
3. 如果必须从业务页开始，优先打开 `证件信息详情表单页面` 或 `用户管理表单` 的运行态表单，确认是否能加上传控件或旁路上传入口。
4. 为 OCR 做一张外置映射表：`appCode + pageCode + upload selector + fieldMap + ocrType + enabled`。
5. 先实现 stub：悬浮助手能打开、OCR 能返回假字段、确认后能填字段，但不保存。
6. 在测试环境验证不会触发保存、提交、删除、归档、导入导出。
7. 再接真实知识库和真实 OCR 服务。

## 7. 仍需补齐的信息

- 智能小助手后台的真实 API 文档或负责人。
- 知识库是否支持引用来源、权限过滤、多租户过滤。
- OCR 服务供应方、证件类型范围、返回字段格式。
- 第一个试点页面的运行态 URL。
- 非敏感测试图片。
- 测试环境或克隆页面。
- 系统代理/VPN 例外是否能持久化，避免每次被 v2rayN 等工具重写。

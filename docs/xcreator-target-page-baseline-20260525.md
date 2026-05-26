# XCreator 首批接入页只读基线

更新时间：2026-05-25  
范围：生产环境只读观察 + 本地非生产克隆页，不记录 token、账号、姓名或真实业务数据。

## 1. 当前生产只读入口

- 平台：汇擎智建-工程建设管理平台
- 主应用编码：`acbbhqib`
- 当前主页面 iframe：待办页
- 可读页面配置数量：约 551
- 可读应用/节点数量：约 155

当前看到的主页面菜单主要是个人中心和电子档案入口。该入口本身是列表/待办形态，不适合直接做 OCR 首点。

## 2. OCR 候选页面基线

| 页面 | appCode | pageCode | pageId | 上传/附件观察 | 适合程度 |
| --- | --- | --- | --- | --- | --- |
| 安全教育流程表单页面(废弃) | `acbbhqib` | `uapSafetyEduFlowForm` | `961be927-9412-3ba5-b8e0-6c4afb1c856b` | `eduFile`、附件 iframe / `common/sysAttachmentList` 形态 | 技术参考，不做正式业务试点 |
| 证件借用流程表单页面 | `pao1l0xs` | `certificateBorrowtest1FlowForm` | `018d69e7-a8b3-46e4-993a-c600ca75f678` | 流程表单 + 附件 iframe 形态 | 候选，但需确认是否测试/克隆应用 |
| 证件信息详情表单页面 | `aji0nnjl` | `certificateInfotest1Form` | `2f596471-0d6a-463f-a394-385b260a4ee8` | 证件名称、证件编号、核发日期、状态等字段清楚；未确认真实上传控件 | 字段映射候选 |
| 用户管理表单 | `uuapv2` | `secUserManageForm` | `3ffb6e3d-829f-4018-aafc-63edf932994a` | 用户姓名、身份证等字段清楚；未确认真实上传控件 | 身份证字段候选 |
| 上传文件测试 | `axgkpgau` | `scwjcs` | `85f0db65-f3f5-44e2-8a11-57b57893c759` | 上传文件测试页 | 技术测试，不碰生产业务 |
| 批次号附件信息 | `axgkpgau` | `pchfjxx` | `4cb5b0e0-dd2d-4321-9b01-f53017012e53` | 批次/附件相关 | 技术参考 |

## 3. 业务动作按钮避让

接入层必须避让以下按钮/动作：

- 保存
- 提交
- 删除 / 批量删除
- 归档
- 下载
- 导入 / 导出
- 审批 / 通过 / 驳回

当前实现的 `SafeFillBridge` 和页面 loader 只设置字段值并触发 `input/change` 事件，不点击上述动作。

## 4. 本地非生产克隆页

为避免在生产页上试动作，已创建本地克隆冒烟页：

- [cloned-page-smoke.html](E:/yolo/xcreator_integration/examples/cloned-page-smoke.html:1)

本地克隆页模拟：

- 证件名称字段：`certificateName`
- 证件编号字段：`certificateNum`
- 核发日期字段：`issueDate`
- 证件附件上传控件：`certificateAttachment`
- 保存/提交按钮：只作为避让对象，不由 OCR 或助手触发

## 5. 后续真实试点前置条件

- 业务负责人确认非生产/克隆 XCreator 页面。
- 安全负责人确认知识库和 OCR 服务端点。
- 提供非敏感证件/材料样例。
- 确认首批字段映射表。
- 生产启用前完成 feature flag、回滚、审计和脱敏检查。


# 工地 PPE 识别现阶段工作总结

日期：2026-05-21

## 1. 当前结论

目前已经完成从现场视频到第一版 PPE 识别闭环的打通，包括：

```text
视频样本整理
抽帧
初始伪标注
多模态质检
训练第一版模型
生成 demo 识别结果
多模态验收
错误分析
复核队列生成
Codex 草稿标签生成
```

现阶段可以明确表述为：

> 已完成工地 PPE 识别技术链路打通，能够输出人员、安全帽、反光衣疑似状态，并形成事件 CSV、标注图、复核队列和下一轮训练数据闭环。当前模型可用于技术演示和样板验证，但自动告警准确性尚未达到业务验收标准，需进一步进行人工标签修正和二次训练。

核心判断：

```text
链路已经打通，可以做技术演示；
但当前不能作为业务验收结果。
```

## 2. 当前模型能力判断

当前模型能力分化比较明显：

```text
人员检测：
已有可用基础，但远景、遮挡、局部人体仍不稳定。

安全帽检测：
相对最可用，能支撑第一版演示。

反光衣检测：
模型头没有真正训起来，目前主要靠颜色规则兜底。

人脸识别：
当前高位视频不适合做，必须依赖近景固定点位摄像头。
```

因此当前不建议对外承诺“完整自动告警准确率已达交付标准”。更准确的说法是：

```text
已打通 PPE 识别演示链路；
可输出人员、安全帽、反光衣疑似状态；
正在通过复核队列和人工修正样本提升模型准确性。
```

## 3. Demo 验收情况

原始 demo 存在明显问题：

```text
同一个人被重复计数
袋子、覆盖物、灭火器、材料被误检成人
部分戴帽人员被误报未戴帽
反光衣识别依赖颜色规则，不能算模型稳定能力
```

因此后续做了 `strict_v5` 版本，将输出拆成三层：

```text
自动演示事件
人工复核队列
拒绝候选
```

`strict_v5` 当前结果：

```text
accepted person event rows: 19
auto_demo_ok: 13
needs_review: 6
rejected person candidates: 45
manual review queue rows: 39
```

解释：

```text
13 条可作为技术演示中的相对干净样本；
6 条虽然被识别到，但因为依赖规则、置信度中等或 PPE 状态不确定，需要复核；
39 条进入下一轮人工复核队列，用于修标签和补硬负样本。
```

## 4. 复核队列与草稿标签

已生成复核工作区：

```text
E:\yolo\datasets\station_ppe_20260520_review_queue_v5_workspace
```

工作区包含：

```text
images\
crops\
labels_current\
labels_reviewed\
labels_codex_draft\
crop_contact_sheets\
codex_visual_triage_20260520.csv
codex_draft_label_manifest.csv
```

Codex 多模态初筛结果：

```text
true_worker_fix_label: 24
hard_negative_not_worker: 11
unclear_skip: 3
ppe_status_fix: 1
```

这说明复核队列是有价值的：

```text
一部分是被压掉的真实工人，需要补回或修框；
一部分是袋子、覆盖物、材料、灭火器等误检对象，适合作为硬负样本；
少量样本不清晰，应跳过或等人工确认。
```

基于初筛生成了一版可回滚草稿标签：

```text
E:\yolo\datasets\station_ppe_20260520_review_queue_v5_workspace\labels_codex_draft
```

草稿标签结果：

```text
person_added: 1
person_removed: 10
skipped: 33
```

解释：

```text
多数真实工人原标签中已经存在 person 框，因此没有重复添加；
本轮主要价值是清理了 10 个硬负样本中的误 person 框；
草稿标签不能等同于人工金标，只能作为实验训练或人工复核参考。
```

## 5. 当前重要产物

模型权重：

```text
E:\yolo\runs\detect\station_ppe_20260519_codex_v2_3class\weights\best.pt
```

strict_v5 demo 输出：

```text
E:\yolo\outputs\station_ppe_20260519_codex_v2_demo_strict_v5
```

复核工作区：

```text
E:\yolo\datasets\station_ppe_20260520_review_queue_v5_workspace
```

总技术记录：

```text
E:\yolo\docs\station_ppe_multimodal_qc_20260519.md
```

本总结文件：

```text
E:\yolo\docs\station_ppe_current_work_summary_20260521.md
```

## 6. 当前技术边界

当前系统可以演示：

```text
人员检测
安全帽检测
反光衣疑似状态判断
单帧事件 CSV 输出
标注图输出
复核队列生成
下一轮训练数据闭环
```

当前系统不能可靠承诺：

```text
业务级自动告警准确率
身份级人脸识别
跨摄像头稳定轨迹串联
复杂遮挡下稳定 PPE 判断
反光衣模型级稳定识别
```

特别说明：

```text
当前高位视频不适合做人脸识别。
如果要实现“什么人、什么时间、有什么违规行为”，必须增加近中景固定摄像头作为身份入口。
高位摄像头更适合做人、区域、安全帽、反光衣疑似状态和火灾/烟雾等异常场景检测。
```

## 7. 下一步建议

优先顺序如下：

```text
1. 人工确认 review_queue_v5_workspace 中的 39 条复核样本
2. 修正 labels_reviewed 中的 person / helmet / vest 标签
3. 将袋子、覆盖物、材料、灭火器等误检对象补成硬负样本
4. 用修正后的标签重训一版模型
5. 再用 strict demo 流程做二次验收
6. 补充近中景固定摄像头样本，尤其用于人脸、安全帽、反光衣的正面/半身识别
```

短期不建议继续只调阈值。当前主要矛盾不是参数，而是：

```text
样本质量
标签质量
硬负样本不足
近中景身份入口缺失
```

## 8. 建议汇报口径

对内汇报可以这样说：

> 目前已经完成工地 PPE 识别的端到端技术链路，能够从现场视频生成识别结果、事件表、标注图和复核队列。安全帽检测已有较明显效果，人员检测具备基础能力；反光衣目前仍依赖规则兜底，需补充人工标签继续训练。当前成果适合作为技术演示和样板验证，不建议作为业务验收结果。下一步重点是基于复核队列修正标签、补充硬负样本和近中景摄像头样本，再进行二次训练和验收。

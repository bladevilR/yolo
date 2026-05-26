# AI质监现场素材交付说明

请优先看新版 `01` 和 `04` 文件，不要把底层 CSV/JSON 当对外成果：

1. `01_AI_QC_Demo_Leader_Brief_CN.docx`
   - 最新领导汇报材料，已经更新“点数没有重新训练、118只是候选、旧版5个已撤销、下一步要重走训练闭环”的口径。
   - 同内容另存为 `06_AI_QC_Leader_Report_Updated_CN.docx`，方便区分更新版。

2. `04_AI_QC_Clear_Review_CN.html`
   - 会议展示优先打开这个。
   - 重新按“人能看懂”做了粗框、局部放大和中文结论。
   - 套筒不做数量清点，只判断连接状态、露丝风险和是否需要补拍。
   - 图片都已复制到 `clear_review_assets`，离线打开也能看。

3. `04_AI_QC_Clear_Review_CN.docx`
   - 适合发给领导或建设公司留档。
   - 内容与 HTML 清晰复核版一致，包含 22 张粗框放大复核板。

4. `05_AI_QC_Training_Process_Reassessment_CN.md`
   - 专门说明“有没有重新训练、为什么要重评训练流程、点数场景下一步怎么做”。
   - 结论：当前没有重新训练后的点数模型，`0026` 的 118 是候选检测，不是验收数量。

保留文件：

- `01_AI_QC_Demo_Leader_Brief_CN.docx`：最新版领导汇报说明。
- `06_AI_QC_Leader_Report_Updated_CN.docx`：最新版领导汇报说明的版本化副本。
- `06_AI_QC_Leader_Report_Updated_CN.md`：最新版领导汇报说明的 Markdown 源。
- `02_AI_QC_Demo_Human_Dashboard.html`：上一版简版看板。
- `03_AI_QC_Result_Gallery_CN.html/docx`：上一版全量图册，已被 `04` 清晰复核版替代。
- `05_AI_QC_Training_Process_Reassessment_CN.md`：点数训练流程重评估说明。
- `assets`：上一版代表图素材。
- `gallery_assets`：新版全量图册素材，共 44 张。
- `clear_review_assets`：最新版清晰复核板素材，共 22 张。

当前核心结论：

- 钢筋进场数量识别：7 张图片中只有 0026 端面图可用于点数；旧算法只输出 5 个点位已撤销，新版已圈出端面候选点，但仍需人工点核/补充标注后才能作为验收数量。
- 钢筋套筒露丝：这组图不做数量清点。0019 像单端/未完整连接，0020 和 0022 太远只能定位，0021 和 0023 疑似露丝偏多，适合做异常预警样本。
- 混凝土面检查：可做表观异常初筛。10 张图片共筛出多处疑似区域，输出位置和类型，但缺陷性质、严重程度需要现场复核。

底层 CSV/JSON 仍保留在 `datasets/field_qc`，仅用于开发追溯和复核，不作为对外汇报正文。

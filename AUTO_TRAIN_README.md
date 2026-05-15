# 🚀 YOLO 自动化训练 - 快速使用指南

## ⚡ 最快开始方式

### Windows用户

**方式1: 双击运行（最简单）**
```
📁 yolo/
   ├── RUN_AUTO_TRAIN.bat  ← 双击这个文件!
   └── ...
```

**方式2: PowerShell运行**
```powershell
# 在PowerShell中运行
.\RUN_AUTO_TRAIN.ps1
```

**方式3: 命令行**
```cmd
python auto_train.py
```

### Linux/Mac用户

```bash
python auto_train.py
```

---

## 📋 自动化流程说明

运行 `auto_train.py` 或 `RUN_AUTO_TRAIN.bat` 会自动执行以下步骤：

```
✅ 步骤1: 检查Python环境
   ↓
✅ 步骤2: 安装依赖库（自动）
   ↓
✅ 步骤3: 创建演示数据集（如果没有的话）
   - 100张训练图像
   - 20张验证图像
   - 20张测试图像
   ↓
✅ 步骤4: 配置data.yaml
   ↓
✅ 步骤5: 开始训练（YOLOv8x 最好的模型）
   ↓
✅ 完成: 生成训练结果
```

---

## 🎯 使用真实数据集

如果你有自己的数据，请按以下步骤操作：

### 1. 准备数据目录

```
raw_data/
├── images/              # 所有原始图像
│   ├── img001.jpg
│   ├── img002.jpg
│   └── ...
└── labels/              # YOLO格式标签 (.txt文件)
    ├── img001.txt
    ├── img002.txt
    └── ...
```

### 2. 运行自动脚本

脚本会自动检测到 `raw_data` 目录，并询问是否要划分数据集。

### 3. 使用你的数据进行训练

脚本会自动使用你的数据而不是演示数据集。

---

## 📊 训练参数

自动脚本使用以下默认参数（针对最好的模型）：

| 参数 | 值 | 说明 |
|------|-----|------|
| 模型 | yolov8x.pt | 最好的模型（68.2M参数） |
| Epochs | 100 | 训练轮数 |
| Batch Size | 16 | 批大小 |
| Image Size | 640 | 输入图像大小 |

### 显存要求

- **YOLOv8x**: 需要 8GB+ 显存（或GPU不可用时使用CPU）
- 如果显存不足，脚本会自动询问是否继续

---

## 🎨 完整模型对比

| 模型 | 大小 | 速度 | 精度 | 显存 | 自动脚本 |
|------|------|------|------|------|---------|
| yolov8n | 7M | ⚡⚡⚡ | 中 | 2GB | - |
| yolov8m | 49M | ⚡ | 好 | 4GB | - |
| **yolov8x** | 133M | 一般 | ⭐⭐⭐ | 8GB+ | ✅ 使用这个 |

**为什么选择YOLOv8x？**
- 精度最高，最适合垂直领域应用
- 自动脚本已配置好所有参数
- 适合轨道检测、设备状态检测等精度要求高的应用

---

## 🔍 训练过程监控

训练过程中会实时显示：

```
Epoch 1/100: [===========-->] 50% | Loss: 0.45 | mAP: 0.32
Epoch 2/100: [==========>   ] 60% | Loss: 0.38 | mAP: 0.45
...
```

---

## 📊 训练完成后

自动脚本完成后，结果会保存在：

```
runs/train/exp/
├── weights/
│   ├── best.pt         ← 最佳模型（使用这个）
│   └── last.pt
├── results.csv         ← 训练指标
├── results.png         ← 训练曲线图
└── confusion_matrix.png ← 混淆矩阵
```

---

## 💡 下一步操作

训练完成后，你可以：

### 1. 验证模型
```bash
python train.py --data data.yaml --val-only
```

### 2. 推理测试
```bash
python inference.py --weights runs/train/exp/weights/best.pt --source test_image.jpg
```

### 3. 实时检测
```bash
python inference.py --weights runs/train/exp/weights/best.pt --camera 0
```

### 4. 导出为ONNX（用于部署）
```bash
python train.py --export onnx --weights runs/train/exp/weights/best.pt
```

---

## ⚠️ 常见问题

### Q: 显存不足怎么办？
A: 脚本会自动降级到CPU，但会很慢。你也可以：
- 使用更小的模型：修改 `auto_train.py` 中的 `model = 'yolov8m.pt'`
- 减小批大小：修改 `batch = 8`

### Q: 网络太慢，模型下载失败？
A: 模型会被缓存到 `~/.cache/ultralytics/`，下次会使用本地版本。

### Q: 如何使用自己的数据？
A: 将数据放入 `raw_data/images/` 和 `raw_data/labels/` 目录，脚本会自动检测。

### Q: 训练多久完成？
A:
- GPU（RTX3080+）：1-2小时
- GPU（RTX2080）：2-4小时
- CPU：6-12小时+

### Q: 可以改变训练参数吗？
A: 可以。编辑 `auto_train.py` 或直接运行：
```bash
python train.py --data data.yaml --model yolov8l.pt --epochs 200 --batch 32
```

---

## 📚 相关文档

- **QUICKSTART.md** - 详细的使用指南
- **README.md** - 完整的项目文档
- **YOLO_Training_Tutorial.ipynb** - Jupyter教程

---

## 🎯 核心文件说明

| 文件 | 说明 |
|------|------|
| **auto_train.py** | 自动化训练脚本（核心） |
| **RUN_AUTO_TRAIN.bat** | Windows双击启动脚本 |
| **RUN_AUTO_TRAIN.ps1** | PowerShell启动脚本 |
| train.py | 完整训练脚本（高级用法） |
| inference.py | 推理脚本 |
| data.yaml | 数据集配置 |

---

## 🚀 现在就开始！

**Windows**: 双击 `RUN_AUTO_TRAIN.bat`

**Linux/Mac**: 运行 `python auto_train.py`

**就这么简单！** ✨

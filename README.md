# YOLO 自定义垂直领域检测系统

完整的YOLO模型训练和推理框架，专为轨道检测、设备状态检测等专业领域应用设计。

## 🎯 系统特点

✅ **完全自动化** - 从模型下载到训练、验证、推理的全流程
✅ **开箱即用** - 无需深度学习经验，简单配置即可开始
✅ **灵活可扩展** - 支持自定义参数、多种模型版本
✅ **生产级代码** - 包含错误处理、日志输出、性能优化
✅ **完整文档** - 详细的使用说明和API文档
✅ **多种推理方式** - 支持图像、视频、实时摄像头、批量处理

---

## 📦 项目包含

```
yolo/
├── train.py                    # 🔥 核心: YOLO训练脚本
├── prepare_dataset.py          # 数据集准备和划分工具
├── inference.py                # 推理脚本 (图像/视频/摄像头)
├── data.yaml                   # 数据集配置文件
├── requirements.txt            # Python依赖
├── QUICKSTART.md              # ⭐ 快速开始指南 (必读)
├── README.md                   # 本文件
├── YOLO_Training_Tutorial.ipynb# Jupyter Notebook教程 (Colab友好)
├── start.bat                   # Windows快速启动菜单
├── start.sh                    # Linux/Mac快速启动菜单
└── datasets/                   # 数据集目录 (自动创建)
    └── custom_dataset/
        ├── images/
        │   ├── train/
        │   ├── val/
        │   └── test/
        └── labels/
            ├── train/
            ├── val/
            └── test/
```

---

## 🚀 5分钟快速开始

### 1️⃣ 安装依赖

```bash
pip install -r requirements.txt
```

### 2️⃣ 准备数据集

将你的标注数据放入以下结构：

```
raw_data/
├── images/        # 所有原始图像
│   ├── img001.jpg
│   ├── img002.jpg
│   └── ...
└── labels/        # YOLO格式标签 (.txt文件)
    ├── img001.txt
    ├── img002.txt
    └── ...
```

**标签格式** (每行一个对象)：
```
<class_id> <x_center> <y_center> <width> <height>
```

示例：
```
0 0.5 0.5 0.3 0.4
1 0.2 0.3 0.1 0.15
```

### 3️⃣ 自动划分数据集

```bash
python prepare_dataset.py --source raw_data --output datasets/custom_dataset
```

### 4️⃣ 修改配置

编辑 `data.yaml`：

```yaml
path: ./datasets/custom_dataset
nc: 3  # 你的类别数
names:
  0: 'track'     # 修改为你的类别名称
  1: 'defect'
  2: 'fastener'
```

### 5️⃣ 开始训练

```bash
python train.py --data data.yaml --model yolov8n.pt --epochs 100
```

### 6️⃣ 推理

```bash
python inference.py --weights runs/train/exp/weights/best.pt --source your_image.jpg
```

---

## 💻 详细用法

### 训练脚本 (train.py)

#### 基础训练
```bash
python train.py \
  --data data.yaml \
  --model yolov8n.pt \
  --epochs 100
```

#### 完整配置
```bash
python train.py \
  --data data.yaml \
  --model yolov8m.pt \
  --epochs 150 \
  --batch 32 \
  --imgsz 1280 \
  --patience 50 \
  --workers 8 \
  --optimizer SGD \
  --lr0 0.01 \
  --save-dir runs/train
```

#### 仅验证模型
```bash
python train.py --data data.yaml --val-only --weights runs/train/exp/weights/best.pt
```

#### 导出模型
```bash
python train.py --export onnx --weights runs/train/exp/weights/best.pt
```

---

### 推理脚本 (inference.py)

#### 推理单张图像
```bash
python inference.py \
  --weights runs/train/exp/weights/best.pt \
  --source path/to/image.jpg \
  --conf 0.25 \
  --show
```

#### 推理整个目录
```bash
python inference.py \
  --weights runs/train/exp/weights/best.pt \
  --source path/to/images/ \
  --conf 0.25
```

#### 推理视频
```bash
python inference.py \
  --weights runs/train/exp/weights/best.pt \
  --source path/to/video.mp4 \
  --conf 0.25
```

#### 实时摄像头检测
```bash
python inference.py \
  --weights runs/train/exp/weights/best.pt \
  --camera 0 \
  --conf 0.25
```

#### 性能基准测试
```bash
python inference.py \
  --weights runs/train/exp/weights/best.pt \
  --source path/to/image.jpg \
  --benchmark \
  --iterations 100
```

---

### 数据集准备脚本 (prepare_dataset.py)

#### 准备数据集
```bash
python prepare_dataset.py \
  --source raw_data \
  --output datasets/custom_dataset \
  --split 0.8,0.1,0.1
```

#### 创建示例结构
```bash
python prepare_dataset.py --create-example
```

---

## 🎛️ 模型选择指南

| 模型 | 大小 | 速度 | 精度 | 推荐场景 |
|------|------|------|------|---------|
| **yolov8n** | 7M | ⚡⚡⚡ | 中 | 实时推理、边缘设备 |
| yolov8s | 22M | ⚡⚡ | 较好 | 性能平衡 |
| yolov8m | 49M | ⚡ | 好 | 通用场景（推荐） |
| yolov8l | 83M | 一般 | 很好 | 高精度应用 |
| yolov8x | 133M | 慢 | ⭐⭐⭐ | 极致精度 |
| yolov11n | 5M | ⚡⚡⚡ | 中 | **最新，超轻** |
| yolov11m | 20M | ⚡ | 好 | **最新，推荐** |

**对于轨道/设备检测：**
- 优先选择 **yolov8m** 或 **yolov11m**（精度与速度平衡）
- 如需极致速度：选择 **yolov8n** 或 **yolov11n**
- 如需极致精度：选择 **yolov8x** 或 **yolov11x**

---

## 📊 训练参数说明

### 核心参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--data` | data.yaml | 数据集配置文件 |
| `--model` | yolov8n.pt | 预训练模型 |
| `--epochs` | 100 | 训练轮数（推荐100-300） |
| `--batch` | 16 | 批大小（根据显存调整） |
| `--imgsz` | 640 | 输入图像大小 |
| `--patience` | 50 | 早停耐心值（轮数） |
| `--optimizer` | auto | 优化器类型 |
| `--lr0` | 0.01 | 初始学习率 |

### 性能优化

```bash
# 加快训练速度
python train.py --batch 32 --workers 8 --amp True

# 提高精度
python train.py --epochs 200 --imgsz 1280 --model yolov8l.pt

# 减少显存占用
python train.py --batch 8 --imgsz 512 --model yolov8n.pt
```

---

## 🛠️ 快速启动菜单

### Windows
```bash
start.bat
```

### Linux/Mac
```bash
bash start.sh
```

---

## 📈 训练监控

训练过程中会自动生成：

```
runs/train/exp/
├── weights/
│   ├── best.pt           # ⭐ 最佳模型（验证集最优）
│   └── last.pt           # 最后一个epoch的模型
├── results.csv           # 所有指标的CSV表格
├── results.png           # 训练曲线图
├── confusion_matrix.png  # 混淆矩阵
├── val_batch0_labels.jpg # 验证集标注样本
├── val_batch0_pred.jpg   # 验证集预测样本
└── events.out.tfevents.* # TensorBoard日志
```

**查看训练曲线：**
```bash
# 用浏览器打开
start runs/train/exp/results.png  # Windows
open runs/train/exp/results.png   # Mac
```

---

## 🎓 使用Jupyter Notebook

推荐在Colab或本地Jupyter中使用：

```bash
jupyter notebook YOLO_Training_Tutorial.ipynb
```

Notebook包含：
- ✅ 完整的代码说明
- ✅ 交互式执行和可视化
- ✅ Colab集成（无需本地GPU）

---

## 💡 最佳实践

### 数据集准备
- ✅ 确保标注准确（最重要！）
- ✅ 类别分布平衡
- ✅ 增加数据增强（脚本已内置）
- ✅ 维持 80:10:10 的训练/验证/测试比例

### 模型训练
- ✅ 从小模型开始（yolov8n）
- ✅ 先用较少的epoch（50）测试流程
- ✅ 使用早停避免过拟合
- ✅ 监控验证��指标

### 推理和部署
- ✅ 在验证集上评估性能
- ✅ 导出为ONNX格式便于部署
- ✅ 使用INT8量化加快推理
- ✅ 在目标环境上测试

---

## ⚠️ 常见问题

### Q: 需要多少训练数据？
A: 最少100张，推荐1000+张。高质量 > 数量多。

### Q: 显存不足怎么办？
A: 减小 `--batch` (16→8→4) 或 `--imgsz` (640→512)

### Q: 精度不够怎么办？
A: 增加 `--epochs`，使用更大模型，增加训练数据

### Q: 如何加速推理？
A: 使用小模型，导出为ONNX/TensorRT格式

### Q: 类别不平衡如何处理？
A: 脚本自动使用加权损失，可增加数据增强

---

## 🔗 相关资源

- **Ultralytics官方文档**: https://docs.ultralytics.com
- **YOLOv8论文**: https://arxiv.org/abs/2305.10199
- **Roboflow数据标注**: https://roboflow.com
- **GitHub Issues**: https://github.com/ultralytics/ultralytics/issues

---

## 📝 文件说明

| 文件 | 说明 |
|------|------|
| **train.py** | 完整的训练脚本，包含模型下载、数据验证、训练、验证、导出 |
| **prepare_dataset.py** | 数据集准备工具，自动划分训练/验证/测试集 |
| **inference.py** | 推理脚本，支持图像、视频、摄像头、批量处理、基准测试 |
| **data.yaml** | 数据集配置文件，修改此文件指向你的数据集 |
| **requirements.txt** | Python依赖，包含所有必需的库 |
| **QUICKSTART.md** | ��速开始指南（推荐首先阅读） |
| **YOLO_Training_Tutorial.ipynb** | Jupyter Notebook，包含完整的教程代码 |

---

## 🎯 工作流总结

```
1. 数据收集和标注
        ↓
2. 数据集准备 (prepare_dataset.py)
        ↓
3. 配置 data.yaml
        ↓
4. 模型训练 (train.py)
        ↓
5. 模型验证和评估
        ↓
6. 推理和部署 (inference.py)
        ↓
7. 性能优化（可选）
```

---

## 🎉 你已准备好开始！

1. 阅读 [QUICKSTART.md](QUICKSTART.md)
2. 准备你的数据集
3. 运行 `python train.py --data data.yaml --model yolov8n.pt --epochs 100`
4. 使用 `inference.py` 进行推理

祝你成功！如有问题，查阅Ultralytics官方文档或GitHub讨论。

---

**版本**: 1.0.0
**最后更新**: 2026年1月
**支持**: YOLOv8, YOLOv11

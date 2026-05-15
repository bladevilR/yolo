# YOLO 完整训练系统

这是一个完整的YOLO自定义数据集训练和推理系统，支持YOLOv8/YOLOv11等版本。

## 项目结构

```
yolo/
├── train.py                    # 训练脚本（核心）
├── prepare_dataset.py          # 数据集准备脚本
├── inference.py                # 推理脚本
├── data.yaml                   # 数据集配置文件
├── requirements.txt            # 依赖库
├── QUICKSTART.md              # 本文件
└── datasets/
    └── custom_dataset/         # 你的数据集目录（自动创建）
        ├── images/
        │   ├── train/
        │   ├── val/
        │   └── test/
        └── labels/
            ├── train/
            ├── val/
            └── test/
```

## 快速开始（5分钟）

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

首次运行时，Ultralytics会自动下载预训练模型到 `~/.cache/ultralytics`（约100-300MB）

### 2. 准备你的数据集

#### 方式A: 如果你已有标注好的数据

创建以下目录结构：

```
raw_data/
├── images/          # 放你的所有图像
│   ├── img001.jpg
│   ├── img002.jpg
│   └── ...
└── labels/          # 对应的YOLO格式标签（.txt文件）
    ├── img001.txt
    ├── img002.txt
    └── ...
```

**标签格式说明** (每行一个对象)：
```
<class_id> <x_center> <y_center> <width> <height>
```

例如：
```
0 0.5 0.5 0.3 0.4
1 0.2 0.3 0.1 0.15
```

其中坐标和大小都是 **相对值** (0-1)。

然后运行数据集准备脚本：

```bash
python prepare_dataset.py --source raw_data --output datasets/custom_dataset
```

#### 方式B: 使用Roboflow（推荐快速标注）

访问 https://roboflow.com 上传图像，在线标注后导出为YOLO格式。

#### 方式C: 创建示例数据集结构

```bash
python prepare_dataset.py --create-example
```

### 3. 修改配置文件

编辑 `data.yaml`：

```yaml
path: ./datasets/custom_dataset  # 你的数据集路径
train: images/train
val: images/val
test: images/test

nc: 3  # 你的类别数（轨道检测:1, 多类别:3, 等）
names:
  0: 'track'
  1: 'defect'
  2: 'fastener'
```

### 4. 开始训练

#### 基础训练（推荐）

```bash
python train.py --data data.yaml --model yolov8n.pt --epochs 100 --batch 16
```

#### 使用参数调优

```bash
python train.py \
  --data data.yaml \
  --model yolov8n.pt \
  --epochs 150 \
  --batch 32 \
  --imgsz 640 \
  --patience 50 \
  --lr0 0.01 \
  --optimizer SGD
```

#### GPU和CPU自动选择

脚本会自动检测GPU，如果没有GPU则使用CPU（较慢）。

### 5. 查看训练结果

训练完成后，结果保存在 `runs/train/exp/` 目录：

```
runs/train/exp/
├── weights/
│   ├── best.pt          # 最佳模型（使用这个）
│   └── last.pt          # 最后一个epoch的模型
├── results.csv          # 训练指标
├── results.png          # 训练曲线图
└── confusion_matrix.png # 混淆矩阵
```

### 6. 推理（检测新图像）

#### 检测单张图像

```bash
python inference.py \
  --weights runs/train/exp/weights/best.pt \
  --source path/to/image.jpg \
  --conf 0.25
```

#### 检测图像目录

```bash
python inference.py \
  --weights runs/train/exp/weights/best.pt \
  --source path/to/images/ \
  --conf 0.25
```

#### 检测视频

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
  --source path/to/test.jpg \
  --benchmark \
  --iterations 100
```

---

## 模型选择指南

| 模型 | 参数量 | 速度 | 精度 | 推荐场景 |
|------|--------|------|------|---------|
| **yolov8n** | 3.2M | 最快⚡ | 中等 | 实时检测、边缘设备 |
| yolov8s | 11.2M | 快 | 较好 | 性能平衡 |
| yolov8m | 25.9M | 中等 | 好 | 通用场景 |
| yolov8l | 43.7M | 慢 | 很好 | 高精度要求 |
| yolov8x | 68.2M | 最慢 | 最好⭐ | 对精度要求极高 |
| yolov11n | 2.6M | 最快⚡ | 中等 | **最新，轻量** |
| yolov11m | 20.1M | 快 | 好 | **最新，推荐** |

**轨道检测/设备检测推荐**：
- **小模型+速度优先**: `yolov8n` 或 `yolov11n`
- **精度与速度平衡**: `yolov8m` 或 `yolov11m` （推荐）
- **极致精度**: `yolov8x` 或 `yolov11x`

---

## 训练参数说明

### 常用参数

```python
python train.py \
  --data data.yaml          # 数据集配置
  --model yolov8n.pt        # 预训练模型
  --epochs 100              # 训练轮数 (100-300推荐)
  --batch 16                # 批大小 (16, 32, 64, 128)
  --imgsz 640               # 输入图像大小 (640, 1280)
  --patience 50             # 早停耐心值
  --workers 8               # 数据加载线程数
  --optimizer auto          # 优化器 (SGD, Adam, AdamW, auto)
  --lr0 0.01                # 初始学习率
  --save-dir runs/train     # 结果保存目录
```

### 如何调整参数

**GPU显存不足？**
- 减小 `--batch` (16 → 8 或 4)
- 减小 `--imgsz` (640 → 512 或 416)

**想要更高精度？**
- 增加 `--epochs` (100 → 200 或 300)
- 增大模型 `yolov8n` → `yolov8m` 或 `yolov8l`
- 增加 `--imgsz` (640 → 1280)

**想要更快速度？**
- 使用小模型 `yolov8n` 或 `yolov11n`
- 减小 `--imgsz`
- 减小 `--epochs`

**过拟合？**
- 增加 `--patience` (50 → 100)
- 增加数据增强 (脚本已内置)
- 增加数据量（最重要！）

---

## 数据标注工具推荐

### 免费工具
- **LabelImg**: https://github.com/heartexlabs/labelImg
- **Roboflow**: https://roboflow.com (免费额度足够小团队使用)

### 数据标注流程
1. 用标注工具标注图像
2. 导出为YOLO格式 (.txt文件)
3. 使用 `prepare_dataset.py` 自动划分训练/验证/测试集

---

## 常见问题

### Q: 需要多少数据才能训练？
A: 最少100张，推荐1000+张。质量 > 数量，100张高质量数据 > 10000张低质量数据。

### Q: 模型多久能训练完？
A:
- 100张数据 + GPU: 5-10分钟
- 1000张数据 + GPU: 30分钟-1小时
- CPU会慢10-50倍

### Q: 显存要求是多少？
A:
- yolov8n: 2GB (可用)
- yolov8m: 4GB (推荐)
- yolov8l+: 6GB+

### Q: 如何部署到生产环境？
A: 导出模型为ONNX或TensorRT格式：
```bash
python train.py --export onnx
```

### Q: 类别不平衡怎么办？
A: 脚本内置了加权损失，自动处理。可增加数据增强。

### Q: 如何加速标注数据？
A:
1. 优先标注难样本
2. 使用自动标注 (先用预训练模型标注，再人工修正)
3. 使用众包平台

---

## 进阶用法

### 转移学习（微调）

如果你的数据集很小（<100张），使用预训练模型进行微调：

```bash
python train.py \
  --data data.yaml \
  --model yolov8n.pt \
  --epochs 50 \
  --batch 8 \
  --patience 20 \
  --lr0 0.001  # 用较小学习率
```

### 验证已训练的模型

```bash
python train.py --data data.yaml --val-only --weights runs/train/exp/weights/best.pt
```

### 导出为ONNX格式

```bash
python train.py --export onnx --weights runs/train/exp/weights/best.pt
```

### 使用最新的YOLOv11

```bash
python train.py --model yolov11n.pt --epochs 100
```

---

## 性能优化建议

### 训练阶段
- 使用 `--amp True` (自动混合精度) - 加快训练2倍
- 使用较大 `--batch` - 提高GPU利用率
- 使用 `--cache True` - 加快数据加载（小数据集）

### 推理阶段
- 使用INT8量化 - 加快3-5倍，精度损失<5%
- 使用TensorRT导出 - 加快2-3倍
- 减小 `--imgsz` (640 → 416) - 加快1.5-2倍，精度略���

---

## 故障排除

### 1. CUDA Out of Memory

```bash
# 减小批大小
python train.py --batch 8
```

### 2. 模型收敛缓慢

- 增加学习率: `--lr0 0.05`
- 检查数据标注质量
- 增加数据量

### 3. 模型过拟合（训练集精度高，验证集低）

- 增加数据增强
- 增加 `--patience`
- 使用Dropout (脚本已内置)

### 4. 类别检测效果差

- 增加该类别的训练样本
- 调整损失权重
- 使用焦点损失 (脚本已内置)

---

## 联系和支持

- Ultralytics 官方文档: https://docs.ultralytics.com
- GitHub Issue: https://github.com/ultralytics/ultralytics/issues
- 论文: https://arxiv.org/abs/2305.10199 (YOLOv8)

---

## 下一步

1. ✅ 准备你的数据集
2. ✅ 修改 `data.yaml` 配置
3. ✅ 运行 `python train.py` 开始训练
4. ✅ 使用 `inference.py` 进行推理
5. ✅ 部署到生产环境

祝你训练顺利！🚀

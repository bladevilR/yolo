#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO训练完整示例
演示从数据集创建到模型训练的完整流程
"""

import os
from pathlib import Path


def print_step(title):
    """打印步骤标题"""
    print("\n" + "=" * 60)
    print(f"   {title}")
    print("=" * 60)


def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     🎯 YOLO 自定义垂直领域检测系统 - 使用示例              ║
║                                                          ║
║     适用场景: 轨道检测、设备状态检测等                     ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)

    # 步骤1: 检查环境
    print_step("步骤 1/6: 检查环境")
    print("\n1. 检查Python版本...")
    import sys
    print(f"   ✅ Python {sys.version}")

    print("\n2. 检查依赖库...")
    try:
        import torch
        import ultralytics
        import cv2
        print(f"   ✅ PyTorch {torch.__version__}")
        print(f"   ✅ Ultralytics {ultralytics.__version__}")
        print(f"   ✅ OpenCV {cv2.__version__}")

        # GPU检查
        if torch.cuda.is_available():
            print(f"   ✅ GPU可用: {torch.cuda.get_device_name(0)}")
            print(f"      显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
        else:
            print("   ⚠️  GPU不可用，将使用CPU训练（速度较慢）")

    except ImportError as e:
        print(f"   ❌ 缺少依赖库: {e}")
        print("\n   请先运行: pip install -r requirements.txt")
        return

    # 步骤2: 数据集准备
    print_step("步骤 2/6: 数据集准备")
    print("""
数据集目录结构应该是：

raw_data/
├── images/          # 所有原始图像
│   ├── img001.jpg
│   ├── img002.jpg
│   └── ...
└── labels/          # YOLO格式标签 (.txt文件)
    ├── img001.txt
    ├── img002.txt
    └── ...

标签格式（每行一个对象）:
<class_id> <x_center> <y_center> <width> <height>

例如:
0 0.5 0.5 0.3 0.4
1 0.2 0.3 0.1 0.15
    """)

    raw_data = Path('raw_data')
    if not raw_data.exists() or not (raw_data / 'images').exists():
        print(f"⚠️  未找到 raw_data 目录")
        print(f"\n   请创建 raw_data 目录并放入你的图像和标签文件")
        print(f"   或运行: python prepare_dataset.py --create-example")
        print("\n   现在跳过数据集准备...")
    else:
        print(f"✅ 找到 raw_data 目录")

        # 运行数据集准备
        print("\n   是否运行数据集准备脚本？")
        choice = input("   [y/N]: ").strip().lower()

        if choice == 'y':
            print("\n   运行: python prepare_dataset.py --source raw_data --output datasets/custom_dataset")
            os.system('python prepare_dataset.py --source raw_data --output datasets/custom_dataset')

    # 步骤3: 配置文件检查
    print_step("步骤 3/6: 检查配置文件")

    if not Path('data.yaml').exists():
        print("❌ 未找到 data.yaml 配置文件")
        return

    import yaml
    with open('data.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    print(f"\n✅ 配置文件内容:")
    print(f"   - 数据集路径: {config.get('path')}")
    print(f"   - 类别数: {config.get('nc')}")
    print(f"   - 类别名称: {config.get('names')}")

    # 步骤4: 模型选择
    print_step("步骤 4/6: 选择模型")
    print("""
可用模型:
[1] yolov8n.pt  - Nano   (最快，3.2M参数)
[2] yolov8s.pt  - Small  (快速，11.2M参数)
[3] yolov8m.pt  - Medium (推荐，25.9M参数) ⭐
[4] yolov8l.pt  - Large  (精确，43.7M参数)
[5] yolov8x.pt  - XLarge (极致精度，68.2M参数)
[6] yolov11n.pt - YOLOv11 Nano (最新，2.6M参数)
[7] yolov11m.pt - YOLOv11 Medium (最新推荐，20.1M参数) ⭐
    """)

    model_choice = input("选择模型 [默认: 3]: ").strip() or '3'

    models = {
        '1': 'yolov8n.pt',
        '2': 'yolov8s.pt',
        '3': 'yolov8m.pt',
        '4': 'yolov8l.pt',
        '5': 'yolov8x.pt',
        '6': 'yolov11n.pt',
        '7': 'yolov11m.pt',
    }

    model_name = models.get(model_choice, 'yolov8m.pt')
    print(f"\n✅ 选择的模型: {model_name}")

    # 步骤5: 训练参数
    print_step("步骤 5/6: 训练参数设置")
    print(f"""
默认训练参数:
- Epochs: 100 (训练轮数)
- Batch Size: 16 (批大小，根据显存自动调整)
- Image Size: 640 (输入图像大小)
- Patience: 50 (早停耐心值)
    """)

    use_default = input("使用默认参数？[Y/n]: ").strip().lower()

    if use_default != 'n':
        epochs = 100
        batch = 16
        imgsz = 640
    else:
        epochs = int(input("Epochs [100]: ").strip() or 100)
        batch = int(input("Batch Size [16]: ").strip() or 16)
        imgsz = int(input("Image Size [640]: ").strip() or 640)

    print(f"\n✅ 训练参数:")
    print(f"   - Epochs: {epochs}")
    print(f"   - Batch Size: {batch}")
    print(f"   - Image Size: {imgsz}")

    # 步骤6: 开始训练
    print_step("步骤 6/6: 开始训练")
    print("\n准备启动训练...")
    print(f"\n命令:")
    cmd = f"python train.py --data data.yaml --model {model_name} --epochs {epochs} --batch {batch} --imgsz {imgsz}"
    print(f"   {cmd}")

    confirm = input("\n确认开始训练？[Y/n]: ").strip().lower()

    if confirm != 'n':
        print("\n🏋️  启动训练...")
        os.system(cmd)

        print("\n" + "=" * 60)
        print("   ✅ 训练完成!")
        print("=" * 60)

        print(f"""
📊 训练结果位置:
   - 最佳模型: runs/train/exp/weights/best.pt
   - 最后模型: runs/train/exp/weights/last.pt
   - 训练曲线: runs/train/exp/results.png
   - 混淆矩阵: runs/train/exp/confusion_matrix.png

🔍 下一步:

1. 验证模型性能:
   python train.py --data data.yaml --val-only --weights runs/train/exp/weights/best.pt

2. 推理测试:
   python inference.py --weights runs/train/exp/weights/best.pt --source path/to/test_image.jpg

3. 实时检测:
   python inference.py --weights runs/train/exp/weights/best.pt --camera 0

4. 导出为ONNX:
   python train.py --export onnx --weights runs/train/exp/weights/best.pt
        """)

    else:
        print("\n⚠️  训练已取消")

    print("\n" + "=" * 60)
    print("   感谢使用 YOLO 自定义检测系统!")
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

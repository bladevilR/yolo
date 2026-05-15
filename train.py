#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO模型训练脚本 - 完整流程实现
支持YOLOv8/YOLOv11的自定义数据集训练
"""

import os
import sys
from pathlib import Path
import yaml
import torch
from ultralytics import YOLO
import argparse


class YOLOTrainer:
    """YOLO训练器类"""

    def __init__(self, config_path='data.yaml', model_name='yolov8n.pt'):
        """
        初始化训练器

        Args:
            config_path: 数据集配置文件路径
            model_name: 预训练模型名称
                - yolov8n.pt: nano版本（最快，参数最少）
                - yolov8s.pt: small版本
                - yolov8m.pt: medium版本
                - yolov8l.pt: large版本
                - yolov8x.pt: xlarge版本（最准，参数最多）
                - yolov11n.pt: YOLOv11 nano版本
        """
        self.config_path = config_path
        self.model_name = model_name
        self.model = None

        # 检查CUDA是否可用
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"🚀 使用设备: {self.device}")
        if self.device == 'cuda':
            print(f"   GPU型号: {torch.cuda.get_device_name(0)}")
            print(f"   显存容量: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")

    def download_model(self):
        """下载预训练模型"""
        print(f"\n📥 正在下载/加载预训练模型: {self.model_name}")
        try:
            # Ultralytics会自动下载模型到 ~/.cache/ultralytics
            self.model = YOLO(self.model_name)
            print(f"✅ 模型加载成功！")

            # 打印模型信息
            print(f"\n📊 模型信息:")
            print(f"   - 架构: {self.model_name.replace('.pt', '')}")
            print(f"   - 参数量: {sum(p.numel() for p in self.model.model.parameters()):,}")

        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            sys.exit(1)

    def verify_dataset(self):
        """验证数据集配置"""
        print(f"\n🔍 验证数据集配置: {self.config_path}")

        if not os.path.exists(self.config_path):
            print(f"❌ 错误: 配置文件不存在: {self.config_path}")
            print(f"   请确保 {self.config_path} 文件存在")
            sys.exit(1)

        # 读取配置
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 检查必要字段
        required_fields = ['path', 'train', 'val', 'nc', 'names']
        for field in required_fields:
            if field not in config:
                print(f"❌ 错误: 配置文件缺少必要字段: {field}")
                sys.exit(1)

        # 检查数据集路径
        dataset_path = Path(config['path'])
        if not dataset_path.exists():
            print(f"⚠️  警告: 数据集路径不存在: {dataset_path}")
            print(f"   将创建示例目录结构...")
            self._create_dataset_structure(dataset_path)
        else:
            print(f"✅ 数据集路径验证通过: {dataset_path}")

        print(f"   - 类别数: {config['nc']}")
        print(f"   - 类别名称: {config['names']}")

        return config

    def _create_dataset_structure(self, dataset_path):
        """创建数据集目录结构"""
        dirs = [
            dataset_path / 'images' / 'train',
            dataset_path / 'images' / 'val',
            dataset_path / 'images' / 'test',
            dataset_path / 'labels' / 'train',
            dataset_path / 'labels' / 'val',
            dataset_path / 'labels' / 'test',
        ]

        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

        print(f"✅ 已创建数据集目录结构")
        print(f"\n📁 请将数据放入以下目录:")
        print(f"   - 训练图像: {dataset_path / 'images' / 'train'}")
        print(f"   - 验证图像: {dataset_path / 'images' / 'val'}")
        print(f"   - 训练标签: {dataset_path / 'labels' / 'train'}")
        print(f"   - 验证标签: {dataset_path / 'labels' / 'val'}")
        print(f"\n⚠️  标签格式: 每行一个对象 <class_id> <x_center> <y_center> <width> <height> (归一化坐标)")

    def train(self,
              epochs=100,
              imgsz=640,
              batch=16,
              patience=50,
              workers=8,
              optimizer='auto',
              lr0=0.01,
              save_dir='runs/train'):
        """
        开始训练

        Args:
            epochs: 训练轮数（推荐: 100-300）
            imgsz: 输入图像大小（640, 1280等）
            batch: 批大小（根据显存调整，-1为自动）
            patience: 早停耐心值（无改善轮数）
            workers: 数据加载线程数
            optimizer: 优化器 ('SGD', 'Adam', 'AdamW', 'auto')
            lr0: 初始学习率
            save_dir: 结果保存目录
        """
        if self.model is None:
            print("❌ 错误: 请先调用 download_model() 加载模型")
            sys.exit(1)

        print(f"\n🏋️  开始训练...")
        print(f"   训练参数:")
        print(f"   - Epochs: {epochs}")
        print(f"   - Image Size: {imgsz}")
        print(f"   - Batch Size: {batch}")
        print(f"   - Patience: {patience}")
        print(f"   - Workers: {workers}")
        print(f"   - Optimizer: {optimizer}")
        print(f"   - Learning Rate: {lr0}")

        try:
            results = self.model.train(
                data=self.config_path,
                epochs=epochs,
                imgsz=imgsz,
                batch=batch,
                patience=patience,
                workers=workers,
                optimizer=optimizer,
                lr0=lr0,
                device=self.device,
                project=save_dir,
                name='exp',
                exist_ok=True,
                pretrained=True,
                verbose=True,

                # 数据增强参数
                hsv_h=0.015,        # HSV-Hue增强
                hsv_s=0.7,          # HSV-Saturation增强
                hsv_v=0.4,          # HSV-Value增强
                degrees=0.0,        # 旋转角度
                translate=0.1,      # 平移
                scale=0.5,          # 缩放
                shear=0.0,          # 剪切
                perspective=0.0,    # 透视变换
                flipud=0.0,         # 上下翻转
                fliplr=0.5,         # 左右翻转
                mosaic=1.0,         # 马赛克增强
                mixup=0.0,          # Mixup增强
                copy_paste=0.0,     # 复制粘贴增强

                # 损失权重
                box=7.5,            # box损失权重
                cls=0.5,            # 分类损失权重
                dfl=1.5,            # DFL损失权重

                # 保存选项
                save=True,          # 保存检查点
                save_period=-1,     # 每N个epoch保存一次（-1为仅保存最后）

                # 验证选项
                val=True,           # 训练时进行验证
                plots=True,         # 生成训练图表

                # 性能优化
                amp=True,           # 自动混合精度训练
                cache=False,        # 缓存图像到内存（小数据集可用）
            )

            print(f"\n✅ 训练完成!")
            print(f"   最佳模型保存位置: {results.save_dir}/weights/best.pt")
            print(f"   最后模型保存位置: {results.save_dir}/weights/last.pt")

            return results

        except Exception as e:
            print(f"❌ 训练失败: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def validate(self, weights='runs/train/exp/weights/best.pt'):
        """
        验证模型

        Args:
            weights: 模型权重路径
        """
        print(f"\n🧪 验证模型: {weights}")

        if not os.path.exists(weights):
            print(f"❌ 错误: 模型文件不存在: {weights}")
            sys.exit(1)

        model = YOLO(weights)
        metrics = model.val(data=self.config_path, device=self.device)

        print(f"\n📊 验证结果:")
        print(f"   - mAP50: {metrics.box.map50:.4f}")
        print(f"   - mAP50-95: {metrics.box.map:.4f}")
        print(f"   - Precision: {metrics.box.mp:.4f}")
        print(f"   - Recall: {metrics.box.mr:.4f}")

        return metrics

    def export_model(self, weights='runs/train/exp/weights/best.pt', format='onnx'):
        """
        导出模型为其他格式

        Args:
            weights: 模型权重路径
            format: 导出格式 ('onnx', 'torchscript', 'tflite', 'engine', etc.)
        """
        print(f"\n📦 导出模型为 {format.upper()} 格式...")

        model = YOLO(weights)
        export_path = model.export(format=format)

        print(f"✅ 导出成功: {export_path}")
        return export_path


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='YOLO模型训练脚本')

    # 基础参数
    parser.add_argument('--data', type=str, default='data.yaml', help='数据集配置文件路径')
    parser.add_argument('--model', type=str, default='yolov8n.pt',
                       help='预训练模型 (yolov8n/s/m/l/x.pt 或 yolov11n.pt)')

    # 训练参数
    parser.add_argument('--epochs', type=int, default=100, help='训练轮数')
    parser.add_argument('--batch', type=int, default=16, help='批大小')
    parser.add_argument('--imgsz', type=int, default=640, help='输入图像大小')
    parser.add_argument('--patience', type=int, default=50, help='早停耐心值')
    parser.add_argument('--workers', type=int, default=8, help='数据加载线程数')
    parser.add_argument('--optimizer', type=str, default='auto', help='优化器')
    parser.add_argument('--lr0', type=float, default=0.01, help='初始学习率')

    # 其他参数
    parser.add_argument('--save-dir', type=str, default='runs/train', help='结果保存目录')
    parser.add_argument('--val-only', action='store_true', help='仅验证模型')
    parser.add_argument('--export', type=str, default=None,
                       help='导出模型格式 (onnx, torchscript, tflite等)')

    args = parser.parse_args()

    # 打印欢迎信息
    print("=" * 60)
    print("🎯 YOLO 自定义数据集训练工具")
    print("=" * 60)

    # 创建训练器
    trainer = YOLOTrainer(
        config_path=args.data,
        model_name=args.model
    )

    # 验证数据集
    config = trainer.verify_dataset()

    # 仅验证模式
    if args.val_only:
        trainer.validate()
        return

    # 下载模型
    trainer.download_model()

    # 开始训练
    results = trainer.train(
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        patience=args.patience,
        workers=args.workers,
        optimizer=args.optimizer,
        lr0=args.lr0,
        save_dir=args.save_dir
    )

    # 自动验证最佳模型
    print("\n" + "=" * 60)
    best_weights = str(Path(results.save_dir) / 'weights' / 'best.pt')
    trainer.validate(weights=best_weights)

    # 导出模型（如果指定）
    if args.export:
        trainer.export_model(weights=best_weights, format=args.export)

    print("\n" + "=" * 60)
    print("🎉 所有任务完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()

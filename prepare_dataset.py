#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集准备工具
用于从原始图像创建YOLO格式数据集
"""

import os
import shutil
import random
from pathlib import Path
from typing import List, Tuple
import argparse


class DatasetPreparer:
    """数据集准备器"""

    def __init__(self, source_dir: str, output_dir: str, split_ratio: Tuple[float, float, float] = (0.8, 0.1, 0.1)):
        """
        初始化

        Args:
            source_dir: 原始数据目录（包含images和labels子目录）
            output_dir: 输出数据集目录
            split_ratio: 训练集、验证集、测试集比例 (train, val, test)
        """
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.split_ratio = split_ratio

        # 验证比例总和为1
        if abs(sum(split_ratio) - 1.0) > 0.001:
            raise ValueError(f"split_ratio总和必须为1.0，当前为 {sum(split_ratio)}")

    def prepare(self):
        """准备数据集"""
        print(f"\n📂 数据集准备工具")
        print(f"   源目录: {self.source_dir}")
        print(f"   输出目录: {self.output_dir}")
        print(f"   划分比例: train={self.split_ratio[0]}, val={self.split_ratio[1]}, test={self.split_ratio[2]}")

        # 检查源目录
        if not self.source_dir.exists():
            print(f"❌ 错误: 源目录不存在: {self.source_dir}")
            print(f"\n请创建以下目录结构:")
            print(f"   {self.source_dir}/")
            print(f"   ├── images/       # 存放所有原始图像")
            print(f"   └── labels/       # 存放对应的YOLO格式标签文件")
            return

        # 获取所有图像文件
        images_dir = self.source_dir / 'images'
        labels_dir = self.source_dir / 'labels'

        if not images_dir.exists() or not labels_dir.exists():
            print(f"❌ 错误: 源目录必须包含 'images' 和 'labels' 子目录")
            return

        # 支持的图像格式
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        image_files = [f for f in images_dir.iterdir()
                      if f.suffix.lower() in image_extensions]

        if not image_files:
            print(f"❌ 错误: 在 {images_dir} 中没有找到图像文件")
            return

        print(f"✅ 找到 {len(image_files)} 个图像文件")

        # 验证标签文件
        valid_pairs = []
        for img_file in image_files:
            label_file = labels_dir / f"{img_file.stem}.txt"
            if label_file.exists():
                valid_pairs.append((img_file, label_file))
            else:
                print(f"⚠️  警告: 图像 {img_file.name} 没有对应的标签文件")

        print(f"✅ 验证通过: {len(valid_pairs)} 个有效的图像-标签对")

        if len(valid_pairs) == 0:
            print(f"❌ 错误: 没有找到有效的图像-标签对")
            return

        # 随机打乱
        random.shuffle(valid_pairs)

        # 划分数据集
        total = len(valid_pairs)
        train_size = int(total * self.split_ratio[0])
        val_size = int(total * self.split_ratio[1])

        train_pairs = valid_pairs[:train_size]
        val_pairs = valid_pairs[train_size:train_size + val_size]
        test_pairs = valid_pairs[train_size + val_size:]

        print(f"\n📊 数据集划分:")
        print(f"   - 训练集: {len(train_pairs)} ({len(train_pairs)/total*100:.1f}%)")
        print(f"   - 验证集: {len(val_pairs)} ({len(val_pairs)/total*100:.1f}%)")
        print(f"   - 测试集: {len(test_pairs)} ({len(test_pairs)/total*100:.1f}%)")

        # 创建输出目录结构
        for split in ['train', 'val', 'test']:
            (self.output_dir / 'images' / split).mkdir(parents=True, exist_ok=True)
            (self.output_dir / 'labels' / split).mkdir(parents=True, exist_ok=True)

        # 复制文件
        print(f"\n📋 复制文件...")
        self._copy_files(train_pairs, 'train')
        self._copy_files(val_pairs, 'val')
        self._copy_files(test_pairs, 'test')

        print(f"\n✅ 数据集准备完成!")
        print(f"   输出目录: {self.output_dir}")
        print(f"\n下一步: 更新 data.yaml 中的 path 为: {self.output_dir.absolute()}")

    def _copy_files(self, pairs: List[Tuple[Path, Path]], split: str):
        """复制文件到对应目录"""
        for img_file, label_file in pairs:
            # 复制图像
            dst_img = self.output_dir / 'images' / split / img_file.name
            shutil.copy2(img_file, dst_img)

            # 复制标签
            dst_label = self.output_dir / 'labels' / split / label_file.name
            shutil.copy2(label_file, dst_label)

        print(f"   ✓ {split}: 复制了 {len(pairs)} 个文件")


def create_sample_dataset(output_dir: str):
    """创建示例数据集结构"""
    output_path = Path(output_dir)

    # 创建目录
    dirs = [
        output_path / 'raw_data' / 'images',
        output_path / 'raw_data' / 'labels',
    ]

    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)

    # 创建示例README
    readme_content = """# 数据集准备说明

## 1. 准备原始数据

将你的图像和标签文件放入以下目录:

```
raw_data/
├── images/          # 所有原始图像文件
│   ├── img001.jpg
│   ├── img002.jpg
│   └── ...
└── labels/          # 对应的YOLO格式标签文件
    ├── img001.txt
    ├── img002.txt
    └── ...
```

## 2. 标签格式

每个标签文件(.txt)的格式为:
```
<class_id> <x_center> <y_center> <width> <height>
```

其中:
- class_id: 类别ID (从0开始)
- x_center, y_center: 边界框中心点坐标 (归一化到0-1)
- width, height: 边界框宽度和高度 (归一化到0-1)

示例:
```
0 0.5 0.5 0.3 0.4
1 0.2 0.3 0.1 0.15
```

## 3. 运行数据集准备脚本

```bash
python prepare_dataset.py --source raw_data --output datasets/custom_dataset
```

## 4. 更新配置文件

修改 data.yaml 中的 path 字段为你的数据集路径。

## 5. 开始训练

```bash
python train.py --data data.yaml --model yolov8n.pt --epochs 100
```
"""

    readme_path = output_path / 'README_DATASET.md'
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    print(f"\n✅ 已创建示例数据集结构: {output_path}")
    print(f"   请阅读: {readme_path}")


def main():
    parser = argparse.ArgumentParser(description='YOLO数据集准备工具')

    parser.add_argument('--source', type=str, default='raw_data',
                       help='源数据目录（包含images和labels子目录）')
    parser.add_argument('--output', type=str, default='datasets/custom_dataset',
                       help='输出数据集目录')
    parser.add_argument('--split', type=str, default='0.8,0.1,0.1',
                       help='数据集划分比例（train,val,test）')
    parser.add_argument('--seed', type=int, default=42,
                       help='随机种子')
    parser.add_argument('--create-example', action='store_true',
                       help='创建示例数据集结构')

    args = parser.parse_args()

    # 设置随机种子
    random.seed(args.seed)

    # 创建示例结构
    if args.create_example:
        create_sample_dataset('.')
        return

    # 解析划分比例
    split_ratio = tuple(map(float, args.split.split(',')))

    if len(split_ratio) != 3:
        print("❌ 错误: split参数必须包含3个值（train,val,test）")
        return

    # 准备数据集
    preparer = DatasetPreparer(
        source_dir=args.source,
        output_dir=args.output,
        split_ratio=split_ratio
    )

    preparer.prepare()


if __name__ == '__main__':
    main()

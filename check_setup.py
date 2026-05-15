#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目完整性检查脚本
"""

import os
from pathlib import Path


def check_file(filepath, description):
    """检查文件是否存在"""
    if Path(filepath).exists():
        size = Path(filepath).stat().st_size / 1024
        print(f"   ✅ {filepath:<35} ({size:.1f} KB) - {description}")
        return True
    else:
        print(f"   ❌ {filepath:<35} - {description}")
        return False


def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║          YOLO 训练系统 - 项目完整性检查                   ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)

    files_to_check = {
        # 核心脚本
        'train.py': '核心训练脚本',
        'inference.py': '推理脚本',
        'prepare_dataset.py': '数据集准备脚本',
        'example.py': '完整示例脚本',

        # 配置文件
        'data.yaml': '数据集配置文件',
        'requirements.txt': 'Python依赖列表',

        # 文档
        'README.md': '项目说明文档',
        'QUICKSTART.md': '快速开始指南',

        # 启动脚本
        'start.bat': 'Windows启动菜单',
        'start.sh': 'Linux/Mac启动菜单',

        # Jupyter Notebook
        'YOLO_Training_Tutorial.ipynb': 'Jupyter教程',
    }

    print("\n📋 检查核心文件...")
    all_good = True
    for filepath, desc in files_to_check.items():
        if not check_file(filepath, desc):
            all_good = False

    print("\n" + "=" * 60)

    if all_good:
        print("✅ 所有文件检查通过！")
        print("\n🎉 项目已准备就绪，可以开始使用！")

        print("\n📚 使用方法:")
        print("   1. 阅读 QUICKSTART.md 快速开始指南")
        print("   2. 或运行: python example.py (交互式示例)")
        print("   3. 或在Windows运行: start.bat (图形菜单)")
        print("   4. 或在Linux/Mac运行: bash start.sh (图形菜单)")

        print("\n💡 推荐步骤:")
        print("   1. pip install -r requirements.txt")
        print("   2. python prepare_dataset.py --create-example")
        print("   3. python example.py")

    else:
        print("❌ 部分文件缺失，请重新下载或创建")

    print("\n" + "=" * 60)

    # 额外的环境检查
    print("\n🔍 环境检查...")

    try:
        import torch
        print(f"   ✅ PyTorch已安装 (版本 {torch.__version__})")

        if torch.cuda.is_available():
            print(f"   ✅ GPU可用: {torch.cuda.get_device_name(0)}")
        else:
            print("   ⚠️  GPU不可用 (将使用CPU，速度较慢)")
    except ImportError:
        print("   ❌ PyTorch未安装")
        print("      运行: pip install -r requirements.txt")

    try:
        import ultralytics
        print(f"   ✅ Ultralytics已安装 (版本 {ultralytics.__version__})")
    except ImportError:
        print("   ❌ Ultralytics未安装")
        print("      运行: pip install -r requirements.txt")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()

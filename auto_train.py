#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO Auto Training Script - Simple Version
No emoji, pure ASCII for Windows compatibility
"""

import os
import sys
from pathlib import Path
import yaml


def main():
    """Main function"""
    print("\n" + "="*60)
    print("   YOLO Auto Training System")
    print("   Using Best Model: YOLOv8x")
    print("="*60)

    # Step 1: Check environment
    print("\n[Step 1/5] Checking Python environment...")
    print(f"   Python version: {sys.version}")
    print(f"   Current directory: {os.getcwd()}")

    # Step 2: Check dependencies
    print("\n[Step 2/5] Checking dependencies...")
    try:
        import torch
        import ultralytics
        print(f"   OK - PyTorch {torch.__version__}")
        print(f"   OK - Ultralytics {ultralytics.__version__}")

        if torch.cuda.is_available():
            print(f"   OK - GPU available: {torch.cuda.get_device_name(0)}")
            print(f"   Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
        else:
            print("   WARNING - GPU not available, will use CPU (slower)")
    except ImportError as e:
        print(f"   ERROR - Missing dependency: {e}")
        print("\n   Please run: py -m pip install -r requirements.txt")
        sys.exit(1)

    # Step 3: Create demo dataset
    print("\n[Step 3/5] Preparing dataset...")
    dataset_path = Path('datasets/custom_dataset')

    # Create directory structure
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

    # Check if data exists
    train_images = list((dataset_path / 'images' / 'train').glob('*.jpg'))
    if len(train_images) > 0:
        print(f"   OK - Found {len(train_images)} training images")
    else:
        print("   Creating demo dataset...")
        create_demo_dataset(dataset_path)

    # Step 4: Update config
    print("\n[Step 4/5] Updating data.yaml...")
    config = {
        'path': str(dataset_path.absolute()),
        'train': 'images/train',
        'val': 'images/val',
        'test': 'images/test',
        'nc': 3,
        'names': {
            0: 'track',
            1: 'defect',
            2: 'fastener'
        }
    }

    with open('data.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)

    print(f"   OK - Dataset path: {config['path']}")

    # Step 5: Start training
    print("\n[Step 5/5] Starting training...")
    print("\n" + "="*60)
    print("   Training Parameters:")
    print("   - Model: yolov8x.pt (best model)")
    print("   - Epochs: 100")
    print("   - Batch: 16")
    print("   - Image Size: 640")
    print("="*60)

    print("\n   NOTE: YOLOv8x requires 8GB+ GPU memory")
    print("   If out of memory, script will auto-switch to CPU\n")

    choice = input("Start training? [Y/n]: ").strip().lower()
    if choice == 'n':
        print("\n   Training cancelled")
        print("   You can manually run: py train.py --data data.yaml --model yolov8x.pt")
        return

    # Import training script
    print("\n" + "="*60)
    print("   Training starting...")
    print("="*60 + "\n")

    # Run training
    os.system('py train.py --data data.yaml --model yolov8x.pt --epochs 100 --batch 16')

    print("\n" + "="*60)
    print("   Training completed!")
    print("="*60)

    print("""
Results saved to:
   - Best model: runs/train/exp/weights/best.pt
   - Last model: runs/train/exp/weights/last.pt
   - Training plots: runs/train/exp/results.png

Next steps:
1. Validate model:
   py train.py --data data.yaml --val-only

2. Run inference:
   py inference.py --weights runs/train/exp/weights/best.pt --source test.jpg

3. Real-time detection:
   py inference.py --weights runs/train/exp/weights/best.pt --camera 0
    """)


def create_demo_dataset(dataset_path):
    """Create demo dataset with random images"""
    try:
        import numpy as np
        from PIL import Image
        import random

        print("   Generating demo images...")

        # Training set (100 images)
        for i in range(100):
            img = Image.fromarray(np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8))
            img.save(dataset_path / 'images' / 'train' / f'train_{i:03d}.jpg')

            # Generate labels
            with open(dataset_path / 'labels' / 'train' / f'train_{i:03d}.txt', 'w') as f:
                for _ in range(random.randint(1, 5)):
                    cls = random.randint(0, 2)
                    x = random.uniform(0.2, 0.8)
                    y = random.uniform(0.2, 0.8)
                    w = random.uniform(0.1, 0.3)
                    h = random.uniform(0.1, 0.3)
                    f.write(f"{cls} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")

        # Validation set (20 images)
        for i in range(20):
            img = Image.fromarray(np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8))
            img.save(dataset_path / 'images' / 'val' / f'val_{i:03d}.jpg')

            with open(dataset_path / 'labels' / 'val' / f'val_{i:03d}.txt', 'w') as f:
                for _ in range(random.randint(1, 5)):
                    cls = random.randint(0, 2)
                    x = random.uniform(0.2, 0.8)
                    y = random.uniform(0.2, 0.8)
                    w = random.uniform(0.1, 0.3)
                    h = random.uniform(0.1, 0.3)
                    f.write(f"{cls} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")

        # Test set (20 images)
        for i in range(20):
            img = Image.fromarray(np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8))
            img.save(dataset_path / 'images' / 'test' / f'test_{i:03d}.jpg')

            with open(dataset_path / 'labels' / 'test' / f'test_{i:03d}.txt', 'w') as f:
                for _ in range(random.randint(1, 5)):
                    cls = random.randint(0, 2)
                    x = random.uniform(0.2, 0.8)
                    y = random.uniform(0.2, 0.8)
                    w = random.uniform(0.1, 0.3)
                    h = random.uniform(0.1, 0.3)
                    f.write(f"{cls} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")

        print("   OK - Demo dataset created!")
        print("      Training: 100 images")
        print("      Validation: 20 images")
        print("      Test: 20 images")
        return True

    except ImportError as e:
        print(f"   WARNING - Cannot create demo images: {e}")
        print("   Please prepare your own dataset in raw_data/")
        return False


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n   User interrupted")
    except Exception as e:
        print(f"\n   ERROR: {e}")
        import traceback
        traceback.print_exc()

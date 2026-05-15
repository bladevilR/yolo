#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO模型推理脚本
支持图像、视频、摄像头实时推理
"""

import os
import sys
from pathlib import Path
import argparse
import cv2
import torch
from ultralytics import YOLO
import time


class YOLOInference:
    """YOLO推理器"""

    def __init__(self, weights: str, conf_threshold: float = 0.25, iou_threshold: float = 0.45):
        """
        初始化推理器

        Args:
            weights: 模型权重路径
            conf_threshold: 置信度阈值
            iou_threshold: NMS的IOU阈值
        """
        self.weights = weights
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold

        # 检查权重文件
        if not os.path.exists(weights):
            print(f"❌ 错误: 模型文件不存在: {weights}")
            sys.exit(1)

        # 检查设备
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"🚀 使用设备: {self.device}")

        # 加载模型
        print(f"📥 加载模型: {weights}")
        self.model = YOLO(weights)
        print(f"✅ 模型加载成功!")

    def predict_image(self, source: str, save_dir: str = 'runs/predict', show: bool = False):
        """
        对图像进行推理

        Args:
            source: 图像路径或目录
            save_dir: 结果保存目录
            show: 是否显示结果
        """
        print(f"\n🖼️  图像推理")
        print(f"   源: {source}")
        print(f"   置信度阈值: {self.conf_threshold}")

        # 推理
        results = self.model.predict(
            source=source,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            device=self.device,
            save=True,
            project=save_dir,
            name='exp',
            exist_ok=True,
            show=show,
            verbose=True
        )

        # 打印结果统计
        print(f"\n📊 检测结果:")
        for i, result in enumerate(results):
            boxes = result.boxes
            print(f"   图像 {i+1}: 检测到 {len(boxes)} 个对象")

            # 显示每个检测框的详细信息
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                cls_name = result.names[cls_id]
                print(f"      - {cls_name}: {conf:.2f}")

        print(f"\n✅ 结果已保存到: {save_dir}/exp")

        return results

    def predict_video(self, source: str, save_dir: str = 'runs/predict', show: bool = False):
        """
        对视频进行推理

        Args:
            source: 视频路径或摄像头ID (0, 1, ...)
            save_dir: 结果保存目录
            show: 是否显示结果
        """
        print(f"\n🎥 视频推理")
        print(f"   源: {source}")
        print(f"   置信度阈值: {self.conf_threshold}")

        # 推理
        results = self.model.predict(
            source=source,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            device=self.device,
            save=True,
            project=save_dir,
            name='exp',
            exist_ok=True,
            show=show,
            stream=True,  # 流式处理视频
            verbose=False
        )

        # 处理结果
        frame_count = 0
        total_detections = 0
        start_time = time.time()

        for result in results:
            frame_count += 1
            detections = len(result.boxes)
            total_detections += detections

            # 每30帧打印一次
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                print(f"   帧 {frame_count}: {detections} 个对象, FPS: {fps:.1f}")

        elapsed = time.time() - start_time
        avg_fps = frame_count / elapsed

        print(f"\n📊 视频处理完成:")
        print(f"   - 总帧数: {frame_count}")
        print(f"   - 总检测数: {total_detections}")
        print(f"   - 平均FPS: {avg_fps:.1f}")
        print(f"   - 总时长: {elapsed:.1f}秒")
        print(f"\n✅ 结果已保存到: {save_dir}/exp")

    def predict_realtime(self, camera_id: int = 0):
        """
        实时摄像头推理

        Args:
            camera_id: 摄像头ID
        """
        print(f"\n📹 实时摄像头推理 (按 'q' 退出)")
        print(f"   摄像头ID: {camera_id}")
        print(f"   置信度阈值: {self.conf_threshold}")

        # 打开摄像头
        cap = cv2.VideoCapture(camera_id)

        if not cap.isOpened():
            print(f"❌ 错误: 无法打开摄像头 {camera_id}")
            return

        # 获取摄像头信息
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        print(f"   分辨率: {width}x{height}, FPS: {fps}")

        frame_count = 0
        start_time = time.time()

        print(f"\n开始推理...")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1

                # 推理
                results = self.model.predict(
                    source=frame,
                    conf=self.conf_threshold,
                    iou=self.iou_threshold,
                    device=self.device,
                    verbose=False
                )

                # 绘制结果
                annotated_frame = results[0].plot()

                # 计算FPS
                elapsed = time.time() - start_time
                current_fps = frame_count / elapsed

                # 显示FPS
                cv2.putText(
                    annotated_frame,
                    f"FPS: {current_fps:.1f}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2
                )

                # 显示检测数
                detections = len(results[0].boxes)
                cv2.putText(
                    annotated_frame,
                    f"Objects: {detections}",
                    (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2
                )

                # 显示画面
                cv2.imshow('YOLO Real-time Detection', annotated_frame)

                # 按 'q' 退出
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        except KeyboardInterrupt:
            print("\n⚠️  用户中断")

        finally:
            cap.release()
            cv2.destroyAllWindows()

            elapsed = time.time() - start_time
            avg_fps = frame_count / elapsed

            print(f"\n📊 统计信息:")
            print(f"   - 处理帧数: {frame_count}")
            print(f"   - 运行时长: {elapsed:.1f}秒")
            print(f"   - 平均FPS: {avg_fps:.1f}")

    def benchmark(self, source: str, iterations: int = 100):
        """
        性能基准测试

        Args:
            source: 测试图像路径
            iterations: 测试迭代次数
        """
        print(f"\n⚡ 性能基准测试")
        print(f"   图像: {source}")
        print(f"   迭代次数: {iterations}")

        if not os.path.exists(source):
            print(f"❌ 错误: 测试图像不存在: {source}")
            return

        # 预热
        print(f"   预热中...")
        for _ in range(10):
            _ = self.model.predict(source, verbose=False)

        # 基准测试
        print(f"   测试中...")
        start_time = time.time()

        for i in range(iterations):
            results = self.model.predict(source, verbose=False)

            if (i + 1) % 20 == 0:
                print(f"      进度: {i+1}/{iterations}")

        elapsed = time.time() - start_time

        # 计算统计
        avg_time = elapsed / iterations
        fps = iterations / elapsed

        print(f"\n📊 性能结果:")
        print(f"   - 平均推理时间: {avg_time*1000:.2f} ms")
        print(f"   - 吞吐量 (FPS): {fps:.1f}")
        print(f"   - 总耗时: {elapsed:.2f}秒")


def main():
    parser = argparse.ArgumentParser(description='YOLO模型推理脚本')

    # 模型参数
    parser.add_argument('--weights', type=str, required=True,
                       help='模型权重路径 (如: runs/train/exp/weights/best.pt)')
    parser.add_argument('--conf', type=float, default=0.25,
                       help='置信度阈值 (0.0-1.0)')
    parser.add_argument('--iou', type=float, default=0.45,
                       help='NMS的IOU阈值 (0.0-1.0)')

    # 输入源
    parser.add_argument('--source', type=str, default=None,
                       help='输入源 (图像路径/目录/视频路径)')
    parser.add_argument('--camera', type=int, default=None,
                       help='摄像头ID (0, 1, ...)')

    # 输出参数
    parser.add_argument('--save-dir', type=str, default='runs/predict',
                       help='结果保存目录')
    parser.add_argument('--show', action='store_true',
                       help='显示结果')

    # 其他
    parser.add_argument('--benchmark', action='store_true',
                       help='运行性能基准测试')
    parser.add_argument('--iterations', type=int, default=100,
                       help='基准测试迭代次数')

    args = parser.parse_args()

    # 检查输入
    if args.source is None and args.camera is None:
        print("❌ 错误: 必须指定 --source 或 --camera")
        parser.print_help()
        return

    # 创建推理器
    inferencer = YOLOInference(
        weights=args.weights,
        conf_threshold=args.conf,
        iou_threshold=args.iou
    )

    # 基准测试
    if args.benchmark:
        if args.source is None:
            print("❌ 错误: 基准测试需要指定 --source")
            return
        inferencer.benchmark(args.source, args.iterations)
        return

    # 摄像头推理
    if args.camera is not None:
        inferencer.predict_realtime(camera_id=args.camera)
        return

    # 判断输入类型
    source_path = Path(args.source)

    if source_path.is_file():
        # 判断是图像还是视频
        image_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}

        if source_path.suffix.lower() in image_exts:
            inferencer.predict_image(args.source, args.save_dir, args.show)
        elif source_path.suffix.lower() in video_exts:
            inferencer.predict_video(args.source, args.save_dir, args.show)
        else:
            print(f"❌ 错误: 不支持的文件格式: {source_path.suffix}")

    elif source_path.is_dir():
        # 图像目录
        inferencer.predict_image(args.source, args.save_dir, args.show)

    else:
        print(f"❌ 错误: 无效的输入源: {args.source}")


if __name__ == '__main__':
    main()

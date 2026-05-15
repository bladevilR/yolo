#!/bin/bash

# YOLO训练系统 - 快速启动脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

show_menu() {
    clear
    echo -e "${BLUE}====================================${NC}"
    echo -e "${BLUE}   YOLO 训练系统 - 快速启动${NC}"
    echo -e "${BLUE}====================================${NC}"
    echo ""
    echo "请选择操作:"
    echo ""
    echo "[1] 安装依赖"
    echo "[2] 创建示例数据集结构"
    echo "[3] 准备数据集 (从raw_data划分)"
    echo "[4] 开始训练 (YOLOv8n, 100 epochs)"
    echo "[5] 开始训练 (YOLOv8m, 150 epochs, 推荐)"
    echo "[6] 验证模型"
    echo "[7] 推理单张图像"
    echo "[8] 推理视频"
    echo "[9] 实时摄像头检测"
    echo "[0] 退出"
    echo ""
}

install_deps() {
    echo -e "${GREEN}[1] 安装依赖...${NC}"
    pip install -r requirements.txt
    echo ""
    echo -e "${GREEN}完成!${NC}"
    read -p "按Enter键继续..."
}

create_example() {
    echo -e "${GREEN}[2] 创建示例数据集结构...${NC}"
    python3 prepare_dataset.py --create-example
    echo ""
    echo -e "${YELLOW}请将数据放入 raw_data 目录${NC}"
    read -p "按Enter键继续..."
}

prepare_dataset() {
    echo -e "${GREEN}[3] 准备数据集...${NC}"
    read -p "输入源数据目录 [默认: raw_data]: " source
    source=${source:-raw_data}
    read -p "输入输出目录 [默认: datasets/custom_dataset]: " output
    output=${output:-datasets/custom_dataset}
    python3 prepare_dataset.py --source "$source" --output "$output"
    echo ""
    echo -e "${GREEN}完成!${NC}"
    read -p "按Enter键继续..."
}

train_n() {
    echo -e "${GREEN}[4] 开始训练 (YOLOv8n, 100 epochs)...${NC}"
    python3 train.py --data data.yaml --model yolov8n.pt --epochs 100 --batch 16
    echo ""
    echo -e "${GREEN}训练完成!${NC}"
    read -p "按Enter键继续..."
}

train_m() {
    echo -e "${GREEN}[5] 开始训练 (YOLOv8m, 150 epochs, 推荐)...${NC}"
    python3 train.py --data data.yaml --model yolov8m.pt --epochs 150 --batch 16
    echo ""
    echo -e "${GREEN}训练完成!${NC}"
    read -p "按Enter键继续..."
}

validate_model() {
    echo -e "${GREEN}[6] 验证模型...${NC}"
    read -p "输入模型路径 [默认: runs/train/exp/weights/best.pt]: " weights
    weights=${weights:-runs/train/exp/weights/best.pt}
    python3 train.py --data data.yaml --val-only --weights "$weights"
    echo ""
    echo -e "${GREEN}完成!${NC}"
    read -p "按Enter键继续..."
}

inference_image() {
    echo -e "${GREEN}[7] 推理单张图像...${NC}"
    read -p "输入模型路径 [默认: runs/train/exp/weights/best.pt]: " weights
    weights=${weights:-runs/train/exp/weights/best.pt}
    read -p "输入图像路径: " image
    python3 inference.py --weights "$weights" --source "$image" --conf 0.25 --show
    echo ""
    echo -e "${GREEN}完成!${NC}"
    read -p "按Enter键继续..."
}

inference_video() {
    echo -e "${GREEN}[8] 推理视频...${NC}"
    read -p "输入模型路径 [默认: runs/train/exp/weights/best.pt]: " weights
    weights=${weights:-runs/train/exp/weights/best.pt}
    read -p "输入视频路径: " video
    python3 inference.py --weights "$weights" --source "$video" --conf 0.25
    echo ""
    echo -e "${GREEN}完成!${NC}"
    read -p "按Enter键继续..."
}

inference_camera() {
    echo -e "${GREEN}[9] 实时摄像头检测...${NC}"
    read -p "输入模型路径 [默认: runs/train/exp/weights/best.pt]: " weights
    weights=${weights:-runs/train/exp/weights/best.pt}
    read -p "输入摄像头ID [默认: 0]: " camera
    camera=${camera:-0}
    python3 inference.py --weights "$weights" --camera "$camera" --conf 0.25
    echo ""
    echo -e "${GREEN}完成!${NC}"
    read -p "按Enter键继续..."
}

# 主循环
while true; do
    show_menu
    read -p "输入选项 (0-9): " choice
    case $choice in
        1) install_deps ;;
        2) create_example ;;
        3) prepare_dataset ;;
        4) train_n ;;
        5) train_m ;;
        6) validate_model ;;
        7) inference_image ;;
        8) inference_video ;;
        9) inference_camera ;;
        0) echo -e "${BLUE}再见!${NC}"; exit 0 ;;
        *) echo -e "${RED}无效选项，请重试${NC}"; sleep 2 ;;
    esac
done

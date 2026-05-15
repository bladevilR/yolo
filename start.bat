@echo off
chcp 65001 >nul
echo ====================================
echo   YOLO 训练系统 - 快速启动
echo ====================================
echo.

:menu
echo 请选择操作:
echo.
echo [1] 安装依赖
echo [2] 创建示例数据集结构
echo [3] 准备数据集 (从raw_data划分)
echo [4] 开始训练 (YOLOv8n, 100 epochs)
echo [5] 开始训练 (YOLOv8m, 150 epochs, 推荐)
echo [6] 验证模型
echo [7] 推理单张图像
echo [8] 推理视频
echo [9] 实时摄像头检测
echo [0] 退出
echo.
set /p choice="输入选项 (0-9): "

if "%choice%"=="1" goto install
if "%choice%"=="2" goto create_example
if "%choice%"=="3" goto prepare_dataset
if "%choice%"=="4" goto train_n
if "%choice%"=="5" goto train_m
if "%choice%"=="6" goto validate
if "%choice%"=="7" goto inference_image
if "%choice%"=="8" goto inference_video
if "%choice%"=="9" goto inference_camera
if "%choice%"=="0" goto exit
goto menu

:install
echo.
echo [1] 安装依赖...
pip install -r requirements.txt
echo.
echo 完成! 按任意键返回主菜单...
pause >nul
goto menu

:create_example
echo.
echo [2] 创建示例数据集结构...
python prepare_dataset.py --create-example
echo.
echo 完成! 请将数据放入 raw_data 目录
echo 按任意键返回主菜单...
pause >nul
goto menu

:prepare_dataset
echo.
echo [3] 准备数据集...
set /p source="输入源数据目录 [默认: raw_data]: "
if "%source%"=="" set source=raw_data
set /p output="输入输出目录 [默认: datasets/custom_dataset]: "
if "%output%"=="" set output=datasets/custom_dataset
python prepare_dataset.py --source %source% --output %output%
echo.
echo 完成! 按任意键返回主菜单...
pause >nul
goto menu

:train_n
echo.
echo [4] 开始训练 (YOLOv8n, 100 epochs)...
python train.py --data data.yaml --model yolov8n.pt --epochs 100 --batch 16
echo.
echo 训练完成! 按任意键返回主菜单...
pause >nul
goto menu

:train_m
echo.
echo [5] 开始训练 (YOLOv8m, 150 epochs, 推荐)...
python train.py --data data.yaml --model yolov8m.pt --epochs 150 --batch 16
echo.
echo 训练完成! 按任意键返回主菜单...
pause >nul
goto menu

:validate
echo.
echo [6] 验证模型...
set /p weights="输入模型路径 [默认: runs/train/exp/weights/best.pt]: "
if "%weights%"=="" set weights=runs/train/exp/weights/best.pt
python train.py --data data.yaml --val-only --weights %weights%
echo.
echo 完成! 按任意键返回主菜单...
pause >nul
goto menu

:inference_image
echo.
echo [7] 推理单张图像...
set /p weights="输入模型路径 [默认: runs/train/exp/weights/best.pt]: "
if "%weights%"=="" set weights=runs/train/exp/weights/best.pt
set /p image="输入图像路径: "
python inference.py --weights %weights% --source %image% --conf 0.25 --show
echo.
echo 完成! 按任意键返回主菜单...
pause >nul
goto menu

:inference_video
echo.
echo [8] 推理视频...
set /p weights="输入模型路径 [默认: runs/train/exp/weights/best.pt]: "
if "%weights%"=="" set weights=runs/train/exp/weights/best.pt
set /p video="输入视频路径: "
python inference.py --weights %weights% --source %video% --conf 0.25
echo.
echo 完成! 按任意键返回主菜单...
pause >nul
goto menu

:inference_camera
echo.
echo [9] 实时摄��头检测...
set /p weights="输入模型路径 [默认: runs/train/exp/weights/best.pt]: "
if "%weights%"=="" set weights=runs/train/exp/weights/best.pt
set /p camera="输入摄像头ID [默认: 0]: "
if "%camera%"=="" set camera=0
python inference.py --weights %weights% --camera %camera% --conf 0.25
echo.
echo 完成! 按任意键返回主菜单...
pause >nul
goto menu

:exit
echo.
echo 再见!
exit

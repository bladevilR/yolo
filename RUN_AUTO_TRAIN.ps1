# YOLO自动训练脚本 - PowerShell版本
# 双击运行即可自动完成所有步骤

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                          ║" -ForegroundColor Cyan
Write-Host "║     🚀 YOLO 自动化训练系统 - 一键启动                     ║" -ForegroundColor Cyan
Write-Host "║                                                          ║" -ForegroundColor Cyan
Write-Host "║     使用最好的模型: YOLOv8x (68.2M参数)                  ║" -ForegroundColor Cyan
Write-Host "║                                                          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 步骤1: 检查Python
Write-Host "【步骤 1/6】检查Python环境..." -ForegroundColor Yellow

$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
}

if ($null -eq $pythonCmd) {
    Write-Host "❌ 错误: 未找到Python" -ForegroundColor Red
    Write-Host ""
    Write-Host "请安装Python 3.8+:" -ForegroundColor Yellow
    Write-Host "   1. 访问: https://www.python.org/downloads/"
    Write-Host "   2. 下载并安装Python"
    Write-Host "   3. 安装时勾选 'Add Python to PATH'"
    Write-Host ""
    Read-Host "按Enter键退出"
    exit
}

Write-Host "✅ Python已安装: $pythonCmd" -ForegroundColor Green
& $pythonCmd --version

# 步骤2: 检查pip
Write-Host ""
Write-Host "【步骤 2/6】检查pip..." -ForegroundColor Yellow

try {
    & $pythonCmd -m pip --version | Out-Null
    Write-Host "✅ pip可用" -ForegroundColor Green
} catch {
    Write-Host "❌ pip不可用" -ForegroundColor Red
    Read-Host "按Enter键退出"
    exit
}

# 步骤3: 安装依赖
Write-Host ""
Write-Host "【步骤 3/6】安装依赖包..." -ForegroundColor Yellow
Write-Host "这可能需要几分钟..." -ForegroundColor Gray

& $pythonCmd -m pip install -r requirements.txt --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "⚠️  依赖安装可能有问题，但继续..." -ForegroundColor Yellow
}

# 步骤4: 检查关键库
Write-Host ""
Write-Host "【步骤 4/6】验证关键库..." -ForegroundColor Yellow

$checkScript = @"
import sys
try:
    import torch
    import ultralytics
    print(f'✅ PyTorch {torch.__version__}')
    print(f'✅ Ultralytics {ultralytics.__version__}')
    if torch.cuda.is_available():
        print(f'✅ GPU可用: {torch.cuda.get_device_name(0)}')
    else:
        print('⚠️  GPU不可用，将使用CPU（较慢）')
    sys.exit(0)
except ImportError as e:
    print(f'❌ 缺少依赖: {e}')
    sys.exit(1)
"@

$result = & $pythonCmd -c $checkScript

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 关键库验证失败" -ForegroundColor Red
    Write-Host "请手动运行: pip install torch ultralytics" -ForegroundColor Yellow
    Read-Host "按Enter键退出"
    exit
}

# 步骤5: 准备数据集
Write-Host ""
Write-Host "【步骤 5/6】数据集准备..." -ForegroundColor Yellow

$datasetPath = "datasets\custom_dataset"

if (Test-Path $datasetPath) {
    $trainImages = (Get-ChildItem -Path "$datasetPath\images\train" -ErrorAction SilentlyContinue).Count
    if ($trainImages -gt 0) {
        Write-Host "✅ 找到现有数据集 ($trainImages 张训练图像)" -ForegroundColor Green
    } else {
        Write-Host "⚠️  数据集目录存在但无图像" -ForegroundColor Yellow
        Write-Host "将创建演示数据集..." -ForegroundColor Gray
    }
} else {
    Write-Host "创建演示数据集..." -ForegroundColor Gray
}

# 步骤6: 启动自动训练
Write-Host ""
Write-Host "【步骤 6/6】启动自动训练脚本..." -ForegroundColor Yellow
Write-Host ""
Write-Host "="*60 -ForegroundColor Cyan
Write-Host "🏋️  准备开始训练..." -ForegroundColor Green
Write-Host "="*60 -ForegroundColor Cyan
Write-Host ""

# 运行自动训练脚本
& $pythonCmd auto_train.py

Write-Host ""
Write-Host "="*60 -ForegroundColor Cyan
Write-Host "🎉 脚本执行完成!" -ForegroundColor Green
Write-Host "="*60 -ForegroundColor Cyan
Write-Host ""
Write-Host "查看QUICKSTART.md了解更多用法" -ForegroundColor Gray
Write-Host ""

Read-Host "按Enter键退出"

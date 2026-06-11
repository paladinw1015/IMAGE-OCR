@echo off
chcp 65001 >nul
echo ======================================
echo   ocr-image 技能 - 安装程序
echo ======================================
echo.

set "PYTHON=C:\Users\pala\AppData\Local\Python\pythoncore-3.14-64\python.exe"

if not exist "%PYTHON%" (
    echo [错误] 未找到 Python: %PYTHON%
    echo 请修改 install.bat 中的 PYTHON 路径后再试。
    pause
    exit /b 1
)

echo [1/2] 安装 Python 依赖 (rapidocr-onnxruntime)...
"%PYTHON%" -m pip install -r "%~dp0requirements.txt" --quiet
if %ERRORLEVEL% NEQ 0 (
    echo [错误] pip 安装失败，请检查网络连接后重试。
    echo 如在国内网络环境，可使用镜像源:
    echo   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    pause
    exit /b 1
)
echo [1/2] 依赖安装完成。

echo.
echo [2/2] 验证 RapidOCR 导入...
"%PYTHON%" -c "from rapidocr_onnxruntime import RapidOCR; print('RapidOCR 导入成功'); print('首次使用时会自动下载模型文件 (~50MB)，请保持网络通畅。')"
if %ERRORLEVEL% NEQ 0 (
    echo [警告] RapidOCR 导入测试未通过，但 pip 安装已成功。
    echo 可能是 Python 版本兼容性问题，请手动测试。
    pause
    exit /b 1
)
echo [2/2] 验证完成。

echo.
echo ======================================
echo   安装完成！ocr-image 技能已就绪。
echo   首次运行 OCR 时会自动下载模型 (~50MB)。
echo ======================================
pause

#!/bin/bash
# 小绿茶XSS反连平台 - 安装脚本

echo "🍃 小绿茶XSS反连平台安装脚本"
echo "=================================="

# 检查Python版本
echo "检查Python环境..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ 未找到Python，请先安装Python 3.8+"
    exit 1
fi

echo "✅ 使用Python: $($PYTHON_CMD --version)"

# 安装依赖包
echo ""
echo "安装依赖包..."
$PYTHON_CMD -m pip install --upgrade pip
$PYTHON_CMD -m pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ 依赖包安装成功"
else
    echo "❌ 依赖包安装失败"
    exit 1
fi

# 创建必要目录
echo ""
echo "创建必要目录..."
mkdir -p data/sessions jstemplates myjs logs

echo "✅ 目录创建完成"

# 设置权限
echo ""
echo "设置文件权限..."
chmod +x app.py
chmod +x install.sh
chmod 777 -R data  install.sh  jstemplates  logs  myjs  static  templates


echo "✅ 权限设置完成"

echo ""
echo "=================================="
echo "🎉 安装完成！"
echo ""
echo "启动应用:"
echo "  python app.py"
echo ""
echo "访问地址:"
echo "  后台: http://127.0.0.1:5000/admin"
echo "  反连地址: http://127.0.0.1:5000"
echo "  反连地址2: http://127.0.0.1:5000/api/collect"
echo ""
echo "默认密码: godxing"
echo "=================================="

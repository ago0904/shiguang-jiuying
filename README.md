# 拾光旧影 - AI老照片修复小程序

<p align="center">
  <img src="images/avatar-option2.png" width="120" alt="拾光旧影 Logo">
</p>

<p align="center">
  <b>用AI的力量，让褪色的记忆重新鲜活</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/微信小程序-原生框架-blue" alt="微信小程序">
  <img src="https://img.shields.io/badge/Django-3.x-green" alt="Django">
  <img src="https://img.shields.io/badge/Python-3.11-yellow" alt="Python">
  <img src="https://img.shields.io/badge/数据库-SQLite%2FMySQL-orange" alt="Database">
</p>

---

## 项目简介

「拾光旧影」是一款专注老照片修复的AI智能小程序，支持四大修复功能：

| 功能 | 说明 |
|------|------|
| **黑白上色** | 为黑白老照片赋予自然真实的色彩 |
| **破损修复** | 智能填补划痕、折痕、污渍 |
| **清晰度增强** | 模糊照片变清晰，人脸细节还原 |
| **智能去噪** | 去除老旧照片噪点，画面干净通透 |

---

## 项目结构

```
.
├── README.md                          # 项目说明
├── .gitignore
├── docs/
│   └── 小程序介绍文案.md               # 小程序商店/推广文案
│
├── 微信小程序前端
│   ├── app.js                         # 全局逻辑+登录状态管理
│   ├── app.json                       # 页面路由+TabBar
│   ├── app.wxss                       # 全局设计系统
│   ├── utils/
│   │   ├── api.js                     # 后端API封装
│   │   └── auth.js                    # 微信登录+JWT管理
│   ├── pages/
│   │   ├── login/                     # 登录页面
│   │   ├── index/                     # 首页-Hero+模式介绍+案例
│   │   ├── restore/                   # 修复页-上传+处理+对比
│   │   ├── gallery/                   # 画廊页-修复案例展示
│   │   └── mine/                      # 我的页-用户中心+历史
│   ├── components/
│   │   ├── upload-zone/               # 上传区域组件
│   │   ├── mode-card/                 # 修复模式卡片
│   │   ├── compare-slider/            # 前后对比滑块
│   │   └── progress-ring/             # 圆形进度环
│   └── images/                        # 图片素材(29张)
│
├── Django后端 (推荐-新架构)
│   ├── manage.py                      # Django管理命令
│   ├── requirements.txt               # Python依赖
│   ├── .env.example                   # 环境变量模板
│   ├── shiguang/                      # 项目配置
│   │   ├── settings.py                # 数据库/微信/JWT配置
│   │   ├── urls.py                    # 根路由
│   │   └── wsgi.py
│   ├── core/                          # 核心模块
│   │   ├── auth.py                    # 微信登录
│   │   ├── decorators.py              # 认证装饰器
│   │   └── utils.py                   # JWT+响应工具
│   ├── api/                           # 修复API
│   │   ├── models.py                  # RepairRecord
│   │   ├── views.py                   # 上传/修复/结果
│   │   └── urls.py
│   ├── users/                         # 用户管理
│   │   ├── models.py                  # User(微信用户)
│   │   ├── views.py                   # 登录/注册/登出
│   │   └── urls.py
│   ├── stats/                         # 数据统计
│   │   ├── models.py                  # DailyStats/HourlyStats
│   │   ├── views.py                   # 看板/趋势/分布
│   │   └── services.py                # 统计逻辑
│   ├── admin_portal/                  # 管理后台
│   │   ├── views.py                   # 14个管理API
│   │   └── urls.py
│   └── templates/
│       └── admin.html                 # 管理后台页面
│
└── Flask后端 (保留-旧版参考)
    ├── app.py                         # Flask主应用
    ├── api_manager.py                 # 多平台AI轮询
    └── ...
```

---

## 技术栈

### 前端
- 微信小程序原生框架 (WXML + WXSS + JS)
- 微信登录 (wx.login + code2Session)
- 响应式设计，温暖复古风格

### Django后端 (推荐)
- **Django 3.x** + SQLite/MySQL
- JWT认证 (PyJWT)
- 多平台AI API智能轮询 (百度AI/腾讯云/Replicate)
- 数据统计 (DailyStats/HourlyStats)
- 管理后台 (数据看板 + 用户管理 + 修复记录)

### AI平台对接
- 百度AI开放平台（免费额度最多）
- 腾讯云AI（备用）
- Replicate（海外模型）

---

## 数据库模型

| 模型 | 表名 | 说明 |
|------|------|------|
| **User** | users | 微信用户 (openid主键) |
| **RepairRecord** | repair_records | 修复记录 |
| **DailyStats** | daily_stats | 每日统计 |
| **HourlyStats** | hourly_stats | 每小时统计 |

---

## 数据库切换 (SQLite ↔ MySQL)

```bash
# SQLite（默认，无需安装）
export DATABASE_TYPE=sqlite

# MySQL（随时切换）
export DATABASE_TYPE=mysql
export MYSQL_NAME=shiguang
export MYSQL_USER=root
export MYSQL_PASSWORD=密码
export MYSQL_HOST=127.0.0.1

# 迁移
python manage.py makemigrations
python manage.py migrate
```

---

## 快速启动

### 1. 克隆代码

```bash
git clone https://github.com/ago0904/shiguang-jiuying.git
cd shiguang-jiuying
```

### 2. 启动Django后端

```bash
cd django_backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入: WECHAT_APPID/SECRET + BAIDU_APP_KEY/SECRET

python manage.py makemigrations users api stats
python manage.py migrate
python manage.py runserver
```

后端服务运行在 `http://localhost:8000`
- 管理后台: `http://localhost:8000/admin/`
- Django Admin: `http://localhost:8000/admin/django/`

### 3. 配置小程序

1. 微信开发者工具打开项目根目录
2. 修改 `utils/api.js` 和 `utils/auth.js` 中的 `API_BASE`
3. 编译预览

---

## 获取API密钥

### 百度AI开放平台
1. 访问 [ai.baidu.com](https://ai.baidu.com/)
2. 控制台 → 产品服务 → 图像处理
3. 创建应用，获取 API Key 和 Secret Key

### 微信小程序
1. 访问 [mp.weixin.qq.com](https://mp.weixin.qq.com/)
2. 开发管理 → 开发设置 → AppID/AppSecret

---

## 核心功能

- **微信一键登录** - 自动获取用户信息
- **AI照片修复** - 4种模式，多平台轮询
- **修复前后对比** - 滑动对比条
- **数据统计** - 今日/7天趋势/模式分布
- **管理后台** - 用户管理/修复记录/系统设置
- **免费额度管理** - 新用户3次免费，会员无限

---

## License

MIT License

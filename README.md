# 拾光旧影 - AI老照片修复小程序

<p align="center">
  <img src="images/avatar-option2.png" width="120" alt="拾光旧影 Logo">
</p>

<p align="center">
  <b>用AI的力量，让褪色的记忆重新鲜活</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-微信小程序-blue" alt="Platform">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/python-3.11-yellow" alt="Python">
  <img src="https://img.shields.io/badge/flask-3.0-orange" alt="Flask">
</p>

---

## 项目简介

「拾光旧影」是一款专注老照片修复的AI智能小程序，支持四大修复功能：

| 功能 | 说明 |
|------|------|
| 黑白上色 | 为黑白老照片赋予自然真实的色彩 |
| 破损修复 | 智能填补划痕、折痕、污渍 |
| 清晰度增强 | 模糊照片变清晰，人脸细节还原 |
| 智能去噪 | 去除老旧照片噪点，画面干净通透 |

## 项目结构

```
.
├── README.md              # 项目说明
├── .gitignore             # Git忽略文件
│
├── 微信小程序前端
│   ├── app.js             # 小程序全局逻辑
│   ├── app.json           # 页面路由 + TabBar配置
│   ├── app.wxss           # 全局设计系统
│   ├── project.config.json # 项目配置
│   ├── sitemap.json       # 搜索索引
│   ├── utils/
│   │   └── api.js         # 后端API对接
│   ├── pages/
│   │   ├── index/         # 首页 - Hero + 4大模式
│   │   ├── restore/       # 修复页 - 上传+处理+对比
│   │   ├── gallery/       # 画廊页 - 案例展示
│   │   └── mine/          # 我的页 - 修复历史
│   ├── components/
│   │   ├── upload-zone/   # 上传区域组件
│   │   ├── mode-card/     # 修复模式卡片
│   │   ├── compare-slider/# 前后对比滑块
│   │   └── progress-ring/ # 圆形进度环
│   └── images/            # 图片资源
│
└── 后端服务 (Flask)
    ├── app.py             # Flask主应用
    ├── api_manager.py     # 多平台API管理器
    ├── requirements.txt   # Python依赖
    ├── config.json        # API平台配置
    ├── Dockerfile         # Docker镜像
    ├── docker-compose.yml # Docker编排
    └── DEPLOY.md          # 部署指南
```

## 技术栈

### 前端
- 微信小程序原生框架 (WXML + WXSS + JS)
- 响应式设计，适配各种屏幕
- 温暖复古风格设计

### 后端
- Python 3.11 + Flask 3.0
- 多平台AI API智能轮询
- Docker + Docker Compose 部署

### AI平台对接
- 百度AI开放平台（主平台，免费额度最多）
- 腾讯云AI（备用）
- Replicate（海外模型，效果最佳）

## 多平台免费额度策略

| 平台 | 黑白上色 | 破损修复 | 清晰度增强 | 智能去噪 |
|------|----------|----------|------------|----------|
| 百度AI | 1,000次/月 | 1,500次/月 | 3,000次/月 | 3,000次/月 |
| 腾讯云 | - | - | 1,000次/月 | - |
| Replicate | ~500次 | ~500次 | ~500次 | ~500次 |
| **合计** | **~1,500次** | **~2,000次** | **~4,500次** | **~3,500次** |

**每月总免费额度：约 11,500 次修复**

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/shiguang-jiuying.git
cd shiguang-jiuying
```

### 2. 配置后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入你的百度AI密钥
python app.py
```

后端服务运行在 `http://localhost:5000`

### 3. 配置小程序

1. 用 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html) 打开项目根目录
2. 编辑 `utils/api.js`，修改 `BASE_URL` 为你的后端地址
3. 编译预览

## 部署到生产环境

详见 [backend/DEPLOY.md](backend/DEPLOY.md)，包含以下方案：

- Docker 部署
- 腾讯云云函数SCF（几乎免费）
- 腾讯云轻量服务器

## 获取API密钥

### 百度AI开放平台（推荐）

1. 访问 [ai.baidu.com](https://ai.baidu.com/)
2. 注册/登录百度账号
3. 进入控制台 → 产品服务 → 图像处理
4. 创建应用，获取 `API Key` 和 `Secret Key`
5. 开通图像修复、黑白上色、清晰度增强服务

## 小程序界面预览

| 首页 | 修复页 | 画廊页 | 我的页 |
|------|--------|--------|--------|
| 品牌Hero + 4大模式 | 上传+处理+对比 | 瀑布流案例 | 用户历史 |

## 开源协议

MIT License

## 联系方式

如有问题或建议，欢迎提交 Issue。

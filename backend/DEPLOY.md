# 拾光旧影后端 - 部署指南

## 方案一：本地开发（推荐起步）

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置API密钥

编辑 `.env` 文件：

```bash
cp .env.example .env
# 然后编辑 .env，填入你的百度AI密钥
```

### 3. 运行服务

```bash
python app.py
```

服务启动在 `http://localhost:5000`

---

## 方案二：Docker部署（推荐生产）

### 1. 安装Docker和Docker Compose

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入密钥
```

### 3. 启动服务

```bash
docker-compose up -d
```

---

## 方案三：腾讯云轻量服务器（国内推荐）

### 1. 购买轻量应用服务器
- 推荐配置：2核4G，¥50-100/月
- 系统：Ubuntu 22.04

### 2. 连接服务器

```bash
ssh root@你的服务器IP
```

### 3. 安装Docker

```bash
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
```

### 4. 上传代码

```bash
# 本地执行
scp -r backend root@你的服务器IP:/opt/photo-restore
cp .env backend/.env
scp .env root@你的服务器IP:/opt/photo-restore/.env
```

### 5. 启动

```bash
ssh root@你的服务器IP
cd /opt/photo-restore
docker-compose up -d
```

### 6. 配置Nginx反向代理（HTTPS）

```nginx
server {
    listen 80;
    server_name 你的域名.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

使用 certbot 配置免费SSL证书。

---

## 方案四：腾讯云云函数SCF（几乎免费）

### 优势
- 每月前10万次调用**免费**
- 自动扩缩容
- 无需维护服务器

### 部署步骤

1. 登录 [腾讯云云函数控制台](https://console.cloud.tencent.com/scf)
2. 创建函数 → 自定义创建
3. 运行环境：Python 3.11
4. 上传代码（将backend代码打包zip上传）
5. 配置环境变量（BAIDU_APP_KEY等）
6. 创建API网关触发器（自动生成HTTPS接口）
7. 完成！获得一个HTTPS接口地址

---

## 百度AI API Key 获取教程

1. 访问 [https://ai.baidu.com/](https://ai.baidu.com/)
2. 登录百度账号
3. 进入控制台 → 产品服务 → 图像处理
4. 创建应用，获取 `API Key` 和 `Secret Key`
5. 开通以下服务（全部有免费额度）：
   - 图像修复
   - 黑白图像上色
   - 图像清晰度增强

---

## 微信小程序对接

### 1. 配置服务器域名

登录 [微信小程序后台](https://mp.weixin.qq.com/) → 开发管理 → 开发设置 → 服务器域名

添加：
- request合法域名：`https://你的域名.com`
- uploadFile合法域名：`https://你的域名.com`

### 2. 修改小程序API地址

编辑 `miniprogram/utils/api.js`：

```javascript
const BASE_URL = 'https://你的域名.com';
```

### 3. 重新编译上传

---

## 免费额度汇总

| 平台 | 免费额度 | 每月节省 |
|------|----------|----------|
| 百度AI - 上色 | 1000次 | ~¥60 |
| 百度AI - 修复 | 1500次 | ~¥38 |
| 百度AI - 增强 | 3000次 | ~¥21 |
| 腾讯云SCF | 10万次调用 | ~¥100 |
| **合计** | **5500次修复** | **¥219** |

---

## 常见问题

### Q: 免费额度用完怎么办？
A: 系统会自动轮询下一个平台。建议同时开通多个平台账号（家人朋友账号也可以），用config.json配置多个Key。

### Q: 如何查看剩余额度？
A: 访问 `http://你的域名/api/quota`

### Q: 修复速度怎么样？
A: 百度AI一般1-3秒返回，取决于图片大小和网络状况。

### Q: 支持多大的图片？
A: 最大20MB，建议上传1-5MB的图片，速度和效果最佳。

"""
Django 项目配置 - 拾光旧影
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# ─────────────────────────────────────────────
# 安全设置
# ─────────────────────────────────────────────

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-shiguang-jiuying-secret-key-2024')

DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = ['*']

# ─────────────────────────────────────────────
# 应用配置
# ─────────────────────────────────────────────

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'core',
    'users',
    'api',
    'stats',
    'admin_portal',
    'webapp',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'core.middleware.ExemptCSRFMiddleware',  # 自定义CSRF豁免中间件
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ─────────────────────────────────────────────
# 路由配置
# ─────────────────────────────────────────────

ROOT_URLCONF = 'shiguang.urls'

# ─────────────────────────────────────────────
# 模板配置
# ─────────────────────────────────────────────

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ─────────────────────────────────────────────
# WSGI配置
# ─────────────────────────────────────────────

WSGI_APPLICATION = 'shiguang.wsgi.application'

# ─────────────────────────────────────────────
# 数据库配置
# ─────────────────────────────────────────────

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db' / 'shiguang.db',
    }
}

# MySQL 配置（可选）
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': os.getenv('DB_NAME', 'shiguang'),
#         'USER': os.getenv('DB_USER', 'root'),
#         'PASSWORD': os.getenv('DB_PASSWORD', ''),
#         'HOST': os.getenv('DB_HOST', 'localhost'),
#         'PORT': os.getenv('DB_PORT', '3306'),
#         'OPTIONS': {
#             'charset': 'utf8mb4',
#         },
#     }
# }

# ─────────────────────────────────────────────
# 密码验证
# ─────────────────────────────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ─────────────────────────────────────────────
# 国际化
# ─────────────────────────────────────────────

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# ─────────────────────────────────────────────
# 静态文件
# ─────────────────────────────────────────────

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'

# 媒体文件
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 默认主键类型
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─────────────────────────────────────────────
# CORS配置
# ─────────────────────────────────────────────

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    '*',
    'authorization',
    'content-type',
    'x-admin-token',
    'x-requested-with',
]
CORS_EXPOSE_HEADERS = ['*']

# ─────────────────────────────────────────────
# CSRF配置
# ─────────────────────────────────────────────

CSRF_TRUSTED_ORIGINS = ['*']

# ─────────────────────────────────────────────
# 微信配置
# ─────────────────────────────────────────────

WECHAT_APPID = os.getenv('WECHAT_APPID', '')
WECHAT_SECRET = os.getenv('WECHAT_SECRET', '')

# ─────────────────────────────────────────────
# JWT配置
# ─────────────────────────────────────────────

JWT_SECRET = os.getenv('JWT_SECRET', 'shiguang-jiuying-secret-key-2024')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRE_HOURS = 24 * 7  # Token有效期7天

# ─────────────────────────────────────────────
# 百度AI配置
# ─────────────────────────────────────────────

BAIDU_APP_KEY = os.getenv('BAIDU_APP_KEY', '')
BAIDU_APP_SECRET = os.getenv('BAIDU_APP_SECRET', '')

# ─────────────────────────────────────────────
# 腾讯云配置
# ─────────────────────────────────────────────

TENCENT_SECRET_ID = os.getenv('TENCENT_SECRET_ID', '')
TENCENT_SECRET_KEY = os.getenv('TENCENT_SECRET_KEY', '')

# ─────────────────────────────────────────────
# Replicate配置
# ─────────────────────────────────────────────

REPLICATE_API_TOKEN = os.getenv('REPLICATE_API_TOKEN', '')

# ─────────────────────────────────────────────
# 免费额度配置
# ─────────────────────────────────────────────

FREE_REPAIRS = int(os.getenv('FREE_REPAIRS', '3'))
FREE_DAILY_LIMIT = int(os.getenv('FREE_DAILY_LIMIT', '3'))

# ─────────────────────────────────────────────
# 会员价格配置
# ─────────────────────────────────────────────

MEMBER_PRICE_MONTHLY = float(os.getenv('MEMBER_PRICE_MONTHLY', '19.9'))
MEMBER_PRICE_QUARTERLY = float(os.getenv('MEMBER_PRICE_QUARTERLY', '49.9'))
MEMBER_PRICE_YEARLY = float(os.getenv('MEMBER_PRICE_YEARLY', '169.9'))
MEMBER_DAILY_LIMIT = int(os.getenv('MEMBER_DAILY_LIMIT', '50'))

# ─────────────────────────────────────────────
# 管理员配置
# ─────────────────────────────────────────────

ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'admin123456')
ADMIN_ACCOUNTS = {
    "admin": {
        "password": os.getenv('ADMIN_PASSWORD', 'admin123'),
        "role": "super_admin",
        "name": "超级管理员"
    }
}

# ─────────────────────────────────────────────
# 系统设置
# ─────────────────────────────────────────────

MAX_IMAGE_SIZE = int(os.getenv('MAX_IMAGE_SIZE', '10'))  # MB
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'support@shiguangjiuying.com')
SYSTEM_NOTICE = os.getenv('SYSTEM_NOTICE', '')

# ─────────────────────────────────────────────
# 日志配置
# ─────────────────────────────────────────────

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'standard',
            'encoding': 'utf-8',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'core': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
        },
        'users': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
        },
        'stats': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
        },
        'admin_portal': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
        },
    },
}

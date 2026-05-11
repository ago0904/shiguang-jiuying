"""统一配置管理"""
import os


class Config:
    """应用配置类，所有配置项集中管理"""

    # ─────────────────────────────────────────────
    # 微信配置
    # ─────────────────────────────────────────────
    WECHAT_APPID = os.getenv('WECHAT_APPID', '')
    WECHAT_SECRET = os.getenv('WECHAT_SECRET', '')

    # 微信登录API
    WECHAT_JS_CODE_URL = 'https://api.weixin.qq.com/sns/jscode2session'

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
    # 免费额度配置
    # ─────────────────────────────────────────────
    FREE_REPAIRS_PER_USER = 3  # 每个用户免费3次

    # ─────────────────────────────────────────────
    # 数据统计配置
    # ─────────────────────────────────────────────
    STATS_FILE = 'stats.json'       # 统计聚合数据
    USERS_FILE = 'users.json'       # 用户数据
    HISTORY_FILE = 'history.json'   # 修复历史记录
    DATA_DIR = 'data'               # 数据文件存放目录

    # ─────────────────────────────────────────────
    # 管理员配置
    # ─────────────────────────────────────────────
    ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'admin123456')  # 后台管理token

    # ─────────────────────────────────────────────
    # 日志配置
    # ─────────────────────────────────────────────
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'

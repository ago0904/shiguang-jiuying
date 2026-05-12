"""
管理后台路由整合模块
将 admin_api.py 的 API 和管理后台页面路由整合到一起

路由说明：
  - /admin/          → 返回管理后台页面 (admin.html)
  - /admin/api/*     → 管理后台 API 接口

使用方法：
  在 app.py 中注册蓝图：
      from admin_routes import admin_bp
      app.register_blueprint(admin_bp, url_prefix='/admin')
"""

from flask import Blueprint, render_template, send_from_directory
from admin_api import admin_api_bp

# ============================================================
# 创建管理后台蓝图
# ============================================================

admin_bp = Blueprint('admin', __name__,
                      template_folder='templates',
                      static_folder='static')

# ============================================================
# 管理后台页面路由
# ============================================================

@admin_bp.route('/', methods=['GET'])
def admin_page():
    """返回管理后台单页应用"""
    return render_template('admin.html')


@admin_bp.route('/<path:filename>')
def admin_static(filename):
    """提供管理后台静态文件"""
    return send_from_directory('templates', filename)


# ============================================================
# 注册 API 子蓝图
# ============================================================

admin_bp.register_blueprint(admin_api_bp, url_prefix='/api')


# ============================================================
# 便捷注册函数
# ============================================================

def register_admin(app, url_prefix='/admin'):
    """
    便捷注册管理后台到 Flask 应用

    参数:
        app: Flask 应用实例
        url_prefix: URL 前缀，默认为 /admin

    用法:
        from admin_routes import register_admin
        register_admin(app)
    """
    app.register_blueprint(admin_bp, url_prefix=url_prefix)
    print(f"[管理后台] 已注册到 {url_prefix}/")
    print(f"[管理后台] 页面地址: http://localhost:5000{url_prefix}/")
    print(f"[管理后台] API地址:  http://localhost:5000{url_prefix}/api/")

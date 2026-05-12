"""
自定义CSRF中间件
为管理后台API路径豁免CSRF检查
"""

class ExemptCSRFMiddleware:
    """
    对指定路径豁免CSRF检查
    适用于使用Token认证的API接口
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # 需要豁免CSRF的路径前缀
        self.exempt_paths = [
            '/admin/api/',
        ]
    
    def __call__(self, request):
        # 检查请求路径是否需要豁免CSRF
        path = request.path_info
        
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                # 标记该请求豁免CSRF检查
                setattr(request, '_dont_enforce_csrf_checks', True)
                break
        
        response = self.get_response(request)
        return response

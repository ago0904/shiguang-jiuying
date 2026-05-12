"""
修复记录 - Django Admin 配置
"""
from django.contrib import admin
from .models import RepairRecord, PlatformConfig


@admin.register(RepairRecord)
class RepairRecordAdmin(admin.ModelAdmin):
    """修复记录管理后台"""
    list_display = [
        'id', 'user_info', 'mode_name', 'platform',
        'cost_time_display', 'is_success', 'status',
        'created_at', 'ip'
    ]
    list_filter = ['mode', 'platform', 'is_success', 'status', 'created_at']
    search_fields = ['file_id', 'user__nickname', 'user__id', 'ip']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    readonly_fields = [
        'id', 'file_id', 'created_at',
        'mode_display_name', 'platform_display_name'
    ]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'file_id', 'status')
        }),
        ('修复信息', {
            'fields': ('mode', 'mode_name', 'platform', 'cost_time', 'is_success')
        }),
        ('文件路径', {
            'fields': ('source_path', 'result_path'),
            'classes': ('collapse',)
        }),
        ('错误信息', {
            'fields': ('error_msg',),
            'classes': ('collapse',)
        }),
        ('其他', {
            'fields': ('ip',),
            'classes': ('collapse',)
        }),
    )
    
    def user_info(self, obj):
        """显示用户信息"""
        if obj.user:
            return f"{obj.user.nickname or obj.user.id[:16]}"
        return "匿名用户"
    user_info.short_description = '用户'
    
    def mode_name(self, obj):
        """显示模式名称"""
        return obj.mode_display_name
    mode_name.short_description = '修复模式'
    
    def cost_time_display(self, obj):
        """显示耗时"""
        return f"{obj.cost_time:.2f}s"
    cost_time_display.short_description = '耗时'


@admin.register(PlatformConfig)
class PlatformConfigAdmin(admin.ModelAdmin):
    """平台配置管理后台"""
    list_display = ['platform', 'platform_name', 'is_enabled', 'updated_at']
    list_filter = ['platform', 'is_enabled']
    search_fields = ['platform', 'remark']
    ordering = ['platform']
    
    fieldsets = (
        ('平台信息', {
            'fields': ('platform', 'is_enabled', 'remark')
        }),
        ('API 配置', {
            'fields': ('api_key', 'api_secret'),
            'classes': ('collapse',)
        }),
        ('额外配置', {
            'fields': ('extra_config',),
            'classes': ('collapse',)
        }),
    )
    
    def platform_name(self, obj):
        """显示平台名称"""
        return obj.get_platform_display()
    platform_name.short_description = '平台名称'

"""
统计数据 - Django Admin 配置
"""
from django.contrib import admin
from .models import DailyStats, HourlyStats


@admin.register(DailyStats)
class DailyStatsAdmin(admin.ModelAdmin):
    """每日统计管理后台"""
    list_display = [
        'date', 'total_repairs', 'unique_users', 'new_users',
        'colorize_display', 'repair_display', 'enhance_display', 'denoise_display',
        'baidu_display', 'tencent_display', 'replicate_display',
        'avg_cost_time', 'errors'
    ]
    list_filter = ['date']
    search_fields = ['date']
    date_hierarchy = 'date'
    ordering = ['-date']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本统计', {
            'fields': ('date', 'total_repairs', 'unique_users', 'new_users')
        }),
        ('模式分布', {
            'fields': ('mode_colorize', 'mode_repair', 'mode_enhance', 'mode_denoise')
        }),
        ('平台分布', {
            'fields': ('platform_baidu', 'platform_tencent', 'platform_replicate')
        }),
        ('性能与错误', {
            'fields': ('avg_cost_time', 'errors')
        }),
    )
    
    def colorize_display(self, obj):
        return obj.mode_colorize
    colorize_display.short_description = '上色'
    
    def repair_display(self, obj):
        return obj.mode_repair
    repair_display.short_description = '修复'
    
    def enhance_display(self, obj):
        return obj.mode_enhance
    enhance_display.short_description = '增强'
    
    def denoise_display(self, obj):
        return obj.mode_denoise
    denoise_display.short_description = '去噪'
    
    def baidu_display(self, obj):
        return obj.platform_baidu
    baidu_display.short_description = '百度'
    
    def tencent_display(self, obj):
        return obj.platform_tencent
    tencent_display.short_description = '腾讯'
    
    def replicate_display(self, obj):
        return obj.platform_replicate
    replicate_display.short_description = 'Replicate'


@admin.register(HourlyStats)
class HourlyStatsAdmin(admin.ModelAdmin):
    """每小时统计管理后台"""
    list_display = ['date', 'hour', 'label', 'repairs', 'hourly_modes']
    list_filter = ['date']
    ordering = ['-date', '-hour']
    
    def hourly_modes(self, obj):
        """显示模式分布"""
        return f"上色{obj.mode_colorize}/修复{obj.mode_repair}/增强{obj.mode_enhance}/去噪{obj.mode_denoise}"
    hourly_modes.short_description = '模式分布'

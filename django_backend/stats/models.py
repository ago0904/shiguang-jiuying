"""
统计模块 - 数据模型
基于 Django ORM，兼容 SQLite 和 MySQL
提供每日统计和每小时统计数据
"""
from django.db import models


class DailyStats(models.Model):
    """
    每日统计数据
    每日汇总所有修复操作的关键指标
    """
    date = models.DateField(unique=True, db_index=True, verbose_name='日期')
    
    # 总体统计
    total_repairs = models.IntegerField(default=0, verbose_name='总修复次数')
    unique_users = models.IntegerField(default=0, verbose_name='独立用户数')
    new_users = models.IntegerField(default=0, verbose_name='新用户数')
    
    # 按模式统计
    mode_colorize = models.IntegerField(default=0, verbose_name='黑白上色次数')
    mode_repair = models.IntegerField(default=0, verbose_name='破损修复次数')
    mode_enhance = models.IntegerField(default=0, verbose_name='清晰度增强次数')
    mode_denoise = models.IntegerField(default=0, verbose_name='智能去噪次数')
    
    # 按平台统计
    platform_baidu = models.IntegerField(default=0, verbose_name='百度AI次数')
    platform_tencent = models.IntegerField(default=0, verbose_name='腾讯云次数')
    platform_replicate = models.IntegerField(default=0, verbose_name='Replicate次数')
    
    # 性能统计
    avg_cost_time = models.FloatField(default=0.0, verbose_name='平均耗时(秒)')
    errors = models.IntegerField(default=0, verbose_name='错误次数')
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'daily_stats'
        ordering = ['-date']
        verbose_name = '每日统计'
        verbose_name_plural = '每日统计数据'
    
    @property
    def mode_distribution(self):
        """返回模式分布数据"""
        return {
            'colorize': self.mode_colorize,
            'repair': self.mode_repair,
            'enhance': self.mode_enhance,
            'denoise': self.mode_denoise,
        }
    
    @property
    def platform_distribution(self):
        """返回平台分布数据"""
        return {
            'baidu': self.platform_baidu,
            'tencent': self.platform_tencent,
            'replicate': self.platform_replicate,
        }
    
    def to_dict(self):
        """转换为字典"""
        return {
            'date': str(self.date),
            'total_repairs': self.total_repairs,
            'unique_users': self.unique_users,
            'new_users': self.new_users,
            'mode_distribution': self.mode_distribution,
            'platform_distribution': self.platform_distribution,
            'avg_cost_time': round(self.avg_cost_time, 2),
            'errors': self.errors,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
    
    def __str__(self):
        return f"[{self.date}] 修复{self.total_repairs}次"


class HourlyStats(models.Model):
    """
    每小时统计数据
    记录每天每小时的修复次数
    """
    date = models.DateField(verbose_name='日期')
    hour = models.IntegerField(verbose_name='小时', help_text='0-23')
    
    # 修复次数
    repairs = models.IntegerField(default=0, verbose_name='修复次数')
    
    # 模式细分（可选，用于更详细的分析）
    mode_colorize = models.IntegerField(default=0, verbose_name='黑白上色')
    mode_repair = models.IntegerField(default=0, verbose_name='破损修复')
    mode_enhance = models.IntegerField(default=0, verbose_name='清晰度增强')
    mode_denoise = models.IntegerField(default=0, verbose_name='智能去噪')
    
    class Meta:
        db_table = 'hourly_stats'
        unique_together = ['date', 'hour']
        ordering = ['date', 'hour']
        verbose_name = '每小时统计'
        verbose_name_plural = '每小时统计数据'
    
    @property
    def label(self):
        """返回时间标签"""
        return f"{self.hour:02d}:00"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'date': str(self.date),
            'hour': self.hour,
            'label': self.label,
            'repairs': self.repairs,
            'mode_distribution': {
                'colorize': self.mode_colorize,
                'repair': self.mode_repair,
                'enhance': self.mode_enhance,
                'denoise': self.mode_denoise,
            },
        }
    
    def __str__(self):
        return f"[{self.date} {self.hour:02d}:00] 修复{self.repairs}次"

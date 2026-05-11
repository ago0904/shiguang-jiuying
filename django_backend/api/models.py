"""
修复记录模块 - 数据模型
基于 Django ORM，兼容 SQLite 和 MySQL
"""
from django.db import models


class RepairRecord(models.Model):
    """
    修复记录模型
    记录每次图片修复/上色的详细信息
    """
    
    # 修复模式选项
    MODE_CHOICES = [
        ('colorize', '黑白上色'),
        ('repair', '破损修复'),
        ('enhance', '清晰度增强'),
        ('denoise', '智能去噪'),
    ]
    
    # 用户关联（外键，匿名用户为 null）
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='用户',
        db_column='user_id',
    )
    
    # 文件标识
    file_id = models.CharField(max_length=128, verbose_name='文件ID')
    
    # 修复模式
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, verbose_name='修复模式')
    mode_name = models.CharField(max_length=50, default='', verbose_name='模式名称')
    
    # AI 平台
    platform = models.CharField(max_length=50, default='', verbose_name='AI平台', help_text='baidu/tencent/replicate')
    
    # 处理耗时（秒）
    cost_time = models.FloatField(default=0.0, verbose_name='耗时(秒)')
    
    # 创建时间
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    # IP 地址
    ip = models.CharField(max_length=50, blank=True, default='', verbose_name='IP地址')
    
    # 是否成功
    is_success = models.BooleanField(default=True, verbose_name='是否成功')
    
    # 错误信息（失败时记录）
    error_msg = models.TextField(blank=True, default='', verbose_name='错误信息')
    
    # 源文件路径
    source_path = models.CharField(max_length=255, blank=True, default='', verbose_name='源文件路径')
    
    # 结果文件路径
    result_path = models.CharField(max_length=255, blank=True, default='', verbose_name='结果文件路径')
    
    # 回调状态（异步处理时使用）
    STATUS_CHOICES = [
        ('pending', '等待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    status = models.CharField(max_length=20, default='completed', choices=STATUS_CHOICES, verbose_name='处理状态')
    
    class Meta:
        db_table = 'repair_records'  # 指定表名，避免冲突
        ordering = ['-created_at']
        verbose_name = '修复记录'
        verbose_name_plural = '修复记录列表'
        indexes = [
            models.Index(fields=['user', '-created_at'], name='idx_user_created'),
            models.Index(fields=['mode'], name='idx_mode'),
            models.Index(fields=['platform'], name='idx_platform'),
            models.Index(fields=['is_success'], name='idx_success'),
            models.Index(fields=['file_id'], name='idx_file_id'),
        ]

    @property
    def mode_display_name(self):
        """获取模式的中文显示名称"""
        mode_map = dict(self.MODE_CHOICES)
        return mode_map.get(self.mode, self.mode)

    @property
    def platform_display_name(self):
        """获取平台的中文显示名称"""
        platform_map = {
            'baidu': '百度AI',
            'tencent': '腾讯云',
            'replicate': 'Replicate',
            '': '未指定',
        }
        return platform_map.get(self.platform, self.platform)

    def to_dict(self):
        """
        将记录转换为字典（用于 API 返回）
        """
        return {
            'id': str(self.id),
            'file_id': self.file_id,
            'mode': self.mode,
            'mode_name': self.mode_display_name,
            'platform': self.platform,
            'platform_name': self.platform_display_name,
            'cost_time': round(self.cost_time, 2),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'ip': self.ip,
            'is_success': self.is_success,
            'error_msg': self.error_msg,
            'status': self.status,
        }

    def __str__(self):
        user_label = self.user.nickname if self.user else '匿名'
        return f"[{user_label}] {self.mode_display_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

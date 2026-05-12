"""
修复记录模块 - 数据模型
基于 Django ORM，兼容 SQLite 和 MySQL
"""
from django.db import models


class PlatformConfig(models.Model):
    """
    AI平台配置模型
    存储百度云、腾讯云、Replicate等平台的API密钥配置
    """
    
    # 平台类型
    PLATFORM_CHOICES = [
        ('baidu', '百度AI'),
        ('tencent', '腾讯云'),
        ('replicate', 'Replicate'),
    ]
    
    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES, unique=True, verbose_name='平台')
    
    # API Key / App Key
    api_key = models.CharField(max_length=255, blank=True, default='', verbose_name='API Key')
    
    # API Secret / Secret Key
    api_secret = models.CharField(max_length=255, blank=True, default='', verbose_name='API Secret')
    
    # 其他配置（JSON格式存储）
    extra_config = models.TextField(blank=True, default='{}', verbose_name='额外配置', help_text='JSON格式的额外配置')
    
    # 是否启用
    is_enabled = models.BooleanField(default=True, verbose_name='是否启用')
    
    # 备注
    remark = models.CharField(max_length=255, blank=True, default='', verbose_name='备注')
    
    # 创建和更新时间
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'platform_config'
        verbose_name = '平台配置'
        verbose_name_plural = '平台配置列表'
    
    def to_dict(self):
        """转换为字典"""
        import json
        return {
            'id': str(self.id),
            'platform': self.platform,
            'platform_name': self.get_platform_display(),
            'api_key': self.api_key,
            'api_secret': self.api_secret,
            'extra_config': json.loads(self.extra_config) if self.extra_config else {},
            'is_enabled': self.is_enabled,
            'remark': self.remark,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
    
    def __str__(self):
        return f"{self.get_platform_display()}配置"


class SystemSettings(models.Model):
    """
    系统设置模型
    存储系统级别的配置项
    """
    
    # 设置键（唯一）
    key = models.CharField(max_length=100, unique=True, verbose_name='设置键')
    
    # 设置值（JSON格式存储，支持各种类型）
    value = models.TextField(verbose_name='设置值', help_text='JSON格式存储')
    
    # 描述
    description = models.CharField(max_length=255, blank=True, default='', verbose_name='描述')
    
    # 更新时间
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'system_settings'
        verbose_name = '系统设置'
        verbose_name_plural = '系统设置列表'
    
    @staticmethod
    def get_setting(key, default=None):
        """获取设置值"""
        try:
            import json
            setting = SystemSettings.objects.get(key=key)
            return json.loads(setting.value)
        except SystemSettings.DoesNotExist:
            return default
        except Exception:
            return default
    
    @staticmethod
    def set_setting(key, value, description=''):
        """设置值"""
        import json
        setting, created = SystemSettings.objects.get_or_create(
            key=key,
            defaults={'value': json.dumps(value), 'description': description}
        )
        if not created:
            setting.value = json.dumps(value)
            setting.description = description
            setting.save()
        return setting
    
    def __str__(self):
        return f"{self.key} = {self.value[:50]}..."


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

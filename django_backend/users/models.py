"""
用户模块 - 数据模型
基于 Django ORM，兼容 SQLite 和 MySQL
"""
from django.db import models
from django.utils.timezone import now as django_now


class User(models.Model):
    """
    微信用户模型
    - id: 使用微信 openid 作为主键
    - free_remaining: 新用户默认 3 次免费修复机会
    - is_member: 是否会员
    - status: 账号状态
    """
    id = models.CharField(max_length=64, primary_key=True, verbose_name='用户ID', help_text='微信openid')
    union_id = models.CharField(max_length=64, blank=True, default='', verbose_name='UnionID')
    nickname = models.CharField(max_length=100, blank=True, default='', verbose_name='昵称')
    avatar = models.URLField(blank=True, default='', verbose_name='头像URL')
    
    # 免费次数控制
    free_remaining = models.IntegerField(default=3, verbose_name='剩余免费次数')
    
    # 会员相关
    is_member = models.BooleanField(default=False, verbose_name='是否会员')
    member_expire = models.DateTimeField(null=True, blank=True, verbose_name='会员过期时间')
    
    # 统计数据
    total_repairs = models.IntegerField(default=0, verbose_name='总修复次数')
    
    # 状态控制
    STATUS_CHOICES = [
        ('active', '正常'),
        ('banned', '已禁用'),
    ]
    status = models.CharField(max_length=20, default='active', choices=STATUS_CHOICES, verbose_name='状态')
    
    # 管理员标识
    is_admin = models.BooleanField(default=False, verbose_name='是否管理员')
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    last_login = models.DateTimeField(auto_now=True, verbose_name='最后登录')
    
    # 额外信息
    session_key = models.CharField(max_length=64, blank=True, default='', verbose_name='SessionKey')
    raw_data = models.TextField(blank=True, default='', verbose_name='原始用户信息(JSON)')

    class Meta:
        db_table = 'users'  # 指定表名，避免冲突
        ordering = ['-created_at']
        verbose_name = '用户'
        verbose_name_plural = '用户列表'

    @property
    def remaining_display(self):
        """
        返回用户剩余次数的友好显示文本
        """
        if self.is_member and self.member_expire and self.member_expire > django_now():
            return "会员无限"
        return f"免费剩余{self.free_remaining}次"

    def has_quota(self):
        """
        检查用户是否还有可用的修复次数
        会员永不过期时有无限次数，普通用户检查免费次数
        """
        if self.status == 'banned':
            return False
        if self.is_member and self.member_expire and self.member_expire > django_now():
            return True
        return self.free_remaining > 0

    def consume_quota(self):
        """
        消耗一次修复配额
        会员不消耗免费次数，普通用户消耗 free_remaining
        :return: 是否成功
        """
        if not self.has_quota():
            return False
        
        # 会员不扣减免费次数
        if self.is_member and self.member_expire and self.member_expire > django_now():
            return True
        
        # 普通用户扣减免费次数
        if self.free_remaining > 0:
            self.free_remaining -= 1
            self.save(update_fields=['free_remaining'])
            return True
        
        return False

    def restore_quota(self, count=1):
        """
        恢复用户免费次数（例如删除记录时恢复）
        """
        self.free_remaining += count
        self.save(update_fields=['free_remaining'])

    def to_dict(self):
        """
        将用户信息转换为字典（用于 API 返回）
        """
        return {
            'id': self.id,
            'union_id': self.union_id,
            'nickname': self.nickname,
            'avatar': self.avatar,
            'free_remaining': self.free_remaining,
            'is_member': self.is_member,
            'member_expire': self.member_expire.isoformat() if self.member_expire else None,
            'total_repairs': self.total_repairs,
            'status': self.status,
            'is_admin': self.is_admin,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S'),
            'remaining_display': self.remaining_display,
        }

    def __str__(self):
        return f"{self.nickname or self.id[:16]}"

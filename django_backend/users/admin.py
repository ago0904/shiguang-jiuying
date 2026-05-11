"""用户模块admin配置"""
from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'nickname', 'free_remaining', 'is_member',
        'total_repairs', 'status', 'created_at', 'last_login'
    ]
    list_filter = ['status', 'is_member', 'created_at']
    search_fields = ['id', 'nickname', 'union_id']
    ordering = ['-created_at']
    readonly_fields = ['id', 'created_at', 'last_login']

"""
Web前端路由
"""
from django.urls import path
from . import views

app_name = 'webapp'

urlpatterns = [
    path('', views.index, name='index'),
    path('config', views.webapp_config, name='config'),
]

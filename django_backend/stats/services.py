"""数据统计服务 - 自动记录和聚合"""
import logging
from datetime import datetime, date, timedelta
from django.db.models import Sum, Avg, Count
from .models import DailyStats, HourlyStats

logger = logging.getLogger(__name__)


def track_repair(user_id, mode, platform, cost_time, is_success):
    """记录一次修复操作
    
    每次修复请求完成后调用，自动更新每日和小时统计数据。
    
    Args:
        user_id: 用户ID
        mode: 修复模式 (colorize/repair/enhance/denoise)
        platform: 使用的AI平台 (百度AI/腾讯云/Replicate)
        cost_time: 耗时（秒）
        is_success: 是否成功
    """
    today = date.today()
    now = datetime.now()
    
    try:
        # 更新每日统计
        daily, created = DailyStats.objects.get_or_create(
            date=today,
            defaults={
                'total_repairs': 0,
                'unique_users': 0,
                'new_users': 0,
                'avg_cost_time': 0.0,
                'total_cost_time': 0.0,
                'errors': 0,
                'mode_colorize': 0,
                'mode_repair': 0,
                'mode_enhance': 0,
                'mode_denoise': 0,
                'platform_baidu': 0,
                'platform_tencent': 0,
                'platform_replicate': 0,
            }
        )
        
        daily.total_repairs += 1
        daily.total_cost_time += cost_time
        if daily.total_repairs > 0:
            daily.avg_cost_time = daily.total_cost_time / daily.total_repairs
        
        # 模式统计
        if mode == 'colorize':
            daily.mode_colorize += 1
        elif mode == 'repair':
            daily.mode_repair += 1
        elif mode == 'enhance':
            daily.mode_enhance += 1
        elif mode == 'denoise':
            daily.mode_denoise += 1
        
        # 平台统计
        if platform == '百度AI':
            daily.platform_baidu += 1
        elif platform == '腾讯云':
            daily.platform_tencent += 1
        elif platform == 'Replicate':
            daily.platform_replicate += 1
        
        # 错误统计
        if not is_success:
            daily.errors += 1
        
        daily.save()
        
        # 更新小时统计
        hourly, _ = HourlyStats.objects.get_or_create(
            date=today,
            hour=now.hour,
            defaults={'repairs': 0}
        )
        hourly.repairs += 1
        hourly.save()
        
        logger.debug(f"修复操作已记录: user={user_id[:16]}, mode={mode}, platform={platform}")
        
    except Exception as e:
        logger.error(f"记录修复操作失败: {e}")


def get_dashboard_data():
    """获取看板数据
    
    返回管理后台看板所需的统计数据，包括今日概况、7天趋势、小时分布等。
    
    Returns:
        dict: 看板数据字典
    """
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    # 今日数据
    try:
        today_stats = DailyStats.objects.get(date=today)
    except DailyStats.DoesNotExist:
        today_stats = None
    
    # 7天趋势
    trend = DailyStats.objects.filter(
        date__gte=week_ago, 
        date__lte=today
    ).order_by('date')
    
    # 小时分布
    hourly = HourlyStats.objects.filter(date=today).order_by('hour')
    
    return {
        'today': {
            'total_repairs': today_stats.total_repairs if today_stats else 0,
            'unique_users': today_stats.unique_users if today_stats else 0,
            'new_users': today_stats.new_users if today_stats else 0,
        },
        'trend_7d': [
            {
                'date': d.date.strftime('%m-%d'),
                'repairs': d.total_repairs,
                'users': d.unique_users
            } 
            for d in trend
        ],
        'hourly': [
            {
                'hour': f"{h.hour:02d}:00",
                'repairs': h.repairs
            } 
            for h in hourly
        ],
        'mode_distribution': {
            'colorize': today_stats.mode_colorize if today_stats else 0,
            'repair': today_stats.mode_repair if today_stats else 0,
            'enhance': today_stats.mode_enhance if today_stats else 0,
            'denoise': today_stats.mode_denoise if today_stats else 0,
        },
        'platform_distribution': {
            '百度AI': today_stats.platform_baidu if today_stats else 0,
            '腾讯云': today_stats.platform_tencent if today_stats else 0,
            'Replicate': today_stats.platform_replicate if today_stats else 0,
        }
    }


def get_trend_data(days=7):
    """获取趋势数据
    
    Args:
        days: 查询天数
        
    Returns:
        list: 每日统计数据列表
    """
    start_date = date.today() - timedelta(days=days)
    stats = DailyStats.objects.filter(date__gte=start_date).order_by('date')
    return [
        {
            'date': s.date.strftime('%Y-%m-%d'),
            'total_repairs': s.total_repairs,
            'unique_users': s.unique_users,
            'new_users': s.new_users,
            'avg_cost_time': round(s.avg_cost_time, 2),
            'errors': s.errors,
        }
        for s in stats
    ]


def get_mode_distribution(start_date=None, end_date=None):
    """获取修复模式分布
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        dict: 各模式使用次数
    """
    queryset = DailyStats.objects.all()
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    if end_date:
        queryset = queryset.filter(date__lte=end_date)
    
    result = queryset.aggregate(
        colorize=Sum('mode_colorize'),
        repair=Sum('mode_repair'),
        enhance=Sum('mode_enhance'),
        denoise=Sum('mode_denoise'),
    )
    
    return {
        'colorize': result.get('colorize') or 0,
        'repair': result.get('repair') or 0,
        'enhance': result.get('enhance') or 0,
        'denoise': result.get('denoise') or 0,
    }


def get_platform_distribution(start_date=None, end_date=None):
    """获取平台使用分布
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        dict: 各平台使用次数
    """
    queryset = DailyStats.objects.all()
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    if end_date:
        queryset = queryset.filter(date__lte=end_date)
    
    result = queryset.aggregate(
        baidu=Sum('platform_baidu'),
        tencent=Sum('platform_tencent'),
        replicate=Sum('platform_replicate'),
    )
    
    return {
        '百度AI': result.get('baidu') or 0,
        '腾讯云': result.get('tencent') or 0,
        'Replicate': result.get('replicate') or 0,
    }

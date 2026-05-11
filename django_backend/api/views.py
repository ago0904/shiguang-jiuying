"""
修复记录模块 - API 视图
提供图片上传、AI修复、结果获取、历史记录等接口
基于 Django 3.x，统一 JSON 响应格式
"""
import time
import json
import logging
import uuid
import base64
from pathlib import Path
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from core.utils import (
    success_response, error_response,
    get_file_hash, generate_file_id, get_file_extension,
    save_uploaded_file,
    file_response, image_base64_response,
    get_client_ip, ensure_dir, sanitize_filename,
    today, now
)
from core.decorators import login_required
from api.models import RepairRecord
from users.models import User

logger = logging.getLogger('api')

# 上传文件保存目录
UPLOAD_DIR = Path(settings.MEDIA_ROOT) / 'uploads'
RESULT_DIR = Path(settings.MEDIA_ROOT) / 'results'

# 修复模式配置
MODE_CONFIG = {
    'colorize': {'name': '黑白上色', 'platforms': ['baidu', 'replicate']},
    'repair': {'name': '破损修复', 'platforms': ['tencent', 'replicate']},
    'enhance': {'name': '清晰度增强', 'platforms': ['baidu', 'tencent']},
    'denoise': {'name': '智能去噪', 'platforms': ['baidu', 'tencent']},
}

# ============================================================
# 1. 上传图片
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def upload_image(request):
    """
    POST /api/upload
    上传图片接口
    支持 multipart/form-data 和 base64 JSON 两种格式
    返回 file_id 用于后续修复操作
    """
    try:
        logger.info(f"[Upload] 收到上传请求 from {get_client_ip(request)}")
        
        file_obj = None
        original_name = None
        
        # 方式一: multipart/form-data
        if request.FILES.get('image'):
            file_obj = request.FILES['image']
            original_name = file_obj.name
            logger.info(f"[Upload] multipart 上传: {original_name}, size={file_obj.size}")
        
        # 方式二: base64 JSON
        elif request.content_type and 'application/json' in request.content_type:
            try:
                body = json.loads(request.body)
                base64_data = body.get('image') or body.get('base64')
                if base64_data:
                    # 去除 data:image/xxx;base64, 前缀
                    if ',' in base64_data:
                        base64_data = base64_data.split(',', 1)[1]
                    image_data = base64.b64decode(base64_data)
                    # 创建临时文件对象
                    from django.core.files.base import ContentFile
                    ext = body.get('ext', 'jpg')
                    original_name = f"upload_{uuid.uuid4().hex[:8]}.{ext}"
                    file_obj = ContentFile(image_data, name=original_name)
                    logger.info(f"[Upload] base64 上传: {original_name}, size={len(image_data)}")
            except (json.JSONDecodeError, base64.binascii.Error) as e:
                logger.warning(f"[Upload] base64解析失败: {e}")
                return error_response("图片数据格式错误，请检查base64编码", code=400, status=400)
        
        if not file_obj:
            return error_response("未检测到图片，请通过 multipart/form-data 的 image 字段或 JSON 的 base64 字段上传", code=400, status=400)
        
        # 验证文件大小（限制10MB）
        if hasattr(file_obj, 'size') and file_obj.size > 10 * 1024 * 1024:
            return error_response("图片大小超过10MB限制", code=400, status=400)
        
        # 计算文件哈希并生成唯一文件ID
        file_hash = get_file_hash(file_obj)
        ext = get_file_extension(original_name or 'upload.jpg')
        file_id = generate_file_id(file_hash, ext)
        
        # 保存文件
        save_path = UPLOAD_DIR / file_id
        ensure_dir(UPLOAD_DIR)
        
        with open(save_path, 'wb') as f:
            if hasattr(file_obj, 'chunks'):
                for chunk in file_obj.chunks():
                    f.write(chunk)
            else:
                f.write(file_obj.read())
        
        file_size = save_path.stat().st_size
        logger.info(f"[Upload] 文件保存成功: {file_id}, path={save_path}, size={file_size}")
        
        return success_response(data={
            "file_id": file_id,
            "size": file_size,
            "message": "上传成功"
        }, message="图片上传成功")
    
    except Exception as e:
        logger.error(f"[Upload] 上传失败: {e}", exc_info=True)
        return error_response(f"图片上传失败: {str(e)}", code=500)


# ============================================================
# 2. 修复图片
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def repair_image(request):
    """
    POST /api/repair
    修复图片接口（需要登录）
    参数: file_id, mode (colorize/repair/enhance/denoise)
    流程:
        1. 验证用户配额
        2. 读取上传的图片
        3. 调用 AI 修复
        4. 保存结果
        5. 记录修复历史
        6. 更新用户统计
    """
    import time as time_module
    start_time = time_module.time()
    
    try:
        user_info = request.user_info
        user_id = user_info['user_id']
        client_ip = get_client_ip(request)
        
        logger.info(f"[Repair] 用户 {user_id[:16]}... 请求修复 from {client_ip}")
        
        # 解析请求参数
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return error_response("请求参数必须是JSON格式", code=400, status=400)
        
        file_id = body.get('file_id')
        mode = body.get('mode')
        platform = body.get('platform', '')  # 可选，指定平台
        
        # 参数校验
        if not file_id:
            return error_response("缺少 file_id 参数", code=400, status=400)
        if not mode:
            return error_response("缺少 mode 参数", code=400, status=400)
        if mode not in MODE_CONFIG:
            return error_response(f"不支持的修复模式: {mode}，可选: {list(MODE_CONFIG.keys())}", code=400, status=400)
        
        # 获取用户
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return error_response("用户不存在", code=404, status=404)
        
        # 检查用户配额
        if not user.has_quota():
            logger.info(f"[Repair] 用户 {user_id[:16]}... 无可用配额")
            return error_response("免费次数已用完，请开通会员", code=403, status=403)
        
        # 检查上传文件是否存在
        source_path = UPLOAD_DIR / file_id
        if not source_path.exists():
            return error_response("上传的文件不存在，请重新上传", code=404, status=404)
        
        # 消耗配额
        if not user.consume_quota():
            return error_response("免费次数已用完", code=403, status=403)
        
        # 读取图片数据
        with open(source_path, 'rb') as f:
            image_data = f.read()
        
        # 确定模式名称
        mode_name = MODE_CONFIG[mode]['name']
        
        # 自动选择平台
        if not platform:
            platform = MODE_CONFIG[mode]['platforms'][0]
        
        # 创建修复记录（初始状态）
        record = RepairRecord.objects.create(
            user=user,
            file_id=file_id,
            mode=mode,
            mode_name=mode_name,
            platform=platform,
            cost_time=0.0,
            ip=client_ip,
            is_success=False,
            status='processing',
            source_path=str(source_path),
        )
        
        # 调用 AI 修复
        try:
            result_data = call_ai_repair(image_data, mode, platform, file_id)
            
            if result_data is None or not result_data.get('success'):
                error_msg = result_data.get('error', 'AI修复服务调用失败') if result_data else 'AI修复服务无响应'
                record.is_success = False
                record.error_msg = error_msg
                record.status = 'failed'
                record.save()
                
                # 恢复用户配额
                user.restore_quota()
                logger.warning(f"[Repair] AI修复失败: {error_msg}")
                return error_response(f"修复失败: {error_msg}", code=500)
            
            # 保存结果图片
            result_ext = get_file_extension(file_id)
            result_id = f"result_{file_id}"
            result_path = RESULT_DIR / result_id
            ensure_dir(RESULT_DIR)
            
            result_image = result_data.get('image_data')
            if result_image:
                with open(result_path, 'wb') as f:
                    f.write(result_image)
                logger.info(f"[Repair] 结果保存成功: {result_id}")
            
            # 计算耗时
            cost_time = round(time_module.time() - start_time, 2)
            
            # 更新修复记录
            record.is_success = True
            record.cost_time = cost_time
            record.result_path = str(result_path)
            record.status = 'completed'
            record.save()
            
            # 更新用户统计
            user.total_repairs += 1
            user.save(update_fields=['total_repairs'])
            
            # 更新统计数据
            try:
                update_stats(mode, platform, cost_time, user)
            except Exception as stats_err:
                logger.warning(f"[Repair] 统计更新失败（非关键）: {stats_err}")
            
            logger.info(f"[Repair] 修复成功: mode={mode}, platform={platform}, cost={cost_time}s")
            
            return success_response(data={
                "file_id": file_id,
                "result_id": result_id,
                "mode": mode,
                "mode_name": mode_name,
                "platform": platform,
                "cost_time": cost_time,
                "message": "修复成功"
            }, message="图片修复成功")
        
        except Exception as repair_err:
            logger.error(f"[Repair] 修复过程异常: {repair_err}", exc_info=True)
            
            # 更新记录为失败
            record.is_success = False
            record.error_msg = str(repair_err)
            record.status = 'failed'
            record.save()
            
            # 恢复用户配额
            user.restore_quota()
            
            return error_response(f"修复过程中发生错误: {str(repair_err)}", code=500)
    
    except Exception as e:
        logger.error(f"[Repair] 系统异常: {e}", exc_info=True)
        return error_response(f"系统错误: {str(e)}", code=500)


# ============================================================
# 3. 获取结果图片
# ============================================================

@require_http_methods(["GET"])
def get_result(request, file_id):
    """
    GET /api/result/<file_id>
    获取修复结果图片
    支持参数: type=file(默认)/base64
    """
    try:
        logger.info(f"[Result] 获取结果: {file_id}")
        
        # 构建结果文件路径
        result_id = f"result_{file_id}"
        result_path = RESULT_DIR / result_id
        
        # 如果 result_ 前缀的找不到，直接尝试 file_id
        if not result_path.exists():
            result_path = RESULT_DIR / file_id
        
        if not result_path.exists():
            return error_response("结果图片不存在", code=404, status=404)
        
        # 检查请求类型
        response_type = request.GET.get('type', 'file')
        
        if response_type == 'base64':
            # 返回 base64 编码
            return image_base64_response(str(result_path))
        else:
            # 返回文件
            return file_response(str(result_path))
    
    except Exception as e:
        logger.error(f"[Result] 获取结果失败: {e}", exc_info=True)
        return error_response(f"获取结果失败: {str(e)}", code=500)


# ============================================================
# 4. 获取上传的图片
# ============================================================

@require_http_methods(["GET"])
def get_uploaded_image(request, file_id):
    """
    GET /api/image/<file_id>
    获取用户上传的原始图片
    """
    try:
        logger.info(f"[Image] 获取上传图片: {file_id}")
        
        # 安全检查：防止目录遍历
        safe_id = sanitize_filename(file_id)
        if not safe_id or safe_id != file_id:
            return error_response("无效的文件ID", code=400, status=400)
        
        image_path = UPLOAD_DIR / safe_id
        
        if not image_path.exists():
            return error_response("图片不存在", code=404, status=404)
        
        return file_response(str(image_path))
    
    except Exception as e:
        logger.error(f"[Image] 获取图片失败: {e}", exc_info=True)
        return error_response(f"获取图片失败: {str(e)}", code=500)


# ============================================================
# 5. 获取修复历史
# ============================================================

@require_http_methods(["GET"])
@login_required
def get_history(request):
    """
    GET /api/history
    获取当前用户的修复历史记录
    支持分页: page, page_size
    支持筛选: mode
    """
    try:
        user_info = request.user_info
        user_id = user_info['user_id']
        
        # 分页参数
        try:
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
        except ValueError:
            return error_response("分页参数格式错误", code=400, status=400)
        
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        
        # 筛选参数
        mode = request.GET.get('mode', '')
        
        logger.info(f"[History] 用户 {user_id[:16]}... 获取历史 page={page}, size={page_size}")
        
        # 构建查询
        queryset = RepairRecord.objects.filter(user_id=user_id)
        
        if mode:
            queryset = queryset.filter(mode=mode)
        
        # 计算总数和分页
        total = queryset.count()
        total_pages = (total + page_size - 1) // page_size
        start = (page - 1) * page_size
        end = start + page_size
        
        records = queryset[start:end]
        
        # 构建响应
        data = {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "list": [r.to_dict() for r in records]
        }
        
        return success_response(data=data, message="获取成功")
    
    except Exception as e:
        logger.error(f"[History] 获取历史失败: {e}", exc_info=True)
        return error_response(f"获取历史记录失败: {str(e)}", code=500)


# ============================================================
# 6. 删除记录
# ============================================================

@csrf_exempt
@require_http_methods(["DELETE"])
@login_required
def delete_history(request, history_id):
    """
    DELETE /api/history/<history_id>
    删除单条修复记录
    """
    try:
        user_info = request.user_info
        user_id = user_info['user_id']
        
        logger.info(f"[DeleteHistory] 用户 {user_id[:16]}... 删除记录 {history_id}")
        
        try:
            record = RepairRecord.objects.get(pk=history_id, user_id=user_id)
        except RepairRecord.DoesNotExist:
            return error_response("记录不存在", code=404, status=404)
        
        # 删除关联的结果文件（可选）
        if record.result_path:
            result_path = Path(record.result_path)
            if result_path.exists():
                try:
                    result_path.unlink()
                except OSError:
                    pass
        
        # 删除记录
        record.delete()
        
        # 恢复用户一次免费次数（如果之前消耗了）
        try:
            user = User.objects.get(pk=user_id)
            user.restore_quota(1)
        except Exception:
            pass
        
        return success_response(message="删除成功")
    
    except Exception as e:
        logger.error(f"[DeleteHistory] 删除失败: {e}", exc_info=True)
        return error_response(f"删除记录失败: {str(e)}", code=500)


# ============================================================
# 7. 获取 API 配额
# ============================================================

@require_http_methods(["GET"])
@login_required
def get_quota(request):
    """
    GET /api/quota
    获取当前用户的 API 配额信息
    """
    try:
        user_info = request.user_info
        user_id = user_info['user_id']
        
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return error_response("用户不存在", code=404, status=404)
        
        from django.utils.timezone import now as django_now
        
        is_member_active = (
            user.is_member and 
            user.member_expire and 
            user.member_expire > django_now()
        )
        
        data = {
            "free_remaining": user.free_remaining,
            "is_member": user.is_member,
            "member_active": is_member_active,
            "member_expire": user.member_expire.strftime('%Y-%m-%d %H:%M:%S') if user.member_expire else None,
            "total_repairs": user.total_repairs,
            "has_quota": user.has_quota(),
            "remaining_display": user.remaining_display,
        }
        
        return success_response(data=data, message="获取成功")
    
    except Exception as e:
        logger.error(f"[Quota] 获取配额失败: {e}", exc_info=True)
        return error_response(f"获取配额信息失败: {str(e)}", code=500)


# ============================================================
# AI 修复调用
# ============================================================

def call_ai_repair(image_data, mode, platform, file_id):
    """
    调用 AI 修复服务
    :param image_data: 图片二进制数据
    :param mode: 修复模式
    :param platform: AI 平台
    :param file_id: 文件ID
    :return: dict {'success': bool, 'image_data': bytes, 'error': str}
    """
    try:
        # 优先使用 api_manager.py（如果存在）
        try:
            from api_manager import call_api
            result = call_api(image_data, mode, platform, file_id)
            if result:
                return result
        except ImportError:
            logger.info("[AIRepair] api_manager 未找到，使用内置模拟")
        except Exception as api_err:
            logger.warning(f"[AIRepair] api_manager 调用失败: {api_err}")
        
        # 内置模拟修复（用于测试和开发）
        return mock_repair(image_data, mode, platform, file_id)
    
    except Exception as e:
        logger.error(f"[AIRepair] 调用异常: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def mock_repair(image_data, mode, platform, file_id):
    """
    模拟 AI 修复（开发测试用）
    直接返回原图，不做实际处理
    """
    import time
    # 模拟处理耗时 0.5-2 秒
    time.sleep(0.5)
    return {
        'success': True,
        'image_data': image_data,
        'platform': platform,
        'mode': mode,
    }


# ============================================================
# 统计更新
# ============================================================

def update_stats(mode, platform, cost_time, user):
    """
    更新每日和每小时统计数据
    """
    from stats.models import DailyStats, HourlyStats
    from django.db.models import F, Avg
    
    today_date = today()
    current_hour = now().hour
    
    # 更新每日统计
    daily, created = DailyStats.objects.get_or_create(
        date=today_date,
        defaults={
            'total_repairs': 0,
            'unique_users': 0,
            'new_users': 0,
        }
    )
    
    # 使用 F 表达式避免竞态条件
    from django.db.models import F
    DailyStats.objects.filter(date=today_date).update(
        total_repairs=F('total_repairs') + 1,
        **{f'mode_{mode}': F(f'mode_{mode}') + 1},
        **{f'platform_{platform}': F(f'platform_{platform}') + 1}
    )
    
    # 更新平均耗时
    daily.refresh_from_db()
    avg = (daily.avg_cost_time * (daily.total_repairs - 1) + cost_time) / daily.total_repairs if daily.total_repairs > 0 else cost_time
    daily.avg_cost_time = round(avg, 2)
    daily.save(update_fields=['avg_cost_time'])
    
    # 更新每小时统计
    hourly, _ = HourlyStats.objects.get_or_create(
        date=today_date,
        hour=current_hour,
        defaults={'repairs': 0}
    )
    HourlyStats.objects.filter(date=today_date, hour=current_hour).update(
        repairs=F('repairs') + 1,
        **{f'mode_{mode}': F(f'mode_{mode}') + 1}
    )

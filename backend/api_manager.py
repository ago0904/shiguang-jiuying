"""
AI照片修复 API 管理器
支持多平台轮询、免费额度管理、自动降级
"""
import os
import json
import time
import hashlib
import base64
import requests
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Callable
from abc import ABC, abstractmethod
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RepairMode(Enum):
    """修复模式"""
    COLORIZE = "colorize"       # 黑白上色
    REPAIR = "repair"           # 破损修复
    ENHANCE = "enhance"         # 清晰度增强
    DENOISE = "denoise"         # 智能去噪


@dataclass
class APIQuota:
    """API配额追踪"""
    platform: str               # 平台名称
    mode: RepairMode            # 修复模式
    free_limit: int             # 免费额度
    used_count: int = 0         # 已使用次数
    reset_date: str = ""        # 重置日期（每月1号）
    
    @property
    def remaining(self) -> int:
        """剩余额度"""
        return max(0, self.free_limit - self.used_count)
    
    @property
    def is_exhausted(self) -> bool:
        """是否已用完"""
        return self.remaining <= 0
    
    def use_one(self):
        """使用一次额度"""
        self.used_count += 1


@dataclass
class RepairResult:
    """修复结果"""
    success: bool
    image_data: Optional[bytes] = None  # 修复后的图片数据
    image_url: Optional[str] = None      # 修复后的图片URL
    platform: str = ""                   # 使用的平台
    mode: str = ""                       # 修复模式
    message: str = ""                    # 提示信息
    cost_time: float = 0.0               # 耗时(秒)


class BaseAPIPlatform(ABC):
    """API平台抽象基类"""
    
    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)
        self.quotas: Dict[RepairMode, APIQuota] = {}
        
    @abstractmethod
    def _setup_quotas(self):
        """设置各模式配额"""
        pass
    
    @abstractmethod
    def colorize(self, image_b64: str) -> RepairResult:
        """黑白上色"""
        pass
    
    @abstractmethod
    def repair(self, image_b64: str) -> RepairResult:
        """破损修复"""
        pass
    
    @abstractmethod
    def enhance(self, image_b64: str) -> RepairResult:
        """清晰度增强"""
        pass
    
    @abstractmethod
    def denoise(self, image_b64: str) -> RepairResult:
        """智能去噪"""
        pass
    
    def can_handle(self, mode: RepairMode) -> bool:
        """检查是否还能处理该模式"""
        if not self.enabled:
            return False
        quota = self.quotas.get(mode)
        if not quota:
            return False
        return not quota.is_exhausted


class BaiduAPI(BaseAPIPlatform):
    """
    百度AI开放平台
    免费额度（每月）：
    - 图像修复（破损）: 1500次
    - 黑白图像上色: 1000次
    - 图像清晰度增强: 3000次
    - 去噪: 含在清晰度增强中
    """
    
    API_BASE = "https://aip.baidubce.com"
    
    def __init__(self, config: Dict):
        super().__init__("百度AI", config)
        self.app_key = config.get('app_key', '')
        self.app_secret = config.get('app_secret', '')
        self._access_token = None
        self._token_expire = 0
        self._setup_quotas()
    
    def _setup_quotas(self):
        """设置百度AI各模式配额"""
        today = datetime.now()
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        reset_date = next_month.strftime("%Y-%m-%d")
        
        self.quotas = {
            RepairMode.COLORIZE: APIQuota(
                platform="百度AI", mode=RepairMode.COLORIZE,
                free_limit=1000, reset_date=reset_date
            ),
            RepairMode.REPAIR: APIQuota(
                platform="百度AI", mode=RepairMode.REPAIR,
                free_limit=1500, reset_date=reset_date
            ),
            RepairMode.ENHANCE: APIQuota(
                platform="百度AI", mode=RepairMode.ENHANCE,
                free_limit=3000, reset_date=reset_date
            ),
            RepairMode.DENOISE: APIQuota(
                platform="百度AI", mode=RepairMode.DENOISE,
                free_limit=3000, reset_date=reset_date  # 去噪走增强接口
            ),
        }
    
    def _get_access_token(self) -> str:
        """获取百度API访问令牌"""
        if self._access_token and time.time() < self._token_expire:
            return self._access_token
        
        url = f"{self.API_BASE}/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.app_key,
            "client_secret": self.app_secret
        }
        try:
            resp = requests.post(url, params=params, timeout=10)
            data = resp.json()
            self._access_token = data.get('access_token', '')
            expires_in = data.get('expires_in', 2592000)
            self._token_expire = time.time() + expires_in - 3600  # 提前1小时刷新
            logger.info("百度AI Token获取成功")
            return self._access_token
        except Exception as e:
            logger.error(f"百度AI Token获取失败: {e}")
            return ""
    
    def _call_api(self, endpoint: str, image_b64: str, params: Dict = None) -> Dict:
        """调用百度API"""
        token = self._get_access_token()
        if not token:
            return {"error": "获取Token失败"}
        
        url = f"{self.API_BASE}/rest/2.0/image-process/v1/{endpoint}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"image": image_b64, "access_token": token}
        if params:
            data.update(params)
        
        try:
            resp = requests.post(url, headers=headers, data=data, timeout=30)
            return resp.json()
        except Exception as e:
            logger.error(f"百度API调用失败: {e}")
            return {"error": str(e)}
    
    def _process_result(self, api_resp: Dict, mode: RepairMode, start_time: float) -> RepairResult:
        """处理API返回结果"""
        cost = time.time() - start_time
        
        if "error" in api_resp:
            return RepairResult(
                success=False, mode=mode.value,
                message=f"百度AI错误: {api_resp.get('error', '未知错误')}",
                cost_time=cost
            )
        
        if "image" in api_resp:
            img_data = base64.b64decode(api_resp["image"])
            self.quotas[mode].use_one()
            return RepairResult(
                success=True, image_data=img_data,
                platform="百度AI", mode=mode.value,
                message="修复成功", cost_time=cost
            )
        
        return RepairResult(
            success=False, mode=mode.value,
            message=f"返回数据异常: {json.dumps(api_resp)[:200]}",
            cost_time=cost
        )

    def colorize(self, image_b64: str) -> RepairResult:
        """黑白上色"""
        start = time.time()
        resp = self._call_api("colourize", image_b64)
        return self._process_result(resp, RepairMode.COLORIZE, start)

    def repair(self, image_b64: str) -> RepairResult:
        """破损修复"""
        start = time.time()
        resp = self._call_api("inpaint", image_b64)
        return self._process_result(resp, RepairMode.REPAIR, start)

    def enhance(self, image_b64: str) -> RepairResult:
        """清晰度增强"""
        start = time.time()
        resp = self._call_api("image_definition_enhance", image_b64)
        return self._process_result(resp, RepairMode.ENHANCE, start)

    def denoise(self, image_b64: str) -> RepairResult:
        """智能去噪 - 百度用风格转换接口"""
        start = time.time()
        # 百度去噪使用image_quality_enhance接口
        resp = self._call_api("image_quality_enhance", image_b64)
        return self._process_result(resp, RepairMode.DENOISE, start)


class TencentAPI(BaseAPIPlatform):
    """
    腾讯云AI
    免费额度（每月）：
    - 图像清晰度增强: 1000次
    - 其他功能需付费
    """
    
    API_BASE = "https://iai.tencentcloudapi.com"
    
    def __init__(self, config: Dict):
        super().__init__("腾讯云", config)
        self.secret_id = config.get('secret_id', '')
        self.secret_key = config.get('secret_key', '')
        self._setup_quotas()
    
    def _setup_quotas(self):
        today = datetime.now()
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        reset_date = next_month.strftime("%Y-%m-%d")
        
        self.quotas = {
            RepairMode.ENHANCE: APIQuota(
                platform="腾讯云", mode=RepairMode.ENHANCE,
                free_limit=1000, reset_date=reset_date
            ),
        }
    
    def _sign_request(self, action: str, params: Dict) -> Dict:
        """腾讯云API签名"""
        from tencentcloud.common import credential
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.iai.v20200303 import iai_client, models
        
        try:
            cred = credential.Credential(self.secret_id, self.secret_key)
            http_profile = HttpProfile(endpoint="iai.tencentcloudapi.com")
            client_profile = ClientProfile(http_profile=http_profile)
            client = iai_client.IaiClient(cred, "ap-guangzhou", client_profile)
            
            req = models.EnhanceImageRequest()
            req.from_json_string(json.dumps(params))
            resp = client.EnhanceImage(req)
            return json.loads(resp.to_json_string())
        except Exception as e:
            logger.error(f"腾讯云API调用失败: {e}")
            return {"error": str(e)}

    def enhance(self, image_b64: str) -> RepairResult:
        """清晰度增强"""
        start = time.time()
        result = self._sign_request("EnhanceImage", {"Image": image_b64})
        cost = time.time() - start
        
        if "EnhancedImage" in result:
            img_data = base64.b64decode(result["EnhancedImage"])
            self.quotas[RepairMode.ENHANCE].use_one()
            return RepairResult(
                success=True, image_data=img_data,
                platform="腾讯云", mode="enhance",
                message="增强成功", cost_time=cost
            )
        return RepairResult(success=False, message="腾讯云增强失败", cost_time=cost)

    # 腾讯云免费版只支持增强，其他功能需付费
    def colorize(self, image_b64: str) -> RepairResult:
        return RepairResult(success=False, message="腾讯云免费版不支持上色")
    def repair(self, image_b64: str) -> RepairResult:
        return RepairResult(success=False, message="腾讯云免费版不支持修复")
    def denoise(self, image_b64: str) -> RepairResult:
        return RepairResult(success=False, message="腾讯云免费版不支持去噪")


class ReplicateAPI(BaseAPIPlatform):
    """
    Replicate平台 - 开源模型API
    新用户有一定免费额度（约$5）
    """
    
    API_BASE = "https://api.replicate.com/v1"
    
    # 模型映射
    MODELS = {
        RepairMode.COLORIZE: "arielreplicate/deoldify_image:0da600fab0c45a66211339f1c16b71345d22f26ef5fea3dca1bb90bb5711e950",
        RepairMode.REPAIR: "zsxkib/bringing-old-photos-back-to-life:7ef05f9b1d585ec7a88ea0d9e9dbcb7b762d24d6a1de6763e8bed23e185ae62a",
        RepairMode.ENHANCE: "tencentarc/gfpgan:v1.4",
        RepairMode.DENOISE: "tencentarc/gfpgan:v1.4",  # GFPGAN也有去噪效果
    }
    
    def __init__(self, config: Dict):
        super().__init__("Replicate", config)
        self.api_token = config.get('api_token', '')
        self.free_budget = config.get('free_budget', 5.0)  # 免费额度$5
        self.used_budget = 0.0
        self._setup_quotas()
    
    def _setup_quotas(self):
        """Replicate按金额计费，不按次数"""
        today = datetime.now()
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        reset_date = next_month.strftime("%Y-%m-%d")
        
        # 估算每次调用成本约$0.005-0.01
        estimated_calls = int(self.free_budget / 0.01)
        
        for mode in RepairMode:
            self.quotas[mode] = APIQuota(
                platform="Replicate", mode=mode,
                free_limit=estimated_calls, reset_date=reset_date
            )
    
    def _create_prediction(self, model: str, image_url: str) -> Optional[str]:
        """创建预测任务"""
        url = f"{self.API_BASE}/predictions"
        headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json"
        }
        data = {
            "version": model.split(":")[-1] if ":" in model else model,
            "input": {"image": image_url}
        }
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=30)
            result = resp.json()
            return result.get("id")
        except Exception as e:
            logger.error(f"Replicate创建任务失败: {e}")
            return None
    
    def _get_result(self, prediction_id: str) -> Optional[str]:
        """获取预测结果"""
        url = f"{self.API_BASE}/predictions/{prediction_id}"
        headers = {"Authorization": f"Token {self.api_token}"}
        
        for _ in range(60):  # 最多等待2分钟
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                result = resp.json()
                
                if result.get("status") == "succeeded":
                    output = result.get("output", "")
                    if isinstance(output, list):
                        return output[0] if output else None
                    return output
                elif result.get("status") in ["failed", "canceled"]:
                    return None
                
                time.sleep(2)
            except Exception as e:
                logger.error(f"Replicate获取结果失败: {e}")
                return None
        return None

    def _call_with_image(self, image_b64: str, mode: RepairMode) -> RepairResult:
        """通用调用方法"""
        start = time.time()
        
        # 先将图片上传为临时URL（Replicate需要URL）
        # 简化：直接将b64作为data URL
        image_url = f"data:image/jpeg;base64,{image_b64}"
        
        model = self.MODELS.get(mode)
        if not model:
            return RepairResult(success=False, message=f"Replicate不支持{mode.value}")
        
        prediction_id = self._create_prediction(model, image_url)
        if not prediction_id:
            return RepairResult(success=False, message="Replicate任务创建失败")
        
        result_url = self._get_result(prediction_id)
        cost = time.time() - start
        
        if result_url:
            try:
                if result_url.startswith("data:"):
                    # data URL
                    b64_data = result_url.split(",")[1]
                    img_data = base64.b64decode(b64_data)
                else:
                    # HTTP URL
                    resp = requests.get(result_url, timeout=30)
                    img_data = resp.content
                
                self.quotas[mode].use_one()
                self.used_budget += 0.01  # 估算成本
                
                return RepairResult(
                    success=True, image_data=img_data,
                    platform="Replicate", mode=mode.value,
                    message="修复成功", cost_time=cost
                )
            except Exception as e:
                return RepairResult(success=False, message=f"结果解析失败: {e}", cost_time=cost)
        
        return RepairResult(success=False, message="Replicate处理超时", cost_time=cost)

    def colorize(self, image_b64: str) -> RepairResult:
        return self._call_with_image(image_b64, RepairMode.COLORIZE)

    def repair(self, image_b64: str) -> RepairResult:
        return self._call_with_image(image_b64, RepairMode.REPAIR)

    def enhance(self, image_b64: str) -> RepairResult:
        return self._call_with_image(image_b64, RepairMode.ENHANCE)

    def denoise(self, image_b64: str) -> RepairResult:
        return self._call_with_image(image_b64, RepairMode.DENOISE)


class APIRouter:
    """
    API路由器：管理多平台轮询、配额管理、自动降级
    """
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.platforms: List[BaseAPIPlatform] = []
        self._init_platforms()
        
        # 平台优先级（按免费额度从高到低排列）
        self.priority = [
            "百度AI",      # 免费额度最多
            "腾讯云",      # 增强1000次
            "Replicate",   # $5免费额度
        ]
    
    def _load_config(self, path: str) -> Dict:
        """加载配置文件"""
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._default_config()
    
    def _default_config(self) -> Dict:
        """默认配置（从环境变量读取密钥）"""
        return {
            "platforms": {
                "baidu": {
                    "enabled": True,
                    "app_key": os.getenv("BAIDU_APP_KEY", ""),
                    "app_secret": os.getenv("BAIDU_APP_SECRET", "")
                },
                "tencent": {
                    "enabled": True,
                    "secret_id": os.getenv("TENCENT_SECRET_ID", ""),
                    "secret_key": os.getenv("TENCENT_SECRET_KEY", "")
                },
                "replicate": {
                    "enabled": False,  # 默认关闭，需要海外网络
                    "api_token": os.getenv("REPLICATE_API_TOKEN", ""),
                    "free_budget": 5.0
                }
            }
        }
    
    def _init_platforms(self):
        """初始化各平台"""
        platforms_cfg = self.config.get("platforms", {})
        
        # 百度AI
        baidu_cfg = platforms_cfg.get("baidu", {})
        if baidu_cfg.get("enabled") and baidu_cfg.get("app_key"):
            self.platforms.append(BaiduAPI(baidu_cfg))
            logger.info("百度AI平台已初始化")
        
        # 腾讯云
        tencent_cfg = platforms_cfg.get("tencent", {})
        if tencent_cfg.get("enabled") and tencent_cfg.get("secret_id"):
            try:
                self.platforms.append(TencentAPI(tencent_cfg))
                logger.info("腾讯云平台已初始化")
            except ImportError:
                logger.warning("腾讯云SDK未安装，跳过")
        
        # Replicate
        repl_cfg = platforms_cfg.get("replicate", {})
        if repl_cfg.get("enabled") and repl_cfg.get("api_token"):
            self.platforms.append(ReplicateAPI(repl_cfg))
            logger.info("Replicate平台已初始化")
    
    def get_quota_status(self) -> List[Dict]:
        """获取所有平台配额状态"""
        status = []
        for platform in self.platforms:
            for quota in platform.quotas.values():
                status.append({
                    "platform": quota.platform,
                    "mode": quota.mode.value,
                    "free_limit": quota.free_limit,
                    "used": quota.used_count,
                    "remaining": quota.remaining,
                    "reset_date": quota.reset_date,
                    "exhausted": quota.is_exhausted
                })
        return status
    
    def repair(self, image_b64: str, mode: RepairMode) -> RepairResult:
        """
        执行修复：按优先级选择可用平台，自动轮询
        """
        # 按优先级排序平台
        sorted_platforms = sorted(
            self.platforms,
            key=lambda p: self.priority.index(p.name) if p.name in self.priority else 999
        )
        
        errors = []
        for platform in sorted_platforms:
            if not platform.can_handle(mode):
                continue
            
            logger.info(f"尝试使用 {platform.name} 进行 {mode.value} 修复")
            
            # 调用对应方法
            method_map = {
                RepairMode.COLORIZE: platform.colorize,
                RepairMode.REPAIR: platform.repair,
                RepairMode.ENHANCE: platform.enhance,
                RepairMode.DENOISE: platform.denoise,
            }
            
            result = method_map[mode](image_b64)
            
            if result.success:
                logger.info(f"✅ {platform.name} 修复成功，耗时{result.cost_time:.2f}秒")
                return result
            else:
                logger.warning(f"❌ {platform.name} 失败: {result.message}")
                errors.append(f"{platform.name}: {result.message}")
        
        # 所有平台都失败了
        return RepairResult(
            success=False,
            mode=mode.value,
            message=f"所有平台均失败: {'; '.join(errors)}"
        )


# 全局单例
_router: Optional[APIRouter] = None

def get_router() -> APIRouter:
    """获取API路由器单例"""
    global _router
    if _router is None:
        _router = APIRouter()
    return _router


def reset_router():
    """重置路由器（用于测试）"""
    global _router
    _router = None

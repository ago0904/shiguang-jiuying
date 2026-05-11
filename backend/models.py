"""数据模型层 - JSON文件存储

本模块使用JSON文件作为持久化存储，简化部署（无需数据库）。
所有数据操作都是线程安全的（使用文件锁）。
"""

import json
import os
import time
import fcntl
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from contextlib import contextmanager

from config import Config

# 日志
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────


def now_str() -> str:
    """获取当前时间的ISO格式字符串"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def today_str() -> str:
    """获取今日日期字符串 YYYY-MM-DD"""
    return datetime.now().strftime('%Y-%m-%d')


def ensure_dir(path: str) -> str:
    """确保目录存在，返回完整路径"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


# ─────────────────────────────────────────────
# 文件锁（线程安全）
# ─────────────────────────────────────────────


@contextmanager
def file_lock(filepath: str, mode: str = 'r'):
    """文件锁上下文管理器，确保并发安全"""
    lock_path = filepath + '.lock'
    lock_file = None
    try:
        lock_file = open(lock_path, 'w')
        if 'w' in mode or 'a' in mode:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        else:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_SH)
        yield lock_file
    finally:
        if lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()


# ─────────────────────────────────────────────
# JSON存储基类
# ─────────────────────────────────────────────


class JsonStore:
    """JSON文件存储基类，提供读写操作"""

    def __init__(self, filename: str):
        self.filepath = os.path.join(Config.DATA_DIR, filename)
        ensure_dir(self.filepath)
        # 自动初始化文件
        if not os.path.exists(self.filepath):
            self._write_raw({})

    def _read_raw(self) -> dict:
        """读取原始JSON数据"""
        try:
            with file_lock(self.filepath, 'r'):
                if not os.path.exists(self.filepath) or os.path.getsize(self.filepath) == 0:
                    return {}
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except json.JSONDecodeError:
            logger.error(f"JSON解析错误: {self.filepath}")
            return {}
        except Exception as e:
            logger.error(f"读取文件失败: {self.filepath}, 错误: {e}")
            return {}

    def _write_raw(self, data: dict) -> bool:
        """写入原始JSON数据"""
        try:
            with file_lock(self.filepath, 'w'):
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"写入文件失败: {self.filepath}, 错误: {e}")
            return False

    def get_all(self) -> dict:
        """获取所有数据"""
        return self._read_raw()

    def get(self, key: str, default=None):
        """根据key获取数据"""
        data = self._read_raw()
        return data.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """设置单个key的数据"""
        data = self._read_raw()
        data[key] = value
        return self._write_raw(data)

    def delete(self, key: str) -> bool:
        """删除key"""
        data = self._read_raw()
        if key in data:
            del data[key]
            return self._write_raw(data)
        return True

    def exists(self, key: str) -> bool:
        """判断key是否存在"""
        data = self._read_raw()
        return key in data

    def count(self) -> int:
        """获取记录总数"""
        return len(self._read_raw())


# ─────────────────────────────────────────────
# 数据模型定义
# ─────────────────────────────────────────────


@dataclass
class User:
    """用户模型"""
    id: str                     # 用户ID (openid)
    union_id: str = ""          # unionid
    nickname: str = ""          # 昵称
    avatar: str = ""            # 头像URL
    created_at: str = ""        # 注册时间
    last_login: str = ""        # 最后登录时间
    total_repairs: int = 0      # 总修复次数
    free_remaining: int = 0     # 剩余免费次数
    is_member: bool = False     # 是否会员
    member_expire: str = ""     # 会员过期时间
    is_admin: bool = False      # 是否管理员
    status: str = "active"      # 状态: active / banned

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """从字典创建"""
        # 过滤掉多余的字段
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def is_active(self) -> bool:
        """判断用户是否有效"""
        return self.status == "active"

    def is_member_valid(self) -> bool:
        """判断会员是否有效"""
        if not self.is_member or not self.member_expire:
            return False
        try:
            expire = datetime.strptime(self.member_expire, '%Y-%m-%d %H:%M:%S')
            return datetime.now() < expire
        except ValueError:
            return False


@dataclass
class RepairRecord:
    """修复记录模型"""
    id: str                     # 记录ID
    user_id: str = ""           # 用户ID
    mode: str = ""              # 修复模式
    mode_name: str = ""         # 模式中文名
    platform: str = ""          # 使用的AI平台
    cost_time: float = 0.0      # 耗时（秒）
    created_at: str = ""        # 创建时间
    ip: str = ""                # IP地址

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'RepairRecord':
        """从字典创建"""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class DailyStats:
    """每日统计模型"""
    date: str = ""                          # 日期 YYYY-MM-DD
    total_repairs: int = 0                  # 总修复次数
    unique_users: int = 0                   # 独立用户数
    new_users: int = 0                      # 新用户数
    mode_breakdown: Dict[str, int] = field(default_factory=dict)       # 各模式使用次数
    platform_breakdown: Dict[str, int] = field(default_factory=dict)   # 各平台使用次数
    avg_cost_time: float = 0.0              # 平均耗时
    total_cost_time: float = 0.0            # 总耗时
    errors: int = 0                         # 错误次数

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'DailyStats':
        """从字典创建"""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


# ─────────────────────────────────────────────
# 数据访问对象 (DAO)
# ─────────────────────────────────────────────


class UserDAO:
    """用户数据访问对象"""

    def __init__(self):
        self.store = JsonStore(Config.USERS_FILE)

    def get_by_id(self, user_id: str) -> Optional[User]:
        """根据ID获取用户"""
        data = self.store.get(user_id)
        if data:
            return User.from_dict(data)
        return None

    def get_all_users(self) -> List[User]:
        """获取所有用户"""
        data = self.store.get_all()
        return [User.from_dict(v) for v in data.values()]

    def save(self, user: User) -> bool:
        """保存用户"""
        return self.store.set(user.id, user.to_dict())

    def create(self, user_id: str, union_id: str = "", nickname: str = "", avatar: str = "") -> User:
        """创建新用户"""
        now = now_str()
        user = User(
            id=user_id,
            union_id=union_id,
            nickname=nickname,
            avatar=avatar,
            created_at=now,
            last_login=now,
            total_repairs=0,
            free_remaining=Config.FREE_REPAIRS_PER_USER,
            is_member=False,
            member_expire="",
            is_admin=False,
            status="active"
        )
        self.save(user)
        logger.info(f"新用户注册: {user_id}, 昵称: {nickname}")
        return user

    def update_login_time(self, user_id: str) -> bool:
        """更新用户登录时间"""
        user = self.get_by_id(user_id)
        if user:
            user.last_login = now_str()
            return self.save(user)
        return False

    def increment_repair(self, user_id: str) -> bool:
        """增加用户修复次数"""
        user = self.get_by_id(user_id)
        if user:
            user.total_repairs += 1
            if user.free_remaining > 0:
                user.free_remaining -= 1
            return self.save(user)
        return False

    def count(self) -> int:
        """用户总数"""
        return self.store.count()

    def count_today_new(self) -> int:
        """今日新增用户数"""
        today = today_str()
        data = self.store.get_all()
        count = 0
        for user_data in data.values():
            created = user_data.get('created_at', '')
            if created.startswith(today):
                count += 1
        return count

    def count_active(self) -> int:
        """有效用户总数"""
        data = self.store.get_all()
        return sum(1 for u in data.values() if u.get('status') == 'active')


class RepairRecordDAO:
    """修复记录数据访问对象"""

    def __init__(self):
        self.store = JsonStore(Config.HISTORY_FILE)

    def get_by_id(self, record_id: str) -> Optional[RepairRecord]:
        """根据ID获取记录"""
        data = self.store.get(record_id)
        if data:
            return RepairRecord.from_dict(data)
        return None

    def get_all(self) -> List[RepairRecord]:
        """获取所有记录"""
        data = self.store.get_all()
        # 按时间倒序
        records = [RepairRecord.from_dict(v) for v in data.values()]
        records.sort(key=lambda x: x.created_at, reverse=True)
        return records

    def get_by_user(self, user_id: str, limit: int = 50) -> List[RepairRecord]:
        """获取用户的修复记录"""
        all_records = self.get_all()
        user_records = [r for r in all_records if r.user_id == user_id]
        return user_records[:limit]

    def save(self, record: RepairRecord) -> bool:
        """保存记录"""
        return self.store.set(record.id, record.to_dict())

    def create(self, user_id: str, mode: str, mode_name: str, platform: str, cost_time: float, ip: str = "") -> RepairRecord:
        """创建新记录"""
        record_id = f"{user_id}_{int(time.time() * 1000)}"
        record = RepairRecord(
            id=record_id,
            user_id=user_id,
            mode=mode,
            mode_name=mode_name,
            platform=platform,
            cost_time=cost_time,
            created_at=now_str(),
            ip=ip
        )
        self.save(record)
        return record

    def count(self) -> int:
        """记录总数"""
        return self.store.count()

    def count_today(self) -> int:
        """今日记录数"""
        today = today_str()
        data = self.store.get_all()
        return sum(1 for v in data.values() if v.get('created_at', '').startswith(today))

    def get_today_records(self) -> List[RepairRecord]:
        """获取今日所有记录"""
        today = today_str()
        data = self.store.get_all()
        records = []
        for v in data.values():
            if v.get('created_at', '').startswith(today):
                records.append(RepairRecord.from_dict(v))
        return records

    def get_date_range(self, start_date: str, end_date: str) -> List[RepairRecord]:
        """获取日期范围内的记录"""
        data = self.store.get_all()
        records = []
        for v in data.values():
            created = v.get('created_at', '')
            if start_date <= created[:10] <= end_date:
                records.append(RepairRecord.from_dict(v))
        records.sort(key=lambda x: x.created_at, reverse=True)
        return records

    def get_today_hourly(self) -> List[int]:
        """获取今日24小时分布"""
        today = today_str()
        data = self.store.get_all()
        hourly = [0] * 24
        for v in data.values():
            created = v.get('created_at', '')
            if created.startswith(today):
                try:
                    hour = int(created[11:13])
                    hourly[hour] += 1
                except (ValueError, IndexError):
                    continue
        return hourly


class DailyStatsDAO:
    """每日统计数据访问对象"""

    def __init__(self):
        self.store = JsonStore(Config.STATS_FILE)

    def get_by_date(self, date: str) -> Optional[DailyStats]:
        """根据日期获取统计"""
        data = self.store.get(date)
        if data:
            return DailyStats.from_dict(data)
        return None

    def get_or_create(self, date: str) -> DailyStats:
        """获取或创建某日的统计"""
        stats = self.get_by_date(date)
        if not stats:
            stats = DailyStats(date=date)
            self.save(stats)
        return stats

    def save(self, stats: DailyStats) -> bool:
        """保存统计"""
        return self.store.set(stats.date, stats.to_dict())

    def get_all(self) -> List[DailyStats]:
        """获取所有日统计"""
        data = self.store.get_all()
        stats_list = [DailyStats.from_dict(v) for v in data.values()]
        stats_list.sort(key=lambda x: x.date)
        return stats_list

    def get_recent(self, days: int = 7) -> List[DailyStats]:
        """获取最近N天的统计"""
        all_stats = self.get_all()
        if not all_stats:
            return []
        # 生成最近N天的日期列表
        dates = []
        for i in range(days - 1, -1, -1):
            d = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            dates.append(d)
        # 构建结果
        stats_map = {s.date: s for s in all_stats}
        result = []
        for d in dates:
            if d in stats_map:
                result.append(stats_map[d])
            else:
                result.append(DailyStats(date=d))
        return result

    def get_date_range(self, start_date: str, end_date: str) -> List[DailyStats]:
        """获取日期范围内的统计"""
        all_stats = self.get_all()
        result = []
        for s in all_stats:
            if start_date <= s.date <= end_date:
                result.append(s)
        return result

    def aggregate_from_records(self, date: str, records: List[RepairRecord]) -> DailyStats:
        """从修复记录聚合每日统计"""
        stats = DailyStats(date=date)

        if not records:
            self.save(stats)
            return stats

        stats.total_repairs = len(records)

        # 独立用户
        user_ids = set()
        total_cost = 0.0

        for r in records:
            user_ids.add(r.user_id)
            total_cost += r.cost_time

            # 模式分布
            mode = r.mode or 'unknown'
            stats.mode_breakdown[mode] = stats.mode_breakdown.get(mode, 0) + 1

            # 平台分布
            platform = r.platform or 'unknown'
            stats.platform_breakdown[platform] = stats.platform_breakdown.get(platform, 0) + 1

        stats.unique_users = len(user_ids)
        stats.total_cost_time = round(total_cost, 2)
        if stats.total_repairs > 0:
            stats.avg_cost_time = round(total_cost / stats.total_repairs, 2)

        self.save(stats)
        return stats


# ─────────────────────────────────────────────
# 单例实例
# ─────────────────────────────────────────────

user_dao = UserDAO()
record_dao = RepairRecordDAO()
stats_dao = DailyStatsDAO()

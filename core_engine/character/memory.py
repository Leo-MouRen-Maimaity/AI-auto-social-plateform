"""
记忆系统模块

管理AI角色的各类记忆：共同记忆、日常记忆、重要记忆、知识记忆、关系记忆
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime
import json


class MemoryType(str, Enum):
    """记忆类型"""
    COMMON = "common"           # 共同记忆 - 所有AI共享的世界设定
    DAILY = "daily"             # 日常记忆 - 每天一条，最多14条
    IMPORTANT = "important"     # 重要记忆 - 一条长文本，最多1000字符
    KNOWLEDGE = "knowledge"     # 知识记忆 - 学习到的知识
    RELATIONSHIP = "relationship"  # 关系记忆 - 对其他角色的记忆


@dataclass
class Memory:
    """记忆单元"""
    id: int
    memory_type: MemoryType
    content: str
    character_id: int  # 所属角色ID
    target_id: Optional[int] = None  # 关系记忆的目标角色ID
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    game_day: int = 1  # 创建时的游戏天数
    importance: float = 0.5  # 重要度 0-1
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'memory_type': self.memory_type.value,
            'content': self.content,
            'character_id': self.character_id,
            'target_id': self.target_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'game_day': self.game_day,
            'importance': self.importance,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Memory':
        return cls(
            id=data['id'],
            memory_type=MemoryType(data['memory_type']),
            content=data['content'],
            character_id=data['character_id'],
            target_id=data.get('target_id'),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else datetime.now(),
            game_day=data.get('game_day', 1),
            importance=data.get('importance', 0.5),
            metadata=data.get('metadata', {})
        )
    
    @classmethod
    def from_db_row(cls, row) -> 'Memory':
        """从数据库行创建"""
        metadata = {}
        if row.metadata:
            try:
                metadata = json.loads(row.metadata)
            except json.JSONDecodeError:
                pass
        
        return cls(
            id=row.id,
            memory_type=MemoryType(row.memory_type),
            content=row.content,
            character_id=row.character_id,
            target_id=row.target_id,
            created_at=row.created_at,
            updated_at=row.updated_at or row.created_at,
            game_day=row.game_day or 1,
            importance=row.importance or 0.5,
            metadata=metadata
        )


class MemorySystem:
    """
    记忆系统
    
    管理角色的各类记忆，支持存储、检索、整理
    """
    
    # 记忆限制
    MAX_DAILY_MEMORIES = 14
    MAX_IMPORTANT_LENGTH = 1000
    MAX_KNOWLEDGE_MEMORIES = 50
    MAX_RELATIONSHIP_PER_TARGET = 1
    
    def __init__(self, character_id: int, db_session=None):
        self.character_id = character_id
        self._db = db_session
        
        # 内存缓存
        self._common_memories: List[Memory] = []
        self._daily_memories: List[Memory] = []
        self._important_memory: Optional[Memory] = None
        self._knowledge_memories: List[Memory] = []
        self._relationship_memories: Dict[int, Memory] = {}  # target_id -> Memory
        
        # ID计数器（内存模式）
        self._next_id = 1
    
    def load_from_db(self):
        """从数据库加载记忆"""
        if not self._db:
            return
        
        from api_server.models import Memory as MemoryModel
        
        # 加载共同记忆（user_id为0或NULL表示共同记忆）
        common_rows = self._db.query(MemoryModel).filter(
            MemoryModel.memory_type == MemoryType.COMMON.value
        ).all()
        
        for row in common_rows:
            # 共同记忆：user_id可能为空或指向特殊用户
            memory = self._memory_from_db_row(row)
            self._common_memories.append(memory)
        
        # 加载个人记忆
        personal_rows = self._db.query(MemoryModel).filter(
            MemoryModel.user_id == self.character_id
        ).all()
        
        for row in personal_rows:
            memory = self._memory_from_db_row(row)
            
            if memory.memory_type == MemoryType.DAILY:
                self._daily_memories.append(memory)
            elif memory.memory_type == MemoryType.IMPORTANT:
                self._important_memory = memory
            elif memory.memory_type == MemoryType.KNOWLEDGE:
                self._knowledge_memories.append(memory)
            elif memory.memory_type == MemoryType.RELATIONSHIP:
                if memory.target_id:
                    self._relationship_memories[memory.target_id] = memory
        
        # 按时间排序日常记忆
        self._daily_memories.sort(key=lambda m: m.game_day, reverse=True)
        
        # 更新ID计数器
        all_ids = ([m.id for m in self._common_memories] +
                   [m.id for m in self._daily_memories] +
                   [m.id for m in self._knowledge_memories] +
                   [m.id for m in self._relationship_memories.values()])
        if self._important_memory:
            all_ids.append(self._important_memory.id)
        
        if all_ids:
            self._next_id = max(all_ids) + 1
    
    def _memory_from_db_row(self, row) -> Memory:
        """从数据库行创建Memory对象（适配数据库字段）"""
        # 数据库使用 user_id 而不是 character_id
        # 数据库使用 target_user_id 而不是 target_id
        # 数据库没有 updated_at 和 metadata 字段
        
        memory_type_str = row.memory_type
        if isinstance(memory_type_str, str):
            # 处理数据库中 'relation' vs 'relationship' 的差异
            if memory_type_str == 'relation':
                memory_type_str = 'relationship'
            memory_type = MemoryType(memory_type_str)
        else:
            # 如果是Enum对象
            val = memory_type_str.value if hasattr(memory_type_str, 'value') else str(memory_type_str)
            if val == 'relation':
                val = 'relationship'
            memory_type = MemoryType(val)
        
        return Memory(
            id=row.id,
            memory_type=memory_type,
            content=row.content,
            character_id=row.user_id,
            target_id=getattr(row, 'target_user_id', None),
            created_at=row.created_at,
            updated_at=row.created_at,  # 数据库没有updated_at，用created_at代替
            game_day=row.game_day or 1,
            importance=row.importance / 10.0 if row.importance else 0.5,  # 数据库使用1-10，转换为0-1
            metadata={}
        )
    
    def _generate_id(self) -> int:
        """生成新的记忆ID"""
        id = self._next_id
        self._next_id += 1
        return id
    
    def _save_to_db(self, memory: Memory):
        """保存记忆到数据库"""
        if not self._db:
            return
        
        from api_server.models import Memory as MemoryModel
        
        # 检查是否已存在
        existing = self._db.query(MemoryModel).filter(
            MemoryModel.id == memory.id
        ).first()
        
        # 转换memory_type（处理relationship vs relation差异）
        db_memory_type = memory.memory_type.value
        if db_memory_type == 'relationship':
            db_memory_type = 'relation'
        
        if existing:
            existing.content = memory.content
            existing.importance = int(memory.importance * 10)  # 转换为1-10
        else:
            db_memory = MemoryModel(
                memory_type=db_memory_type,
                content=memory.content,
                user_id=memory.character_id if memory.character_id else None,
                target_user_id=memory.target_id,
                game_day=memory.game_day,
                importance=int(memory.importance * 10)
            )
            self._db.add(db_memory)
            self._db.flush()  # 获取自动生成的ID
            memory.id = db_memory.id
        
        self._db.commit()
    
    def _delete_from_db(self, memory_id: int):
        """从数据库删除记忆"""
        if not self._db:
            return
        
        from api_server.models import Memory as MemoryModel
        
        self._db.query(MemoryModel).filter(MemoryModel.id == memory_id).delete()
        self._db.commit()
    
    # ===== 共同记忆 =====
    
    def get_common_memories(self) -> List[Memory]:
        """获取所有共同记忆"""
        return self._common_memories.copy()
    
    def get_common_memory_text(self) -> str:
        """获取共同记忆的文本表示"""
        if not self._common_memories:
            return ""
        return "\n".join([m.content for m in self._common_memories])
    
    # ===== 日常记忆 =====
    
    def add_daily_memory(self, content: str, game_day: int) -> Memory:
        """
        添加日常记忆
        
        如果超出数量限制，删除最旧的记忆
        """
        # 检查当天是否已有记忆
        for mem in self._daily_memories:
            if mem.game_day == game_day:
                # 更新现有记忆
                mem.content = content
                mem.updated_at = datetime.now()
                self._save_to_db(mem)
                return mem
        
        # 创建新记忆
        memory = Memory(
            id=self._generate_id(),
            memory_type=MemoryType.DAILY,
            content=content,
            character_id=self.character_id,
            game_day=game_day
        )
        
        self._daily_memories.insert(0, memory)
        
        # 检查数量限制
        while len(self._daily_memories) > self.MAX_DAILY_MEMORIES:
            old_memory = self._daily_memories.pop()
            self._delete_from_db(old_memory.id)
        
        self._save_to_db(memory)
        return memory
    
    def get_daily_memories(self, limit: int = 14) -> List[Memory]:
        """获取日常记忆（最近的在前）"""
        return self._daily_memories[:limit]
    
    def get_daily_memory_text(self) -> str:
        """获取日常记忆的文本表示"""
        if not self._daily_memories:
            return ""
        
        lines = []
        for mem in self._daily_memories:
            lines.append(f"[第{mem.game_day}天] {mem.content}")
        return "\n".join(lines)
    
    # ===== 重要记忆 =====
    
    def set_important_memory(self, content: str) -> Memory:
        """
        设置重要记忆
        
        如果超出字符限制，截断内容
        """
        if len(content) > self.MAX_IMPORTANT_LENGTH:
            content = content[:self.MAX_IMPORTANT_LENGTH]
        
        if self._important_memory:
            self._important_memory.content = content
            self._important_memory.updated_at = datetime.now()
        else:
            self._important_memory = Memory(
                id=self._generate_id(),
                memory_type=MemoryType.IMPORTANT,
                content=content,
                character_id=self.character_id,
                importance=1.0
            )
        
        self._save_to_db(self._important_memory)
        return self._important_memory
    
    def get_important_memory(self) -> Optional[Memory]:
        """获取重要记忆"""
        return self._important_memory
    
    def get_important_memory_text(self) -> str:
        """获取重要记忆的文本"""
        return self._important_memory.content if self._important_memory else ""
    
    def append_important_memory(self, content: str) -> bool:
        """
        追加内容到重要记忆
        
        Returns:
            是否成功（可能因长度限制失败）
        """
        current = self.get_important_memory_text()
        new_content = current + "\n" + content if current else content
        
        if len(new_content) > self.MAX_IMPORTANT_LENGTH:
            return False
        
        self.set_important_memory(new_content)
        return True
    
    # ===== 知识记忆 =====
    
    def add_knowledge(self, content: str, importance: float = 0.5,
                      metadata: Dict[str, Any] = None) -> Memory:
        """添加知识记忆"""
        memory = Memory(
            id=self._generate_id(),
            memory_type=MemoryType.KNOWLEDGE,
            content=content,
            character_id=self.character_id,
            importance=importance,
            metadata=metadata or {}
        )
        
        self._knowledge_memories.append(memory)
        
        # 如果超出限制，删除重要度最低的
        if len(self._knowledge_memories) > self.MAX_KNOWLEDGE_MEMORIES:
            self._knowledge_memories.sort(key=lambda m: m.importance)
            old_memory = self._knowledge_memories.pop(0)
            self._delete_from_db(old_memory.id)
        
        self._save_to_db(memory)
        return memory
    
    def get_knowledge_memories(self) -> List[Memory]:
        """获取所有知识记忆"""
        return self._knowledge_memories.copy()
    
    def search_knowledge(self, keyword: str) -> List[Memory]:
        """搜索知识记忆"""
        keyword_lower = keyword.lower()
        return [m for m in self._knowledge_memories 
                if keyword_lower in m.content.lower()]
    
    # ===== 关系记忆 =====
    
    def set_relationship_memory(self, target_id: int, content: str,
                                 importance: float = 0.5) -> Memory:
        """
        设置对某个角色的关系记忆
        
        每个目标角色只能有一条关系记忆
        """
        if target_id in self._relationship_memories:
            memory = self._relationship_memories[target_id]
            memory.content = content
            memory.importance = importance
            memory.updated_at = datetime.now()
        else:
            memory = Memory(
                id=self._generate_id(),
                memory_type=MemoryType.RELATIONSHIP,
                content=content,
                character_id=self.character_id,
                target_id=target_id,
                importance=importance
            )
            self._relationship_memories[target_id] = memory
        
        self._save_to_db(memory)
        return memory
    
    def get_relationship_memory(self, target_id: int) -> Optional[Memory]:
        """获取对某个角色的关系记忆"""
        return self._relationship_memories.get(target_id)
    
    def get_all_relationships(self) -> Dict[int, Memory]:
        """获取所有关系记忆"""
        return self._relationship_memories.copy()
    
    def get_relationship_text(self, target_id: int, target_name: str = "") -> str:
        """获取关系记忆的文本表示"""
        memory = self.get_relationship_memory(target_id)
        if not memory:
            return ""
        
        if target_name:
            return f"关于{target_name}: {memory.content}"
        return memory.content
    
    # ===== 综合方法 =====
    
    def get_all_memories_for_context(self) -> Dict[str, str]:
        """
        获取所有记忆用于构建上下文
        
        Returns:
            包含各类记忆文本的字典
        """
        return {
            'common': self.get_common_memory_text(),
            'daily': self.get_daily_memory_text(),
            'important': self.get_important_memory_text(),
            'knowledge': "\n".join([m.content for m in self._knowledge_memories]),
            'relationships': "\n".join([
                f"[{m.target_id}] {m.content}" 
                for m in self._relationship_memories.values()
            ])
        }
    
    def build_memory_prompt(self, include_types: List[MemoryType] = None) -> str:
        """
        构建记忆提示词
        
        Args:
            include_types: 要包含的记忆类型，None表示全部
            
        Returns:
            格式化的记忆文本
        """
        if include_types is None:
            include_types = list(MemoryType)
        
        sections = []
        
        if MemoryType.COMMON in include_types and self._common_memories:
            sections.append("【世界设定】\n" + self.get_common_memory_text())
        
        if MemoryType.IMPORTANT in include_types and self._important_memory:
            sections.append("【重要记忆】\n" + self.get_important_memory_text())
        
        if MemoryType.DAILY in include_types and self._daily_memories:
            sections.append("【日常记忆】\n" + self.get_daily_memory_text())
        
        if MemoryType.KNOWLEDGE in include_types and self._knowledge_memories:
            sections.append("【知识记忆】\n" + "\n".join([m.content for m in self._knowledge_memories[:10]]))
        
        return "\n\n".join(sections)
    
    def summarize_day(self, events: List[str], game_day: int) -> str:
        """
        总结一天的内容为日常记忆
        
        Args:
            events: 当天发生的事件列表
            game_day: 游戏天数
            
        Returns:
            生成的日常记忆内容
        """
        if not events:
            return f"第{game_day}天平静地度过了。"
        
        # 简单总结（实际应由LLM生成）
        summary = f"第{game_day}天: " + "; ".join(events[:5])
        if len(events) > 5:
            summary += f" 等{len(events)}件事"
        
        return summary
    
    def get_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        return {
            'character_id': self.character_id,
            'common_count': len(self._common_memories),
            'daily_count': len(self._daily_memories),
            'has_important': self._important_memory is not None,
            'important_length': len(self.get_important_memory_text()),
            'knowledge_count': len(self._knowledge_memories),
            'relationship_count': len(self._relationship_memories)
        }

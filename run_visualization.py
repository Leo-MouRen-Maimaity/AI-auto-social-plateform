"""
可视化模块启动脚本

从数据库加载地点和角色数据，启动 Pygame 可视化界面
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import List, Dict, Any
import time
import threading

try:
    import pygame
except ImportError:
    print("错误: 需要安装 pygame")
    print("运行: pip install pygame")
    sys.exit(1)

from core_engine.visualization import WorldRenderer
from api_server.database import SessionLocal
from api_server import models


def load_locations_from_db() -> List[Dict[str, Any]]:
    """从数据库加载地点数据"""
    db = SessionLocal()
    try:
        locations = db.query(models.Location).all()
        result = []
        for loc in locations:
            result.append({
                'id': loc.id,
                'name': loc.name,
                'location_type': loc.location_type or 'public',
                'x': loc.x,
                'y': loc.y,
                'width': loc.width or 10,
                'height': loc.height or 10,
                'description': loc.description or '',
                'is_indoor': True,
                'current_occupants': []
            })
        return result
    finally:
        db.close()


def load_characters_from_db() -> List[Dict[str, Any]]:
    """从数据库加载 AI 角色数据"""
    db = SessionLocal()
    try:
        # 只加载 AI 角色
        users = db.query(models.User).filter(models.User.is_ai == True).all()
        result = []
        for user in users:
            result.append({
                'id': user.id,
                'name': user.nickname or user.username,
                'x': user.current_x or 0,
                'y': user.current_y or 0,
                'location_id': user.current_location_id,
                'fatigue': user.fatigue or 0
            })
        return result
    finally:
        db.close()


def load_action_logs_from_db(limit: int = 10) -> List[Dict[str, Any]]:
    """从数据库加载最近的行动日志"""
    db = SessionLocal()
    try:
        # 检查表是否存在
        if not hasattr(models, 'ActionLog'):
            return []
        
        logs = db.query(models.ActionLog).order_by(
            models.ActionLog.created_at.desc()
        ).limit(limit).all()
        
        result = []
        for log in logs:
            char_name = ""
            if log.character:
                char_name = log.character.nickname or log.character.username
            
            result.append({
                'character_id': log.character_id,
                'character_name': char_name,
                'action_name': log.action_name,
                'description': log.description or '',
                'game_time': log.game_time or '',
                'game_day': log.game_day or 0
            })
        return result
    except Exception as e:
        print(f"加载行动日志失败: {e}")
        return []
    finally:
        db.close()


def load_character_details(character_id: int) -> Dict[str, Any]:
    """加载角色详细信息（记忆、行动等）"""
    db = SessionLocal()
    try:
        details = {
            'memories': [],
            'recent_actions': [],
            'daily_plan': []
        }
        
        # 加载重要记忆
        memories = db.query(models.Memory).filter(
            models.Memory.user_id == character_id,
            models.Memory.memory_type.in_(['important', 'relation'])
        ).order_by(models.Memory.created_at.desc()).limit(5).all()
        
        for mem in memories:
            details['memories'].append(mem.content[:100])
        
        # 加载最近行动
        if hasattr(models, 'ActionLog'):
            actions = db.query(models.ActionLog).filter(
                models.ActionLog.character_id == character_id
            ).order_by(models.ActionLog.created_at.desc()).limit(5).all()
            
            for action in actions:
                details['recent_actions'].append({
                    'action_name': action.action_name,
                    'description': action.description or '',
                    'game_time': action.game_time or ''
                })
        
        return details
    except Exception as e:
        print(f"加载角色详情失败: {e}")
        return {'memories': [], 'recent_actions': [], 'daily_plan': []}
    finally:
        db.close()


def calculate_bounds(locations: List[Dict[str, Any]]) -> Dict[str, float]:
    """计算地图边界"""
    if not locations:
        return {'min_x': 0, 'min_y': 0, 'max_x': 500, 'max_y': 500}
    
    min_x = min(loc['x'] for loc in locations)
    min_y = min(loc['y'] for loc in locations)
    max_x = max(loc['x'] + loc['width'] for loc in locations)
    max_y = max(loc['y'] + loc['height'] for loc in locations)
    
    # 添加边距
    padding = 50
    return {
        'min_x': min_x - padding,
        'min_y': min_y - padding,
        'max_x': max_x + padding,
        'max_y': max_y + padding
    }


def create_demo_data() -> Dict[str, Any]:
    """创建演示数据（当数据库无数据时使用）"""
    locations = [
        {'id': 1, 'name': '中央广场', 'location_type': 'public', 
         'x': 200, 'y': 200, 'width': 60, 'height': 60, 'is_indoor': False, 'current_occupants': []},
        {'id': 2, 'name': '咖啡厅', 'location_type': 'commercial',
         'x': 100, 'y': 150, 'width': 30, 'height': 25, 'is_indoor': True, 'current_occupants': []},
        {'id': 3, 'name': '图书馆', 'location_type': 'education',
         'x': 300, 'y': 100, 'width': 50, 'height': 40, 'is_indoor': True, 'current_occupants': []},
        {'id': 4, 'name': '公园', 'location_type': 'recreation',
         'x': 350, 'y': 250, 'width': 80, 'height': 60, 'is_indoor': False, 'current_occupants': []},
        {'id': 5, 'name': '医院', 'location_type': 'medical',
         'x': 50, 'y': 300, 'width': 40, 'height': 50, 'is_indoor': True, 'current_occupants': []},
        {'id': 6, 'name': '市政厅', 'location_type': 'government',
         'x': 200, 'y': 50, 'width': 45, 'height': 35, 'is_indoor': True, 'current_occupants': []},
        {'id': 7, 'name': '小区A', 'location_type': 'residential',
         'x': 100, 'y': 350, 'width': 60, 'height': 50, 'is_indoor': True, 'current_occupants': []},
        {'id': 8, 'name': '小区B', 'location_type': 'residential',
         'x': 300, 'y': 350, 'width': 60, 'height': 50, 'is_indoor': True, 'current_occupants': []},
        {'id': 9, 'name': '超市', 'location_type': 'commercial',
         'x': 150, 'y': 280, 'width': 35, 'height': 30, 'is_indoor': True, 'current_occupants': []},
        {'id': 10, 'name': '办公楼', 'location_type': 'workplace',
         'x': 380, 'y': 150, 'width': 40, 'height': 60, 'is_indoor': True, 'current_occupants': []},
    ]
    
    characters = [
        {'id': 1, 'name': '小明', 'x': 210, 'y': 220},
        {'id': 2, 'name': '小红', 'x': 115, 'y': 165},
        {'id': 3, 'name': '小华', 'x': 320, 'y': 120},
        {'id': 4, 'name': '小李', 'x': 380, 'y': 280},
        {'id': 5, 'name': '小王', 'x': 130, 'y': 370},
    ]
    
    return {
        'locations': locations,
        'bounds': calculate_bounds(locations),
        'characters': characters
    }


class VisualizationApp:
    """可视化应用主类"""
    
    def __init__(self, use_demo: bool = False):
        self.renderer = WorldRenderer(
            width=1280,
            height=720,
            title="AI社区 - 世界可视化"
        )
        self.use_demo = use_demo
        self.running = False
        
        # 模拟数据更新（用于演示移动动画）
        self.simulation_enabled = True
        self.simulation_time = 0
        
        # 数据刷新计时器
        self.data_refresh_timer = 0
        self.data_refresh_interval = 5.0  # 每5秒刷新一次数据
        
        # 上次选中的角色
        self.last_selected_id = None
    
    def load_data(self):
        """加载数据"""
        if self.use_demo:
            print("使用演示数据...")
            data = create_demo_data()
            locations = data['locations']
            characters = data['characters']
        else:
            print("从数据库加载数据...")
            try:
                locations = load_locations_from_db()
                characters = load_characters_from_db()
            except Exception as e:
                print(f"数据库加载失败: {e}")
                print("切换到演示模式...")
                data = create_demo_data()
                locations = data['locations']
                characters = data['characters']
        
        if not locations:
            print("没有找到地点数据，使用演示数据")
            data = create_demo_data()
            locations = data['locations']
            characters = data['characters']
        
        # 加载到渲染器
        world_data = {
            'locations': locations,
            'bounds': calculate_bounds(locations)
        }
        self.renderer.load_world_data(world_data)
        
        # 添加角色
        for char in characters:
            self.renderer.update_character(
                character_id=char['id'],
                name=char['name'],
                x=char['x'],
                y=char['y']
            )
            # 设置疲劳度
            if char['id'] in self.renderer.characters:
                self.renderer.characters[char['id']].fatigue = char.get('fatigue', 0)
        
        # 加载行动日志
        if not self.use_demo:
            self.refresh_action_logs()
        
        print(f"加载完成: {len(locations)} 个地点, {len(characters)} 个角色")
    
    def refresh_action_logs(self):
        """刷新行动日志"""
        if self.use_demo:
            return
        
        try:
            logs = load_action_logs_from_db(limit=10)
            self.renderer.update_action_logs(logs)
        except Exception as e:
            print(f"刷新行动日志失败: {e}")
    
    def refresh_selected_character_details(self):
        """刷新选中角色的详情"""
        if self.use_demo:
            return
        
        char_id = self.renderer.selected_character_id
        if char_id is None:
            return
        
        # 只在角色改变或需要刷新时加载
        if char_id != self.last_selected_id:
            self.last_selected_id = char_id
            try:
                details = load_character_details(char_id)
                self.renderer.update_character_details(
                    character_id=char_id,
                    memories=details.get('memories', []),
                    recent_actions=details.get('recent_actions', []),
                    daily_plan=details.get('daily_plan', [])
                )
            except Exception as e:
                print(f"加载角色详情失败: {e}")
    
    def simulate_movement(self, dt: float):
        """模拟角色移动（演示用）"""
        import math
        import random
        
        self.simulation_time += dt
        
        for char_id, char in self.renderer.characters.items():
            # 如果角色没有在移动，随机给一个移动目标
            if not char.is_moving and random.random() < 0.005:  # 0.5% 几率开始移动
                # 随机选择一个地点作为目标
                if self.renderer.locations:
                    target_loc = random.choice(list(self.renderer.locations.values()))
                    char.target_x = target_loc.x + target_loc.width / 2
                    char.target_y = target_loc.y + target_loc.height / 2
                    char.is_moving = True
            
            # 如果正在移动，更新位置
            if char.is_moving and char.target_x is not None:
                dx = char.target_x - char.x
                dy = char.target_y - char.y
                distance = math.sqrt(dx * dx + dy * dy)
                
                if distance < 2:
                    # 到达目标
                    char.x = char.target_x
                    char.y = char.target_y
                    char.is_moving = False
                    char.target_x = None
                    char.target_y = None
                else:
                    # 移动
                    speed = 30 * dt  # 每秒30单位
                    char.x += (dx / distance) * speed
                    char.y += (dy / distance) * speed
    
    def run(self):
        """运行可视化"""
        self.renderer.initialize()
        self.load_data()
        
        self.running = True
        clock = pygame.time.Clock()
        
        # 模拟游戏时间
        game_hour = 8
        game_minute = 0
        time_accumulator = 0
        
        print("\n可视化已启动!")
        print("操作说明:")
        print("  - 鼠标中键拖拽: 移动地图")
        print("  - 滚轮: 缩放")
        print("  - 点击角色: 选择/查看详情")
        print("  - G: 切换网格")
        print("  - L: 切换标签")
        print("  - I: 切换角色详情面板")
        print("  - D: 切换调试信息")
        print("  - R: 重置视图")
        print("  - ESC: 取消选择")
        print("  - 关闭窗口: 退出")
        print()
        
        while self.running:
            dt = clock.tick(60) / 1000.0
            
            # 处理事件
            if not self.renderer.handle_events():
                self.running = False
                break
            
            # 模拟时间流逝（每秒 = 1游戏分钟）
            time_accumulator += dt
            if time_accumulator >= 1.0:
                time_accumulator = 0
                game_minute += 1
                if game_minute >= 60:
                    game_minute = 0
                    game_hour += 1
                    if game_hour >= 24:
                        game_hour = 0
            
            # 更新世界状态显示
            self.renderer.update_world_state(
                time_str=f"{game_hour:02d}:{game_minute:02d}",
                day=1,
                weather="sunny",
                season="spring"
            )
            
            # 定期刷新数据
            self.data_refresh_timer += dt
            if self.data_refresh_timer >= self.data_refresh_interval:
                self.data_refresh_timer = 0
                self.refresh_action_logs()
            
            # 刷新选中角色详情
            self.refresh_selected_character_details()
            
            # 模拟角色移动
            if self.simulation_enabled:
                self.simulate_movement(dt)
            
            # 渲染
            self.renderer.render(dt)
        
        self.renderer.shutdown()
        print("可视化已关闭")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI社区世界可视化')
    parser.add_argument('--demo', action='store_true', help='使用演示数据')
    args = parser.parse_args()
    
    app = VisualizationApp(use_demo=args.demo)
    app.run()


if __name__ == "__main__":
    main()

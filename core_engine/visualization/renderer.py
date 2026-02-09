"""
世界渲染器

使用 Pygame 渲染游戏世界，包括地点和角色
"""

import pygame
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .camera import Camera


class Colors:
    """颜色定义"""
    # 基础颜色
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GRAY = (128, 128, 128)
    LIGHT_GRAY = (200, 200, 200)
    DARK_GRAY = (64, 64, 64)
    
    # 地点类型颜色
    LOCATION_COLORS = {
        'public': (100, 180, 100),       # 绿色 - 公共场所
        'commercial': (180, 140, 100),   # 棕色 - 商业
        'residential': (100, 140, 180),  # 蓝色 - 住宅
        'workplace': (160, 160, 160),    # 灰色 - 工作场所
        'medical': (180, 100, 100),      # 红色 - 医疗
        'government': (140, 100, 160),   # 紫色 - 政府
        'education': (180, 180, 100),    # 黄色 - 教育
        'recreation': (100, 180, 180),   # 青色 - 休闲
    }
    
    # 角色颜色
    CHARACTER_FILL = (255, 100, 100)
    CHARACTER_BORDER = (180, 50, 50)
    CHARACTER_SELECTED = (255, 200, 100)
    CHARACTER_MOVING = (100, 200, 255)
    
    # UI 颜色
    UI_BACKGROUND = (40, 40, 50)
    UI_TEXT = (220, 220, 220)
    UI_HIGHLIGHT = (100, 150, 200)
    
    # 网格
    GRID_LINE = (60, 60, 70)
    
    # 天气效果
    WEATHER_RAIN = (100, 100, 200, 100)
    WEATHER_SNOW = (255, 255, 255, 150)


@dataclass
class CharacterSprite:
    """角色精灵数据"""
    character_id: int
    name: str
    x: float
    y: float
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    is_moving: bool = False
    color: Tuple[int, int, int] = field(default_factory=lambda: Colors.CHARACTER_FILL)
    
    # 动画状态
    animation_frame: int = 0
    animation_timer: float = 0.0
    
    # 角色详情（用于详情面板）
    state: str = "idle"                     # 当前状态
    fatigue: int = 0                        # 疲劳度
    current_action: str = ""                # 当前行动
    daily_plan: List[str] = field(default_factory=list)  # 今日计划
    recent_actions: List[Dict[str, Any]] = field(default_factory=list)  # 最近行动
    memories: List[str] = field(default_factory=list)    # 重要记忆摘要


@dataclass
class ActionLogDisplay:
    """行动日志显示数据"""
    character_id: int
    character_name: str
    action_name: str
    description: str
    game_time: str
    game_day: int


@dataclass
class LocationSprite:
    """地点精灵数据"""
    location_id: int
    name: str
    location_type: str
    x: float
    y: float
    width: float
    height: float
    is_indoor: bool = True
    occupants: List[int] = field(default_factory=list)


class WorldRenderer:
    """
    世界渲染器
    
    负责使用 Pygame 渲染游戏世界
    """
    
    def __init__(self, width: int = 1280, height: int = 720, title: str = "AI社区 - 世界可视化"):
        """
        初始化渲染器
        
        Args:
            width: 窗口宽度
            height: 窗口高度
            title: 窗口标题
        """
        self.width = width
        self.height = height
        self.title = title
        
        # Pygame 组件
        self.screen: Optional[pygame.Surface] = None
        self.clock: Optional[pygame.time.Clock] = None
        self.font: Optional[pygame.font.Font] = None
        self.small_font: Optional[pygame.font.Font] = None
        self.large_font: Optional[pygame.font.Font] = None
        
        # 相机
        self.camera = Camera(
            screen_width=width,
            screen_height=height
        )
        
        # 世界数据
        self.locations: Dict[int, LocationSprite] = {}
        self.characters: Dict[int, CharacterSprite] = {}
        
        # 世界边界
        self.world_bounds = {
            'min_x': 0, 'min_y': 0,
            'max_x': 500, 'max_y': 500
        }
        
        # UI 状态
        self.selected_character_id: Optional[int] = None
        self.hovered_location_id: Optional[int] = None
        self.show_grid: bool = True
        self.show_labels: bool = True
        self.show_debug: bool = False
        self.show_detail_panel: bool = False  # 是否显示角色详情面板
        
        # 行动日志（全局最近行动）
        self.action_logs: List[ActionLogDisplay] = []
        self.max_action_logs: int = 10
        
        # 世界状态（从引擎获取）
        self.game_time: str = "00:00"
        self.game_day: int = 1
        self.weather: str = "sunny"
        self.season: str = "spring"
        
        # 运行状态
        self.running: bool = False
        self._initialized: bool = False
    
    def initialize(self):
        """初始化 Pygame"""
        if self._initialized:
            return
        
        pygame.init()
        pygame.display.set_caption(self.title)
        
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        
        # 初始化字体
        pygame.font.init()
        try:
            # 尝试使用系统中文字体
            font_path = "C:/Windows/Fonts/msyh.ttc"  # 微软雅黑
            self.font = pygame.font.Font(font_path, 14)
            self.small_font = pygame.font.Font(font_path, 11)
            self.large_font = pygame.font.Font(font_path, 18)
        except:
            # 回退到默认字体
            self.font = pygame.font.Font(None, 16)
            self.small_font = pygame.font.Font(None, 12)
            self.large_font = pygame.font.Font(None, 20)
        
        self._initialized = True
        print("Pygame 渲染器初始化完成")
    
    def shutdown(self):
        """关闭渲染器"""
        if self._initialized:
            pygame.quit()
            self._initialized = False
    
    def load_world_data(self, world_data: Dict[str, Any]):
        """
        加载世界数据
        
        Args:
            world_data: 包含地点和边界信息的字典
        """
        # 加载地点
        self.locations.clear()
        for loc_data in world_data.get('locations', []):
            sprite = LocationSprite(
                location_id=loc_data['id'],
                name=loc_data['name'],
                location_type=loc_data.get('location_type', 'public'),
                x=loc_data['x'],
                y=loc_data['y'],
                width=loc_data.get('width', 10),
                height=loc_data.get('height', 10),
                is_indoor=loc_data.get('is_indoor', True),
                occupants=loc_data.get('current_occupants', [])
            )
            self.locations[sprite.location_id] = sprite
        
        # 更新边界
        if 'bounds' in world_data:
            self.world_bounds = world_data['bounds']
        
        # 将相机居中到世界中心
        center_x = (self.world_bounds['min_x'] + self.world_bounds['max_x']) / 2
        center_y = (self.world_bounds['min_y'] + self.world_bounds['max_y']) / 2
        self.camera.center_on(center_x, center_y)
        
        print(f"加载了 {len(self.locations)} 个地点")
    
    def update_character(self, character_id: int, name: str, 
                        x: float, y: float,
                        target_x: Optional[float] = None,
                        target_y: Optional[float] = None,
                        is_moving: bool = False):
        """更新角色位置"""
        if character_id not in self.characters:
            # 为新角色分配颜色
            color = self._generate_character_color(character_id)
            self.characters[character_id] = CharacterSprite(
                character_id=character_id,
                name=name,
                x=x,
                y=y,
                color=color
            )
        
        char = self.characters[character_id]
        char.x = x
        char.y = y
        char.target_x = target_x
        char.target_y = target_y
        char.is_moving = is_moving
    
    def remove_character(self, character_id: int):
        """移除角色"""
        if character_id in self.characters:
            del self.characters[character_id]
    
    def update_world_state(self, time_str: str, day: int, weather: str, season: str):
        """更新世界状态信息"""
        self.game_time = time_str
        self.game_day = day
        self.weather = weather
        self.season = season
    
    def update_location_occupants(self, location_id: int, occupants: List[int]):
        """更新地点的占用者列表"""
        if location_id in self.locations:
            self.locations[location_id].occupants = occupants
    
    def add_action_log(self, character_id: int, character_name: str,
                       action_name: str, description: str,
                       game_time: str = "", game_day: int = 0):
        """添加一条行动日志"""
        log = ActionLogDisplay(
            character_id=character_id,
            character_name=character_name,
            action_name=action_name,
            description=description,
            game_time=game_time or self.game_time,
            game_day=game_day or self.game_day
        )
        self.action_logs.insert(0, log)
        
        # 限制日志数量
        if len(self.action_logs) > self.max_action_logs:
            self.action_logs = self.action_logs[:self.max_action_logs]
    
    def update_action_logs(self, logs: List[Dict[str, Any]]):
        """批量更新行动日志"""
        self.action_logs.clear()
        for log_data in logs[:self.max_action_logs]:
            self.action_logs.append(ActionLogDisplay(
                character_id=log_data.get('character_id', 0),
                character_name=log_data.get('character_name', ''),
                action_name=log_data.get('action_name', ''),
                description=log_data.get('description', ''),
                game_time=log_data.get('game_time', ''),
                game_day=log_data.get('game_day', 0)
            ))
    
    def update_character_details(self, character_id: int,
                                  state: str = None,
                                  fatigue: int = None,
                                  current_action: str = None,
                                  daily_plan: List[str] = None,
                                  recent_actions: List[Dict] = None,
                                  memories: List[str] = None):
        """更新角色详细信息"""
        if character_id not in self.characters:
            return
        
        char = self.characters[character_id]
        if state is not None:
            char.state = state
        if fatigue is not None:
            char.fatigue = fatigue
        if current_action is not None:
            char.current_action = current_action
        if daily_plan is not None:
            char.daily_plan = daily_plan
        if recent_actions is not None:
            char.recent_actions = recent_actions
        if memories is not None:
            char.memories = memories
    
    def _generate_character_color(self, character_id: int) -> Tuple[int, int, int]:
        """为角色生成独特的颜色"""
        # 使用简单的哈希算法生成颜色
        hue = (character_id * 137) % 360
        # HSV to RGB (简化版)
        h = hue / 60
        x = int(255 * (1 - abs(h % 2 - 1)))
        
        if h < 1:
            return (255, x, 100)
        elif h < 2:
            return (x, 255, 100)
        elif h < 3:
            return (100, 255, x)
        elif h < 4:
            return (100, x, 255)
        elif h < 5:
            return (x, 100, 255)
        else:
            return (255, 100, x)
    
    def handle_events(self) -> bool:
        """
        处理 Pygame 事件
        
        Returns:
            是否继续运行
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            elif event.type == pygame.VIDEORESIZE:
                self.width = event.w
                self.height = event.h
                self.camera.screen_width = event.w
                self.camera.screen_height = event.h
                self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键
                    self._handle_click(event.pos)
                elif event.button == 2:  # 中键
                    self.camera.start_drag(event.pos[0], event.pos[1])
                elif event.button == 4:  # 滚轮上
                    self.camera.zoom_in(1.15, event.pos[0], event.pos[1])
                elif event.button == 5:  # 滚轮下
                    self.camera.zoom_out(1.15, event.pos[0], event.pos[1])
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2:
                    self.camera.end_drag()
            
            elif event.type == pygame.MOUSEMOTION:
                if self.camera.dragging:
                    self.camera.update_drag(event.pos[0], event.pos[1])
                self._update_hover(event.pos)
            
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key)
        
        return True
    
    def _handle_click(self, pos: Tuple[int, int]):
        """处理点击事件"""
        world_x, world_y = self.camera.screen_to_world(pos[0], pos[1])
        
        # 检查是否点击了角色
        for char_id, char in self.characters.items():
            distance = math.sqrt((char.x - world_x) ** 2 + (char.y - world_y) ** 2)
            if distance < 8:  # 点击半径
                if self.selected_character_id == char_id:
                    # 再次点击同一角色，切换详情面板
                    self.show_detail_panel = not self.show_detail_panel
                else:
                    self.selected_character_id = char_id
                    self.show_detail_panel = True
                return
        
        # 点击空白处取消选择
        self.selected_character_id = None
        self.show_detail_panel = False
    
    def _update_hover(self, pos: Tuple[int, int]):
        """更新悬停状态"""
        world_x, world_y = self.camera.screen_to_world(pos[0], pos[1])
        
        # 检查是否悬停在地点上
        self.hovered_location_id = None
        for loc_id, loc in self.locations.items():
            if (loc.x <= world_x <= loc.x + loc.width and
                loc.y <= world_y <= loc.y + loc.height):
                self.hovered_location_id = loc_id
                break
    
    def _handle_keydown(self, key: int):
        """处理按键事件"""
        if key == pygame.K_g:
            self.show_grid = not self.show_grid
        elif key == pygame.K_l:
            self.show_labels = not self.show_labels
        elif key == pygame.K_d:
            self.show_debug = not self.show_debug
        elif key == pygame.K_i:
            # 切换详情面板
            if self.selected_character_id is not None:
                self.show_detail_panel = not self.show_detail_panel
        elif key == pygame.K_r:
            # 重置视图
            center_x = (self.world_bounds['min_x'] + self.world_bounds['max_x']) / 2
            center_y = (self.world_bounds['min_y'] + self.world_bounds['max_y']) / 2
            self.camera.zoom = 1.0
            self.camera.center_on(center_x, center_y)
        elif key == pygame.K_ESCAPE:
            self.selected_character_id = None
            self.show_detail_panel = False
    
    def render(self, dt: float = 0.016):
        """
        渲染一帧
        
        Args:
            dt: 时间增量（秒）
        """
        if not self._initialized:
            return
        
        # 清屏
        self.screen.fill(Colors.UI_BACKGROUND)
        
        # 渲染网格
        if self.show_grid:
            self._render_grid()
        
        # 渲染地点
        self._render_locations()
        
        # 渲染角色
        self._render_characters(dt)
        
        # 渲染 UI
        self._render_ui()
        
        # 更新显示
        pygame.display.flip()
    
    def _render_grid(self):
        """渲染网格"""
        min_x, min_y, max_x, max_y = self.camera.get_visible_bounds()
        
        # 根据缩放级别确定网格间距
        base_spacing = 50
        if self.camera.zoom < 0.5:
            spacing = base_spacing * 2
        elif self.camera.zoom > 2:
            spacing = base_spacing / 2
        else:
            spacing = base_spacing
        
        # 绘制垂直线
        start_x = int(min_x / spacing) * spacing
        x = start_x
        while x < max_x:
            screen_x, _ = self.camera.world_to_screen(x, 0)
            pygame.draw.line(self.screen, Colors.GRID_LINE,
                           (screen_x, 0), (screen_x, self.height))
            x += spacing
        
        # 绘制水平线
        start_y = int(min_y / spacing) * spacing
        y = start_y
        while y < max_y:
            _, screen_y = self.camera.world_to_screen(0, y)
            pygame.draw.line(self.screen, Colors.GRID_LINE,
                           (0, screen_y), (self.width, screen_y))
            y += spacing
    
    def _render_locations(self):
        """渲染地点"""
        for loc in self.locations.values():
            # 检查是否在视野内
            if not self.camera.is_visible(loc.x, loc.y, loc.width, loc.height):
                continue
            
            # 转换坐标
            screen_x, screen_y = self.camera.world_to_screen(loc.x, loc.y)
            screen_w = int(loc.width * self.camera.zoom)
            screen_h = int(loc.height * self.camera.zoom)
            
            # 获取颜色
            color = Colors.LOCATION_COLORS.get(loc.location_type, Colors.GRAY)
            
            # 悬停高亮
            if loc.location_id == self.hovered_location_id:
                color = tuple(min(255, c + 40) for c in color)
            
            # 绘制地点矩形
            rect = pygame.Rect(screen_x, screen_y, screen_w, screen_h)
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, Colors.DARK_GRAY, rect, 2)
            
            # 绘制标签
            if self.show_labels and self.camera.zoom > 0.4:
                label = self.font.render(loc.name, True, Colors.WHITE)
                label_rect = label.get_rect(center=(screen_x + screen_w // 2,
                                                   screen_y + screen_h // 2))
                
                # 背景
                bg_rect = label_rect.inflate(6, 4)
                pygame.draw.rect(self.screen, (0, 0, 0, 128), bg_rect)
                self.screen.blit(label, label_rect)
                
                # 显示占用人数
                if loc.occupants:
                    count_text = self.small_font.render(f"({len(loc.occupants)})", True, Colors.LIGHT_GRAY)
                    count_rect = count_text.get_rect(midtop=(label_rect.centerx, label_rect.bottom + 2))
                    self.screen.blit(count_text, count_rect)
    
    def _render_characters(self, dt: float):
        """渲染角色"""
        for char in self.characters.values():
            # 检查是否在视野内
            if not self.camera.is_visible(char.x - 10, char.y - 10, 20, 20):
                continue
            
            # 更新动画
            char.animation_timer += dt
            if char.animation_timer > 0.2:
                char.animation_timer = 0
                char.animation_frame = (char.animation_frame + 1) % 4
            
            # 转换坐标
            screen_x, screen_y = self.camera.world_to_screen(char.x, char.y)
            
            # 确定颜色
            if char.character_id == self.selected_character_id:
                color = Colors.CHARACTER_SELECTED
                border_color = Colors.WHITE
            elif char.is_moving:
                color = Colors.CHARACTER_MOVING
                border_color = Colors.CHARACTER_BORDER
            else:
                color = char.color
                border_color = Colors.CHARACTER_BORDER
            
            # 绘制角色圆圈
            radius = int(6 * self.camera.zoom)
            radius = max(3, min(15, radius))
            
            pygame.draw.circle(self.screen, color, (screen_x, screen_y), radius)
            pygame.draw.circle(self.screen, border_color, (screen_x, screen_y), radius, 2)
            
            # 绘制移动目标线
            if char.is_moving and char.target_x is not None:
                target_sx, target_sy = self.camera.world_to_screen(char.target_x, char.target_y)
                pygame.draw.line(self.screen, Colors.CHARACTER_MOVING,
                               (screen_x, screen_y), (target_sx, target_sy), 1)
                # 目标点
                pygame.draw.circle(self.screen, Colors.CHARACTER_MOVING,
                                 (target_sx, target_sy), 3)
            
            # 绘制名称
            if self.show_labels and self.camera.zoom > 0.6:
                name_label = self.small_font.render(char.name, True, Colors.WHITE)
                name_rect = name_label.get_rect(midbottom=(screen_x, screen_y - radius - 2))
                
                # 背景
                bg_rect = name_rect.inflate(4, 2)
                s = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
                s.fill((0, 0, 0, 160))
                self.screen.blit(s, bg_rect)
                self.screen.blit(name_label, name_rect)
    
    def _render_ui(self):
        """渲染 UI 面板"""
        # 左上角 - 世界状态
        self._render_world_status_panel()
        
        # 右上角 - 控制说明
        self._render_controls_panel()
        
        # 右下角 - 行动日志
        self._render_action_log_panel()
        
        # 左下角 - 选中角色信息 / 详情面板
        if self.selected_character_id is not None:
            if self.show_detail_panel:
                self._render_character_detail_panel()
            else:
                self._render_character_info_panel()
        
        # 悬停地点信息
        if self.hovered_location_id is not None:
            self._render_location_tooltip()
        
        # 调试信息
        if self.show_debug:
            self._render_debug_info()
    
    def _render_world_status_panel(self):
        """渲染世界状态面板"""
        padding = 10
        line_height = 20
        
        lines = [
            f"第 {self.game_day} 天  {self.game_time}",
            f"季节: {self._translate_season(self.season)}",
            f"天气: {self._translate_weather(self.weather)}",
            f"角色: {len(self.characters)} 个",
        ]
        
        # 计算面板大小
        max_width = max(self.font.size(line)[0] for line in lines)
        panel_width = max_width + padding * 2
        panel_height = len(lines) * line_height + padding * 2
        
        # 绘制背景
        panel_rect = pygame.Rect(10, 10, panel_width, panel_height)
        s = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        s.fill((30, 30, 40, 200))
        self.screen.blit(s, panel_rect)
        pygame.draw.rect(self.screen, Colors.DARK_GRAY, panel_rect, 1)
        
        # 绘制文本
        y = 10 + padding
        for line in lines:
            text = self.font.render(line, True, Colors.UI_TEXT)
            self.screen.blit(text, (10 + padding, y))
            y += line_height
    
    def _render_controls_panel(self):
        """渲染控制说明面板"""
        padding = 8
        line_height = 16
        
        lines = [
            "鼠标中键: 拖拽地图",
            "滚轮: 缩放",
            "G: 网格  L: 标签",
            "R: 重置  D: 调试",
            "I: 角色详情",
        ]
        
        max_width = max(self.small_font.size(line)[0] for line in lines)
        panel_width = max_width + padding * 2
        panel_height = len(lines) * line_height + padding * 2
        
        panel_x = self.width - panel_width - 10
        panel_rect = pygame.Rect(panel_x, 10, panel_width, panel_height)
        
        s = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        s.fill((30, 30, 40, 180))
        self.screen.blit(s, panel_rect)
        
        y = 10 + padding
        for line in lines:
            text = self.small_font.render(line, True, Colors.LIGHT_GRAY)
            self.screen.blit(text, (panel_x + padding, y))
            y += line_height
    
    def _render_character_info_panel(self):
        """渲染选中角色信息面板"""
        char = self.characters.get(self.selected_character_id)
        if not char:
            return
        
        padding = 10
        line_height = 18
        
        lines = [
            f"角色: {char.name}",
            f"位置: ({char.x:.1f}, {char.y:.1f})",
        ]
        
        if char.is_moving and char.target_x is not None:
            lines.append(f"目标: ({char.target_x:.1f}, {char.target_y:.1f})")
            lines.append("状态: 移动中")
        else:
            lines.append("状态: 静止")
        
        max_width = max(self.font.size(line)[0] for line in lines)
        panel_width = max_width + padding * 2
        panel_height = len(lines) * line_height + padding * 2
        
        panel_y = self.height - panel_height - 10
        panel_rect = pygame.Rect(10, panel_y, panel_width, panel_height)
        
        s = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        s.fill((30, 30, 40, 200))
        self.screen.blit(s, panel_rect)
        pygame.draw.rect(self.screen, Colors.CHARACTER_SELECTED, panel_rect, 2)
        
        y = panel_y + padding
        for line in lines:
            text = self.font.render(line, True, Colors.UI_TEXT)
            self.screen.blit(text, (10 + padding, y))
            y += line_height
    
    def _render_location_tooltip(self):
        """渲染地点悬停提示"""
        loc = self.locations.get(self.hovered_location_id)
        if not loc:
            return
        
        mouse_pos = pygame.mouse.get_pos()
        
        lines = [
            loc.name,
            f"类型: {self._translate_location_type(loc.location_type)}",
            f"人数: {len(loc.occupants)}",
        ]
        
        padding = 6
        line_height = 16
        max_width = max(self.font.size(line)[0] for line in lines)
        
        tooltip_width = max_width + padding * 2
        tooltip_height = len(lines) * line_height + padding * 2
        
        # 确保不超出屏幕
        tooltip_x = min(mouse_pos[0] + 15, self.width - tooltip_width - 5)
        tooltip_y = min(mouse_pos[1] + 15, self.height - tooltip_height - 5)
        
        tooltip_rect = pygame.Rect(tooltip_x, tooltip_y, tooltip_width, tooltip_height)
        
        s = pygame.Surface((tooltip_width, tooltip_height), pygame.SRCALPHA)
        s.fill((50, 50, 60, 230))
        self.screen.blit(s, tooltip_rect)
        pygame.draw.rect(self.screen, Colors.LIGHT_GRAY, tooltip_rect, 1)
        
        y = tooltip_y + padding
        for i, line in enumerate(lines):
            color = Colors.WHITE if i == 0 else Colors.LIGHT_GRAY
            text = self.font.render(line, True, color)
            self.screen.blit(text, (tooltip_x + padding, y))
            y += line_height
    
    def _render_debug_info(self):
        """渲染调试信息"""
        lines = [
            f"FPS: {self.clock.get_fps():.1f}",
            f"Zoom: {self.camera.zoom:.2f}",
            f"Camera: ({self.camera.x:.1f}, {self.camera.y:.1f})",
            f"Locations: {len(self.locations)}",
            f"Characters: {len(self.characters)}",
        ]
        
        y = self.height - 10 - len(lines) * 14
        for line in lines:
            text = self.small_font.render(line, True, Colors.LIGHT_GRAY)
            self.screen.blit(text, (self.width - text.get_width() - 10, y))
            y += 14
    
    def _render_action_log_panel(self):
        """渲染行动日志面板（右下角）"""
        if not self.action_logs:
            return
        
        padding = 8
        line_height = 16
        max_lines = min(len(self.action_logs), 8)
        
        # 准备显示的行
        lines = []
        for log in self.action_logs[:max_lines]:
            time_str = f"[{log.game_time}]" if log.game_time else ""
            text = f"{time_str} {log.character_name}: {log.action_name}"
            if log.description:
                text += f" - {log.description[:30]}"
                if len(log.description) > 30:
                    text += "..."
            lines.append(text)
        
        if not lines:
            return
        
        # 计算面板大小
        max_width = max(self.small_font.size(line)[0] for line in lines)
        panel_width = min(max_width + padding * 2, 350)
        panel_height = len(lines) * line_height + padding * 2 + 20  # 20 for title
        
        panel_x = self.width - panel_width - 10
        panel_y = self.height - panel_height - 10
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        
        # 绘制背景
        s = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        s.fill((30, 30, 40, 200))
        self.screen.blit(s, panel_rect)
        pygame.draw.rect(self.screen, Colors.DARK_GRAY, panel_rect, 1)
        
        # 绘制标题
        title = self.font.render("行动日志", True, Colors.UI_HIGHLIGHT)
        self.screen.blit(title, (panel_x + padding, panel_y + padding))
        
        # 绘制日志行
        y = panel_y + padding + 20
        for line in lines:
            # 截断过长的文本
            while self.small_font.size(line)[0] > panel_width - padding * 2:
                line = line[:-4] + "..."
            text = self.small_font.render(line, True, Colors.LIGHT_GRAY)
            self.screen.blit(text, (panel_x + padding, y))
            y += line_height
    
    def _render_character_detail_panel(self):
        """渲染角色详情面板（左侧大面板）"""
        char = self.characters.get(self.selected_character_id)
        if not char:
            return
        
        padding = 12
        line_height = 18
        section_gap = 10
        
        # 面板尺寸
        panel_width = 320
        panel_height = min(self.height - 40, 500)
        panel_x = 10
        panel_y = 120  # 在世界状态面板下方
        
        # 绘制背景
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        s = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        s.fill((25, 25, 35, 230))
        self.screen.blit(s, panel_rect)
        pygame.draw.rect(self.screen, Colors.CHARACTER_SELECTED, panel_rect, 2)
        
        y = panel_y + padding
        
        # === 角色名称 ===
        title = self.large_font.render(f"{char.name} 详情", True, Colors.CHARACTER_SELECTED)
        self.screen.blit(title, (panel_x + padding, y))
        y += 28
        
        # === 基本状态 ===
        self._draw_section_title("基本状态", panel_x + padding, y)
        y += 20
        
        state_text = self._translate_state(char.state)
        info_lines = [
            f"状态: {state_text}",
            f"位置: ({char.x:.1f}, {char.y:.1f})",
            f"疲劳: {char.fatigue}%",
        ]
        if char.current_action:
            info_lines.append(f"当前: {char.current_action}")
        
        for line in info_lines:
            text = self.small_font.render(line, True, Colors.UI_TEXT)
            self.screen.blit(text, (panel_x + padding + 8, y))
            y += line_height
        
        y += section_gap
        
        # === 今日计划 ===
        if char.daily_plan:
            self._draw_section_title("今日计划", panel_x + padding, y)
            y += 20
            
            for i, plan in enumerate(char.daily_plan[:5]):
                plan_text = f"{i+1}. {plan[:35]}"
                if len(plan) > 35:
                    plan_text += "..."
                text = self.small_font.render(plan_text, True, Colors.LIGHT_GRAY)
                self.screen.blit(text, (panel_x + padding + 8, y))
                y += line_height
            
            y += section_gap
        
        # === 最近行动 ===
        if char.recent_actions:
            self._draw_section_title("最近行动", panel_x + padding, y)
            y += 20
            
            for action in char.recent_actions[:5]:
                time_str = action.get('game_time', '')
                name = action.get('action_name', '')
                desc = action.get('description', '')[:25]
                action_text = f"[{time_str}] {name}"
                if desc:
                    action_text += f": {desc}"
                
                text = self.small_font.render(action_text, True, Colors.LIGHT_GRAY)
                self.screen.blit(text, (panel_x + padding + 8, y))
                y += line_height
            
            y += section_gap
        
        # === 重要记忆 ===
        if char.memories:
            self._draw_section_title("重要记忆", panel_x + padding, y)
            y += 20
            
            for memory in char.memories[:4]:
                mem_text = f"- {memory[:40]}"
                if len(memory) > 40:
                    mem_text += "..."
                text = self.small_font.render(mem_text, True, Colors.LIGHT_GRAY)
                self.screen.blit(text, (panel_x + padding + 8, y))
                y += line_height
        
        # === 底部提示 ===
        hint = self.small_font.render("按 I 或点击其他地方关闭", True, Colors.GRAY)
        self.screen.blit(hint, (panel_x + padding, panel_y + panel_height - 20))
    
    def _draw_section_title(self, title: str, x: int, y: int):
        """绘制分区标题"""
        text = self.font.render(f"[{title}]", True, Colors.UI_HIGHLIGHT)
        self.screen.blit(text, (x, y))
    
    def _translate_state(self, state: str) -> str:
        """翻译角色状态"""
        translations = {
            'idle': '空闲',
            'thinking': '思考中',
            'acting': '行动中',
            'talking': '交谈中',
            'sleeping': '睡眠中',
            'waiting': '等待中',
            'moving': '移动中',
        }
        return translations.get(state, state)
    
    def _translate_season(self, season: str) -> str:
        """翻译季节"""
        translations = {
            'spring': '春季', 'summer': '夏季',
            'autumn': '秋季', 'winter': '冬季'
        }
        return translations.get(season, season)
    
    def _translate_weather(self, weather: str) -> str:
        """翻译天气"""
        translations = {
            'sunny': '晴天', 'cloudy': '多云',
            'rainy': '下雨', 'stormy': '暴风雨',
            'snowy': '下雪', 'foggy': '大雾'
        }
        return translations.get(weather, weather)
    
    def _translate_location_type(self, loc_type: str) -> str:
        """翻译地点类型"""
        translations = {
            'public': '公共场所', 'commercial': '商业区',
            'residential': '住宅区', 'workplace': '工作场所',
            'medical': '医疗设施', 'government': '政府机构',
            'education': '教育机构', 'recreation': '休闲场所'
        }
        return translations.get(loc_type, loc_type)
    
    def run_standalone(self, fps: int = 60):
        """
        独立运行模式（用于测试）
        
        Args:
            fps: 目标帧率
        """
        self.initialize()
        self.running = True
        
        print("可视化器启动 - 按 ESC 或关闭窗口退出")
        
        while self.running:
            dt = self.clock.tick(fps) / 1000.0
            
            if not self.handle_events():
                self.running = False
                break
            
            self.render(dt)
        
        self.shutdown()

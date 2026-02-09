"""
相机模块

处理视图平移、缩放等操作
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class Camera:
    """
    2D 相机
    
    管理世界坐标到屏幕坐标的转换
    """
    
    # 相机在世界中的位置（左上角）
    x: float = 0.0
    y: float = 0.0
    
    # 缩放级别
    zoom: float = 1.0
    
    # 屏幕尺寸
    screen_width: int = 1280
    screen_height: int = 720
    
    # 缩放限制
    min_zoom: float = 0.2
    max_zoom: float = 3.0
    
    # 拖拽状态
    dragging: bool = False
    drag_start_x: int = 0
    drag_start_y: int = 0
    drag_camera_start_x: float = 0.0
    drag_camera_start_y: float = 0.0
    
    def world_to_screen(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """将世界坐标转换为屏幕坐标"""
        screen_x = int((world_x - self.x) * self.zoom)
        screen_y = int((world_y - self.y) * self.zoom)
        return screen_x, screen_y
    
    def screen_to_world(self, screen_x: int, screen_y: int) -> Tuple[float, float]:
        """将屏幕坐标转换为世界坐标"""
        world_x = screen_x / self.zoom + self.x
        world_y = screen_y / self.zoom + self.y
        return world_x, world_y
    
    def move(self, dx: float, dy: float):
        """移动相机"""
        self.x += dx / self.zoom
        self.y += dy / self.zoom
    
    def set_zoom(self, new_zoom: float, center_x: int = None, center_y: int = None):
        """
        设置缩放级别
        
        Args:
            new_zoom: 新的缩放级别
            center_x: 缩放中心的屏幕X坐标（默认为屏幕中心）
            center_y: 缩放中心的屏幕Y坐标（默认为屏幕中心）
        """
        new_zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))
        
        if center_x is None:
            center_x = self.screen_width // 2
        if center_y is None:
            center_y = self.screen_height // 2
        
        # 获取缩放中心的世界坐标
        world_center_x, world_center_y = self.screen_to_world(center_x, center_y)
        
        # 更新缩放
        self.zoom = new_zoom
        
        # 调整相机位置，使缩放中心保持不变
        self.x = world_center_x - center_x / self.zoom
        self.y = world_center_y - center_y / self.zoom
    
    def zoom_in(self, factor: float = 1.2, center_x: int = None, center_y: int = None):
        """放大"""
        self.set_zoom(self.zoom * factor, center_x, center_y)
    
    def zoom_out(self, factor: float = 1.2, center_x: int = None, center_y: int = None):
        """缩小"""
        self.set_zoom(self.zoom / factor, center_x, center_y)
    
    def center_on(self, world_x: float, world_y: float):
        """将相机中心对准指定的世界坐标"""
        self.x = world_x - (self.screen_width / 2) / self.zoom
        self.y = world_y - (self.screen_height / 2) / self.zoom
    
    def start_drag(self, screen_x: int, screen_y: int):
        """开始拖拽"""
        self.dragging = True
        self.drag_start_x = screen_x
        self.drag_start_y = screen_y
        self.drag_camera_start_x = self.x
        self.drag_camera_start_y = self.y
    
    def update_drag(self, screen_x: int, screen_y: int):
        """更新拖拽"""
        if self.dragging:
            dx = self.drag_start_x - screen_x
            dy = self.drag_start_y - screen_y
            self.x = self.drag_camera_start_x + dx / self.zoom
            self.y = self.drag_camera_start_y + dy / self.zoom
    
    def end_drag(self):
        """结束拖拽"""
        self.dragging = False
    
    def get_visible_bounds(self) -> Tuple[float, float, float, float]:
        """
        获取当前可见的世界坐标范围
        
        Returns:
            (min_x, min_y, max_x, max_y)
        """
        min_x = self.x
        min_y = self.y
        max_x = self.x + self.screen_width / self.zoom
        max_y = self.y + self.screen_height / self.zoom
        return min_x, min_y, max_x, max_y
    
    def is_visible(self, world_x: float, world_y: float, 
                   width: float = 0, height: float = 0) -> bool:
        """检查指定的世界坐标区域是否在视野内"""
        min_x, min_y, max_x, max_y = self.get_visible_bounds()
        
        # 检查矩形是否与视野相交
        return not (world_x + width < min_x or 
                    world_x > max_x or
                    world_y + height < min_y or 
                    world_y > max_y)

# entities.py

import random
from collections import deque 
import pygame
from config import *

class Tile:
    """迷宫中的单个瓦片单元"""
    def __init__(self, tile_type=PATH):
        self.type = tile_type
        self.is_visible = True

class Boss:
    """游戏中的首领敌人实体"""
    def __init__(self):
        self.health = 0 
    
    def reset(self):
        self.health = 0

class AIPlayer:
    """由 AI 算法控制的玩家角色"""
    def __init__(self, start_pos=(1,1)):
        self.x, self.y = start_pos
        self.color = (10, 10, 10)
        
        self.health = 100
        self.max_health = 100
        self.gold = 20
        self.skills = []
        
        # --- 用于DP计分体系的属性 ---
        self.resource_value = 0
        
        # --- 用于贪心算法结果记录的属性 ---
        self.greedy_score = 0
        self.greedy_path = [start_pos] # 初始化时记录起点
        
        # --- 寻路相关属性 ---
        self.start_pos = start_pos
        self.boss_defeated = False
        self.is_active = True
        self.path_to_follow = []
        self.temporary_target = None
        self.path_history = deque(maxlen=5)
        self.needs_new_target = True

    def decide_move(self, maze, algorithm):
        # 导入贪心算法的决策函数
        from algorithms.greedy import decide_move_greedy
        if not self.is_active: return (0, 0)

        if algorithm == ALGO_DP_VISUALIZATION:
            if not self.path_to_follow: return (0, 0)
            if (self.x, self.y) == self.path_to_follow[0]: self.path_to_follow.pop(0)
            if not self.path_to_follow: return (0, 0)
            next_pos = self.path_to_follow[0]
            return (next_pos[0] - self.x, next_pos[1] - self.y)
        elif algorithm == ALGO_GREEDY:
            # 调用贪心决策函数
            return decide_move_greedy(self, maze)
        return (0, 0)
        
    def update(self, maze, sound_manager, algorithm):
        if not self.is_active: return None
        dx, dy = self.decide_move(maze, algorithm)
        if self.move(dx, dy, maze):
            # 移动成功后，与地块交互
            return self.interact_with_tile(maze, sound_manager)
        return None

    def move(self, dx, dy, maze):
        next_x, next_y = self.x + dx, self.y + dy
        if 0 <= next_x < maze.size and 0 <= next_y < maze.size and maze.grid[next_y][next_x].type != WALL:
            self.x, self.y = next_x, next_y
            self.path_history.append((self.x, self.y))
            # 记录贪心算法的完整路径
            self.greedy_path.append((self.x, self.y))
            return True
        return False

    def interact_with_tile(self, maze, sound_manager):
        tile = maze.grid[self.y][self.x]
        
        if (self.x, self.y) == self.temporary_target:
            self.temporary_target = None
            self.needs_new_target = True

        # 返回地块类型用于计分
        interacted_tile_type = tile.type

        if tile.type == GOLD:
            sound_manager.play('coin')
            tile.type = PATH
            self.needs_new_target = True
            return interacted_tile_type
        elif tile.type == TRAP:
            sound_manager.play('trap')
            tile.type = PATH
            return interacted_tile_type
        elif tile.type == LOCKER:
            return 'start_puzzle'
        elif tile.type == BOSS and not self.boss_defeated:
             return 'start_battle'
        elif tile.type == END:
            return interacted_tile_type
            
        return None

    def draw(self, screen, cell_width, cell_height):
        """在屏幕上绘制AI玩家。"""
        # 计算玩家在屏幕上的中心坐标
        center_x = int((self.x + 0.5) * cell_width)
        center_y = int((self.y + 0.5) * cell_height)
        # 根据单元格大小计算玩家的半径
        radius = int(min(cell_width, cell_height) * 0.4)
        # 绘制一个圆形代表玩家
        pygame.draw.circle(screen, self.color, (center_x, center_y), radius)

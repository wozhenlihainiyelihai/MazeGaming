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
        # Boss的HP现在完全由 battle_config.json 决定
        # health 属性在战斗开始时会被动态赋值为一个列表
        self.health = 0 
    
    def reset(self):
        self.health = 0

class AIPlayer:
    """由 AI 算法控制的玩家角色"""
    def __init__(self, start_pos=(1,1)):
        self.x, self.y = start_pos
        self.color = (10, 10, 10)
        
        # health 仅用于旧的迷宫探索过程中的陷阱交互，与Boss战无关
        self.health = 100
        self.max_health = 100
        self.gold = 20
        
        # 技能列表在战斗开始时被动态赋值
        self.skills = []
        
        # --- 新增属性，以满足验收要求 ---
        self.resource_value = 0  # 用于记录和扣减的总资源值
        
        # --- 寻路相关属性 ---
        self.start_pos = start_pos
        self.boss_defeated = False
        self.is_active = True
        self.path_to_follow = []
        self.temporary_target = None
        self.path_history = deque(maxlen=5)
        self.needs_new_target = True

    def decide_move(self, maze, algorithm):
        from algorithms.greedy import decide_move_greedy as simple_greedy_move
        if not self.is_active: return (0, 0)

        if algorithm == ALGO_DP_VISUALIZATION:
            if not self.path_to_follow: return (0, 0)
            if (self.x, self.y) == self.path_to_follow[0]: self.path_to_follow.pop(0)
            if not self.path_to_follow: return (0, 0)
            next_pos = self.path_to_follow[0]
            return (next_pos[0] - self.x, next_pos[1] - self.y)
        elif algorithm == ALGO_GREEDY:
            return simple_greedy_move(self, maze)
        return (0, 0)
        
    def update(self, maze, sound_manager, algorithm):
        if not self.is_active: return None
        dx, dy = self.decide_move(maze, algorithm)
        if self.move(dx, dy, maze):
            return self.interact_with_tile(maze, sound_manager)
        return None

    def move(self, dx, dy, maze):
        next_x, next_y = self.x + dx, self.y + dy
        if 0 <= next_x < maze.size and 0 <= next_y < maze.size and maze.grid[next_y][next_x].type != WALL:
            self.x, self.y = next_x, next_y
            self.path_history.append((self.x, self.y))
            return True
        return False

    def interact_with_tile(self, maze, sound_manager):
        tile = maze.grid[self.y][self.x]
        
        if (self.x, self.y) == self.temporary_target:
            self.temporary_target = None
            self.needs_new_target = True

        # 简化交互逻辑
        if tile.type == GOLD:
            # Gold现在只作为路径上的一个点，不直接增加资源值
            sound_manager.play('coin')
            tile.type = PATH
            self.needs_new_target = True
        elif tile.type == TRAP:
            sound_manager.play('trap')
            tile.type = PATH
        elif tile.type == LOCKER:
            return 'start_puzzle'
        elif tile.type == BOSS and not self.boss_defeated:
             return 'start_battle'
        elif tile.type == END:
            # --- 新增：输出最终结果，满足验收要求(4) ---
            print("\n=============================")
            print("       游戏流程结束      ")
            print(f"  最终剩余资源值: {self.resource_value}")
            print("=============================\n")
            self.is_active = False
            
        return None

    def draw(self, screen, cell_width, cell_height):
        center_x = int((self.x + 0.5) * cell_width)
        center_y = int((self.y + 0.5) * cell_height)
        radius = int(min(cell_width, cell_height) * 0.4)
        pygame.draw.circle(screen, self.color, (center_x, center_y), radius)

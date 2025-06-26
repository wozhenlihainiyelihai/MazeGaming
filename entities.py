# entities.py (重构版)

import random
from collections import deque 
import pygame
from config import *

# 【删除】不再从此文件导入任何算法相关的函数

class Tile:
    def __init__(self, tile_type=PATH):
        self.type = tile_type
        self.is_visible = True

class Boss:
    def __init__(self):
        self.max_health = BOSS_MAX_HEALTH
        self.health = self.max_health
        self.attack = BOSS_ATTACK
        self.is_frozen_for = 0
    def reset(self):
        self.health = self.max_health
        self.is_frozen_for = 0

class AIPlayer:
    def __init__(self, start_pos=(1,1)):
        self.x, self.y = start_pos
        self.color = (10, 10, 10)
        self.max_health = 100
        self.health = 100
        self.gold = 20
        self.attack = PLAYER_BASE_ATTACK
        self.diamonds = 0
        self.skills = set()
        self.skill_cooldowns = {}
        self.start_pos = start_pos
        self.boss_defeated = False
        self.is_active = True
        self.path_to_follow = []
        self.temporary_target = None
        self.attack_boost_this_turn = 0
        self.path_history = deque(maxlen=5)
        # 状态旗帜，为True时表示AI需要一个新的全局目标
        self.needs_new_target = True

    def decide_move(self, maze, algorithm):
        from algorithms.greedy import decide_move_greedy as simple_greedy_move
        if not self.is_active: return (0, 0)

        if algorithm == ALGO_DP_VISUALIZATION:
            # 如果路径为空，不动
            if not self.path_to_follow:
                return (0, 0)

            # 如果AI当前位置就是路径的下一个点（例如，刚开始或重置后），则弹出该点，目标设为路径中的下一个点
            if (self.x, self.y) == self.path_to_follow[0]:
                self.path_to_follow.pop(0)
            
            # 如果弹出后路径为空（说明已经走完），则不动
            if not self.path_to_follow:
                return (0, 0)

            # 计算走向路径中下一个点的方向
            next_pos = self.path_to_follow[0]
            dx = next_pos[0] - self.x
            dy = next_pos[1] - self.y
            return (dx, dy)

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
        if 0 <= next_x < maze.size and 0 <= next_y < maze.size:
             if maze.grid[next_y][next_x].type != WALL:
                self.x = next_x
                self.y = next_y
                self.path_history.append((self.x, self.y))
                return True
        return False

    def interact_with_tile(self, maze, sound_manager):
        """【修改】交互后只设置状态旗帜，不再执行扫描逻辑"""
        tile = maze.grid[self.y][self.x]
        
        # 到达临时目标后，也需要一个新的目标
        if (self.x, self.y) == self.temporary_target:
            self.temporary_target = None
            self.needs_new_target = True

        if tile.type == SHOP:
            for skill_id, skill_data in SKILLS.items():
                if skill_id not in self.skills and self.diamonds >= skill_data['cost']:
                    self.diamonds -= skill_data['cost']; self.skills.add(skill_id)
                    tile.type = PATH
                    self.needs_new_target = True
                    break
        elif tile.type == GOLD:
            self.gold += GOLD_REWARD; sound_manager.play('coin'); tile.type = PATH
            self.needs_new_target = True
        elif tile.type == HEALTH_POTION:
            self.health = min(100, self.health + POTION_HEAL_AMOUNT); sound_manager.play('potion'); tile.type = PATH
            self.needs_new_target = True
        elif tile.type == TRAP:
            sound_manager.play('trap'); tile.type = PATH
            if self.gold >= TRAP_GOLD_COST: self.gold -= TRAP_GOLD_COST
            else: self.health -= TRAP_HEALTH_COST
        elif tile.type == LOCKER:
            if self.gold >= LOCKER_COST:
                self.gold -= LOCKER_COST; self.diamonds += 1; tile.type = PATH
                self.needs_new_target = True
            else:
                tile.type = WALL
        elif tile.type == BOSS and not self.boss_defeated:
             return 'start_battle'
        elif tile.type == END:
            self.is_active = False
            
        return None
    
    def draw(self, screen, cell_width, cell_height):
        center_x = int((self.x + 0.5) * cell_width)
        center_y = int((self.y + 0.5) * cell_height)
        radius = int(min(cell_width, cell_height) * 0.4)
        pygame.draw.circle(screen, self.color, (center_x, center_y), radius)
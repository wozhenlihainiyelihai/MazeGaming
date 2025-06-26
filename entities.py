# entities.py
# 包含游戏中所有“实体”或“对象”的定义，如地图格子(Tile)和AI玩家(AIPlayer)。

import random
from collections import deque 

import pygame
from config import *
from utils import bfs_path
from algorithms.greedy import decide_move_greedy as simple_greedy_move


class Tile:
    """地图格子对象类"""
    def __init__(self, tile_type=PATH):
        self.type = tile_type
        self.is_visible = True

class Boss:
    """Boss实体类"""
    def __init__(self):
        self.max_health = BOSS_MAX_HEALTH
        self.health = self.max_health
        self.attack = BOSS_ATTACK
        self.is_frozen_for = 0 # Boss被冻结的回合数

    def reset(self):
        self.health = self.max_health
        self.is_frozen_for = 0

class AIPlayer:
    """【最终版】AI角色类 (贪心算法 + 开锁后临时目标策略)"""
    def __init__(self, start_pos=(1,1)):
        # 基础属性
        self.x, self.y = start_pos
        self.color = (10, 10, 10)
        self.max_health = 100
        self.health = 100
        self.gold = 20
        self.attack = PLAYER_BASE_ATTACK
        self.diamonds = 0
        
        # 技能系统
        self.skills = set()
        self.skill_cooldowns = {}
        
        # 记录初始位置和Boss战状态
        self.start_pos = start_pos
        self.boss_defeated = False

        # 状态
        self.is_active = True
        self.path_to_follow = []
        self.temporary_target = None
        self.attack_boost_this_turn = 0
        
        # 短期记忆，用于存储上一个位置
        self.previous_pos = None

    def decide_move(self, maze, algorithm):
        """决策逻辑现在会根据算法类型调用正确的函数"""
        if not self.is_active: return (0, 0)

        # 当算法为贪心时，调用从 greedy.py 导入的简单贪心算法
        if algorithm == ALGO_GREEDY:
            return simple_greedy_move(self, maze)
            
        if algorithm == ALGO_DP_VISUALIZATION:
            if self.path_to_follow and (self.x, self.y) in self.path_to_follow:
                idx = self.path_to_follow.index((self.x, self.y))
                if idx + 1 < len(self.path_to_follow):
                    return (self.path_to_follow[idx+1][0] - self.x, self.path_to_follow[idx+1][1] - self.y)
            self.is_active = False
            
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
                self.previous_pos = (self.x, self.y)
                self.x = next_x
                self.y = next_y
                return True
        return False

    def interact_with_tile(self, maze, sound_manager):
        tile = maze.grid[self.y][self.x]
        
        if tile.type == SHOP:
            for skill_id, skill_data in SKILLS.items():
                if skill_id not in self.skills and self.diamonds >= skill_data['cost']:
                    self.diamonds -= skill_data['cost']; self.skills.add(skill_id)
                    self.skill_cooldowns[skill_id] = 0
                    print(f"AI bought skill: {skill_data['name']}!")
                    tile.type = PATH; break
        elif tile.type == GOLD: self.gold += GOLD_REWARD; sound_manager.play('coin'); tile.type = PATH
        elif tile.type == HEALTH_POTION: self.health = min(100, self.health + POTION_HEAL_AMOUNT); sound_manager.play('potion'); tile.type = PATH
        elif tile.type == TRAP:
            sound_manager.play('trap')
            if self.gold >= TRAP_GOLD_COST: self.gold -= TRAP_GOLD_COST
            else: self.health -= TRAP_HEALTH_COST
            tile.type = PATH
        elif tile.type == LOCKER:
            if self.gold >= LOCKER_COST:
                self.gold -= LOCKER_COST; self.diamonds += 1; tile.type = PATH
                # 开锁成功后，寻找房间内最优的临时目标
                print("开锁成功，正在寻找房间内的最佳目标...")
                room_tiles = self._find_adjacent_room(maze)
                best_target_in_room = self._find_best_target_in_list(room_tiles, maze)
                if best_target_in_room:
                    self.temporary_target = best_target_in_room
                    print(f"设置临时目标为: {self.temporary_target}")
            else:
                tile.type = WALL
        elif tile.type == BOSS and not self.boss_defeated:
             return 'start_battle'
        elif tile.type == END:
            self.is_active = False
        return None

    def _find_adjacent_room(self, maze):
        """从当前位置开始，使用BFS找到整个相连的非主路区域（房间）"""
        room_tiles = set()
        queue = deque([(self.x, self.y)])
        visited = {(self.x, self.y)}
        main_path_set = set(maze._find_main_path())

        while queue:
            cx, cy = queue.popleft()
            # 只有非墙体才可能是房间的一部分
            if maze.grid[cy][cx].type != WALL:
                room_tiles.add((cx, cy))
            
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if (0 <= nx < maze.size and 0 <= ny < maze.size and
                        (nx, ny) not in visited and maze.grid[ny][nx].type != WALL and
                        (nx, ny) not in main_path_set):
                    visited.add((nx, ny))
                    queue.append((nx, ny))
        return list(room_tiles)

    def _find_best_target_in_list(self, tile_list, maze):
        """从一个地块列表中找到价值最高的目标"""
        from algorithms.greedy import get_tile_value # 局部导入避免循环依赖
        best_target = None
        max_value = -1
        for x, y in tile_list:
            value = get_tile_value(maze.grid[y][x].type, self, maze, (x, y))
            if value > max_value:
                max_value = value
                best_target = (x, y)
        return best_target
    
    def draw(self, screen, cell_width, cell_height):
        center_x = int((self.x + 0.5) * cell_width)
        center_y = int((self.y + 0.5) * cell_height)
        radius = int(min(cell_width, cell_height) * 0.4)
        pygame.draw.circle(screen, self.color, (center_x, center_y), radius)
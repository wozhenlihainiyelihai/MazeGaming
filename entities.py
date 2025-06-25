#包含游戏中所有“实体”或“对象”的定义，如地图格子(Tile)和AI玩家(AIPlayer)。

import pygame
from config import *
from algorithms.greedy import decide_move_greedy

class Tile:
    """地图格子对象类"""
    def __init__(self, tile_type=PATH):
        self.type = tile_type
        self.is_visible = True

class AIPlayer:
    """AI角色类"""
    def __init__(self, start_pos=(1,1)):
        self.x, self.y = start_pos
        self.color = (10, 10, 10)
        self.health = 100
        self.gold = 20
        self.path_to_follow = []

    def decide_move(self, maze, algorithm):
        """根据当前设定的算法，决定下一步的移动方向"""
        if algorithm == ALGO_DP_VISUALIZATION:
            if self.path_to_follow:
                if (self.x, self.y) in self.path_to_follow:
                    current_index = self.path_to_follow.index((self.x, self.y))
                    if current_index + 1 < len(self.path_to_follow):
                        next_pos = self.path_to_follow[current_index + 1]
                        return (next_pos[0] - self.x, next_pos[1] - self.y)
            return (0, 0)
        if algorithm == ALGO_GREEDY:
            return decide_move_greedy(self, maze)
        import random
        moves = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        random.shuffle(moves)
        for dx, dy in moves:
            if self.can_move(dx, dy, maze): return (dx, dy)
        return (0, 0)

    def can_move(self, dx, dy, maze):
        next_x, next_y = self.x + dx, self.y + dy
        return maze.grid[next_y][next_x].type != WALL

    def move(self, dx, dy, maze):
        if self.can_move(dx, dy, maze):
            self.x += dx; self.y += dy
            return True
        return False

    def update(self, maze, sound_manager, algorithm):
        dx, dy = self.decide_move(maze, algorithm)
        if self.move(dx, dy, maze):
            self.interact_with_tile(maze, sound_manager)

    def interact_with_tile(self, maze, sound_manager):
        """与当前站立的地块进行互动（已加入陷阱处理）"""
        tile = maze.grid[self.y][self.x]
        
        if tile.type == GOLD:
            self.gold += GOLD_REWARD
            sound_manager.play('coin')
            print(f"AI collected GOLD! Current gold: {self.gold}")
            tile.type = PATH
        elif tile.type == HEALTH_POTION:
            self.health = min(100, self.health + POTION_HEAL_AMOUNT)
            sound_manager.play('potion')
            print(f"AI used a POTION! Current health: {self.health}")
            tile.type = PATH
        elif tile.type == TRAP:
            # 【功能新增】陷阱决策逻辑
            sound_manager.play('trap')
            if self.gold >= TRAP_GOLD_COST:
                self.gold -= TRAP_GOLD_COST
                print(f"AI stepped on a trap! Paid {TRAP_GOLD_COST} gold. Gold left: {self.gold}")
            else:
                self.health -= TRAP_HEALTH_COST
                print(f"AI stepped on a trap! Lost {TRAP_HEALTH_COST} health. Health left: {self.health}")
            tile.type = PATH # 陷阱被消耗
        
    def draw(self, screen, cell_width, cell_height):
        center_x = int((self.x + 0.5) * cell_width)
        center_y = int((self.y + 0.5) * cell_height)
        radius = int(min(cell_width, cell_height) * 0.4)
        pygame.draw.circle(screen, self.color, (center_x, center_y), radius)

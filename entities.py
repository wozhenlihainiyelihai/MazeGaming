# entities.py
# 包含游戏中所有“实体”或“对象”的定义，如地图格子(Tile)和AI玩家(AIPlayer)。

import random
from collections import deque 

import pygame
from config import *
from utils import bfs_path
# 【新增】导入分支限界算法，用于评估威胁
from algorithms.branch_and_bound import get_heuristic_turns


class Tile:
    """地图格子对象类"""
    def __init__(self, tile_type=PATH):
        self.type = tile_type
        self.is_visible = True

class Boss:
    """【新增】Boss实体类"""
    def __init__(self):
        self.max_health = BOSS_MAX_HEALTH
        self.health = self.max_health
        self.attack = BOSS_ATTACK
        self.is_frozen_for = 0 # Boss被冻结的回合数

    def reset(self):
        self.health = self.max_health
        self.is_frozen_for = 0

class AIPlayer:
    """【战略最终版】AI角色类 (完全采用您的逻辑)"""
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

        # 记忆与状态
        self.known_boss_pos = None
        self.objective = 'explore_and_loot' 
        self.target_pos = None              
        self.is_active = True
        
        self.exploration_path = deque() # 使用deque以提高效率
        self.last_move = (0, 0)

        self.path_to_follow = [] 

    def _get_tile_value(self, tile_type):
        """根据规则，为不同地块赋予“贪心”价值"""
        if tile_type == GOLD: return SCORE_PER_GOLD * GOLD_REWARD
        if tile_type == HEALTH_POTION: return (POTION_HEAL_AMOUNT * SCORE_PER_HEALTH) + (100 - self.health)
        if tile_type == LOCKER: return SCORE_LOCKER_UNLOCK + (1 * SCORE_PER_DIAMOND)
        if tile_type == SHOP: return 80
        return 0

    def _assess_boss_threat(self):
        """评估Boss威胁"""
        if not self.known_boss_pos: return True
        # 为了测试方便，暂时调高AI攻击力评估值
        simulated_attack = self.attack * 1.5 
        turns_to_win = (BOSS_MAX_HEALTH / simulated_attack) if simulated_attack > 0 else float('inf')
        damage_taken = turns_to_win * BOSS_ATTACK
        return self.health > damage_taken

    def _find_new_objective(self, maze):
        """【您的逻辑】寻找新的战略目标"""
        potential_targets = []
        for r in range(maze.size):
            for c in range(maze.size):
                tile_type = maze.grid[r][c].type
                value = self._get_tile_value(tile_type)
                if value > 0:
                    path = bfs_path(start=(self.x, self.y), end=(c,r), maze_grid=maze.grid)
                    if path:
                        distance = len(path) - 1
                        if distance > 0:
                            score = value / distance
                            potential_targets.append({'score': score, 'pos': (c,r), 'path': path})

        if potential_targets:
            self.objective = 'explore_and_loot'
            sorted_targets = sorted(potential_targets, key=lambda x: x['score'], reverse=True)
            for target in sorted_targets:
                path_is_safe = not (self.known_boss_pos and self.known_boss_pos in target['path'] and not self._assess_boss_threat())
                if path_is_safe:
                    self.target_pos = target['pos']
                    print(f"Global Objective: Looting. Best safe target is {self.target_pos} with score {target['score']:.2f}")
                    return
            if sorted_targets:
                self.target_pos = sorted_targets[0]['pos']
                print(f"All paths to resources are blocked by Boss. Desperate move to {self.target_pos}.")
                return

        if self.known_boss_pos and not self.boss_defeated:
            self.objective = 'defeat_boss'
            self.target_pos = self.known_boss_pos
            print(f"No resources left. Final objective: Defeat the BOSS at {self.target_pos}")
        else:
            self.objective = 'go_to_end'
            self.target_pos = maze.end_pos
            print(f"Boss defeated or does not exist. Final objective: Go to END at {self.target_pos}")

    def _generate_room_exploration_path(self, maze):
        """【您的逻辑】使用DFS生成一个能走遍房间内所有格子的路径"""
        print("Generating a full exploration path for the dead-end room...")
        path_list = []
        entry_point = (self.x - self.last_move[0], self.y - self.last_move[1])
        visited = {entry_point}
        
        def dfs(x, y):
            visited.add((x, y))
            path_list.append((x, y))
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if (0 <= nx < maze.size and 0 <= ny < maze.size and
                    (nx, ny) not in visited and maze.grid[ny][nx].type != WALL):
                    dfs(nx, ny)
        
        dfs(self.x, self.y)
        if path_list:
            path_list.pop(0) 
        self.exploration_path = deque(path_list)
        print(f"Full exploration path generated with {len(self.exploration_path)} steps.")

    def _decide_move_greedy(self, maze):
        """【您的逻辑】决策逻辑现在优先处理“房间探索”任务"""
        if self.exploration_path:
            if not self.exploration_path:
                print("--- Room exploration complete. Re-evaluating global objectives. ---")
                self.target_pos = None
            else:
                if (self.x, self.y) == self.exploration_path[0]:
                    self.exploration_path.popleft()
                
                if self.exploration_path:
                    next_target_in_path = self.exploration_path[0]
                    path_segment = bfs_path(start=(self.x, self.y), end=next_target_in_path, maze_grid=maze.grid)
                    if path_segment and len(path_segment) > 1:
                        return (path_segment[1][0] - self.x, path_segment[1][1] - self.y)
                else: 
                    self.target_pos = None

        if not self.known_boss_pos:
            view_radius = 2 
            for r_offset in range(-view_radius, view_radius + 1):
                for c_offset in range(-view_radius, view_radius + 1):
                    check_x, check_y = self.x + c_offset, self.y + r_offset
                    if (0 <= check_x < maze.size and 0 <= check_y < maze.size and maze.grid[check_y][check_x].type == BOSS):
                        self.known_boss_pos = (check_x, check_y)
                        self.target_pos = None
                        print(f"!!! Boss sighted at {self.known_boss_pos} !!!")
                        break
                if self.known_boss_pos: break
        
        if self.target_pos is None or (self.x, self.y) == self.target_pos:
             self._find_new_objective(maze)

        if self.target_pos:
            path = bfs_path(start=(self.x, self.y), end=self.target_pos, maze_grid=maze.grid)
            if path and len(path) > 1:
                return (path[1][0] - self.x, path[1][1] - self.y)

        self.is_active = False
        return (0, 0)

    def decide_move(self, maze, algorithm):
        if not self.is_active: return (0, 0)
        if algorithm == ALGO_GREEDY: return self._decide_move_greedy(maze)
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
        self.last_move = (dx, dy)
        if self.move(dx, dy, maze):
            return self.interact_with_tile(maze, sound_manager)
        return None

    def move(self, dx, dy, maze):
        if maze.grid[self.y + dy][self.x + dx].type != WALL:
            self.x += dx; self.y += dy; return True
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
            self.target_pos = None
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
                self._generate_room_exploration_path(maze)
            else:
                tile.type = WALL; self.target_pos = None
        elif tile.type == BOSS and not self.boss_defeated:
             # 【核心改动】只返回信号，不处理战斗逻辑
             return 'start_battle' 
        elif tile.type == END:
            self.is_active = False
        return None
    
    def draw(self, screen, cell_width, cell_height):
        center_x = int((self.x + 0.5) * cell_width); center_y = int((self.y + 0.5) * cell_height)
        radius = int(min(cell_width, cell_height) * 0.4)
        pygame.draw.circle(screen, self.color, (center_x, center_y), radius)

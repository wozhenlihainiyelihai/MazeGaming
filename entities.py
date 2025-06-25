#包含游戏中所有“实体”或“对象”的定义，如地图格子(Tile)和AI玩家(AIPlayer)。

import random
from collections import deque 

import pygame
from config import *
from utils import bfs_path

class Tile:
    """地图格子对象类"""
    def __init__(self, tile_type=PATH):
        self.type = tile_type
        self.is_visible = True

class AIPlayer:
    """【战略升级版V4】AI角色类"""
    def __init__(self, start_pos=(1,1)):
        # 基础属性
        self.x, self.y = start_pos
        self.color = (10, 10, 10)
        self.health = 100
        self.gold = 20
        self.attack = 5
        self.diamonds = 0
        
        # 【新增】记录初始位置和Boss战状态
        self.start_pos = start_pos          # 用于被击败后返回
        self.boss_defeated = False          # 用于追踪Boss是否已被击败

        # 记忆与状态
        self.known_boss_pos = None
        self.objective = 'explore_and_loot' 
        self.target_pos = None              
        self.is_active = True
        
        self.exploration_path = []
        self.last_move = (0, 0)

        self.path_to_follow = [] 

    def _get_tile_value(self, tile_type):
        """根据规则，为不同地块赋予“贪心”价值，用于性价比计算"""
        if tile_type == GOLD:
            return SCORE_PER_GOLD * GOLD_REWARD
        if tile_type == HEALTH_POTION:
            return (POTION_HEAL_AMOUNT * SCORE_PER_HEALTH) + (100 - self.health)
        if tile_type == LOCKER:
            return SCORE_LOCKER_UNLOCK + (1 * SCORE_PER_DIAMOND)
        return 0

    def _assess_boss_threat(self):
        """评估Boss威胁"""
        if not self.known_boss_pos: return True
        # 为了测试方便，暂时调高AI攻击力评估值，确保能打赢
        # 实际游戏中可以改回 self.attack
        simulated_attack = self.attack * 1.5 
        turns_to_win = (BOSS_HEALTH / simulated_attack) if simulated_attack > 0 else float('inf')
        damage_taken = turns_to_win * BOSS_ATTACK
        return self.health > damage_taken

    def _find_new_objective(self, maze):
        """【核心改动】寻找新的战略目标，逻辑更正"""
        potential_targets = []
        # 1. 扫描全图寻找资源和未开的门
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
                            potential_targets.append({'score': score, 'pos': (c,r)})

        # 2. 如果还有资源，选最优的那个
        if potential_targets:
            self.objective = 'explore_and_loot'
            best_target = max(potential_targets, key=lambda x: x['score'])
            self.target_pos = best_target['pos']
            print(f"Global Objective: Looting. Best target is {self.target_pos} with score {best_target['score']:.2f}")
            return

        # 3. 【核心改动】如果没有资源了，决定最终目标
        # 如果Boss存在且未被击败，则目标是Boss
        if self.known_boss_pos and not self.boss_defeated:
            self.objective = 'defeat_boss'
            self.target_pos = self.known_boss_pos
            print(f"No resources left. Final objective: Defeat the BOSS at {self.target_pos}")
        # 否则，目标是终点
        else:
            self.objective = 'go_to_end'
            self.target_pos = maze.end_pos
            print(f"Boss defeated or does not exist. Final objective: Go to END at {self.target_pos}")


    def _generate_room_exploration_path(self, maze):
        """使用DFS生成一个能走遍房间内所有格子的路径"""
        print("Generating a full exploration path for the dead-end room...")
        path = []
        entry_point = (self.x - self.last_move[0], self.y - self.last_move[1])
        visited = {entry_point}
        
        def dfs(x, y):
            visited.add((x, y))
            path.append((x, y))
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if (0 <= nx < maze.size and 0 <= ny < maze.size and
                    (nx, ny) not in visited and maze.grid[ny][nx].type != WALL):
                    dfs(nx, ny)
        
        dfs(self.x, self.y)
        
        if path:
            path.pop(0) 
        self.exploration_path = path
        print(f"Full exploration path generated with {len(self.exploration_path)} steps.")


    def _decide_move_greedy(self, maze):
        """决策逻辑现在优先处理“房间探索”任务"""
        # 1. 最高优先级：房间探索
        if self.exploration_path:
            if (self.x, self.y) == self.exploration_path[0]:
                self.exploration_path.pop(0)
                if not self.exploration_path:
                    print("--- Room exploration complete. Re-evaluating global objectives. ---")
                    self.target_pos = None 
                    return self._decide_move_greedy(maze)

            if self.exploration_path:
                next_target_in_path = self.exploration_path[0]
                path_segment = bfs_path(start=(self.x, self.y), end=next_target_in_path, maze_grid=maze.grid)
                if path_segment and len(path_segment) > 1:
                    next_step = path_segment[1]
                    return (next_step[0] - self.x, next_step[1] - self.y)

        # 2. 更新视野内的Boss位置
        if not self.known_boss_pos:
            view_radius = 2 
            for r_offset in range(-view_radius, view_radius + 1):
                for c_offset in range(-view_radius, view_radius + 1):
                    check_x, check_y = self.x + c_offset, self.y + r_offset
                    if (0 <= check_x < maze.size and 0 <= check_y < maze.size and
                            maze.grid[check_y][check_x].type == BOSS):
                        self.known_boss_pos = (check_x, check_y)
                        print(f"!!! Boss sighted at {self.known_boss_pos} !!!")
                        self.target_pos = None 
                        break
                if self.known_boss_pos: break
        
        # 3. 寻找或更新目标
        if self.target_pos is None or (self.x, self.y) == self.target_pos:
             self._find_new_objective(maze)

        # 4. 计算路径
        if self.target_pos:
            path = bfs_path(start=(self.x, self.y), end=self.target_pos, maze_grid=maze.grid)
            if path and len(path) > 1:
                next_step = path[1]
                return (next_step[0] - self.x, next_step[1] - self.y)

        self.is_active = False
        return (0, 0)

    def decide_move(self, maze, algorithm):
        if not self.is_active: return (0, 0)

        if algorithm == ALGO_GREEDY:
            return self._decide_move_greedy(maze)
        if algorithm == ALGO_DP_VISUALIZATION:
            if self.path_to_follow and (self.x, self.y) in self.path_to_follow:
                current_index = self.path_to_follow.index((self.x, self.y))
                if current_index + 1 < len(self.path_to_follow):
                    next_pos = self.path_to_follow[current_index + 1]
                    return (next_pos[0] - self.x, next_pos[1] - self.y)
            self.is_active = False
            return (0, 0)
        
        moves = [(0, -1), (0, 1), (-1, 0), (1, 0)]; random.shuffle(moves)
        for dx, dy in moves:
            if self.can_move(dx, dy, maze): return (dx, dy)
        return (0, 0)

    def can_move(self, dx, dy, maze):
        next_x, next_y = self.x + dx, self.y + dy
        return maze.grid[next_y][next_x].type != WALL

    def move(self, dx, dy, maze):
        if self.can_move(dx, dy, maze):
            self.x += dx; self.y += dy; return True
        return False

    def update(self, maze, sound_manager, algorithm):
        if not self.is_active: return
        dx, dy = self.decide_move(maze, algorithm)
        self.last_move = (dx, dy)
        if self.move(dx, dy, maze):
            self.interact_with_tile(maze, sound_manager)

    def interact_with_tile(self, maze, sound_manager):
        """与当前站立的地块进行互动"""
        tile = maze.grid[self.y][self.x]
        
        if tile.type == GOLD:
            self.gold += GOLD_REWARD; sound_manager.play('coin'); print(f"AI collected GOLD! Current gold: {self.gold}")
            tile.type = PATH
        elif tile.type == HEALTH_POTION:
            self.health = min(100, self.health + POTION_HEAL_AMOUNT); sound_manager.play('potion'); print(f"AI used a POTION! Current health: {self.health}")
            tile.type = PATH
        elif tile.type == TRAP:
            sound_manager.play('trap')
            if self.gold >= TRAP_GOLD_COST:
                self.gold -= TRAP_GOLD_COST; print(f"AI stepped on a trap! Paid {TRAP_GOLD_COST} gold. Gold left: {self.gold}")
            else:
                self.health -= TRAP_HEALTH_COST; print(f"AI stepped on a trap! Lost {TRAP_HEALTH_COST} health. Health left: {self.health}")
            tile.type = PATH
        elif tile.type == LOCKER:
            print(f"AI at Locker { (self.x, self.y) }. Solving puzzle...")
            if self.gold >= LOCKER_COST:
                self.gold -= LOCKER_COST; self.diamonds += 1
                tile.type = PATH; print(f"Locker opened! Got 1 Diamond. Diamonds: {self.diamonds}")
                self.target_pos = None
                self._generate_room_exploration_path(maze)
            else:
                print("Not enough gold to open locker. Re-evaluating objectives.")
                tile.type = WALL
                self.target_pos = None
        
        # 【新增】完整的Boss战逻辑
        elif tile.type == BOSS:
            if self.boss_defeated:
                return # 如果Boss已被击败，此处只是一个普通地块

            print("--- AI is fighting the Boss! ---")
            # 评估战斗结果
            if self._assess_boss_threat():
                # AI 胜利
                print(">>> AI has DEFEATED the Boss! <<<")
                self.boss_defeated = True
                tile.type = PATH # Boss从地图上消失
                self.known_boss_pos = None # 从记忆中移除Boss位置
                self.target_pos = None # 强制重新评估目标（此时会导向终点E）
            else:
                # AI 失败
                print(">>> AI was defeated by the Boss! Respawning at start... <<<")
                self.x, self.y = self.start_pos # 返回初始点
                self.health = 100 # 生命值补满
                self.target_pos = None # 强制重新评估目标（会去继续寻找资源）

        elif tile.type == END:
            print("--- AI reached the destination! ---")
            self.is_active = False
        
    def draw(self, screen, cell_width, cell_height):
        center_x = int((self.x + 0.5) * cell_width); center_y = int((self.y + 0.5) * cell_height)
        radius = int(min(cell_width, cell_height) * 0.4)
        pygame.draw.circle(screen, self.color, (center_x, center_y), radius)
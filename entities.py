# entities.py

import random
from collections import deque 
import pygame
from config import * # 导入游戏配置，如瓦片类型、颜色等

class Tile:
    """迷宫中的单个瓦片单元"""
    def __init__(self, tile_type=PATH):
        self.type = tile_type  # 瓦片类型（如路径、墙壁、金币、陷阱等）
        self.is_visible = True # 瓦片是否可见 (当前代码中未使用，但保留)

class Boss:
    """游戏中的首领敌人"""
    def __init__(self):
        self.max_health = BOSS_MAX_HEALTH # Boss 最大生命值
        self.health = self.max_health     # Boss 当前生命值
        self.attack = BOSS_ATTACK         # Boss 攻击力
        self.is_frozen_for = 0            # Boss 被冻结的回合数
    
    def reset(self):
        """重置 Boss 的生命值和冻结状态"""
        self.health = self.max_health
        self.is_frozen_for = 0

class AIPlayer:
    """由 AI 算法控制的玩家角色"""
    def __init__(self, start_pos=(1,1)):
        self.x, self.y = start_pos        # 玩家当前迷宫坐标
        self.color = (10, 10, 10)         # 玩家在屏幕上显示的颜色
        self.max_health = 100             # 玩家最大生命值
        self.health = 100                 # 玩家当前生命值
        self.gold = 20                    # 玩家金币数量
        self.attack = PLAYER_BASE_ATTACK  # 玩家基础攻击力
        self.diamonds = 0                 # 玩家钻石数量
        self.skills = set()               # 玩家已获得的技能集合
        self.skill_cooldowns = {}         # 技能冷却时间 (当前未实现冷却机制)
        self.start_pos = start_pos        # 玩家起始位置
        self.boss_defeated = False        # Boss 是否已被击败的标志
        self.is_active = True             # 玩家是否处于活跃状态
        self.path_to_follow = []          # 在 DP 可视化模式下 AI 将遵循的预计算路径
        self.temporary_target = None      # 玩家的临时目标（例如，捡起附近的金币）
        self.attack_boost_this_turn = 0   # 本回合的攻击加成
        self.path_history = deque(maxlen=5) # 玩家最近走过的路径历史，用于回溯等
        # 状态旗帜，为True时表示AI需要一个新的全局目标
        self.needs_new_target = True

    def decide_move(self, maze, algorithm):
        """
        根据当前选择的 AI 算法决定下一步的移动方向。
        返回 (dx, dy) 表示移动的方向向量。
        """
        from algorithms.greedy import decide_move_greedy as simple_greedy_move # 导入贪婪算法的移动决策函数
        if not self.is_active: return (0, 0) # 如果玩家不活跃，则不移动

        if algorithm == ALGO_DP_VISUALIZATION:
            # 动态规划可视化模式：AI 遵循预设路径
            if not self.path_to_follow:
                return (0, 0) # 如果路径为空，不移动

            # 如果 AI 当前位置就是路径的下一个点（例如，刚开始或重置后），则弹出该点
            if (self.x, self.y) == self.path_to_follow[0]:
                self.path_to_follow.pop(0)
            
            # 如果弹出后路径为空（说明已经走完），则不移动
            if not self.path_to_follow:
                return (0, 0)

            # 计算走向路径中下一个点的方向
            next_pos = self.path_to_follow[0]
            dx = next_pos[0] - self.x
            dy = next_pos[1] - self.y
            return (dx, dy)

        elif algorithm == ALGO_GREEDY:
            # 贪婪算法模式：调用贪婪寻路函数
            return simple_greedy_move(self, maze)
        
        return (0, 0) # 默认不移动（如果算法未知）
        
    def update(self, maze, sound_manager, algorithm):
        """
        更新 AI 玩家的状态，包括决定移动、执行移动和与瓦片互动。
        返回互动结果字符串（如 'start_battle', 'start_puzzle'），否则返回 None。
        """
        if not self.is_active: return None # 如果玩家不活跃，不进行更新
        
        dx, dy = self.decide_move(maze, algorithm) # 决定移动方向
        if self.move(dx, dy, maze): # 如果成功移动
            return self.interact_with_tile(maze, sound_manager) # 与新瓦片互动
        return None

    def move(self, dx, dy, maze):
        """
        尝试将玩家移动 (dx, dy)。
        返回 True 表示移动成功，False 表示失败（撞墙或出界）。
        """
        next_x, next_y = self.x + dx, self.y + dy # 计算目标位置
        # 检查目标位置是否在迷宫范围内且不是墙壁
        if 0 <= next_x < maze.size and 0 <= next_y < maze.size:
             if maze.grid[next_y][next_x].type != WALL:
                self.x = next_x # 更新玩家 X 坐标
                self.y = next_y # 更新玩家 Y 坐标
                self.path_history.append((self.x, self.y)) # 记录路径历史
                return True
        return False

    def interact_with_tile(self, maze, sound_manager):
        """
        处理玩家与当前所在瓦片的互动。
        返回特定字符串以触发游戏状态变化，否则返回 None。
        """
        tile = maze.grid[self.y][self.x] # 获取当前瓦片对象
        
        # 到达临时目标后，也需要一个新的全局目标
        if (self.x, self.y) == self.temporary_target:
            self.temporary_target = None
            self.needs_new_target = True

        if tile.type == SHOP:
            # 如果是商店瓦片
            for skill_id, skill_data in SKILLS.items():
                if skill_id not in self.skills and self.diamonds >= skill_data['cost']:
                    # 玩家未拥有该技能且钻石足够，则购买技能
                    self.diamonds -= skill_data['cost'] # 扣除钻石
                    self.skills.add(skill_id)           # 添加技能
                    tile.type = PATH                    # 商店瓦片变为路径
                    self.needs_new_target = True        # 需要新目标
                    break # 每次只购买一个技能
        elif tile.type == GOLD:
            # 如果是金币瓦片
            self.gold += GOLD_REWARD      # 增加金币
            sound_manager.play('coin')    # 播放金币音效
            tile.type = PATH              # 金币瓦片变为路径
            self.needs_new_target = True  # 需要新目标
        elif tile.type == HEALTH_POTION:
            # 如果是生命药水瓦片
            self.health = min(100, self.health + POTION_HEAL_AMOUNT) # 增加生命值，不超过最大值
            sound_manager.play('potion')  # 播放药水音效
            tile.type = PATH              # 药水瓦片变为路径
            self.needs_new_target = True  # 需要新目标
        elif tile.type == TRAP:
            # 如果是陷阱瓦片
            sound_manager.play('trap')    # 播放陷阱音效
            tile.type = PATH              # 陷阱瓦片变为路径
            if self.gold >= TRAP_GOLD_COST: # 如果金币足够，扣除金币
                self.gold -= TRAP_GOLD_COST
            else:                           # 否则扣除生命值
                self.health -= TRAP_HEALTH_COST
        elif tile.type == LOCKER:
            # 如果是储物柜瓦片，触发谜题
            return 'start_puzzle'
        elif tile.type == BOSS and not self.boss_defeated:
             # 如果是 Boss 瓦片且 Boss 未被击败，触发战斗
             return 'start_battle'
        elif tile.type == END:
            # 如果是终点瓦片，玩家停止活跃
            self.is_active = False
            
        return None # 没有特殊互动发生

    def draw(self, screen, cell_width, cell_height):
        """在屏幕上绘制 AI 玩家"""
        center_x = int((self.x + 0.5) * cell_width)  # 计算玩家中心 X 坐标
        center_y = int((self.y + 0.5) * cell_height) # 计算玩家中心 Y 坐标
        radius = int(min(cell_width, cell_height) * 0.4) # 计算玩家绘制半径
        pygame.draw.circle(screen, self.color, (center_x, center_y), radius) # 绘制圆形代表玩家
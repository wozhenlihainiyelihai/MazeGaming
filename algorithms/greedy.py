import random
from config import *
from utils import bfs_path_avoiding_history

def get_tile_value(tile_type, player):
    """
    为贪心算法计算给定地块的战略价值（轻量级高性能版本）。
    """
    if tile_type == GOLD:
        # 金币的基础价值现在相对更高，以确保其吸引力
        return 50
    if tile_type == HEALTH_POTION:
        # 药水的价值与玩家损失的生命值成正比
        if player.health >= player.max_health:
            return 0
        return (POTION_HEAL_AMOUNT * SCORE_PER_HEALTH) + (player.max_health - player.health)
    if tile_type == LOCKER:
        return SCORE_LOCKER_UNLOCK
    if tile_type == TRAP:
        return -50 if player.gold < TRAP_GOLD_COST else -10
    if tile_type == SHOP:
        return 40
    if tile_type == BOSS:
        # AI只会在自身生命值较高时，才将Boss视为有价值的目标
        if player.health > 70:
            return SCORE_BOSS_KILL
        else:
            return -1000  # 给予巨大负分，让AI主动避开
    return 0

# --- 核心决策逻辑：严格遵守“视野受限”原则 ---
def decide_move_greedy(player, maze):
    """
    贪心算法的主要决策逻辑。
    严格遵循“视野受限”原则，只在有限视野内寻找性价比最高的资源。
    """
    history_set = set(player.path_history)
    view_radius = 5  # 定义AI的视野范围为5x5的区域
    local_targets = []

    # 1. 扫描视野内的所有地块
    for r_offset in range(-view_radius, view_radius + 1):
        for c_offset in range(-view_radius, view_radius + 1):
            if r_offset == 0 and c_offset == 0:
                continue

            tx, ty = player.x + c_offset, player.y + r_offset

            if 0 <= tx < maze.size and 0 <= ty < maze.size:
                tile_type = maze.grid[ty][tx].type
                
                # 2. 只关注有价值的资源
                if tile_type in {GOLD, HEALTH_POTION, LOCKER, BOSS, SHOP}:
                    value = get_tile_value(tile_type, player)
                    if value > 0:
                        # 3. 计算到视野内资源的实际距离
                        path = bfs_path_avoiding_history(
                            start=(player.x, player.y),
                            end=(tx, ty),
                            maze_grid=maze.grid,
                            history_path=history_set
                        )
                        if path:
                            distance = len(path) - 1
                            if distance > 0:
                                # 4. 计算“性价比”（单位距离收益）
                                score = value / distance
                                local_targets.append({'score': score, 'pos': (tx, ty), 'path': path})

    # 5. 从视野内的目标中，选择性价比最高的一个
    if local_targets:
        best_target = max(local_targets, key=lambda x: x['score'])
        # 移动向该目标路径上的下一步
        next_step = best_target['path'][1]
        return (next_step[0] - player.x, next_step[1] - player.y)

    # 6. 备用策略：如果视野内没有任何有价值的目标，则朝终点移动以进行探索
    path_to_end = bfs_path_avoiding_history(start=(player.x, player.y), end=maze.end_pos, maze_grid=maze.grid, history_path=history_set)
    if path_to_end and len(path_to_end) > 1:
        return (path_to_end[1][0] - player.x, path_to_end[1][1] - player.y)

    # 7. 最后手段：如果被困，尝试随机移动
    for dx, dy in sorted([(0, 1), (0, -1), (1, 0), (-1, 0)], key=lambda k: random.random()):
        nx, ny = player.x + dx, player.y + dy
        if (nx, ny) not in history_set and (0 <= nx < maze.size and 0 <= ny < maze.size and maze.grid[ny][nx].type != WALL):
            return (dx, dy)
    
    return (0, 0)
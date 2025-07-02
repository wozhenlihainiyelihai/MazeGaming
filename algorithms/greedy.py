import random
from config import *
from utils import bfs_path_avoiding_history

def get_tile_value(tile_type, player):
    """
    为贪心算法计算给定地块的战略价值（轻量级高性能版本）。
    """
    if tile_type == GOLD:
        return SCORE_PER_GOLD * GOLD_REWARD
    if tile_type == HEALTH_POTION:
        # 药水的价值与玩家损失的生命值成正比，血量越低，药水价值越高。
        if player.health >= player.max_health:
            return 0  # 满血时药水无价值。
        return (POTION_HEAL_AMOUNT * SCORE_PER_HEALTH) + (player.max_health - player.health)
    if tile_type == LOCKER:
        # 谜题宝箱具有很高的固定价值。
        return SCORE_LOCKER_UNLOCK
    if tile_type == TRAP:
        # 陷阱是负价值。
        return -50 if player.gold < TRAP_GOLD_COST else -10
    if tile_type == SHOP:
        # 为简单起见，分配一个中等的固定值。
        return 40
    if tile_type == BOSS:
        # AI只会在自身生命值较高时，才将Boss视为有价值的目标。
        if player.health > 60:  # 超过此生命值阈值才考虑挑战Boss。
            return SCORE_BOSS_KILL
        else:
            return -1000  # 生命值较低时，给予巨大负分，让AI主动避开。
    return 0

def find_best_global_target(player, maze):
    """
    根据“价值/距离”评分，在地图上找到最佳的长期目标。
    """
    potential_targets = []
    history_set = set(player.path_history)
    for r in range(maze.size):
        for c in range(maze.size):
            tile_type = maze.grid[r][c].type
            # 只评估有潜在正价值的地块。
            if tile_type in {GOLD, HEALTH_POTION, LOCKER, BOSS, SHOP}:
                value = get_tile_value(tile_type, player)
                if value > 0:
                    # 通过寻路计算真实距离。
                    path = bfs_path_avoiding_history(
                        start=(player.x, player.y),
                        end=(c, r),
                        maze_grid=maze.grid,
                        history_path=history_set
                    )
                    if path:
                        distance = len(path) - 1
                        if distance > 0:
                            # 分数公式优先考虑距离近、价值高的物品。
                            score = value / (distance ** 1.5)
                            potential_targets.append({'score': score, 'pos': (c, r)})

    if potential_targets:
        # 从所有潜在目标中选出得分最高的一个。
        best_target = max(potential_targets, key=lambda x: x['score'])
        player.temporary_target = best_target['pos']
    else:
        # 如果没有可达的有价值物品，则清除目标。
        player.temporary_target = None

    player.needs_new_target = False

def decide_move_greedy(player, maze):
    """
    贪心算法的主要决策逻辑，具有清晰的优先级：
    1. 优先处理紧急的局部需求（如低血量时捡药水）。
    2. 追求最佳的长期全局目标。
    3. 若无目标，则朝终点前进。
    4. 若被困，则尝试回溯或随机移动。
    """
    history_set = set(player.path_history)

    # 1. 检查紧急的局部机会
    if player.health < 40:
        view_radius = 2  # 在紧急情况下看得更远一些。
        for r_offset in range(-view_radius, view_radius + 1):
            for c_offset in range(-view_radius, view_radius + 1):
                if r_offset == 0 and c_offset == 0: continue
                tx, ty = player.x + c_offset, player.y + r_offset
                if 0 <= tx < maze.size and 0 <= ty < maze.size:
                    tile = maze.grid[ty][tx]
                    if tile.type == HEALTH_POTION:
                        # 如果附近有急需的药水，将其作为最高优先级。
                        path = bfs_path_avoiding_history(start=(player.x, player.y), end=(tx, ty), maze_grid=maze.grid, history_path=history_set)
                        if path and len(path) > 1:
                            return (path[1][0] - player.x, path[1][1] - player.y)

    # 2. 如果没有紧急需求，则寻找或跟随一个全局目标。
    if player.needs_new_target or player.temporary_target is None:
        find_best_global_target(player, maze)

    # 如果已设定全局目标，则向其移动。
    if player.temporary_target:
        target_pos = player.temporary_target
        # 验证目标是否仍然有效（可能已被收集）。
        if maze.grid[target_pos[1]][target_pos[0]].type == PATH:
            player.needs_new_target = True  # 目标已消失，下一回合寻找新目标。
        else:
            path = bfs_path_avoiding_history(start=(player.x, player.y), end=player.temporary_target, maze_grid=maze.grid, history_path=history_set)
            if path and len(path) > 1:
                return (path[1][0] - player.x, path[1][1] - player.y)
            else:
                # 到达目标的路径被阻塞，寻找新目标。
                player.needs_new_target = True

    # 3. 备用策略：如果找不到任何目标，则朝终点移动。
    path_to_end = bfs_path_avoiding_history(start=(player.x, player.y), end=maze.end_pos, maze_grid=maze.grid, history_path=history_set)
    if path_to_end and len(path_to_end) > 1:
        return (path_to_end[1][0] - player.x, path_to_end[1][1] - player.y)

    # 4. 最后手段：如果被困，尝试移动到任何不在近期历史中的相邻有效单元格。
    for dx, dy in sorted([(0,1), (0,-1), (1,0), (-1,0)], key=lambda k: random.random()): # 随机化方向
        nx, ny = player.x + dx, player.y + dy
        if (nx, ny) not in history_set and (0 <= nx < maze.size and 0 <= ny < maze.size and maze.grid[ny][nx].type != WALL):
            return (dx, dy)
    
    # 如果所有方法都失败（例如，被困在1x1的空间里），则不移动。
    return (0, 0)

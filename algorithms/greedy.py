import random
from config import *
from utils import bfs_path_avoiding_history # 从中立的 utils 导入
from algorithms.branch_and_bound import analyze_battle_outcome

def get_tile_value(tile_type, player, maze=None, pos=None):
    if tile_type == GOLD: return GOLD_REWARD * SCORE_PER_GOLD
    if tile_type == HEALTH_POTION:
        if player.health >= 100: return 0
        return (POTION_HEAL_AMOUNT * SCORE_PER_HEALTH) + (100 - player.health)
    if tile_type == LOCKER: return SCORE_PER_DIAMOND + 20
    if tile_type == TRAP: return -50 if player.gold < TRAP_GOLD_COST else -10
    if tile_type == SHOP:
        can_afford = any(skill not in player.skills and player.diamonds >= SKILLS[skill]['cost'] for skill in SKILLS)
        return 40 if can_afford else 0
    if tile_type == BOSS:
        if maze and hasattr(maze, 'boss'):
            analysis = analyze_battle_outcome(player, maze.boss)
            if analysis["survives"]:
                return SCORE_BOSS_KILL - (analysis['health_lost'] * SCORE_PER_HEALTH) - analysis['turns']
        return -1000
    return 0

def set_next_global_target(player, maze):
    """独立的全局扫描函数"""
    potential_targets = []
    history_set = set(player.path_history)
    for r in range(maze.size):
        for c in range(maze.size):
            value = get_tile_value(maze.grid[r][c].type, player, maze)
            if value > 0:
                path = bfs_path_avoiding_history(start=(player.x, player.y), end=(c, r), maze_grid=maze.grid, history_path=history_set)
                if path:
                    distance = len(path) - 1
                    if distance > 0:
                        potential_targets.append({'score': value / (distance ** 1.5), 'pos': (c, r)})
    if potential_targets:
        best_target = max(potential_targets, key=lambda x: x['score'])
        player.temporary_target = best_target['pos']
    else:
        player.temporary_target = None
    player.needs_new_target = False

def decide_move_greedy(player, maze):
    """【最终稳健版】决策逻辑"""
    
    # 1. 如果需要新目标，则进行一次全局扫描
    if player.needs_new_target:
        set_next_global_target(player, maze)

    history_set = set(player.path_history)
    
    # 2. 优先处理长期目标
    if player.temporary_target:
        path = bfs_path_avoiding_history(start=(player.x, player.y), end=player.temporary_target, maze_grid=maze.grid, history_path=history_set)
        if path and len(path) > 1:
            return (path[1][0] - player.x, path[1][1] - player.y)

    # 3. 如果长期目标无法到达或不存在，则执行局部扫描寻找机会
    view_radius = 1
    local_targets = []
    for r_offset in range(-view_radius, view_radius + 1):
        for c_offset in range(-view_radius, view_radius + 1):
            if r_offset == 0 and c_offset == 0: continue
            tx, ty = player.x + c_offset, player.y + r_offset
            if (tx, ty) not in history_set and (0 <= tx < maze.size and 0 <= ty < maze.size and maze.grid[ty][tx].type != WALL):
                value = get_tile_value(maze.grid[ty][tx].type, player, maze)
                if value > 0:
                    dist = abs(tx - player.x) + abs(ty - player.y)
                    local_targets.append({'score': value / (dist**1.5), 'pos': (tx, ty)})
    
    if local_targets:
        best_local = max(local_targets, key=lambda x: x['score'])
        path = bfs_path_avoiding_history(start=(player.x, player.y), end=best_local['pos'], maze_grid=maze.grid, history_path=history_set)
        if path and len(path) > 1:
            return (path[1][0] - player.x, path[1][1] - player.y)

    # 4. 如果连局部机会都没有，则走向终点
    path_to_end = bfs_path_avoiding_history(start=(player.x, player.y), end=maze.end_pos, maze_grid=maze.grid, history_path=history_set)
    if path_to_end and len(path_to_end) > 1:
        return (path_to_end[1][0] - player.x, path_to_end[1][1] - player.y)
        
    # 5. 如果被完全困住，允许回头
    if player.path_history and len(player.path_history) > 1:
        return (player.path_history[-2][0] - player.x, player.path_history[-2][1] - player.y)

    return (0, 0)
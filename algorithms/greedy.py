import random
from config import *
from utils import bfs_path
# 导入战斗模拟器
from algorithms.branch_and_bound import analyze_battle_outcome

def get_tile_value(tile_type, player, maze=None, pos=None):
    """
    价值评估函数，包含对Boss的动态评估和对商店的智能评估。
    """
    if tile_type == GOLD:
        return 20
    if tile_type == HEALTH_POTION:
        return 15 + (100 - player.health)
    if tile_type == TRAP:
        return -50 if player.gold < TRAP_GOLD_COST else -10
    if tile_type == LOCKER:
        return 30 if player.gold >= LOCKER_COST else -1
    
    if tile_type == SHOP:
        # 【核心修正】检查是否有买得起的、AI尚未拥有的技能
        can_afford_new_skill = False
        for skill_id, skill_data in SKILLS.items():
            if skill_id not in player.skills and player.diamonds >= skill_data['cost']:
                can_afford_new_skill = True
                break
        
        if can_afford_new_skill:
            print("发现可以购买的技能，商店价值很高。")
            return 40  # 只有买得起的时候，商店才有高价值
        else:
            return 0  # 如果买不起，商店对AI暂时没有吸引力

    if tile_type == BOSS:
        if maze and hasattr(maze, 'boss'):
            print("发现Boss，正在进行战前模拟...")
            boss = maze.boss
            analysis = analyze_battle_outcome(player, boss)
            
            if analysis["survives"]:
                score = 500 + (100 - analysis['health_lost']) * 2
                print(f"模拟结果：可以获胜！预估生命损失: {analysis['health_lost']}。Boss价值评估为: {score}")
                return score
            else:
                print("模拟结果：无法获胜或代价过高。极力避开Boss。")
                return -1000
        else:
            return -1000

    return 0

def decide_move_greedy(player, maze):
    """混合决策：优先临时目标，否则执行包含Boss战评估的局部贪心"""
    
    # 1. 检查是否有临时目标（开锁后）
    if player.temporary_target:
        if (player.x, player.y) == player.temporary_target:
            print(f"已到达临时目标 {player.temporary_target}，清除目标。")
            player.temporary_target = None
        else:
            path_to_target = bfs_path(start=(player.x, player.y), end=player.temporary_target, maze_grid=maze.grid)
            if path_to_target and len(path_to_target) > 1:
                next_step = path_to_target[1]
                print(f"临时目标模式：移动向 {player.temporary_target}")
                return (next_step[0] - player.x, next_step[1] - player.y)
            else:
                print(f"无法到达临时目标 {player.temporary_target}，清除目标。")
                player.temporary_target = None

    # 2. 局部贪心逻辑
    best_target = None
    max_score = -float('inf')
    
    view_radius = 2
    for r_offset in range(-view_radius, view_radius + 1):
        for c_offset in range(-view_radius, view_radius + 1):
            if r_offset == 0 and c_offset == 0:
                continue

            target_x, target_y = player.x + c_offset, player.y + r_offset

            if (0 <= target_x < maze.size and 0 <= target_y < maze.size and
                    maze.grid[target_y][target_x].type != WALL):
                
                tile = maze.grid[target_y][target_x]
                value = get_tile_value(tile.type, player, maze, (target_x, target_y))
                
                if value > 0: # 只考虑有正收益的目标
                    path_to_target_in_view = bfs_path(
                        start=(player.x, player.y),
                        end=(target_x, target_y),
                        maze_grid=maze.grid
                    )
                    
                    if path_to_target_in_view:
                        distance = len(path_to_target_in_view) - 1
                        if distance > 0:
                            score = value / distance
                            if score > max_score:
                                max_score = score
                                best_target = (target_x, target_y)

    # 3. 如果无明确目标，则走向终点
    if best_target is None:
        best_target = maze.end_pos

    # 4. 计算并返回移动
    if best_target:
        final_path = bfs_path(
            start=(player.x, player.y), 
            end=best_target, 
            maze_grid=maze.grid
        )
        if final_path and len(final_path) > 1:
            next_step = final_path[1]
            return (next_step[0] - player.x, next_step[1] - player.y)

    return (0, 0)
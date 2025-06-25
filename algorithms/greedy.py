import random
from config import *
from utils import bfs_path # 导入路径搜索工具

def get_tile_value(tile_type, player):
    """
    【已优化】根据地块类型和玩家当前状态，返回其“贪心”价值。
    """
    if tile_type == GOLD:
        return 20  # 金币提供稳定的高价值
    if tile_type == HEALTH_POTION:
        # 生命值越低，药水价值越高
        return 15 + (100 - player.health)
    if tile_type == TRAP:
        # 如果金币不够支付，陷阱的威胁就巨大
        return -50 if player.gold < TRAP_GOLD_COST else -10
    if tile_type == LOCKER:
        # 对未解的门保持较高的兴趣，鼓励探索
        return 10
    if tile_type == BOSS:
        return -1000  # 极力避开Boss
    return 0  # 其他地块价值为0

def decide_move_greedy(player, maze):
    """
    【已优化】根据AI玩家周围3x3的视野和自身状态，使用贪心策略决定下一步的移动方向。
    """
    best_target = None
    max_score = -float('inf')
    
    # 1. 扫描3x3视野
    view_radius = 1  # 3x3 视野的半径为1
    for r_offset in range(-view_radius, view_radius + 1):
        for c_offset in range(-view_radius, view_radius + 1):
            if r_offset == 0 and c_offset == 0:
                continue

            target_x, target_y = player.x + c_offset, player.y + r_offset

            # 检查目标是否在迷宫范围内且不是墙
            if (0 <= target_x < maze.size and 0 <= target_y < maze.size and
                    maze.grid[target_y][target_x].type != WALL):
                
                tile = maze.grid[target_y][target_x]
                # 【已优化】传入player对象进行动态价值评估
                value = get_tile_value(tile.type, player)
                
                if value != 0:
                    # 2. 计算到达目标的距离 (在视野内)
                    path_to_target_in_view = bfs_path(
                        start=(player.x, player.y),
                        end=(target_x, target_y),
                        maze_grid=maze.grid,
                        view_limit_center=(player.x, player.y),
                        view_limit_radius=view_radius
                    )
                    
                    if path_to_target_in_view:
                        distance = len(path_to_target_in_view) - 1
                        if distance > 0:
                            # 3. 计算性价比
                            score = value / distance
                            if score > max_score:
                                max_score = score
                                best_target = (target_x, target_y)

    # 4. 如果视野内无目标，则将终点设为默认目标
    if best_target is None:
        best_target = maze.end_pos

    # 5. 计算走向最终目标的全局路径
    if best_target:
        final_path = bfs_path(
            start=(player.x, player.y), 
            end=best_target, 
            maze_grid=maze.grid
        )
        if final_path and len(final_path) > 1:
            next_step = final_path[1]
            return (next_step[0] - player.x, next_step[1] - player.y)

    # 6. 如果无路可走（几乎不可能发生），则不移动
    return (0, 0)

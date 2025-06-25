from config import WALL

def decide_move_greedy(player, maze):
    """
    根据AI玩家周围3x3的视野，使用贪心策略决定下一步的移动方向。
    
    输入:
        player (AIPlayer): AI玩家对象。
        maze (Maze): Maze对象。
        
    输出:
        (int, int): 一个代表移动方向的元组, 例如 (0, 1) 代表向下。
    
    实现提示:
        1. 获取AI当前坐标 (player.x, player.y)。
        2. 扫描以该坐标为中心的3x3区域。
        3. 对视野内的每个可用格子（非墙壁）进行价值评估。
           - 定义“性价比”函数，例如：(格子价值 / 到达距离)。
           - 金币/药水为正价值，陷阱为负价值。
        4. 找到性价比最高的格子作为目标。
        5. 计算并返回朝该目标移动的第一步方向。
        6. 如果视野内没有可追求的目标，则可以返回一个随机移动或朝终点移动。
    """
    import random
    
    # --- 在此填充贪心算法核心逻辑 ---
    
    # 当前为占位符逻辑：在可行的移动方向中随机选择一个
    possible_moves = []
    for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
        next_x, next_y = player.x + dx, player.y + dy
        if maze.grid[next_y][next_x].type != WALL:
            possible_moves.append((dx, dy))
            
    if possible_moves:
        return random.choice(possible_moves)
    else:
        return (0, 0) # No move

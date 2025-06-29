from config import *
import numpy as np
import heapq
from collections import defaultdict


def _run_a_star_phase(maze, start_pos, end_pos, resources, initial_context):
    """
    一个通用的A*搜索阶段函数。

    Args:
        maze (Maze): 迷宫对象。
        start_pos (tuple): 当前阶段的起始位置 (x, y)。
        end_pos (tuple): 当前阶段的目标位置 (x, y)。
        resources (list): 在此阶段可供收集的资源列表。每个资源是 (x, y, type) 的元组。
        initial_context (dict): 初始状态，包含 'score', 'health', 'gold' 和可选的 'prev_state'。

    Returns:
        tuple: (best_at_end, dp)
            - best_at_end (tuple): 到达终点时最优的状态 (x, y, mask)。如果无法到达则为 None。
            - dp (dict): 动态规划表，记录了到达每个状态的最优路径信息。
    """
    size = maze.size
    # dp 表的核心数据结构
    # 键 (x, y, mask): 状态，代表玩家在位置(x,y)时，已收集资源的掩码(mask)
    # 值 (score, prev_state, health, gold):
    #   - score: 到达该状态时的累计分数
    #   - prev_state: 到达此状态的前一个状态，用于路径回溯
    #   - health: 到达该状态时的生命值
    #   - gold: 到达该状态时的金币数
    dp = {}

    # A*算法的启发函数 (Heuristic)
    # 使用曼哈顿距离，估算从当前点到终点的最短距离，用于引导搜索方向
    def heuristic(x, y):
        return abs(x - end_pos[0]) + abs(y - end_pos[1])

    # 动态奖励计算函数
    # 根据玩家当前状态（生命、金币）和资源类型，计算获取该资源能获得的奖励分数
    def calculate_reward(res_type, health, gold):
        if res_type == GOLD: return 150
        # 开锁奖励
        if res_type == LOCKER: return 100
        # 生命值低于80时，血瓶价值更高
        if res_type == HEALTH_POTION: return (110-health)*4
        if res_type == TRAP: return -200
        # 挑战Boss需要生命值高于30，否则视为无法通行的路径
        if res_type == BOSS: return 600 if health > 30 else -float('inf')
        return 0

    # 初始化A*搜索的起点
    initial_state = (start_pos[0], start_pos[1], 0)  # (x, y, 初始资源掩码为0)
    initial_score = initial_context['score']
    dp[initial_state] = (
        initial_score,
        initial_context.get('prev_state'),  # 用于多阶段路径回溯连接
        initial_context['health'],
        initial_context['gold']
    )

    # 优先队列 (Min-Heap)，用于A*搜索
    # 存储元组 (f_value, state)
    # f_value = -score + heuristic。因为 heapq 是最小堆，所以对 score 取负，以实现按分数从高到低排序
    pq = [(heuristic(start_pos[0], start_pos[1]) - initial_score, initial_state)]

    best_at_end = None  # 记录到达终点时的最佳状态
    best_score_at_end = float('-inf')  # 记录到达终点时的最高最终得分
    visited_count = 0  # 计数器，用于调试和监控算法性能

    while pq:
        visited_count += 1
        if visited_count % 500 == 0:
            print(f"  [A* Status] Visited states: {visited_count}, Queue size: {len(pq)}")

        # 从优先队列中取出 f_value 最小（即 score 最高）的节点
        _, current = heapq.heappop(pq)
        current_score, _, health, gold = dp[current]
        x, y, resources_mask = current

        # --- 检查是否到达当前阶段的终点 ---
        if (x, y) == end_pos:
            # 到达终点时，计算最终得分（包括剩余生命和金币的奖励）
            final_score = current_score + health * 2 + gold * 3
            if final_score > best_score_at_end:
                best_score_at_end = final_score
                best_at_end = current
            continue  # 继续搜索，因为可能还有其他路径以更高的分数到达终点

        # --- 探索相邻节点 ---
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            next_x, next_y = x + dx, y + dy
            # 检查移动是否合法（在边界内且不是墙）
            if not (0 <= next_x < size and 0 <= next_y < size and maze.grid[next_y][next_x].type != WALL):
                continue

            # 继承当前状态
            new_health, new_gold, new_mask, score_change = health, gold, resources_mask, 0

            # --- 检查新位置上是否有可交互的资源 ---
            for i, (rx, ry, res_type) in enumerate(resources):
                # 如果新位置有资源，并且这个资源之前没有被拾取过
                if (rx, ry) == (next_x, next_y) and not (new_mask & (1 << i)):
                    reward = calculate_reward(res_type, new_health, new_gold)
                    if reward == -float('inf'): continue  # 如果奖励为负无穷（如打不过Boss），则放弃此路径

                    # 模拟拾取资源后的状态变化
                    temp_health, temp_gold = new_health, new_gold
                    if res_type == TRAP:
                        if temp_gold >= TRAP_GOLD_COST:
                            temp_gold -= TRAP_GOLD_COST
                        else:
                            temp_health -= TRAP_HEALTH_COST
                    elif res_type == GOLD:
                        temp_gold += 100
                    elif res_type == HEALTH_POTION:
                        temp_health = min(100, temp_health + 20)
                    elif res_type == BOSS:
                        temp_health -= 30
                    elif res_type == LOCKER:
                        temp_gold -= 10  # 开启LOCKER需要消耗30金币

                    # 只有在交互后生命值大于0的情况下，才认为此次交互有效
                    if temp_health > 0:
                        new_health, new_gold = temp_health, temp_gold
                        new_mask |= (1 << i)  # 更新资源掩码，标记此资源已被拾取
                        score_change += reward
                    break  # 每个位置只处理一个资源

            # --- 更新DP表和优先队列 ---
            new_state = (next_x, next_y, new_mask)
            new_score = current_score + score_change - 1 # 每走一步，分数-1作为移动成本

            # 如果找到了更优的路径（或第一次到达该状态），则更新
            if new_state not in dp or new_score > dp[new_state][0]:
                if new_state in dp:
                    print(f"  [A* Update] Found better path to ({next_x},{next_y}), "
                          f"Old score: {dp[new_state][0]:.0f}, New score: {new_score:.0f}")

                dp[new_state] = (new_score, current, new_health, new_gold)
                # 启发值权重乘以2，加强启发式引导，更快地朝向终点
                f_value = -new_score + heuristic(next_x, next_y) * 2
                heapq.heappush(pq, (f_value, new_state))

    return best_at_end, dp


def calculate_dp_path(maze):
    """
    分阶段动态规划主函数，用于解决整个迷宫问题。
    策略核心是：如果地图上有Boss，则强制执行"先打Boss，后去终点"的两阶段寻路。
    """
    # --- 1. 初始化：扫描地图，找出所有资源和Boss位置 ---
    all_resources = []
    boss_pos = None
    for y in range(maze.size):
        for x in range(maze.size):
            tile_type = maze.grid[y][x].type
            if tile_type in {GOLD, HEALTH_POTION, LOCKER, TRAP, BOSS}:
                if tile_type == BOSS: boss_pos = (x, y)
                all_resources.append((x, y, tile_type))

    # --- 2. 无Boss情况处理 ---
    # 如果地图上没有Boss，则问题简化为从起点到终点的单阶段寻路。
    if not boss_pos:
        print("[DP Path] No boss found. Running single-phase A* to end.")
        # 对所有资源按类型（config.py中定义的枚举值）排序，并取前18个作为候选资源
        resources = sorted(all_resources, key=lambda r: r[2], reverse=True)[:18]
        # 运行单阶段A*
        best_end_state, dp = _run_a_star_phase(maze, maze.start_pos, maze.end_pos, resources,
                                               {'score': 0, 'health': 100, 'gold': 20})
        if not best_end_state: return [], 0
        # 从dp表中回溯路径
        path, score = [], dp[best_end_state][0]
        curr = best_end_state
        while curr:
            path.append((curr[0], curr[1]));
            curr = dp[curr][1]
        return list(reversed(path)), score

    # --- 3. 有Boss情况处理：阶段 1 (从起点到Boss) ---
    print(f"\n[DP Path] Starting Phase 1: Start {maze.start_pos} -> Boss {boss_pos}")
    
    # 新的均衡资源选择策略：为不同类型的资源设置配额，并优先选择离起点近的。
    # 这样可以避免候选列表被单一类型的资源（如血瓶）占满。
    resources_by_type = defaultdict(list)
    for res in all_resources:
        if res[2] != BOSS:  # Boss 不是需要收集的资源
            resources_by_type[res[2]].append(res)

    # --- 根据地图尺寸动态调整资源配额 ---
    if maze.size == 7:
        # 7x7地图: 共选择5个资源 (3血瓶, 2金币)
        quotas = {HEALTH_POTION: 3, GOLD: 2}
    elif maze.size == 15:
        # 15x15地图: 共选择10个资源 (5血瓶, 5金币)
        quotas = {HEALTH_POTION: 5, GOLD: 5}
    elif maze.size == 31:
        # 31x31地图: 共选择20个资源 (10血瓶, 10金币)
        quotas = {HEALTH_POTION: 10, GOLD: 10}
    else:
        # 其他尺寸地图的默认配额
        quotas = {HEALTH_POTION: 5, GOLD: 5}

    resources_p1 = []
    # 为了让选择过程稳定可复现，我们按资源类型的值排序来遍历
    sorted_types = sorted(quotas.keys(), reverse=True)

    for res_type in sorted_types:
        quota = quotas[res_type]
        # 按离起点的距离（曼哈顿距离）对该类型资源进行排序，优先选择近的
        candidates = sorted(
            resources_by_type[res_type],
            key=lambda r: abs(r[0] - maze.start_pos[0]) + abs(r[1] - maze.start_pos[1])
        )
        # 将满足配额的资源加入最终列表
        resources_p1.extend(candidates[:quota])

    best_boss_state, dp1 = _run_a_star_phase(maze, maze.start_pos, boss_pos, resources_p1,
                                             {'score': 0, 'health': 100, 'gold': 20})

    if not best_boss_state:
        print("[DP Path] CRITICAL: Could not find a path to the boss.")
        return [], 0
    print(f"[DP Path] Phase 1 Complete! Arrived at boss with score {dp1[best_boss_state][0]:.0f}.")

    # --- 4. 准备阶段 2 (从Boss到终点) ---
    s1_score, _, s1_health, s1_gold = dp1[best_boss_state]
    s1_mask = best_boss_state[2]

    # 设置阶段2的初始上下文，继承阶段1结束时的状态
    context_p2 = {
        'score': s1_score,
        'health': s1_health,
        'gold': s1_gold,
        'prev_state': best_boss_state  # 关键：将阶段1的终点作为阶段2回溯的起点
    }

    # 确定阶段2的可用资源：即所有未在阶段1中被收集的资源
    res_p1_set = set(resources_p1)
    # 首先加入阶段1中筛选出但未被使用的资源
    resources_p2 = [res for i, res in enumerate(resources_p1) if not (s1_mask & (1 << i)) and res[2] != BOSS]
    # 然后加入所有未在阶段1筛选范围内的其他资源
    for res in all_resources:
        if res not in res_p1_set and res[2] != BOSS:
            resources_p2.append(res)
    # 同样对阶段2的资源进行排序和筛选
    resources_p2 = sorted(resources_p2, key=lambda r: r[2], reverse=True)[:14]

    # --- 5. 运行阶段 2 (从Boss到终点) ---
    print(f"\n[DP Path] Starting Phase 2: Boss {boss_pos} -> End {maze.end_pos}")
    best_end_state, dp2 = _run_a_star_phase(maze, boss_pos, maze.end_pos, resources_p2, context_p2)

    if not best_end_state:
        print("[DP Path] CRITICAL: Could not find a path from boss to end.")
        return [], 0
    print("[DP Path] Phase 2 Complete! Path to end found.")

    # --- 6. 合并并重建最终路径 ---
    # 最终总分 = 阶段2结束时的分数 + 剩余生命/金币的奖励分
    path, final_score = [], dp2[best_end_state][0] + dp2[best_end_state][2] * 2 + dp2[best_end_state][3] * 3

    # 首先，从阶段2的终点回溯到Boss位置
    curr = best_end_state
    while curr and curr != best_boss_state:
        path.append((curr[0], curr[1]))
        curr = dp2[curr][1]

    # 然后，从Boss位置（即阶段1的终点）回溯到起点
    curr = best_boss_state
    while curr:
        path.append((curr[0], curr[1]))
        curr = dp1[curr][1]

    print("[DP Path] Final path reconstruction complete.")

    # 因为是倒序回溯的，所以最后需要将路径反转
    return list(reversed(path)), final_score 
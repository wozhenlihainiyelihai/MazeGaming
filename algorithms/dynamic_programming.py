from config import *
import numpy as np
import heapq

def _run_a_star_phase(maze, start_pos, end_pos, resources, initial_context):
    """
    通用A*搜索函数，用于解决迷宫的一个阶段（例如，从起点到Boss）。
    """
    size = maze.size
    dp = {}  # (x, y, mask) -> (score, prev_state, health, gold)

    # 启发函数：曼哈顿距离，引导搜索向目标前进
    def heuristic(x, y):
        return abs(x - end_pos[0]) + abs(y - end_pos[1])

    def calculate_reward(res_type, health, gold):
        if res_type == GOLD: return 150
        if res_type == LOCKER: return 250 if gold >= 30 else 0
        if res_type == HEALTH_POTION: return 100 if health < 80 else 30
        if res_type == TRAP: return -10
        if res_type == BOSS: return 600 if health > 30 else -float('inf')
        return 0

    initial_state = (start_pos[0], start_pos[1], 0)
    initial_score = initial_context['score']
    dp[initial_state] = (initial_score, initial_context.get('prev_state'), initial_context['health'], initial_context['gold'])
    
    # 优先队列: (f_value, state) where f_value = -score + heuristic
    pq = [(heuristic(start_pos[0], start_pos[1]) - initial_score, initial_state)]
    
    best_at_end = None
    best_score_at_end = float('-inf')
    visited_count = 0  # 计数器用于调试输出

    while pq:
        visited_count += 1
        # 每500次迭代打印一次状态，避免刷屏
        if visited_count % 500 == 0:
            print(f"  [A* Status] Visited states: {visited_count}, Queue size: {len(pq)}")

        _, current = heapq.heappop(pq)
        current_score, _, health, gold = dp[current]
        x, y, resources_mask = current

        if (x, y) == end_pos:
            final_score = current_score + health * 2 + gold * 3
            if final_score > best_score_at_end:
                best_score_at_end = final_score
                best_at_end = current
            continue

        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            next_x, next_y = x + dx, y + dy
            if not (0 <= next_x < size and 0 <= next_y < size and maze.grid[next_y][next_x].type != WALL):
                continue
            
            new_health, new_gold, new_mask, score_change = health, gold, resources_mask, 0
            
            for i, (rx, ry, res_type) in enumerate(resources):
                if (rx, ry) == (next_x, next_y) and not (new_mask & (1 << i)):
                    reward = calculate_reward(res_type, new_health, new_gold)
                    if reward == -float('inf'): continue

                    temp_health, temp_gold = new_health, new_gold
                    if res_type == TRAP:
                        if temp_gold >= TRAP_GOLD_COST: temp_gold -= TRAP_GOLD_COST
                        else: temp_health -= TRAP_HEALTH_COST
                    elif res_type == GOLD: temp_gold += 100
                    elif res_type == HEALTH_POTION: temp_health = min(100, temp_health + 20)
                    elif res_type == BOSS: temp_health -= 30
                    elif res_type == LOCKER: temp_gold -= 30

                    if temp_health > 0:
                        new_health, new_gold = temp_health, temp_gold
                        new_mask |= (1 << i)
                        score_change += reward
                    break
            
            new_state = (next_x, next_y, new_mask)
            new_score = current_score + score_change
            
            if new_state not in dp or new_score > dp[new_state][0]:
                if new_state in dp:
                    print(f"  [A* Update] Found better path to ({next_x},{next_y}), "
                          f"Old score: {dp[new_state][0]:.0f}, New score: {new_score:.0f}")
                
                dp[new_state] = (new_score, current, new_health, new_gold)
                f_value = -new_score + heuristic(next_x, next_y) * 2  # 启发值权重
                heapq.heappush(pq, (f_value, new_state))
                
    return best_at_end, dp

def calculate_dp_path(maze):
    """
    分阶段动态规划，实现"先打Boss，后去终点"的策略。
    """
    all_resources = []
    boss_pos = None
    for y in range(maze.size):
        for x in range(maze.size):
            tile_type = maze.grid[y][x].type
            if tile_type in {GOLD, HEALTH_POTION, LOCKER, TRAP, BOSS}:
                if tile_type == BOSS: boss_pos = (x, y)
                all_resources.append((x, y, tile_type))
    
    # --- 如果没有Boss，则执行单阶段A* ---
    if not boss_pos:
        print("[DP Path] No boss found. Running single-phase A* to end.")
        resources = sorted(all_resources, key=lambda r: r[2], reverse=True)[:18]
        best_end_state, dp = _run_a_star_phase(maze, maze.start_pos, maze.end_pos, resources, 
                                             {'score': 0, 'health': 100, 'gold': 20})
        if not best_end_state: return [], 0
        path, score = [], dp[best_end_state][0]
        curr = best_end_state
        while curr:
            path.append((curr[0], curr[1])); curr = dp[curr][1]
        return list(reversed(path)), score

    # --- 阶段 1: 从起点到Boss ---
    print(f"\n[DP Path] Starting Phase 1: Start {maze.start_pos} -> Boss {boss_pos}")
    resources_p1 = sorted(all_resources, key=lambda r: r[2], reverse=True)[:14]
    best_boss_state, dp1 = _run_a_star_phase(maze, maze.start_pos, boss_pos, resources_p1, 
                                           {'score': 0, 'health': 100, 'gold': 20})

    if not best_boss_state:
        print("[DP Path] CRITICAL: Could not find a path to the boss.")
        return [], 0
    print(f"[DP Path] Phase 1 Complete! Arrived at boss with score {dp1[best_boss_state][0]:.0f}.")

    # --- 准备阶段 2: Boss到终点 ---
    s1_score, _, s1_health, s1_gold = dp1[best_boss_state]
    s1_mask = best_boss_state[2]

    # 计算击败Boss后的状态
    context_p2 = {
        'score': s1_score,
        'health': s1_health,
        'gold': s1_gold,
        'prev_state': best_boss_state # 用于路径回溯
    }

    # 确定阶段2的可用资源 (未在阶段1收集的)
    res_p1_set = set(resources_p1)
    resources_p2 = [res for i, res in enumerate(resources_p1) if not (s1_mask & (1 << i)) and res[2] != BOSS]
    for res in all_resources:
        if res not in res_p1_set and res[2] != BOSS:
            resources_p2.append(res)
    resources_p2 = sorted(resources_p2, key=lambda r: r[2], reverse=True)[:14]

    # --- 阶段 2: 从Boss到终点 ---
    print(f"\n[DP Path] Starting Phase 2: Boss {boss_pos} -> End {maze.end_pos}")
    best_end_state, dp2 = _run_a_star_phase(maze, boss_pos, maze.end_pos, resources_p2, context_p2)

    if not best_end_state:
        print("[DP Path] CRITICAL: Could not find a path from boss to end.")
        return [], 0
    print("[DP Path] Phase 2 Complete! Path to end found.")

    # --- 合并并重建最终路径 ---
    path, final_score = [], dp2[best_end_state][0] + dp2[best_end_state][2]*2 + dp2[best_end_state][3]*3
    
    curr = best_end_state
    while curr and curr != best_boss_state:
        path.append((curr[0], curr[1]))
        curr = dp2[curr][1]
    
    curr = best_boss_state
    while curr:
        path.append((curr[0], curr[1]))
        curr = dp1[curr][1]

    print("[DP Path] Final path reconstruction complete.")
    
    return list(reversed(path)), final_score 
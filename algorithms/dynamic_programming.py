from config import *
import numpy as np
import heapq
from collections import defaultdict

# 为动态规划（路径规划）设定预估成本
# 这些成本现在是DP算法内部的启发式参数，用于评估复杂目标的未来消耗。
ESTIMATED_BOSS_COST_IN_TURNS = 10  # 预估Boss战需要的回合数 (对应资源值扣减)
ESTIMATED_PUZZLE_COST_IN_TRIES = 30 # 预估解谜的尝试次数 (对应资源值扣减)


def _run_a_star_phase(maze, start_pos, end_pos, resources, initial_context):
    """
    A*搜索阶段函数。
    """
    size = maze.size
    dp = {}

    def heuristic(x, y):
        return abs(x - end_pos[0]) + abs(y - end_pos[1])

    # 动态奖励计算函数 - 已更新以反映新的资源规则
    def calculate_reward(res_type, health, gold):
        if res_type == GOLD: return 50
        if res_type == TRAP: return -30
        
        # 宝箱和Boss的价值评估考虑了未来的消耗
        if res_type == LOCKER: return 100 - ESTIMATED_PUZZLE_COST_IN_TRIES
        if res_type == BOSS: return 600 - ESTIMATED_BOSS_COST_IN_TURNS if health > 30 else -float('inf')
        return 0

    # 初始化A*搜索的起点
    initial_state = (start_pos[0], start_pos[1], 0)
    initial_score = initial_context['score']
    dp[initial_state] = (
        initial_score,
        initial_context.get('prev_state'),
        initial_context['health'],
        initial_context['gold']
    )

    pq = [(heuristic(start_pos[0], start_pos[1]) - initial_score, initial_state)]

    best_at_end = None
    best_score_at_end = float('-inf')
    visited_count = 0

    while pq:
        visited_count += 1
        if visited_count % 500 == 0:
            print(f"  [A* Status] Visited states: {visited_count}, Queue size: {len(pq)}")

        _, current = heapq.heappop(pq)
        current_score, _, health, gold = dp[current]
        x, y, resources_mask = current

        if (x, y) == end_pos:
            # 到达终点时，计算最终得分（包括剩余生命和金币的奖励）
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

                    # 模拟拾取资源后的状态变化（这部分用于路径模拟，非最终计分）
                    temp_health, temp_gold = new_health, new_gold
                    if res_type == TRAP:
                        # 简单模拟生命值下降
                        temp_health -= 20
                    elif res_type == GOLD:
                        temp_gold += 10
                    
                    if temp_health > 0:
                        new_health, new_gold = temp_health, temp_gold
                        new_mask |= (1 << i)
                        score_change += reward
                    break

            new_state = (next_x, next_y, new_mask)
            new_score = current_score + score_change - 1

            if new_state not in dp or new_score > dp[new_state][0]:
                dp[new_state] = (new_score, current, new_health, new_gold)
                f_value = -new_score + heuristic(next_x, next_y)
                heapq.heappush(pq, (f_value, new_state))

    return best_at_end, dp


def calculate_dp_path(maze):
    """
    核心入口函数
    """
    all_resources = []
    boss_pos = None
    for y in range(maze.size):
        for x in range(maze.size):
            tile_type = maze.grid[y][x].type
            if tile_type in {GOLD, LOCKER, TRAP, BOSS}:
                if tile_type == BOSS: boss_pos = (x, y)
                all_resources.append((x, y, tile_type))

    if not boss_pos:
        print("[DP Path] No boss found. Running single-phase A* to end.")
        resources = sorted(all_resources, key=lambda r: r[2], reverse=True)[:18]
        best_end_state, dp = _run_a_star_phase(maze, maze.start_pos, maze.end_pos, resources,
                                               {'score': 0, 'health': 100, 'gold': 20})
        if not best_end_state: return [], 0
        path, score = [], dp[best_end_state][0]
        curr = best_end_state
        while curr:
            path.append((curr[0], curr[1]));
            curr = dp[curr][1]
        return list(reversed(path)), score

    print(f"\n[DP Path] Starting Phase 1: Start {maze.start_pos} -> Boss {boss_pos}")
    
    resources_by_type = defaultdict(list)
    for res in all_resources:
        if res[2] != BOSS:
            resources_by_type[res[2]].append(res)

    # 资源配额现在只包含金币
    if maze.size <= 15:
        quotas = {GOLD: 20}
    else:
        quotas = {GOLD: 30}

    resources_p1 = []
    sorted_types = sorted(quotas.keys(), reverse=True)

    for res_type in sorted_types:
        quota = quotas[res_type]
        candidates = sorted(
            resources_by_type[res_type],
            key=lambda r: (abs(r[0] - maze.start_pos[0]) + abs(r[1] - maze.start_pos[1])) + 
                          (abs(r[0] - boss_pos[0]) + abs(r[1] - boss_pos[1]))
        )
        resources_p1.extend(candidates[:quota])

    best_boss_state, dp1 = _run_a_star_phase(maze, maze.start_pos, boss_pos, resources_p1,
                                             {'score': 0, 'health': 100, 'gold': 20})

    if not best_boss_state:
        print("[DP Path] CRITICAL: Could not find a path to the boss.")
        return [], 0
    print(f"[DP Path] Phase 1 Complete! Arrived at boss with score {dp1[best_boss_state][0]:.0f}.")

    s1_score, _, s1_health, s1_gold = dp1[best_boss_state]
    s1_mask = best_boss_state[2]

    context_p2 = {
        'score': s1_score,
        'health': s1_health,
        'gold': s1_gold,
        'prev_state': best_boss_state
    }

    res_p1_set = set(resources_p1)
    resources_p2 = [res for i, res in enumerate(resources_p1) if not (s1_mask & (1 << i)) and res[2] != BOSS]
    for res in all_resources:
        if res not in res_p1_set and res[2] != BOSS:
            resources_p2.append(res)
    resources_p2 = sorted(resources_p2, key=lambda r: r[2], reverse=True)[:14]

    print(f"\n[DP Path] Starting Phase 2: Boss {boss_pos} -> End {maze.end_pos}")
    best_end_state, dp2 = _run_a_star_phase(maze, boss_pos, maze.end_pos, resources_p2, context_p2)

    if not best_end_state:
        print("[DP Path] CRITICAL: Could not find a path from boss to end.")
        return [], 0
    print("[DP Path] Phase 2 Complete! Path to end found.")

    path, final_score = [], dp2[best_end_state][0] + dp2[best_end_state][2] * 2 + dp2[best_end_state][3] * 3

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

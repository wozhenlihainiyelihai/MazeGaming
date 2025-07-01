import heapq

class BattleNode:
    """
    用于解决Boss车轮战问题的状态节点。
    """
    def __init__(self, state, path, g_cost, h_cost):
        # 状态元组: (当前Boss索引, 当前Boss剩余HP, 技能冷却状态元组)
        self.state = state
        # 到达此状态的技能序列
        self.path = path
        # g_cost: 实际成本 (已用回合数)
        self.g = g_cost
        # h_cost: 启发式成本 (预估剩余回合数)
        self.h = h_cost
        # f_cost: 节点的总评估成本 (f = g + h)
        self.f = self.g + self.h

    def __lt__(self, other):
        """使节点可以在优先队列中基于 f 值排序。"""
        return self.f < other.f

def solve_boss_gauntlet(boss_hp_list, skills):
    """
    使用分支界限法 (A* 算法) 寻找击败所有Boss的最短技能序列。
    """
    num_skills = len(skills)

    # --- 1. 计算启发函数所需的平均伤害 ---
    if not skills:
        return {"turns": -1, "sequence": []}
    
    total_damage = sum(s[0] for s in skills)
    average_damage_per_turn = total_damage / num_skills if num_skills > 0 else 0
    
    if average_damage_per_turn <= 0:
        return {"turns": -1, "sequence": []}

    # 预先计算从每个阶段开始的剩余总血量，用于优化启发函数
    total_hp_remaining_from_stage = [0] * (len(boss_hp_list) + 1)
    for i in range(len(boss_hp_list) - 1, -1, -1):
        total_hp_remaining_from_stage[i] = boss_hp_list[i] + total_hp_remaining_from_stage[i+1]

    def heuristic(state):
        """启发函数 h(n): 预估击败所有剩余Boss所需的最少回合数。"""
        boss_index, current_boss_hp, _ = state
        # 总计需要造成的伤害 = 当前Boss剩余HP + 后续所有Boss的总HP
        total_hp_to_deal = current_boss_hp + total_hp_remaining_from_stage[boss_index + 1]
        return total_hp_to_deal / average_damage_per_turn

    # --- 2. 初始化搜索起点 ---
    # 初始状态: (Boss索引=0, Boss 1的HP, (所有技能冷却都为0,))
    initial_state = (0, boss_hp_list[0], tuple([0] * num_skills))
    initial_h = heuristic(initial_state)
    start_node = BattleNode(initial_state, [], 0, initial_h)

    pq = [start_node]
    visited = {initial_state: 0}

    # --- 3. A* 搜索循环 ---
    while pq:
        current_node = heapq.heappop(pq)
        
        if current_node.g > visited[current_node.state]:
            continue

        boss_index, boss_hp, cooldowns = current_node.state
        
        # 扩展节点：遍历所有技能，如果冷却完毕则尝试使用
        for i in range(num_skills):
            if cooldowns[i] == 0: # 技能可用
                skill_damage, skill_cd = skills[i]
                
                # 计算新状态
                new_g = current_node.g + 1
                new_path = current_node.path + [skills[i]]
                new_boss_hp = boss_hp - skill_damage
                
                # 更新所有技能的冷却时间：所有CD减1
                next_turn_cooldowns = [max(0, cd - 1) for cd in cooldowns]
                # 重置刚使用过的技能的冷却时间
                next_turn_cooldowns[i] = skill_cd
                final_cooldowns_tuple = tuple(next_turn_cooldowns)

                if new_boss_hp > 0: # 当前Boss未被击败
                    new_state = (boss_index, new_boss_hp, final_cooldowns_tuple)
                    if new_state not in visited or new_g < visited[new_state]:
                        visited[new_state] = new_g
                        h = heuristic(new_state)
                        new_node = BattleNode(new_state, new_path, new_g, h)
                        heapq.heappush(pq, new_node)
                else: # 当前Boss被击败
                    new_boss_index = boss_index + 1
                    
                    if new_boss_index >= len(boss_hp_list): # 所有Boss都被击败
                        return {"turns": new_g, "sequence": new_path}
                    
                    # 否则，进入下一个Boss的战斗
                    next_boss_hp = boss_hp_list[new_boss_index]
                    new_state = (new_boss_index, next_boss_hp, final_cooldowns_tuple)
                    if new_state not in visited or new_g < visited[new_state]:
                        visited[new_state] = new_g
                        h = heuristic(new_state)
                        new_node = BattleNode(new_state, new_path, new_g, h)
                        heapq.heappush(pq, new_node)

    return {"turns": -1, "sequence": []}

def find_best_attack_sequence(player, boss, skills):
    """
    保留此函数名作为game.py的统一入口，但内部逻辑已完全改变。
    注意：此处的 player 和 boss 对象已不再使用，所有数据来自skills和boss.health（作为列表）。
    这是一个适应性修改，以避免大规模重构 game.py。
    """
    # 关键：我们将 game.py 传来的 boss.health（单个值）视为 boss_hp_list。
    # 这意味着在 game.py 中，我们需要将 B 列表赋值给 boss.health。
    boss_hp_list = boss.health
    
    return solve_boss_gauntlet(boss_hp_list, skills)
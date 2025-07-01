import heapq

# 全局变量用于让启发函数访问Boss血量列表
B_HPS = [] 

def heuristic(boss_idx, boss_hp):
    if boss_idx >= len(B_HPS):
        return 0
    remaining_hp = boss_hp + sum(B_HPS[boss_idx+1:])
    return remaining_hp / 6

def solve_boss_gauntlet(boss_hp_list, skills):
    """
    使用A*算法
    """
    global B_HPS
    B_HPS = boss_hp_list
    num_skills = len(skills)

    initial_state = (0, boss_hp_list[0], tuple([0] * num_skills))

    entry_count = 0 # 初始化一个唯一的计数器
    pq = [(0 + heuristic(0, boss_hp_list[0]), 0, entry_count, [], initial_state)]
    entry_count += 1
    
    visited = set()

    while pq:
        f, g, _, path, state = heapq.heappop(pq)
        
        boss_idx, boss_hp, cooldowns = state

        if (boss_idx, boss_hp, cooldowns) in visited:
            continue
        visited.add((boss_idx, boss_hp, cooldowns))

        if boss_idx >= len(boss_hp_list):
            return {"turns": g, "sequence": path}

        for i in range(num_skills):
            if cooldowns[i] == 0:
                current_skill = skills[i]
                dmg = current_skill['Damage']
                cd = current_skill['Cooldown']
                
                new_g = g + 1
                new_path = path + [current_skill]
                next_hp = boss_hp - dmg

                next_cooldowns = list(cooldowns)
                next_cooldowns[i] = cd
                for j in range(num_skills):
                    if j != i and next_cooldowns[j] > 0:
                        next_cooldowns[j] -= 1
                final_cooldowns_tuple = tuple(next_cooldowns)

                if next_hp <= 0:
                    new_boss_idx = boss_idx + 1
                    if new_boss_idx >= len(boss_hp_list):
                        return {"turns": new_g, "sequence": new_path}
                    
                    next_boss_hp = boss_hp_list[new_boss_idx]
                    next_state = (new_boss_idx, next_boss_hp, final_cooldowns_tuple)
                else:
                    next_state = (boss_idx, next_hp, final_cooldowns_tuple)

                h = heuristic(next_state[0], next_state[1])
                
                heapq.heappush(pq, (new_g + h, new_g, entry_count, new_path, next_state))
                entry_count += 1 
                
    return {"turns": -1, "sequence": []}


def find_best_attack_sequence(player, boss, skills):
    """
    统一的入口函数，负责将不同格式的数据适配并传入核心求解器。
    """
    boss_hp_list = boss.health
    
    if skills and isinstance(skills[0], list):
        skills_dict = [{"Damage": d, "Cooldown": c} for d, c in skills]
    else:
        skills_dict = skills
        
    return solve_boss_gauntlet(boss_hp_list, skills_dict)

import heapq
from config import *

class BattleNode:
    """用于分支限界搜索的节点"""
    def __init__(self, turns, boss_hp, skill_cooldowns, available_skills, path, player):
        self.g = turns
        self.boss_hp = boss_hp
        self.skill_cooldowns = skill_cooldowns
        self.available_skills = available_skills
        self.path = path
        self.player = player
        self.h = self._get_heuristic_turns()
        self.cost = self.g + self.h

    def __lt__(self, other):
        return self.cost < other.cost

    def _get_heuristic_turns(self):
        """更智能的启发函数，考虑所有*可用*技能的平均伤害"""
        damages = [self.player.attack]
        for skill_id in self.available_skills:
            skill_info = SKILLS.get(skill_id)
            if skill_info and 'damage_multiplier' in skill_info['effect']:
                damages.append(self.player.attack * skill_info['effect']['damage_multiplier'])
        avg_damage = sum(damages) / len(damages) if damages else self.player.attack
        return (self.boss_hp / avg_damage) if avg_damage > 0 else float('inf')

def find_best_attack_sequence(player, boss):
    """【已更新】使用分支限界法，处理一次性技能"""
    pq = []
    initial_skills = player.skills.copy()
    initial_cooldowns = player.skill_cooldowns.copy()
    
    # 【BUG修复】修正了构造函数参数的顺序
    # Corrected the order of arguments in the constructor call
    initial_node = BattleNode(0, boss.health, initial_cooldowns, initial_skills, [], player)
    heapq.heappush(pq, initial_node)
    
    best_path, min_turns = None, float('inf')

    while pq:
        current_node = heapq.heappop(pq)
        if current_node.cost >= min_turns: continue
        if current_node.boss_hp <= 0:
            if current_node.g < min_turns:
                min_turns, best_path = current_node.g, current_node.path
            continue

        next_turns = current_node.g + 1
        
        # 动作1: 普通攻击
        # 普通攻击不影响技能冷却，但我们需要传递下一回合的冷却状态
        next_cooldowns_for_attack = {k: max(0, v - 1) for k, v in current_node.skill_cooldowns.items()}
        attack_node = BattleNode(next_turns, current_node.boss_hp - player.attack, next_cooldowns_for_attack, current_node.available_skills, current_node.path + ["attack"], player)
        if attack_node.cost < min_turns: heapq.heappush(pq, attack_node)

        # 动作2: 遍历所有当前模拟中可用的技能
        for skill_id in current_node.available_skills:
            if current_node.skill_cooldowns.get(skill_id, 0) == 0:
                skill_info = SKILLS[skill_id]
                next_available_skills = current_node.available_skills - {skill_id}
                
                temp_cooldowns = next_cooldowns_for_attack.copy()
                if 'cooldown' in skill_info: # 检查是否存在冷却键
                    temp_cooldowns[skill_id] = skill_info['cooldown']

                temp_boss_hp = current_node.boss_hp
                if 'damage_multiplier' in skill_info['effect']:
                    temp_boss_hp -= player.attack * skill_info['effect']['damage_multiplier']
                
                skill_node = BattleNode(next_turns, temp_boss_hp, temp_cooldowns, next_available_skills, current_node.path + [skill_id], player)
                if skill_node.cost < min_turns: heapq.heappush(pq, skill_node)

    if best_path: return best_path[0]
    return "attack"

def get_heuristic_turns(player):
    """一个独立的启发函数，供AI在探索时评估Boss威胁"""
    damages = [player.attack]
    for skill_id in player.skills:
        skill_info = SKILLS.get(skill_id)
        if skill_info and 'damage_multiplier' in skill_info['effect']:
            damages.append(player.attack * skill_info['effect']['damage_multiplier'])
    avg_damage = sum(damages) / len(damages) if damages else player.attack
    return (BOSS_MAX_HEALTH / avg_damage) if avg_damage > 0 else float('inf')

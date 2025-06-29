import heapq
from config import *
from entities import AIPlayer, Boss 

class BattleNode:
    def __init__(self, turns, boss_hp, player_hp, player_gold, available_skills, path, player_base_attack):
        self.g = turns
        self.boss_hp = boss_hp
        self.player_hp = player_hp
        self.player_gold = player_gold
        self.available_skills = available_skills
        self.path = path
        self.player_base_attack = player_base_attack
        self.h = self._get_heuristic_turns()
        self.cost = self.g + self.h

    def __lt__(self, other):
        return self.cost < other.cost

    def _get_heuristic_turns(self):
        """启发函数现在会考虑所有可能的伤害输出方式"""
        damages = [self.player_base_attack]
        # 考虑技能伤害
        for skill_id in self.available_skills:
            skill_info = SKILLS.get(skill_id)
            if skill_info and 'damage_multiplier' in skill_info['effect']:
                damages.append(self.player_base_attack * skill_info['effect']['damage_multiplier'])
        # 考虑资源换攻击
        if self.player_gold >= GOLD_COST_FOR_BOOST:
            damages.append(self.player_base_attack + ATTACK_BOOST_AMOUNT)
        if self.player_hp > HEALTH_COST_FOR_BOOST:
            damages.append(self.player_base_attack + ATTACK_BOOST_AMOUNT)
            
        avg_damage = sum(damages) / len(damages) if damages else self.player_base_attack
        return (self.boss_hp / avg_damage) if avg_damage > 0 else float('inf')

def analyze_battle_outcome(player, boss):
    """
    战斗模拟器现在会评估包括资源换攻击在内的所有战术。
    """
    pq = []
    initial_node = BattleNode(0, boss.health, player.health, player.gold, player.skills.copy(), [], player.attack)
    heapq.heappush(pq, initial_node)
    
    # 状态定义：(boss血量, 玩家血量, 玩家金币, 可用技能元组)
    visited = set()

    while pq:
        current_node = heapq.heappop(pq)
        
        state = (current_node.boss_hp, current_node.player_hp, current_node.player_gold, tuple(sorted(current_node.available_skills)))
        if state in visited:
            continue
        visited.add(state)

        # 找到胜利路径
        if current_node.boss_hp <= 0:
            turns_to_win = current_node.g
            # 初始血量 - 最终血量 = 损失血量
            health_lost = player.health - current_node.player_hp
            
            return {
                "survives": current_node.player_hp > 0,
                "turns": turns_to_win,
                "health_lost": health_lost,
                "sequence": current_node.path
            }

        # 如果玩家已死，则此路不通
        if current_node.player_hp <= 0:
            continue

        next_turns = current_node.g + 1
        # Boss在本回合的反击伤害（如果没被冰冻）
        boss_retaliation_damage = boss.attack if not (current_node.path and current_node.path[-1] == 'frost_nova') else 0

        # 行动1: 普通攻击
        player_hp_after_attack = current_node.player_hp - boss_retaliation_damage
        attack_node = BattleNode(next_turns, current_node.boss_hp - current_node.player_base_attack, player_hp_after_attack, current_node.player_gold, current_node.available_skills, current_node.path + ["attack"], current_node.player_base_attack)
        heapq.heappush(pq, attack_node)

        # 行动2: 使用技能
        for skill_id in list(current_node.available_skills):
            skill_info = SKILLS[skill_id]
            next_skills = current_node.available_skills - {skill_id}
            
            temp_boss_hp = current_node.boss_hp
            if 'damage_multiplier' in skill_info['effect']:
                temp_boss_hp -= current_node.player_base_attack * skill_info['effect']['damage_multiplier']

            # 使用冰冻技能可以免受本次反击
            player_hp_after_skill = current_node.player_hp - (0 if 'freeze_turns' in skill_info['effect'] else boss_retaliation_damage)

            skill_node = BattleNode(next_turns, temp_boss_hp, player_hp_after_skill, current_node.player_gold, next_skills, current_node.path + [skill_id], current_node.player_base_attack)
            heapq.heappush(pq, skill_node)

        #行动3: 消耗金币提升攻击
        if current_node.player_gold >= GOLD_COST_FOR_BOOST:
            player_hp_after_boost = current_node.player_hp - boss_retaliation_damage
            boost_gold_node = BattleNode(next_turns, current_node.boss_hp - (current_node.player_base_attack + ATTACK_BOOST_AMOUNT), player_hp_after_boost, current_node.player_gold - GOLD_COST_FOR_BOOST, current_node.available_skills, current_node.path + ["boost_gold_attack"], current_node.player_base_attack)
            heapq.heappush(pq, boost_gold_node)
            
        # 行动4: 消耗生命提升攻击
        if current_node.player_hp > HEALTH_COST_FOR_BOOST:
            # 先扣除消耗的生命，再扣除Boss反击的伤害
            player_hp_after_boost = (current_node.player_hp - HEALTH_COST_FOR_BOOST) - boss_retaliation_damage
            boost_health_node = BattleNode(next_turns, current_node.boss_hp - (current_node.player_base_attack + ATTACK_BOOST_AMOUNT), player_hp_after_boost, current_node.player_gold, current_node.available_skills, current_node.path + ["boost_health_attack"], current_node.player_base_attack)
            heapq.heappush(pq, boost_health_node)

    # 如果队列为空都没找到获胜路径
    return {"survives": False, "turns": float('inf'), "health_lost": float('inf'), "sequence": []}


def find_best_attack_sequence(player, boss):
    """调用新的战斗模拟器，只返回最佳的第一步行动。"""
    analysis = analyze_battle_outcome(player, boss)
    if analysis and analysis["sequence"]:
        return analysis["sequence"][0]
    return "attack"
import random
import json
from config import *
from utils import bfs_path_avoiding_history
from algorithms.branch_and_bound import find_best_attack_sequence

def get_tile_value(tile_type, player, maze=None, pos=None):
    """
    Calculates the strategic value of a given tile for the greedy algorithm.
    """
    if tile_type == GOLD: return GOLD_REWARD * SCORE_PER_GOLD
    if tile_type == HEALTH_POTION:
        if player.health >= 100: return 0
        return (POTION_HEAL_AMOUNT * SCORE_PER_HEALTH) + (100 - player.health)
    if tile_type == LOCKER: return SCORE_PER_DIAMOND + 20
    if tile_type == TRAP: return -50 if player.gold < TRAP_GOLD_COST else -10
    if tile_type == SHOP:
        can_afford = any(skill not in player.skills and player.diamonds >= SKILLS[skill]['cost'] for skill in SKILLS)
        return 40 if can_afford else 0
    
    if tile_type == BOSS:
        try:
            with open('battle_config.json', 'r') as f:
                config = json.load(f)

            from entities import AIPlayer, Boss
            
            sim_player = AIPlayer()
            sim_boss = Boss()

            # --- THE FIX IS HERE ---
            # We must explicitly assign the LIST of boss healths from the config
            # to the simulated boss object's health attribute.
            sim_boss.health = config['B']
            # --- END OF FIX ---

            skills = config['PlayerSkills']
            
            analysis = find_best_attack_sequence(sim_player, sim_boss, skills)

            if analysis and analysis['turns'] != -1:
                return SCORE_BOSS_KILL
            else:
                return -1000

        except (FileNotFoundError, KeyError):
            return -1000
            
    return 0

def set_next_global_target(player, maze):
    """
    Scans the entire map to find the most valuable long-term target.
    """
    potential_targets = []
    history_set = set(player.path_history)
    for r in range(maze.size):
        for c in range(maze.size):
            # We only evaluate the BOSS tile type here, the player object itself is just a placeholder
            # for this specific calculation, as player health is infinite.
            value = get_tile_value(maze.grid[r][c].type, player, maze)
            if value > 0:
                path = bfs_path_avoiding_history(start=(player.x, player.y), end=(c, r), maze_grid=maze.grid, history_path=history_set)
                if path:
                    distance = len(path) - 1
                    if distance > 0:
                        potential_targets.append({'score': value / (distance ** 1.5), 'pos': (c, r)})
    if potential_targets:
        best_target = max(potential_targets, key=lambda x: x['score'])
        player.temporary_target = best_target['pos']
    else:
        player.temporary_target = None
    player.needs_new_target = False

def decide_move_greedy(player, maze):
    """
    The main decision-making logic for the greedy algorithm.
    """
    if player.needs_new_target:
        set_next_global_target(player, maze)

    history_set = set(player.path_history)
    
    if player.temporary_target:
        path = bfs_path_avoiding_history(start=(player.x, player.y), end=player.temporary_target, maze_grid=maze.grid, history_path=history_set)
        if path and len(path) > 1:
            return (path[1][0] - player.x, path[1][1] - player.y)

    view_radius = 1
    local_targets = []
    for r_offset in range(-view_radius, view_radius + 1):
        for c_offset in range(-view_radius, view_radius + 1):
            if r_offset == 0 and c_offset == 0: continue
            tx, ty = player.x + c_offset, player.y + r_offset
            if (tx, ty) not in history_set and (0 <= tx < maze.size and 0 <= ty < maze.size and maze.grid[ty][tx].type != WALL):
                value = get_tile_value(maze.grid[ty][tx].type, player, maze)
                if value > 0:
                    dist = abs(tx - player.x) + abs(ty - player.y)
                    local_targets.append({'score': value / (dist**1.5), 'pos': (tx, ty)})
    
    if local_targets:
        best_local = max(local_targets, key=lambda x: x['score'])
        path = bfs_path_avoiding_history(start=(player.x, player.y), end=best_local['pos'], maze_grid=maze.grid, history_path=history_set)
        if path and len(path) > 1:
            return (path[1][0] - player.x, path[1][1] - player.y)

    path_to_end = bfs_path_avoiding_history(start=(player.x, player.y), end=maze.end_pos, maze_grid=maze.grid, history_path=history_set)
    if path_to_end and len(path_to_end) > 1:
        return (path_to_end[1][0] - player.x, path_to_end[1][1] - player.y)
        
    if player.path_history and len(player.path_history) > 1:
        return (player.path_history[-2][0] - player.x, player.path_history[-2][1] - player.y)

    return (0, 0)
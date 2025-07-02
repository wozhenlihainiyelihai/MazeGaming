import random
from config import *
from utils import bfs_path_avoiding_history

# --- REVISED AND OPTIMIZED ---
def get_tile_value(tile_type, player):
    """
    Calculates the strategic value of a given tile for the greedy algorithm.
    This is a lightweight, high-performance version.
    
    Args:
        tile_type (int): The type of the tile (e.g., GOLD, BOSS).
        player (AIPlayer): The player object, used to get current status like health.

    Returns:
        int: The calculated strategic value of the tile.
    """
    if tile_type == GOLD:
        return SCORE_PER_GOLD * GOLD_REWARD
    if tile_type == HEALTH_POTION:
        # The value of a potion increases as the player's health decreases.
        if player.health >= player.max_health:
            return 0
        return (POTION_HEAL_AMOUNT * SCORE_PER_HEALTH) + (player.max_health - player.health)
    if tile_type == LOCKER:
        # A high, constant value for unlocking puzzles.
        return SCORE_LOCKER_UNLOCK
    if tile_type == TRAP:
        # A penalty. It's less severe if the player has enough gold to disarm it.
        return -50 if player.gold < TRAP_GOLD_COST else -10
    if tile_type == SHOP:
        # For simplicity, we assign a moderate constant value. A more complex check
        # could see if the player can afford skills they don't have.
        return 40
    if tile_type == BOSS:
        # --- CRITICAL FIX ---
        # Replaced the expensive, slow simulation with a simple and fast heuristic.
        # The AI will only consider the Boss a valuable target if its health is high.
        if player.health > 60:  # A sensible health threshold to consider fighting the boss.
            return SCORE_BOSS_KILL
        else:
            return -1000  # A large penalty to actively avoid the boss when at low health.
    return 0

# --- REVISED AND OPTIMIZED ---
def find_best_global_target(player, maze):
    """
    Finds the best long-term target on the map based on value and distance.
    This function scans the map for all valuable items and picks the one with the
    best score, where score is a function of value and distance.

    Args:
        player (AIPlayer): The AI player instance.
        maze (Maze): The maze instance.
    """
    potential_targets = []
    history_set = set(player.path_history)

    # OPTIMIZATION NOTE: For even better performance, this list of valuable tiles
    # could be cached in the Game or AIPlayer object when a new game starts,
    # avoiding the need to scan the entire grid every time a new target is needed.
    for r in range(maze.size):
        for c in range(maze.size):
            tile_type = maze.grid[r][c].type
            # We only evaluate tiles that have a potential positive value.
            if tile_type in {GOLD, HEALTH_POTION, LOCKER, BOSS, SHOP}:
                value = get_tile_value(tile_type, player)
                if value > 0:
                    # Find a path to calculate the real distance.
                    path = bfs_path_avoiding_history(
                        start=(player.x, player.y),
                        end=(c, r),
                        maze_grid=maze.grid,
                        history_path=history_set
                    )
                    if path:
                        distance = len(path) - 1
                        if distance > 0:
                            # The score formula prioritizes closer, high-value items.
                            score = value / (distance ** 1.5)
                            potential_targets.append({'score': score, 'pos': (c, r)})

    if potential_targets:
        best_target = max(potential_targets, key=lambda x: x['score'])
        player.temporary_target = best_target['pos']
    else:
        # If no valuable items are reachable, clear the target.
        player.temporary_target = None

    player.needs_new_target = False

# --- REVISED AND OPTIMIZED ---
def decide_move_greedy(player, maze):
    """
    The main decision-making logic for the greedy algorithm.
    This revised version has a clearer priority:
    1. Handle critical local needs (like a nearby health potion when health is low).
    2. Pursue the best long-term global target.
    3. If no targets, head for the exit.
    4. If stuck, backtrack.

    Args:
        player (AIPlayer): The AI player instance.
        maze (Maze): The maze instance.

    Returns:
        tuple: The (dx, dy) move for the player.
    """
    history_set = set(player.path_history)

    # 1. Check for critical local opportunities (e.g., low health and nearby potion).
    if player.health < 40:
        view_radius = 2  # Look a bit further when in critical need.
        for r_offset in range(-view_radius, view_radius + 1):
            for c_offset in range(-view_radius, view_radius + 1):
                if r_offset == 0 and c_offset == 0: continue
                tx, ty = player.x + c_offset, player.y + r_offset
                if 0 <= tx < maze.size and 0 <= ty < maze.size:
                    tile = maze.grid[ty][tx]
                    if tile.type == HEALTH_POTION:
                        # If a health potion is nearby and needed, make it the top priority.
                        path = bfs_path_avoiding_history(start=(player.x, player.y), end=(tx, ty), maze_grid=maze.grid, history_path=history_set)
                        if path and len(path) > 1:
                            return (path[1][0] - player.x, path[1][1] - player.y)

    # 2. If no critical need, find or follow a global target.
    if player.needs_new_target or player.temporary_target is None:
        find_best_global_target(player, maze)

    # If a global target is set, move towards it.
    if player.temporary_target:
        target_pos = player.temporary_target
        # Verify the target is still valid (hasn't been collected already).
        if maze.grid[target_pos[1]][target_pos[0]].type == PATH:
            player.needs_new_target = True  # Target is gone, find a new one next turn.
        else:
            path = bfs_path_avoiding_history(start=(player.x, player.y), end=player.temporary_target, maze_grid=maze.grid, history_path=history_set)
            if path and len(path) > 1:
                return (path[1][0] - player.x, path[1][1] - player.y)
            else:
                # Path to target is blocked, find a new one.
                player.needs_new_target = True

    # 3. Fallback: If no target can be found, move towards the end point.
    path_to_end = bfs_path_avoiding_history(start=(player.x, player.y), end=maze.end_pos, maze_grid=maze.grid, history_path=history_set)
    if path_to_end and len(path_to_end) > 1:
        return (path_to_end[1][0] - player.x, path_to_end[1][1] - player.y)

    # 4. Last resort: If stuck, try to move to any valid adjacent cell not in recent history.
    for dx, dy in sorted([(0,1), (0,-1), (1,0), (-1,0)], key=lambda k: random.random()): # Randomize direction
        nx, ny = player.x + dx, player.y + dy
        if (nx, ny) not in history_set and (0 <= nx < maze.size and 0 <= ny < maze.size and maze.grid[ny][nx].type != WALL):
            return (dx, dy)
    
    # If all else fails (e.g., trapped in a 1x1 space), don't move.
    return (0, 0)

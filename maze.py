#包含Maze类，使用分治法生成迷宫，并根据规则智能地放置所有游戏元素。

import pygame
import random
from collections import deque
from config import *
from entities import Tile
from utils import create_all_icons

class Maze:
    """迷宫生成与管理类"""
    def __init__(self, size):
        self.size = size if size % 2 != 0 else size + 1
        self.grid = [[Tile(PATH) for _ in range(self.size)] for _ in range(self.size)]
        self.cell_width = MAZE_AREA_SIZE // self.size
        self.cell_height = MAZE_AREA_SIZE // self.size
        
        self._generate_base_maze()
        self._place_start_end_points()
        main_path = self._find_main_path()
        if main_path:
            large_treasure_rooms = self._create_gated_treasure_rooms(main_path)
            self._place_boss(main_path, large_treasure_rooms)
            self._place_traps_on_main_path(main_path)
            
        # 【功能新增】保存一份原始地图的快照，用于重置
        self.pristine_grid = [[Tile(tile.type) for tile in row] for row in self.grid]
        self._load_icons()

    def reset(self):
        """【功能新增】将地图恢复到初始状态"""
        self.grid = [[Tile(tile.type) for tile in row] for row in self.pristine_grid]

    def _load_icons(self):
        self.tile_icons = {}
        icon_size = int(min(self.cell_width, self.cell_height) * 0.7)
        if icon_size <= 0: return
        self.tile_icons = create_all_icons(icon_size)

    def _generate_base_maze(self):
        for i in range(self.size):
            self.grid[0][i].type = WALL
            self.grid[self.size - 1][i].type = WALL
            self.grid[i][0].type = WALL
            self.grid[i][self.size - 1].type = WALL
        self._divide(1, 1, self.size - 2, self.size - 2)

    def _divide(self, x, y, width, height):
        if width < 2 or height < 2: return
        horizontal = width < height or (width == height and random.choice([True, False]))
        if horizontal:
            wall_y = y + (random.randrange(height // 2) * 2 + 1)
            passage_x = x + (random.randrange((width + 1) // 2) * 2)
            for i in range(x, x + width + 1): self.grid[wall_y][i].type = WALL
            self.grid[wall_y][passage_x].type = PATH
            self._divide(x, y, width, wall_y - y)
            self._divide(x, wall_y + 1, width, y + height - (wall_y + 1))
        else:
            wall_x = x + (random.randrange(width // 2) * 2 + 1)
            passage_y = y + (random.randrange((height + 1) // 2) * 2)
            for i in range(y, y + height + 1): self.grid[i][wall_x].type = WALL
            self.grid[passage_y][wall_x].type = PATH
            self._divide(x, y, wall_x - x, height)
            self._divide(wall_x + 1, y, x + width - (wall_x + 1), height)

    def _place_start_end_points(self):
        self.start_pos = (1, 1)
        self.end_pos = (self.size - 2, self.size - 2)
        self.grid[self.start_pos[1]][self.start_pos[0]].type = START
        self.grid[self.end_pos[1]][self.end_pos[0]].type = END
    
    def _find_main_path(self):
        queue = deque([(self.start_pos, [self.start_pos])])
        visited = {self.start_pos}
        while queue:
            (x, y), path = queue.popleft()
            if (x, y) == self.end_pos: return path
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                next_x, next_y = x + dx, y + dy
                if (0 <= next_x < self.size and 0 <= next_y < self.size and 
                    self.grid[next_y][next_x].type != WALL and (next_x, next_y) not in visited):
                    visited.add((next_x, next_y))
                    queue.append(((next_x, next_y), path + [(next_x, next_y)]))
        return []

    def _place_boss(self, main_path, large_treasure_rooms):
        # Implementation remains the same...
        if random.random() < 0.6 or not large_treasure_rooms:
            if len(main_path) > 2:
                start_index, end_index = int(len(main_path) * 0.2), int(len(main_path) * 0.8)
                if start_index < end_index:
                    boss_pos = random.choice(main_path[start_index:end_index])
                    self.grid[boss_pos[1]][boss_pos[0]].type = BOSS
        else:
            chosen_room_tiles = random.choice(large_treasure_rooms)
            gate_pos = None
            for tile_pos in chosen_room_tiles:
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    if (tile_pos[0] + dx, tile_pos[1] + dy) in main_path:
                        gate_pos = (tile_pos[0] + dx, tile_pos[1] + dy); break
                if gate_pos: break
            if gate_pos:
                farthest_tile, max_dist = None, -1
                for tile_pos in chosen_room_tiles:
                    dist = abs(tile_pos[0] - gate_pos[0]) + abs(tile_pos[1] - gate_pos[1])
                    if dist > max_dist: max_dist, farthest_tile = dist, tile_pos
                if farthest_tile: self.grid[farthest_tile[1]][farthest_tile[0]].type = BOSS

    def _create_gated_treasure_rooms(self, main_path):
        # Implementation remains the same...
        main_path_set = set(main_path); processed_branches = set(); large_rooms_tiles = []
        for r in range(1, self.size - 1):
            for c in range(1, self.size - 1):
                current_pos = (c, r)
                if (self.grid[r][c].type == PATH and current_pos not in main_path_set and 
                    current_pos not in processed_branches):
                    branch_tiles, gates, queue = set(), set(), deque([current_pos]); visited_in_branch = {current_pos}
                    while queue:
                        (curr_x, curr_y) = queue.popleft(); branch_tiles.add((curr_x, curr_y))
                        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                            next_x, next_y, neighbor_pos = curr_x + dx, curr_y + dy, (curr_x + dx, curr_y + dy)
                            if (0 <= next_x < self.size and 0 <= next_y < self.size and 
                                self.grid[next_y][next_x].type != WALL):
                                if neighbor_pos in main_path_set: gates.add((curr_x, curr_y))
                                elif neighbor_pos not in visited_in_branch: visited_in_branch.add(neighbor_pos); queue.append(neighbor_pos)
                    processed_branches.update(branch_tiles)
                    if len(gates) == 1:
                        gate_pos = gates.pop(); self.grid[gate_pos[1]][gate_pos[0]].type = LOCKER; branch_tiles.remove(gate_pos)
                        if branch_tiles:
                           if self._populate_treasure_room(branch_tiles): large_rooms_tiles.append(branch_tiles)
        return large_rooms_tiles

    def _populate_treasure_room(self, tiles):
        # Implementation remains the same...
        tile_count, tile_list, is_large_room = len(tiles), list(tiles), False
        if tile_count <= 4:
            for pos in random.sample(tile_list, min(len(tile_list), random.randint(1, 2))): self.grid[pos[1]][pos[0]].type = GOLD
        elif 4 < tile_count <= 15:
            num_gold, num_potion, available_tiles = random.randint(2, 4), random.randint(0, 1), list(tile_list)
            for pos in random.sample(available_tiles, min(len(available_tiles), num_gold)): self.grid[pos[1]][pos[0]].type = GOLD; available_tiles.remove(pos)
            if available_tiles:
                 for pos in random.sample(available_tiles, min(len(available_tiles), num_potion)): self.grid[pos[1]][pos[0]].type = HEALTH_POTION; available_tiles.remove(pos)
            if random.random() < 0.5 and available_tiles: self.grid[random.choice(available_tiles)[1]][random.choice(available_tiles)[0]].type = SHOP
        else:
            is_large_room, num_gold, num_potion, available_tiles = True, random.randint(5, tile_count//2), random.randint(2, tile_count//3), list(tile_list)
            shop_pos = random.choice(available_tiles); self.grid[shop_pos[1]][shop_pos[0]].type = SHOP; available_tiles.remove(shop_pos)
            if available_tiles:
                 for pos in random.sample(available_tiles, min(len(available_tiles), num_gold)): self.grid[pos[1]][pos[0]].type = GOLD; available_tiles.remove(pos)
            if available_tiles:
                 for pos in random.sample(available_tiles, min(len(available_tiles), num_potion)): self.grid[pos[1]][pos[0]].type = HEALTH_POTION; available_tiles.remove(pos)
        return is_large_room

    def _place_traps_on_main_path(self, main_path):
        # Implementation remains the same...
        path_cells = [cell for cell in main_path if self.grid[cell[1]][cell[0]].type == PATH]
        num_traps = int(len(path_cells) * 0.05)
        if num_traps > 0 and len(path_cells) > num_traps:
            for x, y in random.sample(path_cells, num_traps): self.grid[y][x].type = TRAP
    
    def draw(self, screen, dp_path_to_show=None):
        screen.fill(COLOR_BG)
        for r, row_of_tiles in enumerate(self.grid):
            for c, tile in enumerate(row_of_tiles):
                color = TILE_TYPE_COLORS.get(tile.type, COLOR_PATH)
                rect = (c * self.cell_width, r * self.cell_height, self.cell_width, self.cell_height)
                pygame.draw.rect(screen, color, rect)
                if tile.type in self.tile_icons:
                    icon = self.tile_icons[tile.type]
                    icon_rect = icon.get_rect(center=pygame.Rect(rect).center)
                    screen.blit(icon, icon_rect)

        # 【功能新增】可视化DP路径
        if dp_path_to_show:
            for i in range(len(dp_path_to_show) - 1):
                start_pos = (dp_path_to_show[i][0] * self.cell_width + self.cell_width // 2, 
                             dp_path_to_show[i][1] * self.cell_height + self.cell_height // 2)
                end_pos = (dp_path_to_show[i+1][0] * self.cell_width + self.cell_width // 2, 
                           dp_path_to_show[i+1][1] * self.cell_height + self.cell_height // 2)
                pygame.draw.line(screen, COLOR_DP_PATH, start_pos, end_pos, 4)

        for i in range(self.size + 1):
            pygame.draw.line(screen, COLOR_GRID, (i * self.cell_width, 0), (i * self.cell_width, MAZE_AREA_SIZE))
            pygame.draw.line(screen, COLOR_GRID, (0, i * self.cell_height), (MAZE_AREA_SIZE, i * self.cell_height))

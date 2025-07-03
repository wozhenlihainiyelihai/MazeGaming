import os
import pygame
import random
from collections import deque
from config import *  # 配置文件：颜色、迷宫区域大小、常量等
from entities import Tile  # Tile类代表迷宫中的单元格
from utils import create_all_icons  # 加载图标资源
import json

class Maze:
    """迷宫生成与管理类（支持从文件加载或随机生成）"""

    def __init__(self, size=None, source_data=None):
        if source_data:
            # 如果传入字符矩阵，则从数据中加载迷宫
            self._load_from_data(source_data)
        elif size:
            # 如果传入尺寸，则生成一个新的随机迷宫（确保为奇数）
            self.size = size if size % 2 != 0 else size + 1
            self.grid = [[Tile(PATH) for _ in range(self.size)] for _ in range(self.size)]
            self._generate_base_maze()  # 生成基本通路结构（分治法）
            self._place_start_end_points()  # 设置起点与终点
            main_path = self._find_main_path()  # 计算主路径（起点到终点的路径）

            if main_path:
                large_treasure_rooms = self._create_gated_treasure_rooms()  # 使用死胡同生成宝藏房间
                self._place_boss(main_path, large_treasure_rooms)  # 放置 Boss（可能放在主路径或宝藏房间）
                self._place_traps_on_main_path(main_path)  # 主路径上放置陷阱
                self._place_additional_resources(main_path)  # 放置额外金币资源
        else:
            raise ValueError("Maze 构造函数需要 'size' 或 'source_data' 参数。")

        # 初始化每个单元格的像素尺寸
        self.cell_width = MAZE_AREA_SIZE // self.size
        self.cell_height = MAZE_AREA_SIZE // self.size

        # 保存初始迷宫状态，用于重置
        self.pristine_grid = [[Tile(tile.type) for tile in row] for row in self.grid]
        self._load_icons()  # 加载图标资源

    def _load_from_data(self, maze_data):
        """从字符数组加载迷宫结构（#墙、空格、S起点、E终点、G金币等）"""
        CHAR_TO_TILE = {
            '#': WALL, ' ': PATH, 'S': START, 'E': END, 'B': BOSS,
            'L': LOCKER, 'G': GOLD, 'T': TRAP
        }
        self.size = len(maze_data)
        self.grid = [[Tile(PATH) for _ in range(self.size)] for _ in range(self.size)]

        found_start = False
        found_end = False

        for r, row_list in enumerate(maze_data):
            for c, char in enumerate(row_list):
                tile_type = CHAR_TO_TILE.get(char, PATH)
                self.grid[r][c].type = tile_type
                if tile_type == START:
                    self.start_pos = (c, r)
                    found_start = True
                elif tile_type == END:
                    self.end_pos = (c, r)
                    found_end = True

        # 若缺少起点或终点，则设为默认位置
        if not found_start:
            self.start_pos = (1, 1)
            self.grid[1][1].type = START
            print("警告: 未找到起点 'S'，使用默认位置 (1,1)")
        if not found_end:
            self.end_pos = (self.size - 2, self.size - 2)
            self.grid[self.size - 2][self.size - 2].type = END
            print("警告: 未找到终点 'E'，使用默认位置")

    def reset(self):
        """将迷宫恢复为初始状态"""
        self.grid = [[Tile(tile.type) for tile in row] for row in self.pristine_grid]

    def _load_icons(self):
        """加载图标资源，并缩放为合适大小"""
        self.tile_icons = {}
        icon_size = int(min(self.cell_width, self.cell_height) * 0.7)
        if icon_size <= 0: return
        self.tile_icons = create_all_icons(icon_size)

    def _generate_base_maze(self):
        """使用递归分治法构建基础迷宫结构（四周为墙）"""
        for i in range(self.size):
            self.grid[0][i].type = WALL
            self.grid[self.size - 1][i].type = WALL
            self.grid[i][0].type = WALL
            self.grid[i][self.size - 1].type = WALL
        self._divide(1, 1, self.size - 2, self.size - 2)

    def _divide(self, x, y, width, height):
        """递归地划分区域并添加墙壁"""
        if width < 2 or height < 2: return
        horizontal = width < height or (width == height and random.choice([True, False]))
        if horizontal:
            wall_y = y + (random.randrange(height // 2) * 2 + 1)
            passage_x = x + (random.randrange((width + 1) // 2) * 2)
            for i in range(x, x + width + 1):
                self.grid[wall_y][i].type = WALL
            self.grid[wall_y][passage_x].type = PATH  # 保留一个通道
            self._divide(x, y, width, wall_y - y)
            self._divide(x, wall_y + 1, width, y + height - wall_y - 1)
        else:
            wall_x = x + (random.randrange(width // 2) * 2 + 1)
            passage_y = y + (random.randrange((height + 1) // 2) * 2)
            for i in range(y, y + height + 1):
                self.grid[i][wall_x].type = WALL
            self.grid[passage_y][wall_x].type = PATH
            self._divide(x, y, wall_x - x, height)
            self._divide(wall_x + 1, y, x + width - wall_x - 1, height)

    def _place_start_end_points(self):
        """设置起点终点坐标并标记在网格上"""
        self.start_pos = (1, 1)
        self.end_pos = (self.size - 2, self.size - 2)
        self.grid[self.start_pos[1]][self.start_pos[0]].type = START
        self.grid[self.end_pos[1]][self.end_pos[0]].type = END

    def _find_main_path(self):
        """使用 BFS 寻找从起点到终点的路径"""
        queue = deque([(self.start_pos, [self.start_pos])])
        visited = {self.start_pos}
        while queue:
            (x, y), path = queue.popleft()
            if (x, y) == self.end_pos:
                return path
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.size and 0 <= ny < self.size and \
                   self.grid[ny][nx].type != WALL and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append(((nx, ny), path + [(nx, ny)]))
        return []

    def _find_dead_ends(self, maze_grid):
        """找到所有死胡同（仅一个邻居的路径格）"""
        dead_ends = []
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        for r in range(self.size):
            for c in range(self.size):
                if maze_grid[r][c].type == PATH:
                    path_neighbors = 0
                    for dr, dc in directions:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.size and 0 <= nc < self.size and maze_grid[nr][nc].type != WALL:
                            path_neighbors += 1
                    if path_neighbors == 1:
                        dead_ends.append((c, r))
        return dead_ends

    def _create_gated_treasure_rooms(self):
        """将死胡同变成宝藏房间（带门和金币）"""
        dead_ends = self._find_dead_ends(self.grid)
        potential = [p for p in dead_ends if p != self.start_pos and p != self.end_pos]
        random.shuffle(potential)

        # 根据迷宫大小设置宝藏房间数量
        if self.size <= 7:
            count = random.randint(2, 3)
        elif self.size <= 15:
            count = random.randint(4, 6)
        else:
            count = random.randint(8, 12)

        rooms = []
        for i in range(min(count, len(potential))):
            lx, ly = potential[i]
            self.grid[ly][lx].type = LOCKER  # 放置上锁门
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nr, nc = ly + dr, lx + dc
                if 0 <= nr < self.size and 0 <= nc < self.size and self.grid[nr][nc].type == PATH:
                    self.grid[nr][nc].type = GOLD
                    rooms.append([(lx, ly), (nc, nr)])
                    break
        return rooms

    def _place_boss(self, main_path, large_rooms):
        """放置 Boss（优先宝藏房间，其次主路径）"""
        boss_placed = False
        if large_rooms and random.random() < 0.6:
            pos = random.choice(large_rooms)[1]
            if self.grid[pos[1]][pos[0]].type not in [START, END]:
                self.grid[pos[1]][pos[0]].type = BOSS
                boss_placed = True

        if not boss_placed and len(main_path) > 2:
            start_i = int(len(main_path) * 0.2)
            end_i = int(len(main_path) * 0.8)
            choices = [p for p in main_path[start_i:end_i] if self.grid[p[1]][p[0]].type == PATH]
            if choices:
                px, py = random.choice(choices)
                self.grid[py][px].type = BOSS
                boss_placed = True

        if not boss_placed:
            # 最后保底策略：强制放置
            for r in range(1, self.size - 1):
                for c in range(1, self.size - 1):
                    if self.grid[r][c].type == PATH:
                        self.grid[r][c].type = BOSS
                        return
            print("警告: Boss 无法放置")

    def _place_traps_on_main_path(self, main_path):
        """在主路径上放置陷阱（15% 概率）"""
        path_cells = [p for p in main_path if self.grid[p[1]][p[0]].type == PATH]
        num_traps = int(len(path_cells) * 0.15)
        for x, y in random.sample(path_cells, min(num_traps, len(path_cells))):
            self.grid[y][x].type = TRAP

    def _place_additional_resources(self, main_path):
        """在迷宫中非主路径上放置金币资源"""
        path_cells = [(c, r) for r in range(self.size) for c in range(self.size) if self.grid[r][c].type == PATH]
        main_path_set = set(main_path)
        eligible_cells = [cell for cell in path_cells if cell not in main_path_set]

        # 根据迷宫规模控制资源密度
        if self.size <= 15:
            num_gold = int(len(eligible_cells) * 0.1)
        else:
            num_gold = int(len(eligible_cells) * 0.15)

        for x, y in random.sample(eligible_cells, min(num_gold, len(eligible_cells))):
            self.grid[y][x].type = GOLD

    def draw(self, screen, dp_path_to_show=None):
        """绘制迷宫和可视化路径"""
        screen.fill(COLOR_BG)
        for r, row in enumerate(self.grid):
            for c, tile in enumerate(row):
                rect = (c * self.cell_width, r * self.cell_height, self.cell_width, self.cell_height)
                pygame.draw.rect(screen, TILE_TYPE_COLORS.get(tile.type, COLOR_PATH), rect)
                if tile.type in self.tile_icons:
                    icon = self.tile_icons[tile.type]
                    icon_rect = icon.get_rect(center=pygame.Rect(rect).center)
                    screen.blit(icon, icon_rect)

        # 绘制路径线条
        if dp_path_to_show:
            for i in range(len(dp_path_to_show) - 1):
                p1 = dp_path_to_show[i]
                p2 = dp_path_to_show[i + 1]
                start = (p1[0] * self.cell_width + self.cell_width // 2,
                         p1[1] * self.cell_height + self.cell_height // 2)
                end = (p2[0] * self.cell_width + self.cell_width // 2,
                       p2[1] * self.cell_height + self.cell_height // 2)
                pygame.draw.line(screen, COLOR_DP_PATH, start, end, 4)

        # 画网格线（增强视觉辅助）
        for i in range(self.size + 1):
            pygame.draw.line(screen, COLOR_GRID, (i * self.cell_width, 0), (i * self.cell_width, MAZE_AREA_SIZE))
            pygame.draw.line(screen, COLOR_GRID, (0, i * self.cell_height), (MAZE_AREA_SIZE, i * self.cell_height))

    def save_to_json(self, filename=None):
        """将当前迷宫保存为 JSON 格式（只保存字符矩阵）"""
        TILE_TO_CHAR = {
            WALL: '#', PATH: ' ', START: 'S', END: 'E', BOSS: 'B',
            LOCKER: 'L', GOLD: 'G', TRAP: 'T'
        }

        maze_chars = []
        for row_of_tiles in self.grid:
            row_chars = [TILE_TO_CHAR.get(tile.type, ' ') for tile in row_of_tiles]
            maze_chars.append(row_chars)
            
        data = {"maze": maze_chars}

        if filename is None:
            output_dir = TEST_MAZE_DIR
            output_filename = TEST_MAZE_FILENAME
            full_path = os.path.join(output_dir, output_filename)
        else:
            output_dir = os.path.dirname(filename) or "."
            full_path = filename

        os.makedirs(output_dir, exist_ok=True)

        try:
            with open(full_path, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"迷宫已成功保存到 {full_path}")
        except IOError as e:
            print(f"保存迷宫失败: {e}")

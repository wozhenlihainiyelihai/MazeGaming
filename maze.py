import os
import pygame
import random
from collections import deque
from config import *  # 包含颜色配置、地图大小、常量定义等
from entities import Tile  # Tile 是地图上的单元格类
from utils import create_all_icons  # 用于生成图标资源
import json

class Maze:
    """迷宫生成与管理类（支持随机生成或从文件加载）"""

    def __init__(self, size=None, source_data=None):
        if source_data:
            # 从字符矩阵加载迷宫
            self._load_from_data(source_data)
        elif size:
            # 随机生成迷宫（必须为奇数）
            self.size = size if size % 2 != 0 else size + 1
            self.grid = [[Tile(PATH) for _ in range(self.size)] for _ in range(self.size)]
            self._generate_base_maze()  # 生成基础迷宫结构（递归分治法）
            self._place_start_end_points()  # 放置起点和终点
            main_path = self._find_main_path()  # 计算主路径（用于后续放Boss）
            if main_path:
                large_treasure_rooms = self._create_gated_treasure_rooms()  # 利用死胡同构造宝藏房间
                self._place_boss(main_path, large_treasure_rooms)  # 放置 Boss
                self._place_traps_on_main_path(main_path)  # 在主路径设置陷阱
        else:
            raise ValueError("Maze 构造函数需要 'size' 或 'source_data' 参数。")

        # 通用参数初始化
        self.cell_width = MAZE_AREA_SIZE // self.size
        self.cell_height = MAZE_AREA_SIZE // self.size

        # 保存迷宫初始状态（用于 reset）
        self.pristine_grid = [[Tile(tile.type) for tile in row] for row in self.grid]
        self._load_icons()  # 加载图标资源

    def _load_from_data(self, maze_data):
        """从字符数组加载迷宫结构"""
        CHAR_TO_TILE = {
            '#': WALL, ' ': PATH, 'S': START, 'E': END, 'B': BOSS,
            'L': LOCKER, 'G': GOLD, 'T': TRAP, 'P': SHOP, 'H': HEALTH_POTION
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

        if not found_start:
            self.start_pos = (1, 1)
            self.grid[1][1].type = START
            print("警告: 未找到起点 'S'，使用默认位置 (1,1)")
        if not found_end:
            self.end_pos = (self.size - 2, self.size - 2)
            self.grid[self.size - 2][self.size - 2].type = END
            print("警告: 未找到终点 'E'，使用默认位置")

    def reset(self):
        """将迷宫重置为初始状态"""
        self.grid = [[Tile(tile.type) for tile in row] for row in self.pristine_grid]

    def _load_icons(self):
        """加载图标资源并缩放到适当尺寸"""
        self.tile_icons = {}
        icon_size = int(min(self.cell_width, self.cell_height) * 0.7)
        if icon_size <= 0: return
        self.tile_icons = create_all_icons(icon_size)

    def _generate_base_maze(self):
        """使用递归分治法生成基础迷宫结构"""
        for i in range(self.size):
            self.grid[0][i].type = WALL
            self.grid[self.size - 1][i].type = WALL
            self.grid[i][0].type = WALL
            self.grid[i][self.size - 1].type = WALL
        self._divide(1, 1, self.size - 2, self.size - 2)

    def _divide(self, x, y, width, height):
        """递归构建墙体"""
        if width < 2 or height < 2: return
        horizontal = width < height or (width == height and random.choice([True, False]))
        if horizontal:
            wall_y = y + (random.randrange(height // 2) * 2 + 1)
            passage_x = x + (random.randrange((width + 1) // 2) * 2)
            for i in range(x, x + width + 1):
                self.grid[wall_y][i].type = WALL
            self.grid[wall_y][passage_x].type = PATH
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
        """起点放在左上角，终点放在右下角"""
        self.start_pos = (1, 1)
        self.end_pos = (self.size - 2, self.size - 2)
        self.grid[self.start_pos[1]][self.start_pos[0]].type = START
        self.grid[self.end_pos[1]][self.end_pos[0]].type = END

    def _find_main_path(self):
        """BFS 找起点到终点的路径"""
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
        """找所有死胡同位置（只有1个邻居的PATH）"""
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
        """根据死胡同生成有宝藏和门的房间"""
        dead_ends = self._find_dead_ends(self.grid)
        potential = [p for p in dead_ends if p != self.start_pos and p != self.end_pos]
        random.shuffle(potential) #打乱顺序，随机

        # 控制数量（可微调）
        if self.size <= 7:
            count = random.randint(1, 2)
        elif self.size <= 15:
            count = random.randint(2, 4)
        else:
            count = random.randint(4, 7)

        rooms = []
        for i in range(min(count, len(potential))):
            lx, ly = potential[i]
            self.grid[ly][lx].type = LOCKER
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nr, nc = ly + dr, lx + dc
                if 0 <= nr < self.size and 0 <= nc < self.size and self.grid[nr][nc].type == PATH:
                    self.grid[nr][nc].type = GOLD if random.random() < 0.6 else HEALTH_POTION
                    rooms.append([(lx, ly), (nc, nr)])
                    break
        return rooms

    def _place_boss(self, main_path, large_rooms):
        """将Boss放在宝藏房间或主路径上"""
        boss_placed = False
        if large_rooms and random.random() < 0.6:
            pos = large_rooms[random.randint(0, len(large_rooms)-1)][1]
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
            for r in range(1, self.size - 1):
                for c in range(1, self.size - 1):
                    if self.grid[r][c].type == PATH:
                        self.grid[r][c].type = BOSS
                        return
            print("警告: Boss 无法放置")

    def _place_traps_on_main_path(self, main_path):
        """主路径上放置陷阱（5%）"""
        path_cells = [p for p in main_path if self.grid[p[1]][p[0]].type == PATH]
        num_traps = int(len(path_cells) * 0.05)
        for x, y in random.sample(path_cells, min(num_traps, len(path_cells))):
            self.grid[y][x].type = TRAP

    def draw(self, screen, dp_path_to_show=None):
        """绘制地图及路径"""
        screen.fill(COLOR_BG)
        for r, row in enumerate(self.grid):
            for c, tile in enumerate(row):
                rect = (c * self.cell_width, r * self.cell_height, self.cell_width, self.cell_height)
                pygame.draw.rect(screen, TILE_TYPE_COLORS.get(tile.type, COLOR_PATH), rect)
                if tile.type in self.tile_icons:
                    icon = self.tile_icons[tile.type]
                    icon_rect = icon.get_rect(center=pygame.Rect(rect).center)
                    screen.blit(icon, icon_rect)

        # 路径可视化（如 DP 路径）
        if dp_path_to_show:
            for i in range(len(dp_path_to_show) - 1):
                p1 = dp_path_to_show[i]
                p2 = dp_path_to_show[i + 1]
                start = (p1[0] * self.cell_width + self.cell_width // 2,
                         p1[1] * self.cell_height + self.cell_height // 2)
                end = (p2[0] * self.cell_width + self.cell_width // 2,
                       p2[1] * self.cell_height + self.cell_height // 2)
                pygame.draw.line(screen, COLOR_DP_PATH, start, end, 4)

        # 绘制网格线
        for i in range(self.size + 1):
            pygame.draw.line(screen, COLOR_GRID, (i * self.cell_width, 0), (i * self.cell_width, MAZE_AREA_SIZE))
            pygame.draw.line(screen, COLOR_GRID, (0, i * self.cell_height), (MAZE_AREA_SIZE, i * self.cell_height))

    def save_to_json(self, filename=None): # filename 参数改为可选，默认 None
        """
        将当前迷宫的布局保存到 JSON 文件中，只包含迷宫字符矩阵。
        默认保存到 config.py 中定义的固定测试迷宫路径。
        """
        # 定义 Tile 类型到字符的映射
        TILE_TO_CHAR = {
            WALL: '#', PATH: ' ', START: 'S', END: 'E', BOSS: 'B',
            LOCKER: 'L', GOLD: 'G', TRAP: 'T', HEALTH_POTION: 'H', SHOP: 'P'
        }

        maze_chars = []
        for r, row_of_tiles in enumerate(self.grid):
            row_chars = []
            for c, tile in enumerate(row_of_tiles):
                # 确保每个瓦片类型都有对应的字符，否则默认为空格
                row_chars.append(TILE_TO_CHAR.get(tile.type, ' ')) 
            maze_chars.append(row_chars)
            
        data = {
            "maze": maze_chars
        }

        # 构建完整的文件路径
        # 如果 filename 参数未提供，则使用 config.py 中定义的固定路径
        if filename is None:
            output_dir = TEST_MAZE_DIR
            output_filename = TEST_MAZE_FILENAME
            full_path = os.path.join(output_dir, output_filename)
        else:
            # 如果提供了 filename，则使用它
            output_dir = os.path.dirname(filename)
            if not output_dir: # 如果 filename 没有路径信息，则默认为当前目录
                output_dir = "."
            full_path = filename

        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)

        try:
            with open(full_path, 'w') as f:
                json.dump(data, f, indent=4) # 使用 indent=4 使 JSON 文件更易读
            print(f"迷宫已成功保存到 {full_path}")
        except IOError as e:
            print(f"保存迷宫失败: {e}")


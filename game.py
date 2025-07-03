import pygame
import sys
import random
import hashlib
from collections import deque
import json
from config import *
from utils import SoundManager, create_all_icons
from maze import Maze
from entities import AIPlayer, Boss
from algorithms.dynamic_programming import calculate_dp_path
from algorithms.branch_and_bound import find_best_attack_sequence
from algorithms.backtracking import solve_puzzle_by_method
from algorithms.greedy import get_tile_value


class Game:
    """游戏主类"""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Maze Adventure - AI Algorithms")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.game_state = STATE_MAIN_MENU
        self.sound_manager = SoundManager()

        self.maze, self.ai_player, self.boss = None, None, None
        self.ai_timer, self.ai_move_interval = 100, 100  

        self.battle_config = None
        self.battle_result = None
        self.battle_end_timer = 0
        self.battle_display_duration = 5000

        self.active_algorithm = ALGO_GREEDY
        self.dp_optimal_path, self.dp_max_score = [], 0
        self.battle_log = deque(maxlen=8)

        self.puzzle_solver = None
        self.puzzle_timer = 0
        self.puzzle_update_interval = 100
        self.puzzle_current_path = []
        self.puzzle_status_text = ""
        self.puzzle_clue_texts = []
        self.puzzle_length = 0
        self.puzzle_target_hash = ""
        self.puzzle_tries_count = 0
        self.puzzle_active_method = ""

        try:
            font_name = 'sans-serif'
            self.font_title = pygame.font.SysFont(font_name, 80);
            self.font_button = pygame.font.SysFont(font_name, 50)
            self.font_info = pygame.font.SysFont(font_name, 32);
            self.font_info_bold = pygame.font.SysFont(font_name, 36, bold=True)
            self.font_legend = pygame.font.SysFont(font_name, 40);
            self.font_battle = pygame.font.SysFont(font_name, 24)
            self.font_vs = pygame.font.SysFont(font_name, 100, bold=True)
            self.font_result = pygame.font.SysFont(font_name, 120, bold=True)
        except pygame.error:
            self.font_title = pygame.font.SysFont(None, 80);
            self.font_button = pygame.font.SysFont(None, 50)
            self.font_info = pygame.font.SysFont(None, 32);
            self.font_info_bold = pygame.font.SysFont(None, 36, bold=True)
            self.font_legend = pygame.font.SysFont(None, 40);
            self.font_battle = pygame.font.SysFont(None, 24)
            self.font_vs = pygame.font.SysFont(None, 100, bold=True)
            self.font_result = pygame.font.SysFont(None, 120, bold=True)

        self.buttons = {}
        self.icons = create_all_icons(50)

    def load_battle_config(self, filepath='battle_config.json'):
        """加载Boss战配置文件。"""
        try:
            with open(filepath, 'r') as f:
                self.battle_config = json.load(f)
            print(f"Battle config '{filepath}' loaded successfully.")
        except FileNotFoundError:
            print(f"Error: Battle config file '{filepath}' not found.")
            self.battle_config = None
        except json.JSONDecodeError:
            print(f"Error: Battle config file '{filepath}' has invalid format.")
            self.battle_config = None

    def start_new_game(self, size=None, source_data=None):
        """开始新游戏，创建所有实体并计算初始资源值。"""
        self.maze = Maze(size=15, source_data=source_data)
        if size is not None and source_data is None:
            self.maze.save_to_json()
        self.boss = Boss()
        self.load_battle_config()

        self.dp_optimal_path, _ = calculate_dp_path(self.maze)

        self.reset_simulation(ALGO_GREEDY)

        resource_count = 0
        trap_count = 0
        if self.dp_optimal_path:
            path_coords = set(tuple(p) for p in self.dp_optimal_path)
            for x, y in path_coords:
                tile_type = self.maze.pristine_grid[y][x].type
                if tile_type in [LOCKER, GOLD, HEALTH_POTION, BOSS]:
                    resource_count += 1
                elif tile_type == TRAP:
                    trap_count += 1

        initial_value = (resource_count * 50) + (trap_count * (-30))
        self.ai_player.resource_value = initial_value

        print("\n--- 任务3: 动态规划阶段 ---")
        print(f"最优路径已规划，覆盖 {resource_count} 个资源和 {trap_count} 个陷阱。")
        print(f"路径: {self.dp_optimal_path}")
        print(f"初始资源值计算完成: {initial_value}")
        print("---------------------------\n")

        self.game_state = STATE_GAMEPLAY
        self.sound_manager.play('coin')

    def update_state(self):
        """更新游戏状态机。"""
        if self.game_state == STATE_GAMEPLAY and self.ai_player and self.ai_player.is_active:
            self.ai_timer += self.clock.get_time()
            if self.ai_timer >= self.ai_move_interval:
                self.ai_timer = 0
                interaction_result = self.ai_player.update(self.maze, self.sound_manager, self.active_algorithm)

                # 更新D-score
                if self.active_algorithm == ALGO_DP_VISUALIZATION:
                    if interaction_result == GOLD:
                        self.ai_player.resource_value += 50
                    elif interaction_result == TRAP:
                        self.ai_player.resource_value -= 30
                if self.active_algorithm == ALGO_GREEDY:
                    if isinstance(interaction_result, int):  # 检查返回的是否为地块类型常量
                        # 陷阱的价值本身是负数，所以直接相加即可
                        value_change = get_tile_value(interaction_result, self.ai_player)
                        self.ai_player.greedy_score += value_change

                        # 如果到达终点，则输出贪心算法的结果
                        if interaction_result == END:
                            print("\n--- 贪心算法执行完毕 ---")
                            # 移除重复的坐标点，使路径更清晰
                            unique_path = list(dict.fromkeys(self.ai_player.greedy_path))
                            print(f"  资源拾取路径: {unique_path}")
                            print(f"  最终资源得分: {self.ai_player.greedy_score}")
                            print("--------------------------\n")
                            self.ai_player.is_active = False  # 停止AI

                if interaction_result == 'start_battle':
                    self.initiate_battle()
                elif interaction_result == 'start_puzzle':
                    self.initiate_puzzle()

        elif self.game_state == STATE_BATTLE:
            self.battle_end_timer += self.clock.get_time()
            if self.battle_end_timer >= self.battle_display_duration:
                self.conclude_battle()

        elif self.game_state == STATE_PUZZLE:
            self.puzzle_timer += self.clock.get_time()
            if self.puzzle_timer >= self.puzzle_update_interval:
                self.puzzle_timer = 0
                self.update_puzzle()

    def initiate_battle(self):
        """初始化战斗，计算结果并准备扣分。"""
        if not self.battle_config:
            self.load_battle_config()
            if not self.battle_config:
                print("Cannot start battle: battle_config.json not found or invalid.")
                self.game_state = STATE_GAMEPLAY
                return

        self.game_state = STATE_BATTLE

        boss_hp_list = self.battle_config['B']
        skills = self.battle_config['PlayerSkills']

        self.boss.health = boss_hp_list
        self.ai_player.skills = skills

        self.battle_result = find_best_attack_sequence(self.ai_player, self.boss, self.ai_player.skills)

        print("\n--- 任务5: Boss 战阶段 ---")
        if self.battle_result and self.battle_result['turns'] != -1:
            print(f"分析完成! 最优解需要 {self.battle_result['turns']} 回合。")
            print(f"技能序列: {self.battle_result['sequence']}")
        else:
            print("分析完成! 未找到获胜序列。")

        self.battle_log.clear()
        self.battle_log.append("Boss Gauntlet! Analyzing...")
        if self.battle_result and self.battle_result['turns'] != -1:
            self.battle_log.append(f"Optimal solution: {self.battle_result['turns']} turns.")
            self.battle_log.append("Skill Sequence (Dmg, CD):")
            seq_str_ui = ' -> '.join([f"[{s['Damage']},{s['Cooldown']}]" for s in self.battle_result['sequence']])
            max_len = 45
            if len(seq_str_ui) > max_len:
                parts = [seq_str_ui[i:i + max_len] for i in range(0, len(seq_str_ui), max_len)]
                for part in parts: self.battle_log.append(part)
            else:
                self.battle_log.append(seq_str_ui)
        else:
            self.battle_log.append("Analysis complete: Victory is not possible!")
        self.battle_end_timer = 0

    def conclude_battle(self):
        """根据战斗结果扣减资源值。"""
        if self.battle_result and self.battle_result['turns'] != -1:
            self.ai_player.boss_defeated = True
            self.maze.grid[self.ai_player.y][self.ai_player.x].type = PATH
            self.ai_player.needs_new_target = True

            deduction = self.battle_result['turns']
            self.ai_player.resource_value -= deduction
            print(f"Boss战胜利！扣除资源值: {deduction}。")
            print(f"当前剩余资源值: {self.ai_player.resource_value}")
            print("------------------------\n")

            # 贪心算法计分
            if self.active_algorithm == ALGO_GREEDY:
                self.ai_player.greedy_score += get_tile_value(BOSS, self.ai_player)
        else:
            self.ai_player.x, self.ai_player.y = self.ai_player.start_pos
            print("AI was defeated and has respawned.")

        self.battle_result = None
        self.game_state = STATE_GAMEPLAY

    def initiate_puzzle(self):
        """初始化解谜环节。"""
        self.game_state = STATE_PUZZLE
        salt = b'\xb2\x53\x22\x65\x7d\xdf\xb0\xfe\x9c\xde\xde\xfe\xf3\x1d\xdc\x3e'
        puzzles = [{"L": "81d5400ab2eca801a80837500be67485d0f8b297db1fa8ecbe4a23b66b65f6b8", "C": [[3, 1], [-1, -1, 5]],
                    "length": 3, "salt": salt}]
        chosen_puzzle = random.choice(puzzles)
        self.puzzle_length = chosen_puzzle["length"]
        self.puzzle_clue_texts = self.generate_clue_texts(chosen_puzzle["C"], chosen_puzzle["length"])
        self.puzzle_target_hash = chosen_puzzle["L"]
        self.puzzle_active_method = "method1"
        self.puzzle_solver = solve_puzzle_by_method(self.puzzle_active_method, chosen_puzzle["C"],
                                                    self.puzzle_target_hash, self.puzzle_length, chosen_puzzle["salt"],
                                                    {"count": 0})
        self.puzzle_current_path, self.puzzle_status_text, self.puzzle_timer, self.puzzle_tries_count = [], "Initializing...", 0, 0

    def update_puzzle(self):
        """更新谜题求解进程并扣减资源值。"""
        if not self.puzzle_solver: return
        try:
            self.puzzle_current_path, self.puzzle_status_text, self.puzzle_tries_count = next(self.puzzle_solver)
            if "Success!" in self.puzzle_status_text:
                self.draw_puzzle_screen();
                self.draw_final_puzzle_result("SUCCESS", COLOR_HEALTH_PLAYER)

                deduction = self.puzzle_tries_count
                self.ai_player.resource_value -= deduction
                print("\n--- 任务4: 解谜阶段 ---")
                password = self.puzzle_status_text.split(": ")[-1]
                print(f"密码破解成功！密码: {password}，尝试次数: {self.puzzle_tries_count}")
                print(f"扣除资源值: {deduction}。当前剩余资源值: {self.ai_player.resource_value}")
                print("-----------------------\n")

                # 为贪心算法计分
                if self.active_algorithm == ALGO_GREEDY:
                    self.ai_player.greedy_score += get_tile_value(LOCKER, self.ai_player)

                locker_tile = self.maze.grid[self.ai_player.y][self.ai_player.x];
                locker_tile.type = PATH
                self.ai_player.needs_new_target = True
                self.game_state = STATE_GAMEPLAY;
                self.puzzle_solver = None;
                self.sound_manager.play('coin')
        except StopIteration:
            self.draw_puzzle_screen();
            self.draw_final_puzzle_result("FAILURE", COLOR_HEALTH_BOSS)
            locker_tile = self.maze.grid[self.ai_player.y][self.ai_player.x];
            locker_tile.type = WALL
            if len(self.ai_player.path_history) > 1:
                self.ai_player.path_history.pop();
                prev_pos = self.ai_player.path_history[-1]
                self.ai_player.x, self.ai_player.y = prev_pos
            self.ai_player.needs_new_target = True;
            self.game_state = STATE_GAMEPLAY;
            self.puzzle_solver = None

    def run(self):
        """游戏主循环。"""
        while self.game_state != STATE_QUIT:
            self.handle_events()
            self.update_state()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()

    def handle_events(self):
        """处理Pygame事件。"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.game_state = STATE_QUIT
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: self.handle_mouse_click(event.pos)

    def handle_mouse_click(self, mouse_pos):
        """处理鼠标点击。"""
        self.sound_manager.play('click')
        for name, rect in self.buttons.items():
            if rect.collidepoint(mouse_pos): self.on_button_click(name); break

    def on_button_click(self, button_name):
        """处理按钮点击事件。"""
        if self.game_state == STATE_MAIN_MENU:
            if button_name == 'start':
                self.game_state = STATE_INSTRUCTIONS
            elif button_name == 'quit':
                self.game_state = STATE_QUIT
        elif self.game_state == STATE_INSTRUCTIONS:
            if button_name == 'continue':
                self.game_state = STATE_CHOOSE_MAZE_SOURCE
            elif button_name == 'back':
                self.game_state = STATE_MAIN_MENU
        elif self.game_state == STATE_CHOOSE_MAZE_SOURCE:
            if button_name == 'generate':
                self.start_new_game(size=15)
            elif button_name == 'load_test':
                self.load_fixed_maze_and_start()
            elif button_name == 'back':
                self.game_state = STATE_INSTRUCTIONS
        elif self.game_state == STATE_GAMEPLAY:
            if button_name == ALGO_GREEDY:
                self.reset_simulation(ALGO_GREEDY)
            elif button_name == ALGO_DP_VISUALIZATION:
                self.reset_simulation(ALGO_DP_VISUALIZATION)
            elif button_name == 'main_menu':
                self.game_state = STATE_MAIN_MENU

    def reset_simulation(self, algorithm):
        """重置模拟。"""
        self.active_algorithm = algorithm
        self.maze.reset()
        self.boss.reset()
        self.ai_player = AIPlayer(start_pos=self.maze.start_pos)
        if self.active_algorithm == ALGO_DP_VISUALIZATION:
            self.ai_player.path_to_follow = list(self.dp_optimal_path)
            # 初始化resource_value为0
            self.ai_player.resource_value = 0
        # 重置贪心算法的分数和路径
        self.ai_player.greedy_score = 0
        self.ai_player.greedy_path = [self.ai_player.start_pos]

    def load_fixed_maze_and_start(self):
        """加载固定迷宫并开始。"""
        fixed_path = 'test_maze.json'
        try:
            with open(fixed_path, 'r') as f:
                data = json.load(f)
            self.start_new_game(source_data=data['maze'])
        except Exception as e:
            print(f"Error loading fixed maze file: {e}")

    def generate_clue_texts(self, clues, length):
        """生成人类可读的谜题线索。"""
        texts = []
        has_uniqueness_clue = True
        for clue in clues:
            if clue == [-1, -1]:
                texts.append("Each digit is a unique prime number.")
                has_uniqueness_clue = False
            elif len(clue) == 2:
                pos, prop = clue
                pos_text = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(pos, f"{pos}th")
                prop_text = "even" if prop == 0 else "odd"
                texts.append(f"The {pos_text} digit is {prop_text}.")
            elif len(clue) == length:
                for i, digit in enumerate(clue):
                    if digit != -1:
                        pos_text = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(i + 1, f"{i + 1}th")
                        texts.append(f"The {pos_text} digit is {digit}.")
        if has_uniqueness_clue:
            texts.append("Digits do not repeat.")
        return texts

    def draw(self):
        """绘制所有游戏元素。"""
        self.screen.fill(COLOR_BG)
        if self.game_state in [STATE_GAMEPLAY, STATE_BATTLE, STATE_PUZZLE] and self.maze:
            maze_surface = self.screen.subsurface((MAZE_AREA_X, MAZE_AREA_Y, MAZE_AREA_SIZE, MAZE_AREA_SIZE))
            path_to_draw = self.dp_optimal_path if self.active_algorithm == ALGO_DP_VISUALIZATION else None
            self.maze.draw(maze_surface, dp_path_to_show=path_to_draw)
            if self.ai_player: self.ai_player.draw(maze_surface, self.maze.cell_width, self.maze.cell_height)
            self.draw_info_panel()
            if self.game_state == STATE_BATTLE: self.draw_battle_screen()
            if self.game_state == STATE_PUZZLE: self.draw_puzzle_screen()
        else:
            if self.game_state == STATE_MAIN_MENU:
                self.draw_main_menu()
            elif self.game_state == STATE_INSTRUCTIONS:
                self.draw_instructions()
            elif self.game_state == STATE_CHOOSE_MAZE_SOURCE:
                self.draw_choose_maze_source()
        pygame.display.flip()

    def draw_text_on_surface(self, surface, text, font, color, pos, centered=False):
        """在指定表面绘制文本。"""
        text_surface = font.render(text, True, color)
        rect = text_surface.get_rect(center=pos) if centered else text_surface.get_rect(topleft=pos)
        surface.blit(text_surface, rect)

    def draw_text(self, text, font, color, pos, centered=False):
        """在主屏幕上绘制文本。"""
        self.draw_text_on_surface(self.screen, text, font, color, pos, centered)

    def draw_button(self, name, text, center_pos, size, font=None):
        """绘制按钮。"""
        if font is None: font = self.font_button
        rect = pygame.Rect((0, 0), size);
        rect.center = center_pos;
        shadow_rect = rect.copy();
        shadow_rect.move_ip(5, 5)
        pygame.draw.rect(self.screen, COLOR_BTN_SHADOW, shadow_rect, border_radius=20)
        bg_color = COLOR_BTN_HOVER if rect.collidepoint(pygame.mouse.get_pos()) else COLOR_BTN
        pygame.draw.rect(self.screen, bg_color, rect, border_radius=20)
        self.draw_text(text, font, COLOR_TEXT, rect.center, centered=True);
        self.buttons[name] = rect

    def draw_main_menu(self):
        """绘制主菜单。"""
        self.buttons.clear();
        self.screen.fill(COLOR_BG)
        self.draw_text("Maze Adventure", self.font_title, COLOR_BTN_SHADOW, (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4),
                       centered=True)
        self.draw_button('start', 'Start Game', (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2), (280, 75))
        self.draw_button('quit', 'Quit', (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 100), (280, 75))

    def draw_instructions(self):
        """绘制说明和图例。"""
        self.buttons.clear();
        self.screen.fill(COLOR_BG)
        self.draw_text("Legend", self.font_title, COLOR_BTN_SHADOW, (SCREEN_WIDTH / 2, 80), centered=True)
        legend_items = {GOLD: "Gold", HEALTH_POTION: "Potion", TRAP: "Trap", LOCKER: "Locker", BOSS: "Boss"}
        item_height, gap, start_y = 50, 25, (SCREEN_HEIGHT - (len(legend_items) * (50 + 25) - 25)) / 2
        x_icon, x_text = SCREEN_WIDTH / 2 - 150, SCREEN_WIDTH / 2 - 80
        for i, (item_type, text) in enumerate(legend_items.items()):
            y_pos = start_y + i * (item_height + gap)
            if self.icons.get(item_type): self.screen.blit(self.icons.get(item_type), (x_icon, y_pos))
            self.draw_text(text, self.font_legend, COLOR_HUD_BG, (x_text, y_pos + 5))
        self.draw_button('continue', 'Continue', (SCREEN_WIDTH / 2, SCREEN_HEIGHT - 100), (220, 70))
        self.draw_button('back', 'Back', (100, 50), (150, 60))

    def draw_choose_maze_source(self):
        """绘制迷宫来源选择界面。"""
        self.buttons.clear();
        self.screen.fill(COLOR_BG)
        self.draw_text("Choose Maze Source", self.font_title, COLOR_BTN_SHADOW, (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4),
                       centered=True)
        self.draw_button('generate', 'Generate 15x15 Maze', (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50), (450, 75))
        self.draw_button('load_test', 'Load Test Maze', (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50), (450, 75))
        self.draw_button('back', 'Back', (100, 50), (150, 60))

    def draw_info_panel(self):
        """绘制右侧信息面板。"""
        panel_rect = (INFO_PANEL_X, MAZE_AREA_Y, INFO_PANEL_WIDTH, MAZE_AREA_SIZE)
        pygame.draw.rect(self.screen, COLOR_HUD_BG, panel_rect, border_radius=15)
        title_pos = (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, 50)
        self.draw_text("AI STATUS", self.font_button, COLOR_BTN_HOVER, title_pos, centered=True)
        if self.ai_player:
            y_offset = 120
            # 根据当前运行的算法，显示不同的分数
            if self.active_algorithm == ALGO_GREEDY:
                stats = {"G-Score": f"{self.ai_player.greedy_score}"}
            else:
                stats = {"D-Score": f"{self.ai_player.resource_value}"}

            for stat, value in stats.items():
                self.draw_text(f"{stat}:", self.font_info_bold, COLOR_TEXT, (INFO_PANEL_X + 25, y_offset))
                self.draw_text(value, self.font_info, COLOR_SUBTEXT, (INFO_PANEL_X + 180, y_offset))
                y_offset += 40

        y_offset = 450
        self.draw_text("CONTROL", self.font_button, COLOR_BTN_HOVER, (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset),
                       centered=True)
        y_offset += 60;
        btn_w, btn_h, btn_font = 240, 55, pygame.font.SysFont('sans-serif', 35)
        self.draw_button(ALGO_GREEDY, "Run Greedy AI", (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset), (btn_w, btn_h),
                         font=btn_font)
        y_offset += 75
        self.draw_button(ALGO_DP_VISUALIZATION, "Show DP Path", (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset),
                         (btn_w, btn_h), font=btn_font)
        y_offset = 650
        self.draw_text("RUNNING:", self.font_info_bold, COLOR_TEXT, (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset),
                       centered=True)
        self.draw_text(self.active_algorithm, self.font_info, COLOR_SUBTEXT,
                       (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset + 35), centered=True)
        self.draw_button('main_menu', 'Menu', (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, SCREEN_HEIGHT - 60), (220, 60))

    def draw_battle_screen(self):
        """重构后的战斗界面，以展示车轮战进度。"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        popup_width, popup_height = 800, 500
        popup_x, popup_y = (SCREEN_WIDTH - popup_width) / 2, (SCREEN_HEIGHT - popup_height) / 2
        popup_rect = pygame.Rect(popup_x, popup_y, popup_width, popup_height)
        pygame.draw.rect(overlay, COLOR_POPUP_BG, popup_rect, border_radius=20)
        pygame.draw.rect(overlay, COLOR_GRID, popup_rect, 4, border_radius=20)

        self.draw_text_on_surface(overlay, "Boss Gauntlet", self.font_title, COLOR_TEXT,
                                  (popup_x + popup_width / 2, popup_y + 60), centered=True)

        if isinstance(self.boss.health, list):
            total_bosses = len(self.boss.health)
            defeated_bosses = 0
            if self.battle_result and self.battle_result['sequence']:
                temp_hp = list(self.boss.health)
                for skill in self.battle_result['sequence']:
                    if defeated_bosses < len(temp_hp):
                        temp_hp[defeated_bosses] -= skill['Damage']
                        if temp_hp[defeated_bosses] <= 0:
                            defeated_bosses += 1

            progress_text = f"Progress: Boss {min(defeated_bosses + 1, total_bosses)} / {total_bosses}"
            self.draw_text_on_surface(overlay, progress_text, self.font_button, COLOR_SUBTEXT,
                                      (popup_x + popup_width / 2, popup_y + 130), centered=True)

        log_bg_rect = pygame.Rect(popup_x + 50, popup_y + 180, popup_width - 100, 290)
        pygame.draw.rect(overlay, COLOR_BATTLE_LOG_BG, log_bg_rect, border_radius=10)

        y_offset = popup_y + 200
        for log_entry in self.battle_log:
            self.draw_text_on_surface(overlay, log_entry, self.font_battle, COLOR_TEXT, (popup_x + 70, y_offset))
            y_offset += 28

        self.screen.blit(overlay, (0, 0))

    def draw_final_puzzle_result(self, message, color):
        """绘制谜题的最终结果。"""
        result_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        text_surf = self.font_result.render(message, True, color)
        text_rect = text_surf.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
        bg_rect = text_rect.inflate(40, 40)
        pygame.draw.rect(result_overlay, (*COLOR_HUD_BG, 230), bg_rect, border_radius=15)
        result_overlay.blit(text_surf, text_rect)
        self.screen.blit(result_overlay, (0, 0))
        pygame.display.flip();
        pygame.time.wait(1500)

    def draw_puzzle_screen(self):
        """绘制谜题界面。"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA);
        pygame.draw.rect(overlay, COLOR_POPUP_BG, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        title_font, info_font = self.font_title, self.font_info
        self.draw_text_on_surface(overlay, "Password Lock", title_font, COLOR_TEXT, (SCREEN_WIDTH / 2, 80),
                                  centered=True)
        method_text = f"Strategy: {self.puzzle_active_method}";
        self.draw_text_on_surface(overlay, method_text, info_font, COLOR_TEXT, (SCREEN_WIDTH / 2, 160), centered=True)
        clue_y = 200
        for text in self.puzzle_clue_texts: self.draw_text_on_surface(overlay, text, info_font, COLOR_TEXT,
                                                                      (SCREEN_WIDTH / 2, clue_y),
                                                                      centered=True); clue_y += 35
        hash_text = f"Target Hash: {self.puzzle_target_hash[:16]}...";
        self.draw_text_on_surface(overlay, hash_text, info_font, COLOR_TEXT, (SCREEN_WIDTH / 2, clue_y + 20),
                                  centered=True)
        box_size, box_gap, total_width = 80, 20, self.puzzle_length * 80 + (self.puzzle_length - 1) * 20
        start_x, y_pos = (SCREEN_WIDTH - total_width) / 2, SCREEN_HEIGHT / 2 + 30
        for i in range(self.puzzle_length):
            box_rect = pygame.Rect(start_x + i * (box_size + box_gap), y_pos, box_size, box_size)
            pygame.draw.rect(overlay, COLOR_HEALTH_BG, box_rect, border_radius=10);
            pygame.draw.rect(overlay, COLOR_GRID, box_rect, 4, border_radius=10)
            if i < len(self.puzzle_current_path): self.draw_text_on_surface(overlay, str(self.puzzle_current_path[i]),
                                                                            self.font_vs, COLOR_BTN_HOVER,
                                                                            box_rect.center, centered=True)
        tries_text = f"Tries: {self.puzzle_tries_count}";
        self.draw_text_on_surface(overlay, tries_text, self.font_info_bold, COLOR_SUBTEXT,
                                  (start_x + total_width, y_pos - 40))
        self.draw_text_on_surface(overlay, self.puzzle_status_text, self.font_info_bold, COLOR_SUBTEXT,
                                  (SCREEN_WIDTH / 2, y_pos + 150), centered=True)
        self.screen.blit(overlay, (0, 0))

    def update(self, maze, sound_manager, algorithm):
        if not self.ai_player.is_active: return None
        dx, dy = self.ai_player.decide_move(maze, algorithm)
        if self.ai_player.move(dx, dy, maze):
            # 移动成功后，与地块交互
            interaction_result = self.interact_with_tile(maze, sound_manager)
            # 更新D-score
            if algorithm == ALGO_DP_VISUALIZATION:
                if interaction_result == GOLD:
                    self.ai_player.resource_value += 50
                elif interaction_result == TRAP:
                    self.ai_player.resource_value -= 30
            return interaction_result
        return None

    def interact_with_tile(self, maze, sound_manager):
        tile = maze.grid[self.ai_player.y][self.ai_player.x]

        if (self.ai_player.x, self.ai_player.y) == self.ai_player.temporary_target:
            self.ai_player.temporary_target = None
            self.ai_player.needs_new_target = True

        # 返回地块类型用于计分
        interacted_tile_type = tile.type

        if tile.type == GOLD:
            sound_manager.play('coin')
            tile.type = PATH
            self.ai_player.needs_new_target = True
            return interacted_tile_type
        elif tile.type == TRAP:
            sound_manager.play('trap')
            tile.type = PATH
            return interacted_tile_type
        elif tile.type == LOCKER:
            return 'start_puzzle'
        elif tile.type == BOSS and not self.ai_player.boss_defeated:
            return 'start_battle'
        elif tile.type == END:
            return interacted_tile_type

        return None
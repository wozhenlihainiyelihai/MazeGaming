# 包含核心的Game类，负责管理游戏的所有状态（菜单、说明、游戏、选择等）、
# 处理用户事件、更新游戏逻辑以及绘制所有UI界面。

import pygame
import sys
from config import *
from utils import SoundManager, create_all_icons
from maze import Maze
from entities import AIPlayer
from algorithms.dynamic_programming import calculate_dp_path

class Game:
    """游戏主类"""
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Maze Adventure - Algorithm Comparison")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.game_state = STATE_MAIN_MENU
        self.sound_manager = SoundManager()
        
        self.maze, self.ai_player = None, None
        self.ai_timer, self.ai_move_interval = 0, 100
        
        # 【功能新增】用于存储算法和路径
        self.active_algorithm = ALGO_GREEDY
        self.dp_optimal_path = []
        self.dp_max_score = 0

        # 加载字体
        try:
            font_name = 'markerfelt'
            self.font_title = pygame.font.SysFont(font_name, 80); self.font_button = pygame.font.SysFont(font_name, 50)
            self.font_info = pygame.font.SysFont(font_name, 32); self.font_info_bold = pygame.font.SysFont(font_name, 36, bold=True)
            self.font_legend = pygame.font.SysFont(font_name, 40)
        except pygame.error:
            self.font_title = pygame.font.SysFont(None, 80); self.font_button = pygame.font.SysFont(None, 50)
            self.font_info = pygame.font.SysFont(None, 32); self.font_info_bold = pygame.font.SysFont(None, 36, bold=True)
            self.font_legend = pygame.font.SysFont(None, 40)
            
        self.buttons = {}
        self.legend_icons = create_all_icons(50)

    def start_new_game(self, size):
        """开始一个全新的迷宫实例"""
        self.maze = Maze(size)
        # 【功能新增】游戏开始时，预先计算DP路径
        self.dp_optimal_path, self.dp_max_score = calculate_dp_path(self.maze)
        print(f"DP Optimal Path calculated. Max score: {self.dp_max_score}")
        
        self.reset_simulation(ALGO_GREEDY) # 默认以贪心算法开始
        self.game_state = STATE_GAMEPLAY
        self.sound_manager.play('coin')

    def reset_simulation(self, algorithm):
        """【功能新增】重置模拟并设置新的算法"""
        print(f"Resetting simulation with algorithm: {algorithm}")
        self.active_algorithm = algorithm
        self.maze.reset() # 恢复迷宫到初始状态
        self.ai_player = AIPlayer(start_pos=self.maze.start_pos)
        
        # 如果是DP可视化，将预计算的路径交给AI
        if self.active_algorithm == ALGO_DP_VISUALIZATION:
            self.ai_player.path_to_follow = list(self.dp_optimal_path)

    def run(self):
        while self.game_state != STATE_QUIT:
            self.handle_events(); self.update_state(); self.draw()
            self.clock.tick(FPS)
        pygame.quit(); sys.exit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.game_state = STATE_QUIT
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: self.handle_mouse_click(event.pos)

    def handle_mouse_click(self, mouse_pos):
        self.sound_manager.play('click')
        for name, rect in self.buttons.items():
            if rect.collidepoint(mouse_pos): self.on_button_click(name); break

    def on_button_click(self, button_name):
        if self.game_state == STATE_MAIN_MENU:
            if button_name == 'start': self.game_state = STATE_INSTRUCTIONS
            elif button_name == 'quit': self.game_state = STATE_QUIT
        elif self.game_state == STATE_INSTRUCTIONS:
            if button_name == 'continue': self.game_state = STATE_SELECT_MODE
            elif button_name == 'back': self.game_state = STATE_MAIN_MENU
        elif self.game_state == STATE_SELECT_MODE:
            if 'x' in button_name: self.start_new_game(int(button_name.split('x')[0]))
            elif button_name == 'back': self.game_state = STATE_INSTRUCTIONS
        elif self.game_state == STATE_GAMEPLAY:
            # 【功能新增】处理游戏中的算法切换按钮
            if button_name == ALGO_GREEDY: self.reset_simulation(ALGO_GREEDY)
            elif button_name == ALGO_DP_VISUALIZATION: self.reset_simulation(ALGO_DP_VISUALIZATION)
            elif button_name == 'main_menu': self.game_state = STATE_MAIN_MENU

    def update_state(self):
        if self.game_state == STATE_GAMEPLAY and self.ai_player:
            self.ai_timer += self.clock.get_time()
            if self.ai_timer >= self.ai_move_interval:
                self.ai_timer = 0
                self.ai_player.update(self.maze, self.sound_manager, self.active_algorithm)

    def draw(self):
        self.screen.fill(COLOR_BG)
        if self.game_state == STATE_GAMEPLAY and self.maze:
            maze_surface = self.screen.subsurface((MAZE_AREA_X, MAZE_AREA_Y, MAZE_AREA_SIZE, MAZE_AREA_SIZE))
            path_to_draw = self.dp_optimal_path if self.active_algorithm == ALGO_DP_VISUALIZATION else None
            self.maze.draw(maze_surface, dp_path_to_show=path_to_draw)
            
            if self.ai_player: self.ai_player.draw(maze_surface, self.maze.cell_width, self.maze.cell_height)
            self.draw_info_panel()
        elif self.game_state == STATE_MAIN_MENU: self.draw_main_menu()
        elif self.game_state == STATE_INSTRUCTIONS: self.draw_instructions()
        elif self.game_state == STATE_SELECT_MODE: self.draw_select_mode()
        pygame.display.flip()

    def draw_text(self, text, font, color, pos, centered=False):
        text_surface = font.render(text, True, color)
        rect = text_surface.get_rect(center=pos) if centered else text_surface.get_rect(topleft=pos)
        self.screen.blit(text_surface, rect)

    def draw_button(self, name, text, center_pos, size, font=None):
        if font is None: font = self.font_button
        rect = pygame.Rect((0, 0), size); rect.center = center_pos
        shadow_rect = rect.copy(); shadow_rect.move_ip(5, 5)
        pygame.draw.rect(self.screen, COLOR_BTN_SHADOW, shadow_rect, border_radius=20)
        bg_color = COLOR_BTN_HOVER if rect.collidepoint(pygame.mouse.get_pos()) else COLOR_BTN
        pygame.draw.rect(self.screen, bg_color, rect, border_radius=20)
        self.draw_text(text, font, COLOR_TEXT, rect.center, centered=True)
        self.buttons[name] = rect

    def draw_main_menu(self):
        self.buttons.clear(); self.screen.fill(COLOR_BG)
        self.draw_text("Maze Adventure", self.font_title, COLOR_BTN_SHADOW, (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4), centered=True)
        self.draw_button('start', 'Start Game', (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2), (280, 75))
        self.draw_button('quit', 'Quit', (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 100), (280, 75))

    def draw_instructions(self):
        self.buttons.clear(); self.screen.fill(COLOR_BG)
        self.draw_text("Legend", self.font_title, COLOR_BTN_SHADOW, (SCREEN_WIDTH / 2, 80), centered=True)
        legend_items = { GOLD: "Gold: Provides +10 gold.", HEALTH_POTION: "Potion: Restores +20 health.", TRAP: "Trap: A dangerous obstacle.", LOCKER: "Locker: Blocks a treasure area.", SHOP: "Shop: Buy upgrades here.", BOSS: "Boss: The final challenge."}
        num_items, item_height, gap = len(legend_items), 50, 25
        total_block_height = num_items * item_height + (num_items - 1) * gap
        start_y = (SCREEN_HEIGHT - total_block_height) / 2 + 20
        x_icon, x_text = SCREEN_WIDTH / 2 - 250, SCREEN_WIDTH / 2 - 180
        for i, (item_type, text) in enumerate(legend_items.items()):
            y_pos = start_y + i * (item_height + gap)
            icon_surface = self.legend_icons.get(item_type)
            if icon_surface: self.screen.blit(icon_surface, (x_icon, y_pos))
            self.draw_text(text, self.font_legend, COLOR_HUD_BG, (x_text, y_pos + 5))
        self.draw_button('continue', 'Continue', (SCREEN_WIDTH / 2 + 150, SCREEN_HEIGHT - 100), (220, 70))
        self.draw_button('back', 'Back', (SCREEN_WIDTH / 2 - 150, SCREEN_HEIGHT - 100), (220, 70))

    def draw_select_mode(self):
        self.buttons.clear(); self.screen.fill(COLOR_BG)
        self.draw_text("Select Maze Size", self.font_title, COLOR_BTN_SHADOW, (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 5), centered=True)
        btn_w, btn_h = 220, 70
        self.draw_button('7x7', '7 x 7', (SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.40), (btn_w, btn_h))
        self.draw_button('15x15', '15 x 15', (SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.55), (btn_w, btn_h))
        self.draw_button('31x31', '31 x 31', (SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.70), (btn_w, btn_h))
        self.draw_button('back', 'Back', (SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.85), (btn_w, btn_h))

    def draw_info_panel(self):
        panel_rect = (INFO_PANEL_X, MAZE_AREA_Y, INFO_PANEL_WIDTH, MAZE_AREA_SIZE)
        pygame.draw.rect(self.screen, COLOR_HUD_BG, panel_rect, border_radius=15)
        
        title_pos = (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, 50)
        self.draw_text("AI STATUS", self.font_button, COLOR_BTN_HOVER, title_pos, centered=True)
        if self.ai_player:
            y_offset = 120
            self.draw_text("Health:", self.font_info_bold, COLOR_TEXT, (INFO_PANEL_X + 25, y_offset))
            self.draw_text(f"{self.ai_player.health}", self.font_info, COLOR_SUBTEXT, (INFO_PANEL_X + 150, y_offset))
            y_offset += 40
            self.draw_text("Gold:", self.font_info_bold, COLOR_TEXT, (INFO_PANEL_X + 25, y_offset))
            self.draw_text(f"{self.ai_player.gold}", self.font_info, COLOR_SUBTEXT, (INFO_PANEL_X + 150, y_offset))
            
        y_offset = 250
        self.draw_text("CONTROL", self.font_button, COLOR_BTN_HOVER, (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset), centered=True)
        y_offset += 60
        btn_w, btn_h, btn_font = 240, 55, pygame.font.SysFont('markerfelt', 35) if 'markerfelt' in pygame.font.get_fonts() else pygame.font.SysFont(None, 35)

        # 【功能新增】添加算法切换按钮
        self.draw_button(ALGO_GREEDY, "Run Greedy AI", (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset), (btn_w, btn_h), font=btn_font)
        y_offset += 75
        self.draw_button(ALGO_DP_VISUALIZATION, "Show DP Path", (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset), (btn_w, btn_h), font=btn_font)
        
        y_offset = 550
        self.draw_text("RUNNING:", self.font_info_bold, COLOR_TEXT, (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset), centered=True)
        self.draw_text(self.active_algorithm, self.font_info, COLOR_SUBTEXT, (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset + 35), centered=True)
        
        self.draw_button('main_menu', 'Menu', (INFO_PANEL_X + INFO_PANEL_WIDTH/2, SCREEN_HEIGHT - 80), (220, 60))

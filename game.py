import pygame
import sys
import random
from collections import deque
import json
from config import *
from utils import SoundManager, create_all_icons
from maze import Maze
from entities import AIPlayer, Boss
from algorithms.dynamic_programming import calculate_dp_path
from algorithms.branch_and_bound import find_best_attack_sequence

class Game:
    """游戏主类"""
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Maze Adventure - Boss Battle")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.game_state = STATE_MAIN_MENU
        self.sound_manager = SoundManager()
        
        self.maze, self.ai_player, self.boss = None, None, None
        self.ai_timer, self.ai_move_interval = 0, 100
        self.battle_turn_timer, self.battle_turn_interval = 0, 1000

        self.active_algorithm = ALGO_GREEDY
        self.dp_optimal_path, self.dp_max_score = [], 0
        self.battle_log = deque(maxlen=5)

        try:
            font_name = '楷体-简'
            self.font_title = pygame.font.SysFont(font_name, 80); self.font_button = pygame.font.SysFont(font_name, 50)
            self.font_info = pygame.font.SysFont(font_name, 32); self.font_info_bold = pygame.font.SysFont(font_name, 36, bold=True)
            self.font_legend = pygame.font.SysFont(font_name, 40); self.font_battle = pygame.font.SysFont(font_name, 28)
            self.font_vs = pygame.font.SysFont(font_name, 100, bold=True)
        except pygame.error:
            # Fallback fonts
            self.font_title = pygame.font.SysFont(None, 80); self.font_button = pygame.font.SysFont(None, 50)
            self.font_info = pygame.font.SysFont(None, 32); self.font_info_bold = pygame.font.SysFont(None, 36, bold=True)
            self.font_legend = pygame.font.SysFont(None, 40); self.font_battle = pygame.font.SysFont(None, 28)
            self.font_vs = pygame.font.SysFont(None, 100, bold=True)
            
        self.buttons = {}
        self.legend_icons = create_all_icons(50)

    def start_new_game(self, size=None, source_data=None):
        self.maze = Maze(size=size, source_data=source_data)
        self.boss = Boss()
        self.dp_optimal_path, self.dp_max_score = calculate_dp_path(self.maze)
        self.reset_simulation(ALGO_GREEDY)
        self.game_state = STATE_GAMEPLAY
        self.sound_manager.play('coin')

    def load_fixed_maze_and_start(self):
        fixed_path = 'test_maze.json'
        print(f"正在尝试从固定路径加载测试迷宫: {fixed_path}")
        try:
            with open(fixed_path, 'r') as f:
                data = json.load(f)
            if 'maze' in data and isinstance(data['maze'], list):
                self.start_new_game(source_data=data['maze'])
            else:
                print(f"错误: 文件 '{fixed_path}' 的格式不正确。")
        except FileNotFoundError:
            print(f"错误: 找不到测试文件 '{fixed_path}'。")
        except Exception as e:
            print(f"加载固定迷宫文件时出错: {e}")

    def reset_simulation(self, algorithm):
        self.active_algorithm = algorithm; self.maze.reset(); self.boss.reset()
        self.ai_player = AIPlayer(start_pos=self.maze.start_pos)
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
            if button_name == 'continue': self.game_state = STATE_CHOOSE_MAZE_SOURCE
            elif button_name == 'back': self.game_state = STATE_MAIN_MENU
        elif self.game_state == STATE_CHOOSE_MAZE_SOURCE:
            if button_name == 'generate': self.game_state = STATE_SELECT_MODE
            elif button_name == 'load_test': 
                self.load_fixed_maze_and_start()
            elif button_name == 'back': self.game_state = STATE_INSTRUCTIONS
        elif self.game_state == STATE_SELECT_MODE:
            if 'x' in button_name: self.start_new_game(size=int(button_name.split('x')[0]))
            elif button_name == 'back': self.game_state = STATE_CHOOSE_MAZE_SOURCE 
        elif self.game_state == STATE_GAMEPLAY:
            if button_name == ALGO_GREEDY: self.reset_simulation(ALGO_GREEDY)
            elif button_name == ALGO_DP_VISUALIZATION: self.reset_simulation(ALGO_DP_VISUALIZATION)
            elif button_name == 'main_menu': self.game_state = STATE_MAIN_MENU

    def update_state(self):
        if self.game_state == STATE_GAMEPLAY and self.ai_player and self.ai_player.is_active:
            self.ai_timer += self.clock.get_time()
            if self.ai_timer >= self.ai_move_interval:
                self.ai_timer = 0
                interaction_result = self.ai_player.update(self.maze, self.sound_manager, self.active_algorithm)
                if interaction_result == 'start_battle':
                    self.game_state = STATE_BATTLE; self.battle_log.clear(); self.battle_log.append("The battle begins!")
        elif self.game_state == STATE_BATTLE:
            self.battle_turn_timer += self.clock.get_time()
            if self.battle_turn_timer >= self.battle_turn_interval:
                self.battle_turn_timer = 0; self.update_battle()

    def update_battle(self):
        if self.ai_player.health <= 0 or self.boss.health <= 0: return
        
        # 【核心修改】在每回合开始时，重置临时攻击力
        self.ai_player.attack_boost_this_turn = 0
        
        action = find_best_attack_sequence(self.ai_player, self.boss)
        
        is_frozen_this_turn = False

        if action == "attack":
            self.battle_log.append(f"AI attacks, dealing {self.ai_player.attack} damage!")

        elif action == "boost_gold_attack":
            self.ai_player.gold -= GOLD_COST_FOR_BOOST
            # 【核心修改】设置临时攻击力状态
            self.ai_player.attack_boost_this_turn = ATTACK_BOOST_AMOUNT
            self.battle_log.append(f"AI pays {GOLD_COST_FOR_BOOST} gold to power up!")
            total_damage = self.ai_player.attack + self.ai_player.attack_boost_this_turn
            self.battle_log.append(f"Empowered attack deals {total_damage} damage!")

        elif action == "boost_health_attack":
            self.ai_player.health -= HEALTH_COST_FOR_BOOST
            # 【核心修改】设置临时攻击力状态
            self.ai_player.attack_boost_this_turn = ATTACK_BOOST_AMOUNT
            self.battle_log.append(f"AI sacrifices {HEALTH_COST_FOR_BOOST} health to power up!")
            total_damage = self.ai_player.attack + self.ai_player.attack_boost_this_turn
            self.battle_log.append(f"Empowered attack deals {total_damage} damage!")
            
        elif action in self.ai_player.skills:
            skill_data = SKILLS[action]
            self.ai_player.skills.remove(action)
            self.battle_log.append(f"AI uses skill: {skill_data['name']}!")
            if 'freeze_turns' in skill_data['effect']:
                self.boss.is_frozen_for = skill_data['effect']['freeze_turns']
                is_frozen_this_turn = True
                self.battle_log.append(f"Boss is frozen for {self.boss.is_frozen_for} turn(s)!")

        # --- 应用伤害和结算 ---
        # 【核心修改】计算最终伤害，包含基础攻击、临时提升和技能加成
        final_damage = self.ai_player.attack + self.ai_player.attack_boost_this_turn
        if action in SKILLS and 'damage_multiplier' in SKILLS[action]['effect']:
            final_damage *= SKILLS[action]['effect']['damage_multiplier']
            self.battle_log.append(f"It's super effective! Final damage: {int(final_damage)}!")

        self.boss.health -= final_damage
        
        if self.boss.health <= 0:
            self.battle_log.append("Boss has been defeated!")
            self.ai_player.boss_defeated = True
            self.maze.grid[self.ai_player.y][self.ai_player.x].type = PATH
            self.game_state = STATE_GAMEPLAY
            self.ai_player.target_pos = None
            return

        pygame.time.wait(500)

        # --- Boss反击 ---
        if self.boss.is_frozen_for > 0:
            if not is_frozen_this_turn:
                self.battle_log.append("Boss is frozen and cannot move!")
                self.boss.is_frozen_for -= 1
        else:
            damage_from_boss = self.boss.attack
            self.ai_player.health -= damage_from_boss
            self.battle_log.append(f"Boss retaliates, dealing {damage_from_boss} damage!")
        
        if is_frozen_this_turn and self.boss.is_frozen_for > 0:
            self.boss.is_frozen_for -= 1
            
        if self.ai_player.health <= 0:
            self.battle_log.append("AI has been defeated! Respawning...")
            self.ai_player.x, self.ai_player.y = self.ai_player.start_pos
            self.ai_player.health = self.ai_player.max_health
            self.game_state = STATE_GAMEPLAY
            self.ai_player.target_pos = None
    
    def draw(self):
        self.screen.fill(COLOR_BG)
        if self.game_state in [STATE_GAMEPLAY, STATE_BATTLE] and self.maze:
            maze_surface = self.screen.subsurface((MAZE_AREA_X, MAZE_AREA_Y, MAZE_AREA_SIZE, MAZE_AREA_SIZE))
            path_to_draw = self.dp_optimal_path if self.active_algorithm == ALGO_DP_VISUALIZATION else None
            self.maze.draw(maze_surface, dp_path_to_show=path_to_draw)
            if self.ai_player: self.ai_player.draw(maze_surface, self.maze.cell_width, self.maze.cell_height)
            self.draw_info_panel()
            if self.game_state == STATE_BATTLE: self.draw_battle_screen()
        else: 
            if self.game_state == STATE_MAIN_MENU: self.draw_main_menu()
            elif self.game_state == STATE_INSTRUCTIONS: self.draw_instructions()
            elif self.game_state == STATE_CHOOSE_MAZE_SOURCE: self.draw_choose_maze_source()
            elif self.game_state == STATE_SELECT_MODE: self.draw_select_mode()
        pygame.display.flip()
    
    def draw_choose_maze_source(self):
        self.buttons.clear(); self.screen.fill(COLOR_BG)
        self.draw_text("Choose Maze Source", self.font_title, COLOR_BTN_SHADOW, (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4), centered=True)
        y_pos_start = SCREEN_HEIGHT / 2 - 50
        btn_size = (450, 75)
        self.draw_button('generate', 'Generate Random Maze', (SCREEN_WIDTH / 2, y_pos_start), btn_size)
        self.draw_button('load_test', 'Load Test Maze', (SCREEN_WIDTH / 2, y_pos_start + 100), btn_size)
        self.draw_button('back', 'Back', (100, 50), (150, 60))

    def draw_battle_screen(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        popup_width, popup_height = 800, 500
        popup_x = (SCREEN_WIDTH - popup_width) / 2
        popup_y = (SCREEN_HEIGHT - popup_height) / 2
        popup_rect = pygame.Rect(popup_x, popup_y, popup_width, popup_height)
        pygame.draw.rect(overlay, COLOR_POPUP_BG, popup_rect, border_radius=20)
        pygame.draw.rect(overlay, COLOR_GRID, popup_rect, 4, border_radius=20)
        self.draw_text_on_surface(overlay, "VS", self.font_vs, COLOR_BTN_SHADOW, (SCREEN_WIDTH/2, popup_y + 180), centered=True)
        player_x = popup_x + 200
        self.draw_text_on_surface(overlay, "AI PLAYER", self.font_button, COLOR_TEXT, (player_x, popup_y + 80), centered=True)
        pygame.draw.circle(overlay, COLOR_HUD_BG, (player_x, popup_y + 180), 60)
        pygame.draw.circle(overlay, COLOR_HEALTH_PLAYER, (player_x, popup_y + 180), 60, 5)
        self.draw_health_bar(overlay, player_x - 100, popup_y + 260, 200, 25, self.ai_player.health, self.ai_player.max_health, COLOR_HEALTH_PLAYER)
        self.draw_text_on_surface(overlay, f"{int(self.ai_player.health)}/{self.ai_player.max_health}", self.font_info, COLOR_TEXT, (player_x, popup_y + 295), centered=True)
        boss_x = popup_x + popup_width - 200
        self.draw_text_on_surface(overlay, "THE BOSS", self.font_button, COLOR_TEXT, (boss_x, popup_y + 80), centered=True)
        pygame.draw.circle(overlay, COLOR_HUD_BG, (boss_x, popup_y + 180), 60)
        pygame.draw.circle(overlay, COLOR_HEALTH_BOSS, (boss_x, popup_y + 180), 60, 5)
        self.draw_health_bar(overlay, boss_x - 100, popup_y + 260, 200, 25, self.boss.health, self.boss.max_health, COLOR_HEALTH_BOSS)
        self.draw_text_on_surface(overlay, f"{int(self.boss.health)}/{self.boss.max_health}", self.font_info, COLOR_TEXT, (boss_x, popup_y + 295), centered=True)
        log_bg_rect = pygame.Rect(popup_x + 50, popup_y + 350, popup_width - 100, 120)
        pygame.draw.rect(overlay, COLOR_BATTLE_LOG_BG, log_bg_rect, border_radius=10)
        y_offset = popup_y + 370
        for log_entry in self.battle_log:
            self.draw_text_on_surface(overlay, log_entry, self.font_battle, COLOR_TEXT, (SCREEN_WIDTH/2, y_offset), centered=True)
            y_offset += 25
        self.screen.blit(overlay, (0, 0))
        
    def draw_text_on_surface(self, surface, text, font, color, pos, centered=False):
        text_surface = font.render(text, True, color)
        rect = text_surface.get_rect(center=pos) if centered else text_surface.get_rect(topleft=pos)
        surface.blit(text_surface, rect)
        
    def draw_text(self, text, font, color, pos, centered=False):
        self.draw_text_on_surface(self.screen, text, font, color, pos, centered)
        
    def draw_button(self, name, text, center_pos, size, font=None):
        if font is None: font = self.font_button
        rect = pygame.Rect((0, 0), size); rect.center = center_pos; shadow_rect = rect.copy(); shadow_rect.move_ip(5, 5)
        pygame.draw.rect(self.screen, COLOR_BTN_SHADOW, shadow_rect, border_radius=20)
        bg_color = COLOR_BTN_HOVER if rect.collidepoint(pygame.mouse.get_pos()) else COLOR_BTN
        pygame.draw.rect(self.screen, bg_color, rect, border_radius=20)
        self.draw_text(text, font, COLOR_TEXT, rect.center, centered=True); self.buttons[name] = rect
        
    def draw_health_bar(self, surf, x, y, w, h, current, max_val, color):
        if current < 0: current = 0
        fill_pct = current / max_val
        pygame.draw.rect(surf, COLOR_HEALTH_BG, (x, y, w, h), border_radius=5)
        pygame.draw.rect(surf, color, (x, y, w * fill_pct, h), border_radius=5)
        pygame.draw.rect(surf, COLOR_TEXT, (x, y, w, h), 2, border_radius=5)
        
    def draw_main_menu(self):
        # ...此函数无变化...
        self.buttons.clear(); self.screen.fill(COLOR_BG)
        self.draw_text("Maze Adventure", self.font_title, COLOR_BTN_SHADOW, (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4), centered=True)
        self.draw_button('start', 'Start Game', (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2), (280, 75))
        self.draw_button('quit', 'Quit', (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 100), (280, 75))
        
    def draw_instructions(self):
        # ...此函数无变化...
        self.buttons.clear(); self.screen.fill(COLOR_BG)
        self.draw_text("Legend", self.font_title, COLOR_BTN_SHADOW, (SCREEN_WIDTH / 2, 80), centered=True)
        legend_items = { GOLD: "Gold: Provides +10 gold.", HEALTH_POTION: "Potion: Restores +20 health.", TRAP: "Trap: A dangerous obstacle.", LOCKER: "Locker: Blocks a treasure area.", SHOP: "Shop: Buy upgrades here.", BOSS: "Boss: The final challenge."}
        num_items, item_height, gap = len(legend_items), 50, 25
        total_block_height = num_items * item_height + (num_items - 1) * gap; start_y = (SCREEN_HEIGHT - total_block_height) / 2 + 20
        x_icon, x_text = SCREEN_WIDTH / 2 - 250, SCREEN_WIDTH / 2 - 180
        for i, (item_type, text) in enumerate(legend_items.items()):
            y_pos = start_y + i * (item_height + gap)
            icon_surface = self.legend_icons.get(item_type)
            if icon_surface: self.screen.blit(icon_surface, (x_icon, y_pos))
            self.draw_text(text, self.font_legend, COLOR_HUD_BG, (x_text, y_pos + 5))
        self.draw_button('continue', 'Continue', (SCREEN_WIDTH / 2, SCREEN_HEIGHT - 100), (220, 70))
        self.draw_button('back', 'Back', (100, 50), (150, 60))
        
    def draw_select_mode(self):
        # ...此函数无变化...
        self.buttons.clear(); self.screen.fill(COLOR_BG)
        self.draw_text("Select Maze Size", self.font_title, COLOR_BTN_SHADOW, (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 5), centered=True)
        btn_w, btn_h = 220, 70
        self.draw_button('7x7', '7 x 7', (SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.40), (btn_w, btn_h))
        self.draw_button('15x15', '15 x 15', (SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.55), (btn_w, btn_h))
        self.draw_button('31x31', '31 x 31', (SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.70), (btn_w, btn_h))
        self.draw_button('back', 'Back', (100, 50), (150, 60))
        
    def draw_info_panel(self):
        panel_rect = (INFO_PANEL_X, MAZE_AREA_Y, INFO_PANEL_WIDTH, MAZE_AREA_SIZE)
        pygame.draw.rect(self.screen, COLOR_HUD_BG, panel_rect, border_radius=15)
        title_pos = (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, 50)
        self.draw_text("AI STATUS", self.font_button, COLOR_BTN_HOVER, title_pos, centered=True)
        if self.ai_player:
            y_offset = 120
            self.draw_text("Health:", self.font_info_bold, COLOR_TEXT, (INFO_PANEL_X + 25, y_offset)); self.draw_text(f"{self.ai_player.health}/{self.ai_player.max_health}", self.font_info, COLOR_SUBTEXT, (INFO_PANEL_X + 180, y_offset))
            y_offset += 40
            self.draw_text("Gold:", self.font_info_bold, COLOR_TEXT, (INFO_PANEL_X + 25, y_offset)); self.draw_text(f"{self.ai_player.gold}", self.font_info, COLOR_SUBTEXT, (INFO_PANEL_X + 180, y_offset))
            y_offset += 40
            self.draw_text("Diamonds:", self.font_info_bold, COLOR_TEXT, (INFO_PANEL_X + 25, y_offset)); self.draw_text(f"{self.ai_player.diamonds}", self.font_info, COLOR_SUBTEXT, (INFO_PANEL_X + 180, y_offset))
            y_offset += 40
            
            # 动态显示攻击力
            self.draw_text("Attack:", self.font_info_bold, COLOR_TEXT, (INFO_PANEL_X + 25, y_offset))
            attack_text = f"{self.ai_player.attack}"
            text_color = COLOR_SUBTEXT
            if hasattr(self.ai_player, 'attack_boost_this_turn') and self.ai_player.attack_boost_this_turn > 0:
                attack_text += f" (+{self.ai_player.attack_boost_this_turn})"
                text_color = COLOR_HEALTH_PLAYER # 使用绿色高亮
            self.draw_text(attack_text, self.font_info, text_color, (INFO_PANEL_X + 180, y_offset))
            
            y_offset += 40
            self.draw_text("Skills:", self.font_info_bold, COLOR_TEXT, (INFO_PANEL_X + 25, y_offset))
            skill_y = y_offset
            for skill_id in self.ai_player.skills: self.draw_text(f"- {SKILLS[skill_id]['name']}", self.font_info, COLOR_SUBTEXT, (INFO_PANEL_X + 140, skill_y)); skill_y += 30
        
        y_offset = 450
        self.draw_text("CONTROL", self.font_button, COLOR_BTN_HOVER, (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset), centered=True)
        y_offset += 60
        btn_w, btn_h, btn_font = 240, 55, pygame.font.SysFont('楷体-简', 35) if 'markerfelt' in pygame.font.get_fonts() else pygame.font.SysFont(None, 35)
        self.draw_button(ALGO_GREEDY, "Run Greedy AI", (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset), (btn_w, btn_h), font=btn_font)
        y_offset += 75
        self.draw_button(ALGO_DP_VISUALIZATION, "Show DP Path", (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset), (btn_w, btn_h), font=btn_font)
        y_offset = 650
        self.draw_text("RUNNING:", self.font_info_bold, COLOR_TEXT, (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset), centered=True)
        self.draw_text(self.active_algorithm, self.font_info, COLOR_SUBTEXT, (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset + 35), centered=True)
        self.draw_button('main_menu', 'Menu', (INFO_PANEL_X + INFO_PANEL_WIDTH/2, SCREEN_HEIGHT - 60), (220, 60))
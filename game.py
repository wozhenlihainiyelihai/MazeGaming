import pygame
import sys
import random
import hashlib
from collections import deque
import json
from config import * # 导入游戏配置，例如颜色、状态常量等
from utils import SoundManager, create_all_icons  # 导入音效管理器和图标创建函数
from maze import Maze  # 导入迷宫类
from entities import AIPlayer, Boss  # 导入 AI 玩家和 Boss 实体类
from algorithms.dynamic_programming import calculate_dp_path  # 导入动态规划寻路算法
from algorithms.branch_and_bound import find_best_attack_sequence  # 导入分支定界攻击序列算法
from algorithms.backtracking import solve_puzzle_by_method  # 导入回溯法解谜算法

class Game:
    """游戏主类"""
    def __init__(self):
        pygame.init()  # 初始化 Pygame
        pygame.display.set_caption("Maze Adventure - AI Algorithms")  # 设置窗口标题
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))  # 创建游戏窗口
        self.clock = pygame.time.Clock()  # 创建游戏时钟
        self.game_state = STATE_MAIN_MENU  # 初始游戏状态为主菜单
        self.sound_manager = SoundManager()  # 初始化音效管理器
        
        self.maze, self.ai_player, self.boss = None, None, None  # 迷宫、AI 玩家、Boss 对象
        self.ai_timer, self.ai_move_interval = 0, 100  # AI 移动计时器及间隔
        self.battle_turn_timer, self.battle_turn_interval = 0, 1000  # 战斗回合计时器及间隔

        self.active_algorithm = ALGO_GREEDY  # 当前活跃的 AI 算法
        self.dp_optimal_path, self.dp_max_score = [], 0  # 动态规划的最优路径和最高得分
        self.battle_log = deque(maxlen=5)  # 战斗日志，最多存储 5 条

        # 谜题状态变量
        self.puzzle_solver = None  # 谜题求解器
        self.puzzle_timer = 0  # 谜题更新计时器
        self.puzzle_update_interval = 100  # 谜题更新间隔
        self.puzzle_current_path = []  # 谜题当前尝试的路径
        self.puzzle_status_text = ""  # 谜题状态文本
        self.puzzle_clue_texts = []  # 谜题线索文本
        self.puzzle_length = 0  # 谜题长度
        self.puzzle_target_hash = ""  # 谜题目标哈希值
        self.puzzle_tries_count = 0  # 谜题尝试次数
        self.puzzle_active_method = ""  # 谜题当前使用的解法

        try:
            # 尝试加载自定义字体
            font_name = 'sans-serif'
            self.font_title = pygame.font.SysFont(font_name, 80); self.font_button = pygame.font.SysFont(font_name, 50)
            self.font_info = pygame.font.SysFont(font_name, 32); self.font_info_bold = pygame.font.SysFont(font_name, 36, bold=True)
            self.font_legend = pygame.font.SysFont(font_name, 40); self.font_battle = pygame.font.SysFont(font_name, 28)
            self.font_vs = pygame.font.SysFont(font_name, 100, bold=True)
            self.font_result = pygame.font.SysFont(font_name, 120, bold=True)
        except pygame.error:
            # 字体加载失败时的备用字体
            self.font_title = pygame.font.SysFont(None, 80); self.font_button = pygame.font.SysFont(None, 50)
            self.font_info = pygame.font.SysFont(None, 32); self.font_info_bold = pygame.font.SysFont(None, 36, bold=True)
            self.font_legend = pygame.font.SysFont(None, 40); self.font_battle = pygame.font.SysFont(None, 28)
            self.font_vs = pygame.font.SysFont(None, 100, bold=True)
            self.font_result = pygame.font.SysFont(None, 120, bold=True)
            
        self.buttons = {}  # 存储按钮的字典
        self.legend_icons = create_all_icons(50)  # 创建所有图例图标

    def start_new_game(self, size=None, source_data=None):
        """开始新游戏，创建迷宫、Boss 和 AI 玩家，并计算 DP 路径"""
        self.maze = Maze(size=size, source_data=source_data)  # 创建迷宫
        self.boss = Boss()  # 创建 Boss
        self.dp_optimal_path, self.dp_max_score = calculate_dp_path(self.maze)  # 计算动态规划最优路径
        self.reset_simulation(ALGO_GREEDY)  # 重置模拟，默认使用贪婪算法
        self.game_state = STATE_GAMEPLAY  # 切换到游戏进行中状态
        self.sound_manager.play('coin')  # 播放音效

    def load_fixed_maze_and_start(self):
        """加载预设迷宫并开始游戏"""
        fixed_path = 'test_maze.json'  # 预设迷宫文件路径
        print(f"Attempting to load test maze from: {fixed_path}")
        try:
            with open(fixed_path, 'r') as f:
                data = json.load(f)  # 加载 JSON 数据
            if 'maze' in data and isinstance(data['maze'], list):
                self.start_new_game(source_data=data['maze'])  # 使用加载的数据开始游戏
            else:
                print(f"Error: Format of '{fixed_path}' is incorrect.")
        except FileNotFoundError:
            print(f"Error: Test file '{fixed_path}' not found.")
        except Exception as e:
            print(f"Error loading fixed maze file: {e}")

    def reset_simulation(self, algorithm):
        """重置模拟，并设置新的 AI 算法"""
        self.active_algorithm = algorithm  # 设置当前活跃算法
        self.maze.reset()  # 重置迷宫
        self.boss.reset()  # 重置 Boss
        self.ai_player = AIPlayer(start_pos=self.maze.start_pos)  # 创建新的 AI 玩家
        if self.active_algorithm == ALGO_DP_VISUALIZATION:
            self.ai_player.path_to_follow = list(self.dp_optimal_path)  # 如果是 DP 可视化，则设置 AI 玩家跟随 DP 路径

    def run(self):
        """游戏主循环"""
        while self.game_state != STATE_QUIT:  # 只要游戏状态不是退出，就一直运行
            self.handle_events()  # 处理事件
            self.update_state()  # 更新游戏状态
            self.draw()  # 绘制画面
            self.clock.tick(FPS)  # 控制游戏帧率
        pygame.quit()  # 退出 Pygame
        sys.exit()  # 退出程序

    def handle_events(self):
        """处理 Pygame 事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.game_state = STATE_QUIT  # 关闭窗口事件
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: self.handle_mouse_click(event.pos)  # 鼠标左键点击事件

    def handle_mouse_click(self, mouse_pos):
        """处理鼠标点击逻辑"""
        self.sound_manager.play('click')  # 播放点击音效
        for name, rect in self.buttons.items():
            if rect.collidepoint(mouse_pos): self.on_button_click(name); break  # 如果点击到按钮，则触发按钮点击事件

    def on_button_click(self, button_name):
        """根据按钮名称执行相应操作"""
        if self.game_state == STATE_MAIN_MENU:
            if button_name == 'start': self.game_state = STATE_INSTRUCTIONS  # 开始游戏
            elif button_name == 'quit': self.game_state = STATE_QUIT  # 退出游戏
        elif self.game_state == STATE_INSTRUCTIONS:
            if button_name == 'continue': self.game_state = STATE_CHOOSE_MAZE_SOURCE  # 继续
            elif button_name == 'back': self.game_state = STATE_MAIN_MENU  # 返回主菜单
        elif self.game_state == STATE_CHOOSE_MAZE_SOURCE:
            if button_name == 'generate': self.game_state = STATE_SELECT_MODE  # 生成随机迷宫
            elif button_name == 'load_test': 
                self.load_fixed_maze_and_start()  # 加载测试迷宫
            elif button_name == 'back': self.game_state = STATE_INSTRUCTIONS  # 返回说明
        elif self.game_state == STATE_SELECT_MODE:
            if 'x' in button_name: self.start_new_game(size=int(button_name.split('x')[0]))  # 根据选择的尺寸开始新游戏
            elif button_name == 'back': self.game_state = STATE_CHOOSE_MAZE_SOURCE  # 返回迷宫来源选择
        elif self.game_state == STATE_GAMEPLAY:
            if button_name == ALGO_GREEDY: self.reset_simulation(ALGO_GREEDY)  # 切换到贪婪算法
            elif button_name == ALGO_DP_VISUALIZATION: self.reset_simulation(ALGO_DP_VISUALIZATION)  # 切换到 DP 可视化
            elif button_name == 'main_menu': self.game_state = STATE_MAIN_MENU  # 返回主菜单

    def generate_clue_texts(self, clues, length):
        """动态生成人类可读的谜题线索描述"""
        texts = []
        has_uniqueness_clue = True
        for clue in clues:
            if clue == [-1, -1]:
                texts.append("Each digit is a unique prime number.")  # 每个数字都是唯一的质数
                has_uniqueness_clue = False 
            elif len(clue) == 2:
                pos, prop = clue
                pos_text = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(pos, f"{pos}th")
                prop_text = "even" if prop == 0 else "odd"
                texts.append(f"The {pos_text} digit is {prop_text}.")  # 第 n 位是偶数/奇数
            elif len(clue) == length:
                for i, digit in enumerate(clue):
                    if digit != -1:
                        pos_text = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(i + 1, f"{i+1}th")
                        texts.append(f"The {pos_text} digit is {digit}.")  # 第 n 位是某个数字
        if has_uniqueness_clue:
             texts.append("Digits do not repeat.")  # 数字不重复
        return texts

    def update_state(self):
        """更新游戏状态逻辑"""
        if self.game_state == STATE_GAMEPLAY and self.ai_player and self.ai_player.is_active:
            self.ai_timer += self.clock.get_time()
            if self.ai_timer >= self.ai_move_interval:
                self.ai_timer = 0
                interaction_result = self.ai_player.update(self.maze, self.sound_manager, self.active_algorithm)  # 更新 AI 玩家状态
                if interaction_result == 'start_battle':
                    self.game_state = STATE_BATTLE; self.battle_log.clear(); self.battle_log.append("The battle begins!")  # 进入战斗
                elif interaction_result == 'start_puzzle':
                    self.game_state = STATE_PUZZLE  # 进入谜题
                    
                    salt = b'\xb2\x53\x22\x65\x7d\xdf\xb0\xfe\x9c\xde\xde\xfe\xf3\x1d\xdc\x3e' # 固定盐值

                    # 谜题列表
                    puzzles = [
                        {
                            "L":  "81d5400ab2eca801a80837500be67485d0f8b297db1fa8ecbe4a23b66b65f6b8", # 密码: 825
                            "C": [[3,1],[-1,-1,5]], "length": 3, "salt": salt
                        },
                        {
                            "L": "78cc114968ab659cb55dabd23e31d30186cf6529d6e7529cdfadb5940d5be8e5", #"密码": "357"
                            "C":[[-1,-1]], "length":3, "salt":salt
                        },
                        {
                           "L": "fd6c3f5085ea7aec0ea67683fd144303b0747091af782b246683811047e6dab8", # 密码: 715
                           "C": [[1,1], [-1,1,-1], [3,1]], "length": 3, "salt": salt
                        }
                    ]
                    chosen_puzzle = random.choice(puzzles)  # 随机选择一个谜题
                    
                    self.puzzle_length = chosen_puzzle["length"]  # 谜题长度
                    self.puzzle_clue_texts = self.generate_clue_texts(chosen_puzzle["C"], chosen_puzzle["length"])  # 生成线索文本
                    self.puzzle_target_hash = chosen_puzzle["L"]  # 目标哈希
                    self.puzzle_active_method = random.choice(["method1", "method2", "method3"])  # 随机选择解法
                    
                    self.puzzle_solver = solve_puzzle_by_method( # 初始化谜题求解器
                        self.puzzle_active_method,
                        chosen_puzzle["C"],
                        chosen_puzzle["L"],
                        chosen_puzzle["length"],
                        chosen_puzzle["salt"],
                        {"count": 0} 
                    )
                    self.puzzle_current_path = []  # 重置当前路径
                    self.puzzle_status_text = "Initializing puzzle sequence..."  # 初始化状态文本
                    self.puzzle_timer = 0  # 重置计时器
                    self.puzzle_tries_count = 0  # 重置尝试次数
        elif self.game_state == STATE_BATTLE:
            self.battle_turn_timer += self.clock.get_time()
            if self.battle_turn_timer >= self.battle_turn_interval:
                self.battle_turn_timer = 0; self.update_battle()  # 更新战斗状态
        elif self.game_state == STATE_PUZZLE:
            self.puzzle_timer += self.clock.get_time()
            if self.puzzle_timer >= self.puzzle_update_interval:
                self.puzzle_timer = 0
                self.update_puzzle()  # 更新谜题状态

    def update_puzzle(self):
        """驱动回溯法谜题进程并处理结果"""
        if not self.puzzle_solver: return

        try:
            self.puzzle_current_path, self.puzzle_status_text, self.puzzle_tries_count = next(self.puzzle_solver)  # 获取谜题求解器的下一步

            if "Success!" in self.puzzle_status_text:  # 谜题成功
                self.draw_puzzle_screen()  # 绘制谜题界面
                self.draw_final_puzzle_result("SUCCESS", COLOR_HEALTH_PLAYER)  # 绘制成功结果

                locker_tile = self.maze.grid[self.ai_player.y][self.ai_player.x]
                locker_tile.type = PATH  # 储物柜变为路径
                self.ai_player.diamonds += PUZZLE_REWARD_DIAMONDS  # 获得钻石奖励
                self.ai_player.needs_new_target = True  # AI 玩家需要新目标
                self.game_state = STATE_GAMEPLAY  # 返回游戏进行中状态
                self.puzzle_solver = None  # 清空求解器
                self.sound_manager.play('coin')  # 播放音效

        except StopIteration:  # 谜题失败（无解或达到尝试上限）
            self.draw_puzzle_screen()
            self.draw_final_puzzle_result("FAILURE", COLOR_HEALTH_BOSS)  # 绘制失败结果

            locker_tile = self.maze.grid[self.ai_player.y][self.ai_player.x]
            locker_tile.type = WALL  # 储物柜变为墙

            # 智能撤退逻辑
            if len(self.ai_player.path_history) > 1:
                self.ai_player.path_history.pop()  # 移除最后一个（墙）
                prev_pos = self.ai_player.path_history[-1]  # 获取上一个位置
                self.ai_player.x, self.ai_player.y = prev_pos  # 移动回上一个位置

            self.ai_player.needs_new_target = True  # AI 玩家需要新目标
            self.game_state = STATE_GAMEPLAY  # 返回游戏进行中状态
            self.puzzle_solver = None  # 清空求解器

    def update_battle(self):
        """更新战斗状态逻辑"""
        if self.ai_player.health <= 0 or self.boss.health <= 0: return  # 任意一方生命值归零则结束战斗
        
        self.ai_player.attack_boost_this_turn = 0  # 重置本回合攻击加成
        action = find_best_attack_sequence(self.ai_player, self.boss)  # AI 玩家选择最佳攻击序列
        is_frozen_this_turn = False  # 本回合是否冻结 Boss

        if action == "attack": self.battle_log.append(f"AI attacks, dealing {self.ai_player.attack} damage!")  # 普通攻击
        elif action == "boost_gold_attack":
            self.ai_player.gold -= GOLD_COST_FOR_BOOST  # 消耗金币
            self.ai_player.attack_boost_this_turn = ATTACK_BOOST_AMOUNT  # 增加攻击力
            self.battle_log.append(f"AI pays {GOLD_COST_FOR_BOOST} gold to power up!")
            self.battle_log.append(f"Empowered attack deals {self.ai_player.attack + self.ai_player.attack_boost_this_turn} damage!")
        elif action == "boost_health_attack":
            self.ai_player.health -= HEALTH_COST_FOR_BOOST  # 消耗生命值
            self.ai_player.attack_boost_this_turn = ATTACK_BOOST_AMOUNT  # 增加攻击力
            self.battle_log.append(f"AI sacrifices {HEALTH_COST_FOR_BOOST} health to power up!")
            self.battle_log.append(f"Empowered attack deals {self.ai_player.attack + self.ai_player.attack_boost_this_turn} damage!")
        elif action in self.ai_player.skills:
            skill_data = SKILLS[action]
            self.ai_player.skills.remove(action)  # 移除已使用的技能
            self.battle_log.append(f"AI uses skill: {skill_data['name']}!")
            if 'freeze_turns' in skill_data['effect']:
                self.boss.is_frozen_for = skill_data['effect']['freeze_turns']  # 冻结 Boss
                is_frozen_this_turn = True
                self.battle_log.append(f"Boss is frozen for {self.boss.is_frozen_for} turn(s)!")

        final_damage = self.ai_player.attack + self.ai_player.attack_boost_this_turn  # 计算最终伤害
        if action in SKILLS and 'damage_multiplier' in SKILLS[action]['effect']:
            final_damage *= SKILLS[action]['effect']['damage_multiplier']  # 技能伤害倍率
            self.battle_log.append(f"It's super effective! Final damage: {int(final_damage)}!")

        self.boss.health -= final_damage  # Boss 掉血
        if self.boss.health <= 0:
            self.battle_log.append("Boss has been defeated!")
            self.ai_player.boss_defeated = True  # 标记 Boss 已被击败
            self.maze.grid[self.ai_player.y][self.ai_player.x].type = PATH  # Boss 所在格子变为路径
            self.game_state = STATE_GAMEPLAY  # 返回游戏进行中状态
            self.ai_player.target_pos = None  # 清空目标位置
            return

        pygame.time.wait(500)  # 暂停一段时间

        if self.boss.is_frozen_for > 0:
            if not is_frozen_this_turn:
                self.battle_log.append("Boss is frozen and cannot move!")  # Boss 被冻结
                self.boss.is_frozen_for -= 1
        else:
            self.ai_player.health -= self.boss.attack  # Boss 反击
            self.battle_log.append(f"Boss retaliates, dealing {self.boss.attack} damage!")
        
        if is_frozen_this_turn and self.boss.is_frozen_for > 0: self.boss.is_frozen_for -= 1  # 冻结回合数递减
        if self.ai_player.health <= 0:
            self.battle_log.append("AI has been defeated! Respawning...")  # AI 被击败
            self.ai_player.x, self.ai_player.y = self.ai_player.start_pos  # 重生
            self.ai_player.health = self.ai_player.max_health  # 回复生命
            self.game_state = STATE_GAMEPLAY  # 返回游戏进行中状态
            self.ai_player.target_pos = None  # 清空目标位置
    
    def draw(self):
        """绘制所有游戏元素"""
        self.screen.fill(COLOR_BG)  # 填充背景色
        if self.game_state in [STATE_GAMEPLAY, STATE_BATTLE, STATE_PUZZLE] and self.maze:
            maze_surface = self.screen.subsurface((MAZE_AREA_X, MAZE_AREA_Y, MAZE_AREA_SIZE, MAZE_AREA_SIZE))  # 获取迷宫绘制区域
            path_to_draw = self.dp_optimal_path if self.active_algorithm == ALGO_DP_VISUALIZATION else None  # 根据算法选择是否绘制 DP 路径
            self.maze.draw(maze_surface, dp_path_to_show=path_to_draw)  # 绘制迷宫
            if self.ai_player: self.ai_player.draw(maze_surface, self.maze.cell_width, self.maze.cell_height)  # 绘制 AI 玩家
            self.draw_info_panel()  # 绘制信息面板
            if self.game_state == STATE_BATTLE: self.draw_battle_screen()  # 绘制战斗界面
            if self.game_state == STATE_PUZZLE: self.draw_puzzle_screen()  # 绘制谜题界面
        else: 
            if self.game_state == STATE_MAIN_MENU: self.draw_main_menu()  # 绘制主菜单
            elif self.game_state == STATE_INSTRUCTIONS: self.draw_instructions()  # 绘制说明
            elif self.game_state == STATE_CHOOSE_MAZE_SOURCE: self.draw_choose_maze_source()  # 绘制迷宫来源选择界面
            elif self.game_state == STATE_SELECT_MODE: self.draw_select_mode()  # 绘制选择迷宫尺寸界面
        pygame.display.flip()  # 更新显示

    def draw_final_puzzle_result(self, message, color):
        """绘制谜题最终结果（成功/失败）"""
        result_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)  # 创建透明图层
        text_surf = self.font_result.render(message, True, color)  # 渲染结果文本
        text_rect = text_surf.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))  # 获取文本矩形
        bg_rect = text_rect.inflate(40, 40)  # 背景矩形
        pygame.draw.rect(result_overlay, (*COLOR_HUD_BG, 230), bg_rect, border_radius=15)  # 绘制半透明背景
        result_overlay.blit(text_surf, text_rect)  # 绘制文本
        self.screen.blit(result_overlay, (0, 0))  # 绘制到屏幕
        pygame.display.flip()  # 更新显示
        pygame.time.wait(1500)  # 暂停一段时间

    def draw_puzzle_screen(self):
        """绘制谜题界面"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)  # 创建透明图层
        pygame.draw.rect(overlay, COLOR_POPUP_BG, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))  # 绘制背景

        title_font, info_font = self.font_title, self.font_info
        
        self.draw_text_on_surface(overlay, "Password Lock", title_font, COLOR_TEXT, (SCREEN_WIDTH / 2, 80), centered=True)  # 绘制标题
        
        method_text = f"Strategy: {self.puzzle_active_method}"
        self.draw_text_on_surface(overlay, method_text, info_font, COLOR_TEXT, (SCREEN_WIDTH/2, 160), centered=True)  # 绘制解法

        clue_y = 200
        for text in self.puzzle_clue_texts:
            self.draw_text_on_surface(overlay, text, info_font, COLOR_TEXT, (SCREEN_WIDTH / 2, clue_y), centered=True)  # 绘制线索
            clue_y += 35

        hash_text = f"Target Hash: {self.puzzle_target_hash[:16]}..."
        self.draw_text_on_surface(overlay, hash_text, info_font, COLOR_TEXT, (SCREEN_WIDTH / 2, clue_y + 20), centered=True)  # 绘制目标哈希
        
        box_size, box_gap = 80, 20
        total_width = self.puzzle_length * box_size + (self.puzzle_length - 1) * box_gap
        start_x, y_pos = (SCREEN_WIDTH - total_width) / 2, SCREEN_HEIGHT / 2 + 30

        for i in range(self.puzzle_length):
            box_rect = pygame.Rect(start_x + i * (box_size + box_gap), y_pos, box_size, box_size)
            pygame.draw.rect(overlay, COLOR_HEALTH_BG, box_rect, border_radius=10)  # 绘制数字框背景
            pygame.draw.rect(overlay, COLOR_GRID, box_rect, 4, border_radius=10)  # 绘制数字框边框
            if i < len(self.puzzle_current_path):
                num_text = str(self.puzzle_current_path[i])
                self.draw_text_on_surface(overlay, num_text, self.font_vs, COLOR_BTN_HOVER, box_rect.center, centered=True)  # 绘制当前数字
        
        tries_text = f"Tries: {self.puzzle_tries_count}"
        self.draw_text_on_surface(overlay, tries_text, self.font_info_bold, COLOR_SUBTEXT, (start_x + total_width, y_pos - 40))  # 绘制尝试次数
        self.draw_text_on_surface(overlay, self.puzzle_status_text, self.font_info_bold, COLOR_SUBTEXT, (SCREEN_WIDTH / 2, y_pos + 150), centered=True)  # 绘制状态文本
        self.screen.blit(overlay, (0, 0))  # 绘制到屏幕

    def draw_choose_maze_source(self):
        """绘制选择迷宫来源界面"""
        self.buttons.clear(); self.screen.fill(COLOR_BG)
        self.draw_text("Choose Maze Source", self.font_title, COLOR_BTN_SHADOW, (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4), centered=True)
        self.draw_button('generate', 'Generate Random Maze', (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50), (450, 75))
        self.draw_button('load_test', 'Load Test Maze', (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50), (450, 75))
        self.draw_button('back', 'Back', (100, 50), (150, 60))

    def draw_battle_screen(self):
        """绘制战斗界面"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)  # 创建透明图层
        popup_width, popup_height = 800, 500
        popup_x, popup_y = (SCREEN_WIDTH - popup_width) / 2, (SCREEN_HEIGHT - popup_height) / 2
        popup_rect = pygame.Rect(popup_x, popup_y, popup_width, popup_height)
        pygame.draw.rect(overlay, COLOR_POPUP_BG, popup_rect, border_radius=20)  # 绘制弹窗背景
        pygame.draw.rect(overlay, COLOR_GRID, popup_rect, 4, border_radius=20)  # 绘制弹窗边框
        self.draw_text_on_surface(overlay, "VS", self.font_vs, COLOR_BTN_SHADOW, (SCREEN_WIDTH/2, popup_y + 180), centered=True)  # 绘制 VS 文本
        player_x = popup_x + 200
        self.draw_text_on_surface(overlay, "AI PLAYER", self.font_button, COLOR_TEXT, (player_x, popup_y + 80), centered=True)  # 绘制 AI 玩家标题
        pygame.draw.circle(overlay, COLOR_HUD_BG, (player_x, popup_y + 180), 60); pygame.draw.circle(overlay, COLOR_HEALTH_PLAYER, (player_x, popup_y + 180), 60, 5)  # 绘制 AI 玩家头像
        self.draw_health_bar(overlay, player_x - 100, popup_y + 260, 200, 25, self.ai_player.health, self.ai_player.max_health, COLOR_HEALTH_PLAYER)  # 绘制 AI 玩家血条
        self.draw_text_on_surface(overlay, f"{int(self.ai_player.health)}/{self.ai_player.max_health}", self.font_info, COLOR_TEXT, (player_x, popup_y + 295), centered=True)  # 绘制 AI 玩家血量文本
        boss_x = popup_x + popup_width - 200
        self.draw_text_on_surface(overlay, "THE BOSS", self.font_button, COLOR_TEXT, (boss_x, popup_y + 80), centered=True)  # 绘制 Boss 标题
        pygame.draw.circle(overlay, COLOR_HUD_BG, (boss_x, popup_y + 180), 60); pygame.draw.circle(overlay, COLOR_HEALTH_BOSS, (boss_x, popup_y + 180), 60, 5)  # 绘制 Boss 头像
        self.draw_health_bar(overlay, boss_x - 100, popup_y + 260, 200, 25, self.boss.health, self.boss.max_health, COLOR_HEALTH_BOSS)  # 绘制 Boss 血条
        self.draw_text_on_surface(overlay, f"{int(self.boss.health)}/{self.boss.max_health}", self.font_info, COLOR_TEXT, (boss_x, popup_y + 295), centered=True)  # 绘制 Boss 血量文本
        log_bg_rect = pygame.Rect(popup_x + 50, popup_y + 350, popup_width - 100, 120)
        pygame.draw.rect(overlay, COLOR_BATTLE_LOG_BG, log_bg_rect, border_radius=10)  # 绘制战斗日志背景
        y_offset = popup_y + 370
        for log_entry in self.battle_log:
            self.draw_text_on_surface(overlay, log_entry, self.font_battle, COLOR_TEXT, (SCREEN_WIDTH/2, y_offset), centered=True)  # 绘制战斗日志条目
            y_offset += 25
        self.screen.blit(overlay, (0, 0))  # 绘制到屏幕
        
    def draw_text_on_surface(self, surface, text, font, color, pos, centered=False):
        """在指定 surface 上绘制文本"""
        text_surface = font.render(text, True, color)
        rect = text_surface.get_rect(center=pos) if centered else text_surface.get_rect(topleft=pos)
        surface.blit(text_surface, rect)
        
    def draw_text(self, text, font, color, pos, centered=False):
        """在主屏幕上绘制文本（封装）"""
        self.draw_text_on_surface(self.screen, text, font, color, pos, centered)
        
    def draw_button(self, name, text, center_pos, size, font=None):
        """绘制按钮"""
        if font is None: font = self.font_button
        rect = pygame.Rect((0, 0), size); rect.center = center_pos; shadow_rect = rect.copy(); shadow_rect.move_ip(5, 5)
        pygame.draw.rect(self.screen, COLOR_BTN_SHADOW, shadow_rect, border_radius=20)  # 绘制按钮阴影
        bg_color = COLOR_BTN_HOVER if rect.collidepoint(pygame.mouse.get_pos()) else COLOR_BTN  # 根据鼠标悬停状态选择颜色
        pygame.draw.rect(self.screen, bg_color, rect, border_radius=20)  # 绘制按钮背景
        self.draw_text(text, font, COLOR_TEXT, rect.center, centered=True); self.buttons[name] = rect  # 绘制按钮文本并存储按钮矩形

    def draw_health_bar(self, surf, x, y, w, h, current, max_val, color):
        """绘制血条"""
        if current < 0: current = 0
        fill_pct = current / max_val  # 计算填充百分比
        pygame.draw.rect(surf, COLOR_HEALTH_BG, (x, y, w, h), border_radius=5)  # 绘制血条背景
        pygame.draw.rect(surf, color, (x, y, w * fill_pct, h), border_radius=5)  # 绘制血条填充
        pygame.draw.rect(surf, COLOR_TEXT, (x, y, w, h), 2, border_radius=5)  # 绘制血条边框
        
    def draw_main_menu(self):
        """绘制主菜单"""
        self.buttons.clear(); self.screen.fill(COLOR_BG)
        self.draw_text("Maze Adventure", self.font_title, COLOR_BTN_SHADOW, (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4), centered=True)
        self.draw_button('start', 'Start Game', (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2), (280, 75))
        self.draw_button('quit', 'Quit', (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 100), (280, 75))
        
    def draw_instructions(self):
        """绘制说明/图例界面"""
        self.buttons.clear(); self.screen.fill(COLOR_BG)
        self.draw_text("Legend", self.font_title, COLOR_BTN_SHADOW, (SCREEN_WIDTH / 2, 80), centered=True)
        legend_items = { GOLD: "Gold", HEALTH_POTION: "Potion", TRAP: "Trap", LOCKER: "Locker", SHOP: "Shop", BOSS: "Boss"}  # 图例项
        item_height, gap, start_y = 50, 25, (SCREEN_HEIGHT - (len(legend_items) * (50 + 25) - 25)) / 2
        x_icon, x_text = SCREEN_WIDTH / 2 - 150, SCREEN_WIDTH / 2 - 80
        for i, (item_type, text) in enumerate(legend_items.items()):
            y_pos = start_y + i * (item_height + gap)
            icon_surface = self.legend_icons.get(item_type)
            if icon_surface: self.screen.blit(icon_surface, (x_icon, y_pos))  # 绘制图标
            self.draw_text(text, self.font_legend, COLOR_HUD_BG, (x_text, y_pos + 5))  # 绘制文本
        self.draw_button('continue', 'Continue', (SCREEN_WIDTH / 2, SCREEN_HEIGHT - 100), (220, 70))
        self.draw_button('back', 'Back', (100, 50), (150, 60))
        
    def draw_select_mode(self):
        """绘制选择迷宫尺寸界面"""
        self.buttons.clear(); self.screen.fill(COLOR_BG)
        self.draw_text("Select Maze Size", self.font_title, COLOR_BTN_SHADOW, (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 5), centered=True)
        btn_w, btn_h = 220, 70
        self.draw_button('7x7', '7 x 7', (SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.40), (btn_w, btn_h))
        self.draw_button('15x15', '15 x 15', (SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.55), (btn_w, btn_h))
        self.draw_button('31x31', '31 x 31', (SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.70), (btn_w, btn_h))
        self.draw_button('back', 'Back', (100, 50), (150, 60))
        
    def draw_info_panel(self):
        """绘制信息面板（AI 状态和控制按钮）"""
        panel_rect = (INFO_PANEL_X, MAZE_AREA_Y, INFO_PANEL_WIDTH, MAZE_AREA_SIZE)
        pygame.draw.rect(self.screen, COLOR_HUD_BG, panel_rect, border_radius=15)  # 绘制面板背景
        title_pos = (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, 50)
        self.draw_text("AI STATUS", self.font_button, COLOR_BTN_HOVER, title_pos, centered=True)  # 绘制 AI 状态标题
        if self.ai_player:
            y_offset = 120
            stats = {"Health": f"{self.ai_player.health}/{self.ai_player.max_health}", "Gold": f"{self.ai_player.gold}", "Diamonds": f"{self.ai_player.diamonds}", "Attack": f"{self.ai_player.attack}"}
            for stat, value in stats.items():
                self.draw_text(f"{stat}:", self.font_info_bold, COLOR_TEXT, (INFO_PANEL_X + 25, y_offset))
                text_color = COLOR_SUBTEXT
                if stat == "Attack" and hasattr(self.ai_player, 'attack_boost_this_turn') and self.ai_player.attack_boost_this_turn > 0:
                    value += f" (+{self.ai_player.attack_boost_this_turn})"  # 显示攻击加成
                    text_color = COLOR_HEALTH_PLAYER
                self.draw_text(value, self.font_info, text_color, (INFO_PANEL_X + 180, y_offset))
                y_offset += 40
            
            y_offset += 10
            self.draw_text("Skills:", self.font_info_bold, COLOR_TEXT, (INFO_PANEL_X + 25, y_offset))  # 绘制技能标题
            skill_y = y_offset
            for skill_id in self.ai_player.skills:
                self.draw_text(f"- {SKILLS[skill_id]['name']}", self.font_info, COLOR_SUBTEXT, (INFO_PANEL_X + 140, skill_y)); skill_y += 30  # 绘制技能列表
        
        y_offset = 450
        self.draw_text("CONTROL", self.font_button, COLOR_BTN_HOVER, (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset), centered=True)  # 绘制控制标题
        y_offset += 60
        btn_w, btn_h, btn_font = 240, 55, pygame.font.SysFont('sans-serif', 35)
        self.draw_button(ALGO_GREEDY, "Run Greedy AI", (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset), (btn_w, btn_h), font=btn_font)  # 绘制贪婪 AI 按钮
        y_offset += 75
        self.draw_button(ALGO_DP_VISUALIZATION, "Show DP Path", (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset), (btn_w, btn_h), font=btn_font)  # 绘制 DP 路径按钮
        y_offset = 650
        self.draw_text("RUNNING:", self.font_info_bold, COLOR_TEXT, (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset), centered=True)  # 绘制当前运行算法标题
        self.draw_text(self.active_algorithm, self.font_info, COLOR_SUBTEXT, (INFO_PANEL_X + INFO_PANEL_WIDTH / 2, y_offset + 35), centered=True)  # 绘制当前运行算法名称
        self.draw_button('main_menu', 'Menu', (INFO_PANEL_X + INFO_PANEL_WIDTH/2, SCREEN_HEIGHT - 60), (220, 60))  # 绘制主菜单按钮
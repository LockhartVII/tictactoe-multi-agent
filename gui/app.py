"""Unified desktop interface for the multi-agent board-game project."""

import time

import pygame

from .other_games import OtherGamesController
from .theme import BG, CYAN, FPS, GREEN, HEIGHT, MUTED, PANEL, PANEL_2, PURPLE, RED, TEXT, WIDTH, YELLOW, button, divider, panel, text
from .tictactoe import STRATEGIES, STRATEGY_LABELS, TicTacToeGame


SCREEN_MENU = "menu"
SCREEN_TTT_CONFIG = "ttt_config"
SCREEN_TTT_GAME = "ttt_game"
SCREEN_OTHER_CONFIG = "other_config"
SCREEN_OTHER_GAME = "other_game"


class BoardGameApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Multi-Agent Board Lab")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.screen_state = SCREEN_MENU
        self.ttt_size = 3
        self.ttt_mode = "human_vs_ai"
        self.ttt_human_side = "X"
        self.x_strategy = "alpha_zero"
        self.o_strategy = "mcts"
        self.other_kind = "gomoku"
        self.other_size = 15
        self.other_mode = "human_vs_ai"
        self.difficulty = "mid"
        self.ttt = None
        self.other = OtherGamesController()

    def run(self):
        while self.running:
            now = time.monotonic()
            mouse = pygame.mouse.get_pos()
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(now)
            self.draw(mouse)
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        position = event.pos
        if self.screen_state == SCREEN_MENU:
            if pygame.Rect(120, 235, 430, 82).collidepoint(position):
                self.screen_state = SCREEN_TTT_CONFIG
            elif pygame.Rect(650, 235, 430, 82).collidepoint(position):
                self.screen_state = SCREEN_OTHER_CONFIG
        elif self.screen_state == SCREEN_TTT_CONFIG:
            self.handle_ttt_config(position)
        elif self.screen_state == SCREEN_TTT_GAME:
            self.handle_ttt_game(position)
        elif self.screen_state == SCREEN_OTHER_CONFIG:
            self.handle_other_config(position)
        elif self.screen_state == SCREEN_OTHER_GAME:
            self.handle_other_game(position)

    def update(self, now):
        if self.screen_state == SCREEN_TTT_GAME and self.ttt:
            self.ttt.tick(now)
        elif self.screen_state == SCREEN_OTHER_GAME:
            self.other.tick(now)

    def handle_ttt_config(self, position):
        if pygame.Rect(48, 112, 120, 44).collidepoint(position):
            self.screen_state = SCREEN_MENU
            return
        for size, rect in self._size_buttons(180, 222, 110):
            if rect.collidepoint(position):
                self.ttt_size = size
        for mode, rect in (("human_vs_ai", pygame.Rect(180, 314, 190, 48)), ("ai_vs_ai", pygame.Rect(390, 314, 190, 48))):
            if rect.collidepoint(position):
                self.ttt_mode = mode
        if self.ttt_mode == "human_vs_ai":
            for side, rect in (("X", pygame.Rect(180, 422, 190, 48)), ("O", pygame.Rect(390, 422, 190, 48))):
                if rect.collidepoint(position):
                    self.ttt_human_side = side
        strategy_y = 510 if self.ttt_mode == "human_vs_ai" else 422
        if self.ttt_mode == "ai_vs_ai" or self.ttt_human_side == "O":
            for strategy, rect in self._strategy_buttons(180, strategy_y):
                if rect.collidepoint(position):
                    self.x_strategy = strategy
        if self.ttt_mode == "ai_vs_ai" or self.ttt_human_side == "X":
            for strategy, rect in self._strategy_buttons(630, strategy_y):
                if rect.collidepoint(position):
                    self.o_strategy = strategy
        start_y = 720 if self.ttt_mode == "human_vs_ai" else 646
        if pygame.Rect(180, start_y, 400, 56).collidepoint(position):
            x_strategy = "human" if self.ttt_mode == "human_vs_ai" and self.ttt_human_side == "X" else self.x_strategy
            o_strategy = "human" if self.ttt_mode == "human_vs_ai" and self.ttt_human_side == "O" else self.o_strategy
            self.ttt = TicTacToeGame(self.ttt_size, x_strategy, o_strategy, self.ttt_mode)
            self.ttt.start()
            self.screen_state = SCREEN_TTT_GAME

    def handle_ttt_game(self, position):
        board_rect = pygame.Rect(46, 112, 650, 650)
        if self.ttt:
            self.ttt.click(position, board_rect)
        if pygame.Rect(760, 690, 210, 54).collidepoint(position):
            self.ttt = TicTacToeGame(self.ttt_size, self.ttt.x_strategy, self.ttt.o_strategy, self.ttt_mode)
            self.ttt.start()
        elif pygame.Rect(990, 690, 210, 54).collidepoint(position):
            self.screen_state = SCREEN_TTT_CONFIG

    def handle_other_config(self, position):
        if pygame.Rect(48, 112, 120, 44).collidepoint(position):
            self.screen_state = SCREEN_MENU
            return
        for kind, rect in (("gomoku", pygame.Rect(180, 212, 180, 50)), ("go", pygame.Rect(380, 212, 180, 50)), ("xiangqi", pygame.Rect(580, 212, 180, 50))):
            if rect.collidepoint(position):
                self.other_kind = kind
        if self.other_kind == "gomoku":
            for size, rect in ((9, pygame.Rect(180, 324, 120, 48)), (13, pygame.Rect(320, 324, 120, 48)), (15, pygame.Rect(460, 324, 120, 48))):
                if rect.collidepoint(position):
                    self.other_size = size
            for difficulty, rect in (("low", pygame.Rect(180, 446, 120, 48)), ("mid", pygame.Rect(320, 446, 120, 48)), ("high", pygame.Rect(460, 446, 120, 48))):
                if rect.collidepoint(position):
                    self.difficulty = difficulty
            for mode, rect in (("human_vs_ai", pygame.Rect(180, 538, 170, 48)), ("ai_vs_ai", pygame.Rect(370, 538, 170, 48)), ("human_vs_human", pygame.Rect(560, 538, 190, 48))):
                if rect.collidepoint(position):
                    self.other_mode = mode
        else:
            for mode, rect in (("human_vs_ai", pygame.Rect(180, 490, 170, 48)), ("ai_vs_ai", pygame.Rect(370, 490, 170, 48)), ("human_vs_human", pygame.Rect(560, 490, 190, 48))):
                if rect.collidepoint(position):
                    self.other_mode = mode
        if pygame.Rect(180, 646, 400, 56).collidepoint(position):
            size = 9 if self.other_kind == "go" else self.other_size
            self.other.start(self.other_kind, self.other_mode, self.difficulty, size)
            self.screen_state = SCREEN_OTHER_GAME

    def handle_other_game(self, position):
        board_rect = pygame.Rect(44, 108, 700, 650)
        self.other.click(position, board_rect)
        if pygame.Rect(790, 690, 210, 54).collidepoint(position):
            size = 9 if self.other_kind == "go" else self.other_size
            self.other.start(self.other_kind, self.other_mode, self.difficulty, size)
        elif pygame.Rect(1020, 690, 210, 54).collidepoint(position):
            self.screen_state = SCREEN_OTHER_CONFIG

    def draw(self, mouse):
        self.screen.fill(BG)
        self.draw_header()
        if self.screen_state == SCREEN_MENU:
            self.draw_menu(mouse)
        elif self.screen_state == SCREEN_TTT_CONFIG:
            self.draw_ttt_config(mouse)
        elif self.screen_state == SCREEN_TTT_GAME:
            self.draw_ttt_game(mouse)
        elif self.screen_state == SCREEN_OTHER_CONFIG:
            self.draw_other_config(mouse)
        elif self.screen_state == SCREEN_OTHER_GAME:
            self.draw_other_game(mouse)

    def draw_header(self):
        text(self.screen, "MULTI-AGENT BOARD LAB", (48, 30), 24, TEXT, bold=True)
        text(self.screen, "Strategy lab · Multi-board · Replayable logs", (48, 62), 15, MUTED)
        pygame.draw.circle(self.screen, GREEN, (1184, 46), 5)
        text(self.screen, "LOCAL READY", (1198, 38), 14, GREEN, bold=True, anchor="midright")
        divider(self.screen, 48, 88, WIDTH - 48, 88, (38, 59, 91))

    def draw_menu(self, mouse):
        text(self.screen, "Choose an experiment", (80, 160), 38, TEXT, bold=True)
        text(self.screen, "Tic-Tac-Toe connects directly to the current strategies and model files.", (82, 208), 18, MUTED)
        cards = [(pygame.Rect(120, 235, 430, 82), "Tic-Tac-Toe", "3x3 · 4x4 · 5x5 · 9x9", CYAN),
                 (pygame.Rect(650, 235, 430, 82), "More games", "Gomoku · Go · Xiangqi", PURPLE)]
        for rect, title, subtitle, accent in cards:
            panel(self.screen, rect, PANEL_2, accent)
            text(self.screen, title, (rect.left + 24, rect.top + 17), 24, TEXT, bold=True)
            text(self.screen, subtitle, (rect.left + 24, rect.top + 52), 16, MUTED)
            text(self.screen, "OPEN  ›", (rect.right - 24, rect.centery), 15, accent, bold=True, anchor="midright")
        panel(self.screen, pygame.Rect(120, 390, 960, 190), PANEL)
        text(self.screen, "Current build", (150, 420), 20, CYAN, bold=True)
        text(self.screen, "Tic-Tac-Toe", (150, 465), 18, TEXT)
        text(self.screen, "Strategies: random / heuristic / minimax / alpha-beta / MCTS / AlphaZero", (270, 465), 17, MUTED)
        text(self.screen, "Models", (150, 510), 18, CYAN)
        text(self.screen, "Loads models/alphazero/*_best.pt by board size", (270, 510), 17, MUTED)

    def draw_ttt_config(self, mouse):
        self.draw_back_button(mouse)
        text(self.screen, "Tic-Tac-Toe settings", (180, 130), 34, TEXT, bold=True)
        text(self.screen, "Choose a board, then assign both strategies", (180, 166), 17, MUTED)
        text(self.screen, "Board size", (180, 194), 17, MUTED)
        for size, rect in self._size_buttons(180, 222, 110):
            button(self.screen, rect, f"{size}x{size}", size == self.ttt_size, rect.collidepoint(mouse), CYAN)
        text(self.screen, "Game mode", (180, 286), 17, MUTED)
        for mode, rect, label in (("human_vs_ai", pygame.Rect(180, 314, 190, 48), "Human vs AI"), ("ai_vs_ai", pygame.Rect(390, 314, 190, 48), "AI vs AI")):
            button(self.screen, rect, label, mode == self.ttt_mode, rect.collidepoint(mouse), PURPLE)
        strategy_y = 510 if self.ttt_mode == "human_vs_ai" else 422
        if self.ttt_mode == "human_vs_ai":
            text(self.screen, "Your side", (180, 382), 17, MUTED)
            for side, rect in (("X", pygame.Rect(180, 422, 190, 48)), ("O", pygame.Rect(390, 422, 190, 48))):
                button(self.screen, rect, f"Play {side}", side == self.ttt_human_side, rect.collidepoint(mouse), RED if side == "X" else CYAN)
            x_label = "X strategy (AI)" if self.ttt_human_side == "O" else "X strategy (Human)"
            o_label = "O strategy (AI)" if self.ttt_human_side == "X" else "O strategy (Human)"
        else:
            x_label, o_label = "X strategy", "O strategy"
        label_y = strategy_y - 32 if self.ttt_mode == "human_vs_ai" else strategy_y - 40
        text(self.screen, x_label, (180, label_y), 17, MUTED)
        text(self.screen, o_label, (630, label_y), 17, MUTED)
        x_enabled = self.ttt_mode == "ai_vs_ai" or self.ttt_human_side == "O"
        o_enabled = self.ttt_mode == "ai_vs_ai" or self.ttt_human_side == "X"
        for strategy, rect in self._strategy_buttons(180, strategy_y):
            active = x_enabled and strategy == self.x_strategy
            button(self.screen, rect, STRATEGY_LABELS[strategy], active, rect.collidepoint(mouse) and x_enabled, CYAN, small=True, enabled=x_enabled)
        for strategy, rect in self._strategy_buttons(630, strategy_y):
            active = o_enabled and strategy == self.o_strategy
            button(self.screen, rect, STRATEGY_LABELS[strategy], active, rect.collidepoint(mouse) and o_enabled, CYAN, small=True, enabled=o_enabled)
        if self.ttt_mode == "human_vs_ai":
            ai_side = "O" if self.ttt_human_side == "X" else "X"
            ai_strategy = self.o_strategy if ai_side == "O" else self.x_strategy
            panel(self.screen, pygame.Rect(180, 672, 400, 40), (17, 47, 66), CYAN)
            text(self.screen, f"Human: {self.ttt_human_side}   ·   AI: {ai_side} ({STRATEGY_LABELS[ai_strategy]})", (205, 684), 15, TEXT, bold=True)
        self.draw_start_button(mouse, "Start Tic-Tac-Toe", 720 if self.ttt_mode == "human_vs_ai" else 646)

    def draw_ttt_game(self, mouse):
        if not self.ttt:
            return
        board_rect = pygame.Rect(46, 112, 650, 650)
        self.ttt.draw(self.screen, board_rect)
        self.ttt.draw_sidebar(self.screen, pygame.Rect(770, 112, 430, 520))
        self.draw_game_buttons(mouse)

    def draw_other_config(self, mouse):
        self.draw_back_button(mouse)
        text(self.screen, "More games", (180, 130), 34, TEXT, bold=True)
        text(self.screen, "Original game modes, refreshed interface", (180, 166), 17, MUTED)
        text(self.screen, "Game", (180, 180), 17, MUTED)
        for kind, rect, label in (("gomoku", pygame.Rect(180, 212, 180, 50), "Gomoku"), ("go", pygame.Rect(380, 212, 180, 50), "Go"), ("xiangqi", pygame.Rect(580, 212, 180, 50), "Xiangqi")):
            button(self.screen, rect, label, kind == self.other_kind, rect.collidepoint(mouse), PURPLE)
        if self.other_kind == "gomoku":
            text(self.screen, "Board size", (180, 292), 17, MUTED)
            for size, rect in ((9, pygame.Rect(180, 324, 120, 48)), (13, pygame.Rect(320, 324, 120, 48)), (15, pygame.Rect(460, 324, 120, 48))):
                button(self.screen, rect, f"{size}x{size}", size == self.other_size, rect.collidepoint(mouse), PURPLE)
            text(self.screen, "AI difficulty", (180, 414), 17, MUTED)
            for difficulty, rect, label in (("low", pygame.Rect(180, 446, 120, 48), "Easy"), ("mid", pygame.Rect(320, 446, 120, 48), "Medium"), ("high", pygame.Rect(460, 446, 120, 48), "Hard")):
                button(self.screen, rect, label, difficulty == self.difficulty, rect.collidepoint(mouse), PURPLE)
            text(self.screen, "Game mode", (180, 514), 17, MUTED)
            mode_y = 538
        else:
            panel(self.screen, pygame.Rect(180, 324, 580, 100), PANEL, PURPLE)
            if self.other_kind == "go":
                text(self.screen, "Go uses a 9x9 board with placement, captures,", (205, 350), 17, TEXT)
                text(self.screen, "and suicide prevention.", (205, 374), 17, TEXT)
            else:
                text(self.screen, "Xiangqi supports selection, movement, captures,", (205, 350), 17, TEXT)
                text(self.screen, "and flying-general checks.", (205, 374), 17, TEXT)
            text(self.screen, "Game mode", (180, 466), 17, MUTED)
            mode_y = 490
        for mode, label, x, width in (("human_vs_ai", "Human vs AI", 180, 170), ("ai_vs_ai", "AI vs AI", 370, 170), ("human_vs_human", "Human vs Human", 560, 190)):
            rect = pygame.Rect(x, mode_y, width, 48)
            button(self.screen, rect, label, mode == self.other_mode, rect.collidepoint(mouse), PURPLE, small=True)
        self.draw_start_button(mouse, "Start " + ("Gomoku" if self.other_kind == "gomoku" else "Go" if self.other_kind == "go" else "Xiangqi"))

    def draw_other_game(self, mouse):
        board_rect = pygame.Rect(44, 108, 700, 650)
        self.other.draw(self.screen, board_rect)
        panel(self.screen, pygame.Rect(790, 108, 410, 520), PANEL_2, PURPLE)
        text(self.screen, self.other.title, (820, 135), 28, TEXT, bold=True)
        if self.other.game_over:
            status = "Draw" if self.other.draw_game else f"{('Red' if self.other.winner == 1 else 'Black')} wins"
        else:
            status = "Red to move" if self.other.current_player == 1 else "Black to move"
        text(self.screen, status, (820, 190), 22, YELLOW if self.other.game_over else GREEN)
        text(self.screen, "Click inside the board to play", (820, 280), 16, MUTED)
        text(self.screen, self.other.engine_status, (820, 320), 15, CYAN if "AI" not in self.other.engine_status else YELLOW)
        self.draw_game_buttons(mouse)

    def draw_back_button(self, mouse):
        rect = pygame.Rect(48, 112, 120, 44)
        button(self.screen, rect, "‹ Back", False, rect.collidepoint(mouse), MUTED, small=True)

    def draw_start_button(self, mouse, label, y=646):
        rect = pygame.Rect(180, y, 400, 56)
        button(self.screen, rect, label + "  ›", True, rect.collidepoint(mouse), CYAN)

    def draw_game_buttons(self, mouse):
        for rect, label, accent in ((pygame.Rect(760, 690, 210, 54), "Restart", CYAN), (pygame.Rect(990, 690, 210, 54), "Settings", PURPLE)):
            button(self.screen, rect, label, False, rect.collidepoint(mouse), accent, small=True)

    @staticmethod
    def _size_buttons(x, y, width):
        return [(size, pygame.Rect(x + index * (width + 12), y, width, 48)) for index, size in enumerate((3, 4, 5, 9))]

    @staticmethod
    def _strategy_buttons(x, y):
        return [(strategy, pygame.Rect(x + (index % 2) * 210, y + (index // 2) * 52, 190, 42)) for index, strategy in enumerate(STRATEGIES)]


def main():
    BoardGameApp().run()

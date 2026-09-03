"""Tic-Tac-Toe controller backed by the project's current strategies and models."""

import json
import random
from datetime import datetime
from pathlib import Path

import pygame

from board_environment import available, new_board, terminal, win_length_for
from minmax import minimax_move
from strategies import alpha_beta_move
from multiboard_tournament import choose_move as choose_multiboard_move
from .theme import CYAN, GREEN, GRID_BRIGHT, MUTED, PANEL_2, RED, TEXT, YELLOW, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STRATEGIES = ("random", "heuristic", "minimax", "alpha_beta", "mcts", "alpha_zero")
STRATEGY_LABELS = {
    "random": "Random",
    "heuristic": "Heuristic",
    "minimax": "Minimax",
    "alpha_beta": "Alpha-Beta",
    "mcts": "MCTS",
    "alpha_zero": "AlphaZero",
}


class TicTacToeGame:
    def __init__(self, size=3, x_strategy="human", o_strategy="alpha_zero", mode="human_vs_ai"):
        self.size = size
        self.x_strategy = x_strategy
        self.o_strategy = o_strategy
        self.mode = mode
        self.win_length = win_length_for(size)
        self.board = new_board(size)
        self.mark = "X"
        self.result = None
        self.moves = []
        self.message = "Waiting for a move"
        self.ai_wait_until = 0.0
        self.log_path = None

    @property
    def current_strategy(self):
        return self.x_strategy if self.mark == "X" else self.o_strategy

    @property
    def human_turn(self):
        return self.current_strategy == "human"

    def start(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.log_path = PROJECT_ROOT / "logs" / "gui" / "tictactoe" / f"game_{timestamp}.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_event({"event": "GAME_START", "size": self.size, "win_length": self.win_length,
                           "x_strategy": self.x_strategy, "o_strategy": self.o_strategy,
                           "mode": self.mode})

    def _write_event(self, event):
        if self.log_path is None:
            return
        with open(self.log_path, "a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _move_for_strategy(self, strategy):
        legal = available(self.board)
        if not legal:
            return None
        if strategy == "minimax" and self.size == 3:
            return minimax_move(self.board, self.mark)
        if strategy == "alpha_beta" and self.size == 3:
            return alpha_beta_move(self.board, self.mark)
        if strategy in ("minimax", "alpha_beta"):
            self.message = f"{STRATEGY_LABELS[strategy]} is 3x3 only; using a heuristic fallback"
            strategy = "heuristic"
        simulations = {3: 120, 4: 80, 5: 50, 9: 20}.get(self.size, 20)
        return choose_multiboard_move(
            self.board,
            self.mark,
            strategy,
            self.size,
            self.win_length,
            simulations,
            random.Random(),
            alpha_simulations=simulations,
            baseline_simulations=max(2, simulations // 4),
        )

    def play(self, move, source="human"):
        legal = available(self.board)
        if move not in legal or self.result is not None:
            return False
        before = self.board.copy()
        mark = self.mark
        strategy = self.current_strategy
        self.board[move] = mark
        self.moves.append(move)
        finished, result = terminal(self.board, self.size, self.win_length)
        self._write_event({"event": "MOVE", "move_number": len(self.moves), "mark": mark,
                           "strategy": strategy, "source": source, "move": move,
                           "board_before": before, "board_after": self.board.copy(),
                           "result": result if finished else None})
        if finished:
            self.result = result
            self.message = "Draw" if result == "DRAW" else f"{result} wins"
            self._write_event({"event": "GAME_OVER", "result": result, "moves": len(self.moves)})
        else:
            self.mark = "O" if self.mark == "X" else "X"
            self.message = f"Turn: {self.mark} · {STRATEGY_LABELS.get(self.current_strategy, 'Human')}"
        return True

    def click(self, position, board_rect):
        if not self.human_turn or self.result is not None or not board_rect.collidepoint(position):
            return False
        cell = board_rect.width / self.size
        column = int((position[0] - board_rect.left) / cell)
        row = int((position[1] - board_rect.top) / cell)
        if not (0 <= row < self.size and 0 <= column < self.size):
            return False
        return self.play(row * self.size + column)

    def tick(self, now):
        if self.result is not None or self.human_turn or now < self.ai_wait_until:
            return
        move = self._move_for_strategy(self.current_strategy)
        self.play(move, source="agent")
        self.ai_wait_until = now + (0.28 if self.mode == "ai_vs_ai" else 0.18)

    def draw(self, surface, board_rect):
        pygame.draw.rect(surface, (10, 18, 34), board_rect, border_radius=16)
        cell = board_rect.width / self.size
        for index in range(self.size + 1):
            position = round(board_rect.left + index * cell)
            pygame.draw.line(surface, GRID_BRIGHT, (position, board_rect.top), (position, board_rect.bottom), 2)
            position = round(board_rect.top + index * cell)
            pygame.draw.line(surface, GRID_BRIGHT, (board_rect.left, position), (board_rect.right, position), 2)
        for index, mark in enumerate(self.board):
            if mark == " ":
                continue
            row, column = divmod(index, self.size)
            center = (round(board_rect.left + (column + 0.5) * cell),
                      round(board_rect.top + (row + 0.5) * cell))
            radius = max(12, int(cell * 0.29))
            colour = RED if mark == "X" else CYAN
            width = max(3, int(cell * 0.07))
            if mark == "X":
                pygame.draw.line(surface, colour, (center[0] - radius, center[1] - radius),
                                 (center[0] + radius, center[1] + radius), width)
                pygame.draw.line(surface, colour, (center[0] + radius, center[1] - radius),
                                 (center[0] - radius, center[1] + radius), width)
            else:
                pygame.draw.circle(surface, colour, center, radius, width)
        text(surface, f"{self.size}x{self.size}  ·  {self.win_length} in a row", (board_rect.left, board_rect.bottom + 14),
             18, MUTED)

    def draw_sidebar(self, surface, rect):
        pygame.draw.rect(surface, PANEL_2, rect, border_radius=18)
        text(surface, "Current game", (rect.left + 24, rect.top + 22), 24, TEXT, bold=True)
        text(surface, self.message, (rect.left + 24, rect.top + 66), 20,
             GREEN if self.result == "X" else YELLOW if self.result == "DRAW" else TEXT)
        text(surface, f"X  {STRATEGY_LABELS.get(self.x_strategy, 'Human')}", (rect.left + 24, rect.top + 120), 18, RED)
        text(surface, f"O  {STRATEGY_LABELS.get(self.o_strategy, 'Human')}", (rect.left + 24, rect.top + 154), 18, CYAN)
        text(surface, f"Moves  {len(self.moves)}", (rect.left + 24, rect.top + 214), 18, MUTED)
        if self.log_path:
            text(surface, "Log saved", (rect.left + 24, rect.bottom - 42), 16, MUTED)

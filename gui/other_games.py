"""Controllers for Gomoku, Go, and Xiangqi from the original GUI."""

import copy
import random

import pygame

from .theme import CYAN, GRID_BRIGHT, MUTED, PANEL_2, RED, TEXT, YELLOW, text


XIANGQI_INIT = [
    ["r", "h", "e", "a", "k", "a", "e", "h", "r"],
    ["", "", "", "", "", "", "", "", ""],
    ["", "c", "", "", "", "", "", "c", ""],
    ["p", "", "p", "", "", "", "p", "", "p"],
    ["", "", "", "", "", "", "", "", ""],
    ["", "", "", "", "", "", "", "", ""],
    ["P", "", "P", "", "", "", "P", "", "P"],
    ["", "C", "", "", "", "", "", "C", ""],
    ["", "", "", "", "", "", "", "", ""],
    ["R", "H", "E", "A", "K", "A", "E", "H", "R"],
]
XIANGQI_NAMES = {
    "r": "车", "h": "马", "e": "象", "a": "士", "k": "将", "c": "炮", "p": "卒",
    "R": "車", "H": "馬", "E": "相", "A": "仕", "K": "帥", "C": "砲", "P": "兵",
}


def gomoku_winner(board, win_length=5):
    size = len(board)
    for row in range(size):
        for column in range(size):
            mark = board[row][column]
            if not mark:
                continue
            directions = ((0, 1), (1, 0), (1, 1), (1, -1))
            for row_step, column_step in directions:
                cells = []
                for offset in range(win_length):
                    r = row + offset * row_step
                    c = column + offset * column_step
                    if not (0 <= r < size and 0 <= c < size):
                        break
                    cells.append(board[r][c])
                if len(cells) == win_length and all(cell == mark for cell in cells):
                    return mark
    return 0


def empty_points(board):
    return [(row, column) for row in range(len(board)) for column in range(len(board)) if board[row][column] == 0]


def gomoku_ai(board, player, difficulty):
    choices = empty_points(board)
    if not choices:
        return None
    opponent = 1 if player == 2 else 2
    if difficulty == "low":
        return random.choice(choices)
    for point, mark in ((point, player) for point in choices):
        trial = copy.deepcopy(board)
        trial[point[0]][point[1]] = mark
        if gomoku_winner(trial) == mark:
            return point
    for point in choices:
        trial = copy.deepcopy(board)
        trial[point[0]][point[1]] = opponent
        if gomoku_winner(trial) == opponent:
            return point
    if difficulty == "mid":
        return random.choice(choices)
    size = len(board)
    center = (size - 1) / 2
    return min(choices, key=lambda point: abs(point[0] - center) + abs(point[1] - center))


def go_neighbors(row, column, size):
    return [(r, c) for r, c in ((row - 1, column), (row + 1, column), (row, column - 1), (row, column + 1))
            if 0 <= r < size and 0 <= c < size]


def go_group(board, row, column, size):
    colour = board[row][column]
    group = {(row, column)}
    stack = [(row, column)]
    while stack:
        current = stack.pop()
        for neighbour in go_neighbors(*current, size):
            if board[neighbour[0]][neighbour[1]] == colour and neighbour not in group:
                group.add(neighbour)
                stack.append(neighbour)
    return group


def go_liberties(board, group, size):
    return len({point for stone in group for point in go_neighbors(*stone, size) if board[point[0]][point[1]] == 0})


def go_play(board, row, column, colour):
    size = len(board)
    if board[row][column] != 0:
        return False
    trial = [line.copy() for line in board]
    trial[row][column] = colour
    opponent = 2 if colour == 1 else 1
    for neighbour in go_neighbors(row, column, size):
        if trial[neighbour[0]][neighbour[1]] == opponent:
            group = go_group(trial, *neighbour, size)
            if go_liberties(trial, group, size) == 0:
                for stone in group:
                    trial[stone[0]][stone[1]] = 0
    if go_liberties(trial, go_group(trial, row, column, size), size) == 0:
        return False
    for row_index in range(size):
        board[row_index][:] = trial[row_index]
    return True


def xiangqi_moves(board, row, column):
    piece = board[row][column]
    if not piece:
        return []
    red = piece.isupper()
    kind = piece.lower()
    moves = []

    def add(target_row, target_column):
        if not (0 <= target_row < 10 and 0 <= target_column < 9):
            return
        target = board[target_row][target_column]
        if not target or target.isupper() != red:
            moves.append((target_row, target_column))

    if kind == "k":
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = row + dr, column + dc
            if (7 <= nr <= 9 and 3 <= nc <= 5) if red else (0 <= nr <= 2 and 3 <= nc <= 5):
                add(nr, nc)
    elif kind == "a":
        for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            nr, nc = row + dr, column + dc
            if (7 <= nr <= 9 and 3 <= nc <= 5) if red else (0 <= nr <= 2 and 3 <= nc <= 5):
                add(nr, nc)
    elif kind == "e":
        for dr, dc in ((-2, -2), (-2, 2), (2, -2), (2, 2)):
            nr, nc = row + dr, column + dc
            if not (0 <= nr < 10 and 0 <= nc < 9) or board[row + dr // 2][column + dc // 2]:
                continue
            if (red and nr >= 5) or (not red and nr <= 4):
                add(nr, nc)
    elif kind == "h":
        for dr, dc, br, bc in ((-2, -1, -1, 0), (-2, 1, -1, 0), (2, -1, 1, 0), (2, 1, 1, 0),
                                (-1, -2, 0, -1), (1, -2, 0, -1), (-1, 2, 0, 1), (1, 2, 0, 1)):
            nr, nc = row + dr, column + dc
            if 0 <= nr < 10 and 0 <= nc < 9 and not board[row + br][column + bc]:
                add(nr, nc)
    elif kind in ("r", "c"):
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc, jumped = row + dr, column + dc, False
            while 0 <= nr < 10 and 0 <= nc < 9:
                target = board[nr][nc]
                if kind == "r":
                    if not target:
                        moves.append((nr, nc))
                    else:
                        add(nr, nc)
                        break
                elif not jumped:
                    if not target:
                        moves.append((nr, nc))
                    else:
                        jumped = True
                elif target:
                    add(nr, nc)
                    break
                nr += dr
                nc += dc
    elif kind == "p":
        step = -1 if red else 1
        add(row + step, column)
        crossed = row <= 4 if red else row >= 5
        if crossed:
            add(row, column - 1)
            add(row, column + 1)
    return moves


class OtherGamesController:
    def __init__(self):
        self.kind = "gomoku"
        self.mode = "human_vs_ai"
        self.difficulty = "mid"
        self.size = 15
        self.board = []
        self.current_player = 1
        self.game_over = False
        self.draw_game = False
        self.winner = 0
        self.selected = None
        self.ai_wait_until = 0.0

    @property
    def title(self):
        return {"gomoku": "Gomoku", "go": "Go", "xiangqi": "Xiangqi"}[self.kind]

    def start(self, kind, mode="human_vs_ai", difficulty="mid", size=15):
        self.kind, self.mode, self.difficulty, self.size = kind, mode, difficulty, size
        self.current_player = 1
        self.game_over = False
        self.draw_game = False
        self.winner = 0
        self.selected = None
        if kind == "xiangqi":
            self.board = [row.copy() for row in XIANGQI_INIT]
        else:
            self.board = [[0 for _ in range(size)] for _ in range(size)]

    def click(self, position, board_rect):
        if self.game_over:
            return
        if self.kind == "xiangqi":
            self._click_xiangqi(position, board_rect)
            return
        if not board_rect.collidepoint(position):
            return
        margin = 28
        cell = (board_rect.width - 2 * margin) / (self.size - 1)
        column = round((position[0] - board_rect.left - margin) / cell)
        row = round((position[1] - board_rect.top - margin) / cell)
        if not (0 <= row < self.size and 0 <= column < self.size):
            return
        if self.kind == "go":
            if go_play(self.board, row, column, self.current_player):
                self.current_player = 2 if self.current_player == 1 else 1
        elif self.current_player == 1 or self.mode == "human_vs_human":
            if self.board[row][column] == 0:
                self.board[row][column] = self.current_player
                self._finish_if_needed()
                if not self.game_over:
                    self.current_player = 2 if self.current_player == 1 else 1
                    self.ai_wait_until = 0.0

    def _click_xiangqi(self, position, board_rect):
        if not board_rect.collidepoint(position):
            return
        margin_x, margin_y = 32, 28
        cell_x = (board_rect.width - 2 * margin_x) / 8
        cell_y = (board_rect.height - 2 * margin_y) / 9
        column = round((position[0] - board_rect.left - margin_x) / cell_x)
        row = round((position[1] - board_rect.top - margin_y) / cell_y)
        if not (0 <= row < 10 and 0 <= column < 9):
            return
        piece = self.board[row][column]
        if self.selected is None:
            if piece and piece.isupper() == (self.current_player == 1):
                self.selected = (row, column)
            return
        if (row, column) in xiangqi_moves(self.board, *self.selected):
            old_row, old_column = self.selected
            captured = self.board[row][column]
            self.board[row][column] = self.board[old_row][old_column]
            self.board[old_row][old_column] = ""
            self.selected = None
            if captured.lower() == "k":
                self.game_over = True
                self.winner = self.current_player
            else:
                self.current_player = 2 if self.current_player == 1 else 1
        elif piece and piece.isupper() == (self.current_player == 1):
            self.selected = (row, column)
        else:
            self.selected = None

    def _finish_if_needed(self):
        self.winner = gomoku_winner(self.board)
        self.draw_game = not self.winner and not empty_points(self.board)
        self.game_over = bool(self.winner or self.draw_game)

    def tick(self, now):
        if self.kind != "gomoku" or self.mode != "human_vs_ai" or self.current_player != 2:
            return
        if self.game_over or now < self.ai_wait_until:
            return
        move = gomoku_ai(self.board, 2, self.difficulty)
        if move is not None:
            self.board[move[0]][move[1]] = 2
            self._finish_if_needed()
            if not self.game_over:
                self.current_player = 1
        self.ai_wait_until = now + 0.3

    def draw(self, surface, board_rect):
        if self.kind == "xiangqi":
            self._draw_xiangqi(surface, board_rect)
        else:
            self._draw_grid_game(surface, board_rect)

    def _draw_grid_game(self, surface, board_rect):
        pygame.draw.rect(surface, (25, 31, 47), board_rect, border_radius=16)
        margin = 28
        cell = (board_rect.width - 2 * margin) / (self.size - 1)
        for index in range(self.size):
            x = round(board_rect.left + margin + index * cell)
            y = round(board_rect.top + margin + index * cell)
            pygame.draw.line(surface, GRID_BRIGHT, (x, board_rect.top + margin), (x, board_rect.bottom - margin), 1)
            pygame.draw.line(surface, GRID_BRIGHT, (board_rect.left + margin, y), (board_rect.right - margin, y), 1)
        radius = max(7, int(cell * 0.34))
        for row in range(self.size):
            for column in range(self.size):
                stone = self.board[row][column]
                if not stone:
                    continue
                center = (round(board_rect.left + margin + column * cell), round(board_rect.top + margin + row * cell))
                colour = (30, 36, 48) if stone == 2 else RED
                pygame.draw.circle(surface, (4, 8, 15), (center[0] + 2, center[1] + 3), radius)
                pygame.draw.circle(surface, colour, center, radius)
                if stone == 2:
                    pygame.draw.circle(surface, CYAN, center, radius, 2)
        if self.kind == "gomoku":
            text(surface, "Black to move" if self.current_player == 1 else "White to move", (board_rect.left, board_rect.bottom + 12), 18, RED if self.current_player == 1 else CYAN)

    def _draw_xiangqi(self, surface, board_rect):
        pygame.draw.rect(surface, (51, 35, 23), board_rect, border_radius=16)
        margin_x, margin_y = 32, 28
        cell_x = (board_rect.width - 2 * margin_x) / 8
        cell_y = (board_rect.height - 2 * margin_y) / 9
        colour = (226, 184, 116)
        for column in range(9):
            x = round(board_rect.left + margin_x + column * cell_x)
            pygame.draw.line(surface, colour, (x, board_rect.top + margin_y), (x, board_rect.bottom - margin_y), 2)
        for row in range(10):
            y = round(board_rect.top + margin_y + row * cell_y)
            pygame.draw.line(surface, colour, (board_rect.left + margin_x, y), (board_rect.right - margin_x, y), 2)
        for row in range(10):
            for column in range(9):
                piece = self.board[row][column]
                if not piece:
                    continue
                center = (round(board_rect.left + margin_x + column * cell_x), round(board_rect.top + margin_y + row * cell_y))
                fill = (183, 42, 55) if piece.isupper() else (28, 32, 42)
                pygame.draw.circle(surface, (8, 8, 12), (center[0] + 2, center[1] + 3), 24)
                pygame.draw.circle(surface, fill, center, 23)
                pygame.draw.circle(surface, YELLOW if self.selected == (row, column) else colour, center, 23, 2)
                text(surface, XIANGQI_NAMES[piece], center, 24, TEXT, bold=True, anchor="center")

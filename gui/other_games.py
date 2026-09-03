"""Controllers for Gomoku, Go, and Xiangqi from the original GUI."""

import copy
import random

import pygame

from .theme import CYAN, GRID_BRIGHT, MUTED, PANEL_2, RED, TEXT, YELLOW, text
from .engine_adapters import KataGoAdapter, PikafishAdapter, ProtocolError


XIANGQI_INIT = [
    ["r", "h", "e", "a", "k", "a", "e", "h", "r"],
    ["", "", "", "", "", "", "", "", ""],
    ["", "c", "", "", "", "", "", "c", ""],
    ["p", "", "p", "", "p", "", "p", "", "p"],
    ["", "", "", "", "", "", "", "", ""],
    ["", "", "", "", "", "", "", "", ""],
    ["P", "", "P", "", "P", "", "P", "", "P"],
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


def go_position_key(board):
    return tuple(tuple(line) for line in board)


def go_play(board, row, column, colour, history=None):
    size = len(board)
    if not (0 <= row < size and 0 <= column < size):
        return False
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
    position_key = go_position_key(trial)
    if history is not None and position_key in history:
        return False
    for row_index in range(size):
        board[row_index][:] = trial[row_index]
    if history is not None:
        history.add(position_key)
    return True


def go_area_score(board):
    """Return Chinese area scores: stones plus surrounded empty points."""
    size = len(board)
    score = {1: 0.0, 2: 7.5}
    visited = set()
    for row in range(size):
        for column in range(size):
            stone = board[row][column]
            if stone:
                score[stone] += 1
                continue
            if (row, column) in visited:
                continue
            region = {(row, column)}
            border_colours = set()
            stack = [(row, column)]
            visited.add((row, column))
            while stack:
                current = stack.pop()
                for neighbour in go_neighbors(*current, size):
                    value = board[neighbour[0]][neighbour[1]]
                    if value == 0 and neighbour not in visited:
                        visited.add(neighbour)
                        region.add(neighbour)
                        stack.append(neighbour)
                    elif value:
                        border_colours.add(value)
            if len(border_colours) == 1:
                score[next(iter(border_colours))] += len(region)
    return score


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
        self.go_engine = None
        self.xiangqi_engine = None
        self.engine_status = "Built-in rules"
        self.go_history = set()
        self.go_passes = 0
        self.go_result = ""
        self.xiangqi_history = {}
        self.xiangqi_halfmove = 0
        self.xiangqi_result = ""

    @property
    def title(self):
        return {"gomoku": "Gomoku", "go": "Go", "xiangqi": "Xiangqi"}[self.kind]

    def start(self, kind, mode="human_vs_ai", difficulty="mid", size=15):
        self.close_engines()
        self.kind, self.mode, self.difficulty, self.size = kind, mode, difficulty, size
        self.current_player = 1
        self.game_over = False
        self.draw_game = False
        self.winner = 0
        self.selected = None
        self.go_history = set()
        self.go_passes = 0
        self.go_result = ""
        self.xiangqi_history = {}
        self.xiangqi_halfmove = 0
        self.xiangqi_result = ""
        if kind == "xiangqi":
            self.board = [row.copy() for row in XIANGQI_INIT]
        else:
            self.board = [[0 for _ in range(size)] for _ in range(size)]
        if kind == "go":
            self.go_history.add(go_position_key(self.board))
        elif kind == "xiangqi":
            self.xiangqi_history[self.xiangqi_position_key()] = 1
        self.engine_status = "Built-in rules"
        if mode != "human_vs_human":
            try:
                if kind == "go":
                    self.go_engine = KataGoAdapter(size)
                    self.engine_status = "KataGo 9x9"
                elif kind == "xiangqi":
                    self.xiangqi_engine = PikafishAdapter()
                    self.engine_status = "Pikafish NNUE"
            except (FileNotFoundError, OSError, ProtocolError) as error:
                self.engine_status = "AI unavailable: " + str(error)

    def click(self, position, board_rect):
        if self.game_over:
            return
        if self.kind == "xiangqi":
            self._click_xiangqi(position, board_rect)
            return
        if not board_rect.collidepoint(position):
            return
        origin_x, origin_y, cell = self._grid_geometry(board_rect)
        column = round((position[0] - origin_x) / cell)
        row = round((position[1] - origin_y) / cell)
        if not (0 <= row < self.size and 0 <= column < self.size):
            return
        if self.kind == "go":
            if self.mode == "human_vs_ai" and self.current_player != 1:
                return
            if go_play(self.board, row, column, self.current_player, self.go_history):
                if self.go_engine:
                    try:
                        self.go_engine.play(self.current_player, row, column)
                    except ProtocolError as error:
                        self.engine_status = "AI error: " + str(error)
                self.go_passes = 0
                self.current_player = 2 if self.current_player == 1 else 1
                self.ai_wait_until = 0.0
        elif self.current_player == 1 or self.mode == "human_vs_human":
            if self.board[row][column] == 0:
                self.board[row][column] = self.current_player
                self._finish_if_needed()
                if not self.game_over:
                    self.current_player = 2 if self.current_player == 1 else 1
                    self.ai_wait_until = 0.0

    def _click_xiangqi(self, position, board_rect):
        if self.mode == "human_vs_ai" and self.current_player != 1:
            return
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
            self.selected = None
            self._apply_xiangqi_move((old_row, old_column, row, column))
        elif piece and piece.isupper() == (self.current_player == 1):
            self.selected = (row, column)
        else:
            self.selected = None

    def _finish_if_needed(self):
        self.winner = gomoku_winner(self.board)
        self.draw_game = not self.winner and not empty_points(self.board)
        self.game_over = bool(self.winner or self.draw_game)

    def tick(self, now):
        if self.mode == "human_vs_human" or self.game_over:
            return
        if self.mode == "human_vs_ai" and self.current_player != 2:
            return
        if now < self.ai_wait_until:
            return
        if self.kind in ("go", "xiangqi") and not (self.go_engine or self.xiangqi_engine):
            self.engine_status = "AI runtime is not installed"
            self.game_over = True
            self.draw_game = True
            return
        move = None
        if self.kind == "gomoku":
            move = gomoku_ai(self.board, self.current_player, self.difficulty)
            if move is not None:
                self.board[move[0]][move[1]] = self.current_player
        elif self.kind == "go" and self.go_engine:
            try:
                move = self.go_engine.genmove(self.current_player)
                if move is None:
                    raise ProtocolError("KataGo returned no move")
                if move == "pass":
                    self._register_go_pass(sync_engine=False)
                elif move == "resign":
                    move = self._fallback_go_move()
                    if move is None:
                        self._register_go_pass(sync_engine=True)
                    else:
                        self.go_engine.play(self.current_player, move[0], move[1])
                        go_play(self.board, move[0], move[1], self.current_player, self.go_history)
                        self.go_passes = 0
                        self.current_player = 2 if self.current_player == 1 else 1
                elif not go_play(self.board, move[0], move[1], self.current_player, self.go_history):
                    self.engine_status = "AI returned an illegal move"
                    self.game_over = True
                else:
                    self.go_passes = 0
                    self.current_player = 2 if self.current_player == 1 else 1
                    move = (move[0], move[1])
            except (ProtocolError, ValueError) as error:
                self.engine_status = "AI error: " + str(error)
                self.game_over = True
        elif self.kind == "xiangqi" and self.xiangqi_engine:
            try:
                move = self.xiangqi_engine.best_move(self.board, self.current_player)
                if move is not None:
                    self._apply_xiangqi_move(move)
                else:
                    self.game_over = True
            except (ProtocolError, ValueError) as error:
                self.engine_status = "AI error: " + str(error)
                self.game_over = True
        if move is not None and not self.game_over and self.kind == "gomoku":
            self._finish_if_needed()
        if move is not None and not self.game_over and self.kind == "gomoku":
            self.current_player = 2 if self.current_player == 1 else 1
        self.ai_wait_until = now + 0.3

    def _register_go_pass(self, sync_engine=True):
        if sync_engine and self.go_engine:
            try:
                self.go_engine.play_pass(self.current_player)
            except ProtocolError as error:
                self.engine_status = "AI error: " + str(error)
                self.game_over = True
                return
        self.go_passes += 1
        if self.go_passes >= 2:
            scores = go_area_score(self.board)
            self.go_result = f"Black {scores[1]:.1f} · White {scores[2]:.1f}"
            self.game_over = True
            self.draw_game = False
        else:
            self.current_player = 2 if self.current_player == 1 else 1

    def _fallback_go_move(self):
        """Choose a legal point if an engine build ignores allowResignation."""
        for row in range(self.size):
            for column in range(self.size):
                trial = [line.copy() for line in self.board]
                if go_play(trial, row, column, self.current_player, set(self.go_history)):
                    return row, column
        return None

    def pass_turn(self):
        if self.kind != "go" or self.game_over or self.mode == "ai_vs_ai":
            return
        if self.mode == "human_vs_ai" and self.current_player != 1:
            return
        self._register_go_pass()

    def _apply_xiangqi_move(self, move):
        old_row, old_column, row, column = move
        if (row, column) not in xiangqi_moves(self.board, old_row, old_column):
            raise ProtocolError("Pikafish returned an illegal move")
        captured = self.board[row][column]
        self.board[row][column] = self.board[old_row][old_column]
        self.board[old_row][old_column] = ""
        if captured and captured.lower() == "k":
            self.game_over = True
            self.winner = self.current_player
        else:
            self.current_player = 2 if self.current_player == 1 else 1
        self.xiangqi_halfmove = 0 if captured else self.xiangqi_halfmove + 1
        position_key = self.xiangqi_position_key()
        self.xiangqi_history[position_key] = self.xiangqi_history.get(position_key, 0) + 1
        if not self.game_over and self.xiangqi_history[position_key] >= 3:
            self.xiangqi_result = "Threefold repetition"
            self.game_over = True
            self.draw_game = True
        elif not self.game_over and self.xiangqi_halfmove >= 120:
            self.xiangqi_result = "120 moves without capture"
            self.game_over = True
            self.draw_game = True

    def xiangqi_position_key(self):
        return tuple(tuple(row) for row in self.board), self.current_player

    def close_engines(self):
        for engine in (self.go_engine, self.xiangqi_engine):
            if engine:
                engine.close()
        self.go_engine = None
        self.xiangqi_engine = None

    def __del__(self):
        self.close_engines()

    def draw(self, surface, board_rect):
        if self.kind == "xiangqi":
            self._draw_xiangqi(surface, board_rect)
        else:
            self._draw_grid_game(surface, board_rect)

    def _draw_grid_game(self, surface, board_rect):
        pygame.draw.rect(surface, (25, 31, 47), board_rect, border_radius=16)
        origin_x, origin_y, cell = self._grid_geometry(board_rect)
        for index in range(self.size):
            x = round(origin_x + index * cell)
            y = round(origin_y + index * cell)
            pygame.draw.line(surface, GRID_BRIGHT, (x, round(origin_y)),
                             (x, round(origin_y + (self.size - 1) * cell)), 1)
            pygame.draw.line(surface, GRID_BRIGHT, (round(origin_x), y),
                             (round(origin_x + (self.size - 1) * cell), y), 1)
        radius = max(7, int(cell * 0.34))
        for row in range(self.size):
            for column in range(self.size):
                stone = self.board[row][column]
                if not stone:
                    continue
                center = (round(origin_x + column * cell), round(origin_y + row * cell))
                colour = (30, 36, 48) if stone == 2 else RED
                pygame.draw.circle(surface, (4, 8, 15), (center[0] + 2, center[1] + 3), radius)
                pygame.draw.circle(surface, colour, center, radius)
                if stone == 2:
                    pygame.draw.circle(surface, CYAN, center, radius, 2)
        if self.kind == "gomoku":
            text(surface, "Black to move" if self.current_player == 1 else "White to move", (board_rect.left, board_rect.bottom + 12), 18, RED if self.current_player == 1 else CYAN)

    def _grid_geometry(self, board_rect):
        """Return a square, centered grid that always stays inside board_rect."""
        padding = 28
        cell = min(
            (board_rect.width - 2 * padding) / (self.size - 1),
            (board_rect.height - 2 * padding) / (self.size - 1),
        )
        grid_width = cell * (self.size - 1)
        origin_x = board_rect.left + (board_rect.width - grid_width) / 2
        origin_y = board_rect.top + (board_rect.height - grid_width) / 2
        return origin_x, origin_y, cell

    def _draw_xiangqi(self, surface, board_rect):
        pygame.draw.rect(surface, (51, 35, 23), board_rect, border_radius=16)
        margin_x, margin_y = 32, 28
        cell_x = (board_rect.width - 2 * margin_x) / 8
        cell_y = (board_rect.height - 2 * margin_y) / 9
        colour = (226, 184, 116)
        left = board_rect.left + margin_x
        right = board_rect.right - margin_x
        top = board_rect.top + margin_y
        bottom = board_rect.bottom - margin_y
        river_y = top + 4.5 * cell_y
        river_band = pygame.Rect(round(left + 2), round(top + 4 * cell_y + 3), round(right - left - 4), round(cell_y - 6))
        pygame.draw.rect(surface, (74, 50, 30), river_band)
        for column in range(9):
            x = round(left + column * cell_x)
            pygame.draw.line(surface, colour, (x, round(top)), (x, round(top + 4 * cell_y)), 2)
            pygame.draw.line(surface, colour, (x, round(top + 5 * cell_y)), (x, round(bottom)), 2)
        for row in range(10):
            y = round(top + row * cell_y)
            pygame.draw.line(surface, colour, (round(left), y), (round(right), y), 2)

        def point(row, column):
            return round(left + column * cell_x), round(top + row * cell_y)

        # The two diagonal palace lines are part of the board, not decorations.
        pygame.draw.line(surface, colour, point(0, 3), point(2, 5), 2)
        pygame.draw.line(surface, colour, point(0, 5), point(2, 3), 2)
        pygame.draw.line(surface, colour, point(7, 3), point(9, 5), 2)
        pygame.draw.line(surface, colour, point(7, 5), point(9, 3), 2)

        # Traditional flower marks identify cannon and soldier intersections.
        for row, columns in ((2, (1, 7)), (3, (0, 2, 4, 6, 8)), (6, (0, 2, 4, 6, 8)), (7, (1, 7))):
            for column in columns:
                x, y = point(row, column)
                size, gap = 7, 4
                for x_direction in (-1, 1):
                    for y_direction in (-1, 1):
                        if column in (0, 8) and x_direction != (1 if column == 0 else -1):
                            continue
                        pygame.draw.line(surface, colour, (x + x_direction * gap, y + y_direction * size), (x + x_direction * size, y + y_direction * size), 1)
                        pygame.draw.line(surface, colour, (x + x_direction * size, y + y_direction * gap), (x + x_direction * size, y + y_direction * size), 1)

        # Clear only the label plates, so no grid stroke runs through 河界 text.
        label_colour = (74, 50, 30)
        for label, x in (("楚河", left + 2.4 * cell_x), ("汉界", left + 6.6 * cell_x)):
            plate = pygame.Rect(round(x - 52), round(river_y - 22), 104, 44)
            pygame.draw.rect(surface, label_colour, plate)
            text(surface, label, (round(x), round(river_y)), 25, (242, 207, 143), bold=True, anchor="center")
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

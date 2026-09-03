"""棋盘尺寸可配置的井字棋/连珠式棋盘规则。"""

from math import isqrt


EMPTY = " "
empty = EMPTY


def board_size(board):
    size = isqrt(len(board))
    if size * size != len(board):
        raise ValueError("棋盘必须是正方形")
    return size


def win_length_for(size):
    return min(size, 5)


def new_board(size):
    if size < 3:
        raise ValueError("棋盘尺寸至少为3")
    return [EMPTY] * (size * size)


def available(board):
    return [index for index, cell in enumerate(board) if cell == EMPTY]


def winner(board, size=None, win_length=None):
    if size is None:
        size = board_size(board)
    if win_length is None:
        win_length = win_length_for(size)

    directions = ((1, 0), (0, 1), (1, 1), (1, -1))
    for row in range(size):
        for column in range(size):
            mark = board[row * size + column]
            if mark == EMPTY:
                continue
            for row_step, column_step in directions:
                end_row = row + (win_length - 1) * row_step
                end_column = column + (win_length - 1) * column_step
                if not (0 <= end_row < size and 0 <= end_column < size):
                    continue
                line = []
                for offset in range(win_length):
                    line.append(
                        board[
                            (row + offset * row_step) * size
                            + column
                            + offset * column_step
                        ]
                    )
                if all(cell == mark for cell in line):
                    return mark
    return None


def winner_from_move(board, move, size=None, win_length=None):
    """只检查最后一步经过的四条线，适合搜索树中的高频判断。"""
    if size is None:
        size = board_size(board)
    if win_length is None:
        win_length = win_length_for(size)
    if move is None or not (0 <= move < len(board)):
        return None
    mark = board[move]
    if mark == EMPTY:
        return None
    row, column = divmod(move, size)
    for row_step, column_step in ((1, 0), (0, 1), (1, 1), (1, -1)):
        count = 1
        for direction in (-1, 1):
            current_row = row + direction * row_step
            current_column = column + direction * column_step
            while (
                0 <= current_row < size
                and 0 <= current_column < size
                and board[current_row * size + current_column] == mark
            ):
                count += 1
                current_row += direction * row_step
                current_column += direction * column_step
        if count >= win_length:
            return mark
    return None


def terminal(board, size=None, win_length=None):
    result = winner(board, size=size, win_length=win_length)
    if result is not None:
        return True, result
    if not available(board):
        return True, "DRAW"
    return False, None

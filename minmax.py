import json
import multiprocessing as mp
import os

from environment import available, terminal
from main import (
    heuristic_move,
    logger_agent,
    make_message,
    random_move,
    referee_agent,
    route_message
)

# Minimax算法
def minimax(board, current_mark, maximizing_mark):
    """递归计算当前棋盘对于maximizing_mark的分数。"""
    finished, result = terminal(board)

    # Base Case：游戏结束，不再继续递归。
    if finished:
        if result == maximizing_mark:
            return 1
        elif result == "DRAW":
            return 0
        else:
            return -1

    # 确定下一层应该由谁落子。
    if current_mark == "X":
        next_mark = "O"
    else:
        next_mark = "X"

    scores = []

    # 尝试当前玩家的每一个合法动作。
    for move in available(board):
        trial = board.copy()
        trial[move] = current_mark

        score = minimax(
            trial,
            next_mark,
            maximizing_mark
        )
        scores.append(score)

    # O是MAX层，希望分数尽量大；X是MIN层，希望O的分数尽量小。
    if current_mark == maximizing_mark:
        return max(scores)
    else:
        return min(scores)

def minimax_move(board, mark):
    """评价所有合法动作，返回Minimax分数最高的动作。"""
    opponent = "O" if mark == "X" else "X"

    best_score = -2
    best_move = None

    for move in available(board):
        trial = board.copy()
        trial[move] = mark

        # 当前mark已经完成假设落子，下一层轮到opponent。
        score = minimax(
            trial,
            opponent,
            mark
        )

        if score > best_score:
            best_score = score
            best_move = move

    return best_move

# 升级后的Player Agent
def player_agent(
    name,
    mark,
    strategy,
    inbox,
    bus
):
    print(name, "PID =", os.getpid())

    while True:
        message = inbox.get()
        kind = message["performative"]

        if kind == "REQUEST_MOVE":
            board = message["content"]["board"]

            if strategy == "heuristic":
                move = heuristic_move(board, mark)

            elif strategy == "minimax":
                move = minimax_move(board, mark)

            elif strategy == "random":
                move = random_move(board)

            else:
                raise ValueError("未知的策略：" + strategy)

            bus.put(
                make_message(
                    name,
                    "referee",
                    "PROPOSE_MOVE",
                    {
                        "move": move,
                        "mark": mark
                    }
                )
            )

        elif kind == "REJECT_MOVE":
            print(name, "的动作被拒绝")

        elif kind == "GAME_OVER":
            break

        elif kind == "SHUTDOWN":
            break

# 测试
def run_minimax_tests():
    """测试立即获胜、阻止X和避免必输。"""
    # Test 1：O可以立即获胜，必须选择2。
    win_board = [
        "O", "O", " ",
        "X", "X", " ",
        " ", " ", " "
    ]
    assert minimax_move(win_board, "O") == 2

    # Test 2：X下一步将在2获胜，O必须选择2阻止。
    block_board = [
        "X", "X", " ",
        "O", " ", " ",
        " ", "O", " "
    ]
    assert minimax_move(block_board, "O") == 2

    # Test 3：X先占角落8。O下其他位置最终会输，选择中心4可平局。
    avoid_loss_board = [
        " ", " ", " ",
        " ", " ", " ",
        " ", " ", "X"
    ]
    assert minimax_move(avoid_loss_board, "O") == 4

    print("Minimax三个策略测试通过。")

# 完整多智能体游戏
def run_one_game(game_number):
    """启动四个Agent进程，运行一局并返回结果。"""
    bus = mp.Queue()

    inboxes = {
        "referee": mp.Queue(),
        "player_x": mp.Queue(),
        "player_o": mp.Queue(),
        "logger": mp.Queue()
    }

    player_x = mp.Process(
        target=player_agent,
        args=(
            "player_x",
            "X",
            "heuristic",
            inboxes["player_x"],
            bus
        )
    )
    # 第三天的核心修改：Player O使用minimax策略。
    player_o = mp.Process(
        target=player_agent,
        args=(
            "player_o",
            "O",
            "minimax",
            inboxes["player_o"],
            bus
        )
    )

    referee = mp.Process(
        target=referee_agent,
        args=(inboxes["referee"], bus)
    )

    log_filename = f"messages_game_{game_number}.jsonl"
    logger = mp.Process(
        target=logger_agent,
        args=(inboxes["logger"], log_filename)
    )

    processes = [player_x, player_o, referee, logger]

    for process in processes:
        process.start()

    # Supervisor发送START，启动本局游戏。
    bus.put(
        make_message(
            "supervisor",
            "referee",
            "START"
        )
    )

    game_is_running = True
    final_result = None

    while game_is_running:
        message = bus.get()
        route_message(message, inboxes)

        if (
            message["receiver"] == "supervisor"
            and message["performative"] == "GAME_OVER"
        ):
            final_result = message["content"]["result"]
            game_is_running = False

    # 结束Logger
    route_message(
        make_message(
            "supervisor",
            "logger",
            "SHUTDOWN"
        ),
        inboxes
    )

    for process in processes:
        process.join()

    # Test 4、5、6：检查O发送动作、MAS结束、Logger正常记录。
    with open(log_filename, "r", encoding="utf-8") as file:
        log_messages = [
            json.loads(line)
            for line in file
        ]

    o_proposed_move = any(
        message["sender"] == "player_o"
        and message["performative"] == "PROPOSE_MOVE"
        for message in log_messages
    )
    assert o_proposed_move

    game_over_recorded = any(
        message["performative"] == "GAME_OVER"
        for message in log_messages
    )
    assert game_over_recorded

    return final_result

def print_results(results):
    """按任务书格式打印五局结果。"""
    print("\nGame   X Win   O Win   Draw")

    for game_number, result in enumerate(results, start=1):
        x_win = "√" if result == "X" else ""
        o_win = "√" if result == "O" else ""
        draw = "√" if result == "DRAW" else ""

        print(
            f"{game_number:<7}"
            f"{x_win:<8}"
            f"{o_win:<8}"
            f"{draw}"
        )

    print("\n统计：")
    print("X获胜：", results.count("X"))
    print("O获胜：", results.count("O"))
    print("平局：", results.count("DRAW"))

def main():
    run_minimax_tests()
    results = []
    for game_number in range(1, 6):
        print("\n========== 第", game_number, "局 ==========")
        result = run_one_game(game_number)
        results.append(result)

    print_results(results)
    print("\n五局完整MAS测试通过，Logger日志已生成。")

if __name__ == "__main__":
    mp.freeze_support()
    main()

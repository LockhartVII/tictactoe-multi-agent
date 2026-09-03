import multiprocessing as mp
import random
import time
import json
import queue
import os

from environment import (
    empty,
    available,
    winner,
    terminal,
    render
)

def make_message(
        sender,
        receiver,
        performative,
        content=None
):
    if content is None:
        content = {}
    message = {
        "sender": sender,
        "receiver": receiver,
        "performative": performative,
        "content": content,
        "timestamp": time.time()
    }
    return message

def route_message(message, inboxes):
    receiver = message["receiver"]
    if receiver=="logger":
        inboxes["logger"].put(message)
        return

    inboxes["logger"].put(message)

    if receiver in inboxes:
        inboxes[receiver].put(message)


def heuristic_move(board, mark):
    moves = available(board)
    # 1.检查自己是否可以立即获胜
    for move in moves:
        test_board = board.copy()
        test_board[move] = mark
        if winner(test_board) == mark:
            return move

    # 2.检查是否需要阻止对手
    if mark == "X":
        opponent = "O"
    else:
        opponent = "X"
    for move in moves:
        test_board = board.copy()
        test_board[move] = opponent
        if winner(test_board) == opponent:
            return move

    # 3.中心
    if 4 in moves:
        return 4

    # 4.角落
    corners = []
    for move in [0, 2, 6, 8]:
        if move in moves:
            corners.append(move)
    if len(corners) > 0:
        return random.choice(corners)

    # 5.其他位置
    return random.choice(moves)

def random_move(board):
    return random.choice(available(board))

def legal_move(board,move):
    return (
        isinstance(move,int)
        and 0<=move<9
        and board[move]==empty
    )

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
            else:
                move = random_move(board)

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
            # Referee随后还会重新发送REQUEST_MOVE。
            print(name, "的动作被拒绝：", message["content"]["reason"])

        elif kind == "GAME_OVER":
            break

        elif kind == "SHUTDOWN":
            break

def referee_agent(inbox, bus):
    print("referee PID =", os.getpid())

    # 只有Referee保存并修改官方棋盘。
    board = [empty] * 9
    current_player = "player_x"
    current_mark = "X"

    while True:
        message = inbox.get()
        kind = message["performative"]

        if kind == "START":
            bus.put(
                make_message(
                    "referee",
                    current_player,
                    "REQUEST_MOVE",
                    {"board": board.copy()}
                )
            )

        elif kind == "PROPOSE_MOVE":
            sender = message["sender"]
            move = message["content"]["move"]
            mark = message["content"]["mark"]

            correct_turn = (
                sender == current_player
                and mark == current_mark
            )

            # 先检查范围，再访问board[move]，避免board[20]报错。
            move_is_legal = legal_move(board, move)

            if not correct_turn or not move_is_legal:
                bus.put(
                    make_message(
                        "referee",
                        sender,
                        "REJECT_MOVE",
                        {"reason": "illegal move"}
                    )
                )

                # 当前玩家重新选择。
                bus.put(
                    make_message(
                        "referee",
                        current_player,
                        "REQUEST_MOVE",
                        {"board": board.copy()}
                    )
                )
                continue

            # 合法动作：只有Referee可以修改官方棋盘。
            board[move] = mark
            print("\n", sender, "选择位置", move)
            render(board)

            finished, result = terminal(board)

            if finished:
                print("\n游戏结束，结果：", result)

                # 通知两个Player结束。
                for player in ["player_x", "player_o"]:
                    bus.put(
                        make_message(
                            "referee",
                            player,
                            "GAME_OVER",
                            {
                                "result": result,
                                "board": board.copy()
                            }
                        )
                    )

                # 通知Supervisor停止路由循环。
                bus.put(
                    make_message(
                        "referee",
                        "supervisor",
                        "GAME_OVER",
                        {
                            "result": result,
                            "board": board.copy()
                        }
                    )
                )
                break

            # 游戏继续：切换玩家。
            if current_player == "player_x":
                current_player = "player_o"
                current_mark = "O"
            else:
                current_player = "player_x"
                current_mark = "X"

            bus.put(
                make_message(
                    "referee",
                    current_player,
                    "REQUEST_MOVE",
                    {"board": board.copy()}
                )
            )

        elif kind == "SHUTDOWN":
            break

def logger_agent(inbox, filename):
    print("logger PID =", os.getpid())

    with open(filename, "w", encoding="utf-8") as file:
        while True:
            message = inbox.get()

            # 每条消息写成JSONL文件中的一行。
            file.write(
                json.dumps(message, ensure_ascii=False)
                + "\n"
            )
            file.flush()

            if message["performative"] == "SHUTDOWN":
                break

def run_basic_tests():
    """完成任务书中不需要启动完整游戏的基础测试。"""
    message = make_message(
        "player_x",
        "referee",
        "PROPOSE_MOVE",
        {
            "move": 4,
            "mark": "X"
        }
    )

    required_keys = [
        "sender",
        "receiver",
        "performative",
        "content",
        "timestamp"
    ]

    for key in required_keys:
        assert key in message

    win_board = [
        "X", "X", empty,
        "O", "O", empty,
        empty, empty, empty
    ]
    assert heuristic_move(win_board, "X") == 2

    block_board = [
        "O", "O", empty,
        "X", empty, empty,
        "X", empty, empty
    ]
    assert heuristic_move(block_board, "X") == 2

    assert not legal_move([empty] * 9, 20)

    occupied_board = [empty] * 9
    occupied_board[4] = "X"
    assert not legal_move(occupied_board, 4)

    print("基础测试通过。")

def main():
    run_basic_tests()
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

    player_o = mp.Process(
        target=player_agent,
        args=(
            "player_o",
            "O",
            "random",
            inboxes["player_o"],
            bus
        )
    )

    referee = mp.Process(
        target=referee_agent,
        args=(inboxes["referee"], bus)
    )

    logger = mp.Process(
        target=logger_agent,
        args=(inboxes["logger"], "messages.jsonl")
    )

    processes = [player_x, player_o, referee, logger]

    for process in processes:
        process.start()

    # Supervisor启动游戏。
    bus.put(
        make_message(
            "supervisor",
            "referee",
            "START"
        )
    )

    game_is_running = True
    final_result = None

    # Supervisor不断从公共bus取消息并转发。
    while game_is_running:
        message = bus.get()
        route_message(message, inboxes)

        if (
                message["receiver"] == "supervisor"
                and message["performative"] == "GAME_OVER"
        ):
            final_result = message["content"]["result"]
            game_is_running = False

    # Logger收到SHUTDOWN后保存最后一条日志并退出。
    shutdown_message = make_message(
        "supervisor",
        "logger",
        "SHUTDOWN"
    )
    route_message(shutdown_message, inboxes)

    for process in processes:
        process.join()

    print("所有进程已经结束。")
    print("最终结果：", final_result)
    print("日志文件：messages.jsonl")


if __name__ == "__main__":
    mp.freeze_support()
    main()

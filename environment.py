empty=" "

def nwe_board():
    return [empty]*9

def available(board):
    moves=[]
    for i in range(9):
        if board[i]==empty:
            moves.append(i)
    return moves

def winner(board):
    winning_lines = (
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),
        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),
        (0, 4, 8),
        (2, 4, 6),
    )
    for a,b,c in winning_lines:
        if(
            board[a]!=empty
            and board[a]==board[b]
            and board[b]==board[c]
        ):
            return board[a]
    return None

def terminal(board):
    result=winner(board)
    if result is not None:
        return True,result
    if len(available(board))==0:
        return True,"DRAW"
    return False,None

def render(board):
    display=[]
    for i in range(9):
        if board[i]==empty:
            display.append(str(i))
        else:
            display.append(board[i])

    print(f" {display[0]} | {display[1]} | {display[2]}")
    print("---+---+---")
    print(f" {display[3]} | {display[4]} | {display[5]}")
    print("---+---+---")
    print(f" {display[6]} | {display[7]} | {display[8]}")

import pygame
import random
import copy

pygame.init()
WIDTH, HEIGHT = 640, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Realistic Board Simulator")
clock = pygame.time.Clock()

# ==========字体【Linux兼容文泉驿】==========
def create_font(size):
    try:
        return pygame.font.SysFont("WenQuanYi Micro Hei", size)
    except Exception:
        return pygame.font.Font(None, size)

font_big = create_font(42)
font_mid = create_font(30)
font_small = create_font(24)
font_qizi = create_font(36)

# 状态常量
STATE_MENU = "menu"
STATE_MODE_SELECT = "mode_select"
STATE_DIFFICULTY_SELECT = "diff_select"
STATE_SIZE_SELECT = "size_select"
STATE_MORE_GAME = "more_game"
STATE_GAME = "game"

game_type = None
play_mode = None
ai_difficulty = "low"
board_size = 0
cell = 0
board = []
current_player = 1
game_over = False
is_draw = False
xiangqi_winner = None
score_human = 0
score_ai = 0
selected_xq = None
state = STATE_MENU

# =========按钮定义==========
btn_3 = pygame.Rect(100, 120, 440, 70)
btn_4 = pygame.Rect(100, 220, 440, 70)
btn_5 = pygame.Rect(100, 320, 440, 70)
btn_more = pygame.Rect(100, 420, 440, 70)

btn_go = pygame.Rect(100,180,440,70)
btn_xiangqi = pygame.Rect(100,280,440,70)
btn_back_more = pygame.Rect(100,420,440,60)

btn_two = pygame.Rect(100, 200, 440, 70)
btn_ai = pygame.Rect(100, 310, 440, 70)

btn_diff_low = pygame.Rect(100,160,440,70)
btn_diff_mid = pygame.Rect(100,260,440,70)
btn_diff_high = pygame.Rect(100,360,440,70)
btn_diff_back = pygame.Rect(100,480,440,60)

btn_size9 = pygame.Rect(100,180,440,60)
btn_size13 = pygame.Rect(100,260,440,60)
btn_size15 = pygame.Rect(100,340,440,60)

btn_again = pygame.Rect(90, 620, 210, 60)
btn_back_game = pygame.Rect(340, 620, 210, 60)

# ---------------------- 象棋数据 ----------------------
XIANGQI_INIT = [
    ["r","h","e","a","k","a","e","h","r"],
    ["","","","","","","","",""],
    ["","c","","","","","","c",""],
    ["p","","p","","","","p","","p"],
    ["","","","","","","","",""],
    ["","","","","","","","",""],
    ["P","","P","","","","P","","P"],
    ["","C","","","","","","C",""],
    ["","","","","","","","",""],
    ["R","H","E","A","K","A","E","H","R"],
]

XIANGQI_PIECE_NAME = {
    "r":"车","h":"马","e":"象","a":"士","k":"将",
    "c":"炮","p":"卒",
    "R":"車","H":"馬","E":"相","A":"仕","K":"帥",
    "C":"砲","P":"兵"
}

def xiangqi_in_board(r,c):
    return 0<=r<10 and 0<=c<9

def xiangqi_is_red(p):
    return p.isupper()

def xiangqi_get_moves(brd, r, c):
    piece = brd[r][c]
    if not piece:
        return []
    moves = []
    red = xiangqi_is_red(piece)
    typ = piece.lower()
    if typ == "k":
        dirs = [(-1,0),(1,0),(0,-1),(0,1)]
        for dr,dc in dirs:
            nr, nc = r+dr, c+dc
            if not xiangqi_in_board(nr,nc): continue
            if red:
                if not (7<=nr<=9 and 3<=nc<=5): continue
            else:
                if not (0<=nr<=2 and 3<=nc<=5): continue
            target = brd[nr][nc]
            if not target or xiangqi_is_red(target)!=red:
                moves.append((nr,nc))
    elif typ == "a":
        for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            nr, nc = r+dr, c+dc
            if not xiangqi_in_board(nr,nc): continue
            if red:
                if not (7<=nr<=9 and 3<=nc<=5): continue
            else:
                if not (0<=nr<=2 and 3<=nc<=5): continue
            target = brd[nr][nc]
            if not target or xiangqi_is_red(target)!=red:
                moves.append((nr,nc))
    elif typ == "e":
        for dr,dc in [(-2,-2),(-2,2),(2,-2),(2,2)]:
            nr, nc = r+dr, c+dc
            mr, mc = r+dr//2, c+dc//2
            if not xiangqi_in_board(nr,nc): continue
            if brd[mr][mc]!="": continue
            if red:
                if nr<5: continue
            else:
                if nr>4: continue
            target = brd[nr][nc]
            if not target or xiangqi_is_red(target)!=red:
                moves.append((nr,nc))
    elif typ == "h":
        jump = [ (-2,-1,-1,0),(-2,1,-1,0),
                 (2,-1,1,0),(2,1,1,0),
                 (-1,-2,0,-1),(1,-2,0,-1),
                 (-1,2,0,1),(1,2,0,1)]
        for dr,dc,jr,jc in jump:
            nr, nc = r+dr, c+dc
            jr_, jc_ = r+jr, c+jc
            if not xiangqi_in_board(nr,nc): continue
            if brd[jr_][jc_]!="": continue
            target = brd[nr][nc]
            if not target or xiangqi_is_red(target)!=red:
                moves.append((nr,nc))
    elif typ == "r":
        for dr,dc in [(1,0),(-1,0),(0,1),(0,-1)]:
            nr, nc = r+dr, c+dc
            while xiangqi_in_board(nr,nc):
                target = brd[nr][nc]
                if target=="":
                    moves.append((nr,nc))
                else:
                    if xiangqi_is_red(target)!=red:
                        moves.append((nr,nc))
                    break
                nr += dr
                nc += dc
    elif typ == "c":
        for dr,dc in [(1,0),(-1,0),(0,1),(0,-1)]:
            nr, nc = r+dr, c+dc
            hop = False
            while xiangqi_in_board(nr,nc):
                target = brd[nr][nc]
                if not hop:
                    if target=="":
                        moves.append((nr,nc))
                    else:
                        hop=True
                else:
                    if target!="":
                        if xiangqi_is_red(target)!=red:
                            moves.append((nr,nc))
                        break
                nr += dr
                nc += dc
    elif typ == "p":
        if red:
            step = -1
        else:
            step = 1
        nr = r+step
        if xiangqi_in_board(nr,c):
            t = brd[nr][c]
            if t=="" or xiangqi_is_red(t)!=red:
                moves.append((nr,c))
        if (red and r<=4) or (not red and r>=5):
            for dc in (-1,1):
                nc = c+dc
                if xiangqi_in_board(r,nc):
                    t = brd[r][nc]
                    if t=="" or xiangqi_is_red(t)!=red:
                        moves.append((r,nc))
    return moves

def xiangqi_check_kings_face(brd):
    krk = None
    krR = None
    for rr in range(10):
        for cc in range(9):
            p = brd[rr][cc]
            if p=="k":
                krk=(rr,cc)
            if p=="K":
                krR=(rr,cc)
    if krk is None or krR is None:
        return False
    if krk[1] != krR[1]:
        return False
    col = krk[1]
    rmin = min(krk[0], krR[0])
    rmax = max(krk[0], krR[0])
    for rr in range(rmin+1, rmax):
        if brd[rr][col]!="":
            return False
    return True

# ---------------------- 围棋逻辑 ----------------------
def go_get_neighbors(r,c,bs):
    return [(nr,nc) for nr,nc in [(r-1,c),(r+1,c),(r,c-1),(r,c+1)] if 0<=nr<bs and 0<=nc<bs]

def go_get_group(b, r,c,bs):
    color = b[r][c]
    visited=set()
    stack=[(r,c)]
    visited.add((r,c))
    while stack:
        x,y = stack.pop()
        for nx,ny in go_get_neighbors(x,y,bs):
            if b[nx][ny]==color and (nx,ny) not in visited:
                visited.add((nx,ny))
                stack.append((nx,ny))
    return visited

def go_liberties(b, group, bs):
    lib=set()
    for (r,c) in group:
        for nx,ny in go_get_neighbors(r,c,bs):
            if b[nx][ny]==0:
                lib.add((nx,ny))
    return len(lib)

def go_remove_group(b, group):
    for r,c in group:
        b[r][c]=0

def go_try_play(b, r,c, color, bs):
    if b[r][c]!=0:
        return False
    new_board = [row.copy() for row in b]
    new_board[r][c]=color
    opp = 2 if color==1 else 1
    remove = []
    for nx,ny in go_get_neighbors(r,c,bs):
        if new_board[nx][ny]==opp:
            g = go_get_group(new_board,nx,ny,bs)
            if go_liberties(new_board,g,bs)==0:
                remove.append(g)
    for g in remove:
        go_remove_group(new_board,g)
    my_group = go_get_group(new_board,r,c,bs)
    if go_liberties(new_board, my_group, bs)==0:
        return False
    for i in range(bs):
        for j in range(bs):
            b[i][j]=new_board[i][j]
    return True

# ---------------------- 五子棋 ----------------------
def gomoku_check_win(b, win_len=5):
    sz = len(b)
    for r in range(sz):
        for c in range(sz):
            v = b[r][c]
            if v == 0:
                continue
            if c + win_len <= sz and all(b[r][c+i]==v for i in range(win_len)):
                return v
            if r + win_len <= sz and all(b[r+i][c]==v for i in range(win_len)):
                return v
            if r+win_len <= sz and c+win_len <= sz and all(b[r+i][c+i]==v for i in range(win_len)):
                return v
            if r+win_len <= sz and c-win_len+1 >=0 and all(b[r+i][c-i]==v for i in range(win_len)):
                return v
    return 0

def is_board_full(b):
    for row in b:
        if 0 in row:
            return False
    return True

def get_empty_positions(board_in):
    res = []
    sz = len(board_in)
    for rr in range(sz):
        for cc in range(sz):
            if board_in[rr][cc]==0:
                res.append((rr,cc))
    return res

# ========= AI五子棋 =========
def ai_low(board_in):
    empty = get_empty_positions(board_in)
    return random.choice(empty) if empty else None

def ai_mid(board_in, ai_player):
    sz = len(board_in)
    opp = 1 if ai_player==2 else 2
    empty = get_empty_positions(board_in)
    for (r,c) in empty:
        tmp = copy.deepcopy(board_in)
        tmp[r][c]=ai_player
        if gomoku_check_win(tmp,5) == ai_player:
            return (r,c)
    for (r,c) in empty:
        tmp = copy.deepcopy(board_in)
        tmp[r][c]=opp
        if gomoku_check_win(tmp,5)==opp:
            return (r,c)
    return random.choice(empty)

def ai_high(board_in, ai_player):
    sz = len(board_in)
    opp = 1 if ai_player==2 else 2
    empty = get_empty_positions(board_in)
    for (r,c) in empty:
        tmp = copy.deepcopy(board_in)
        tmp[r][c] = ai_player
        if gomoku_check_win(tmp,5) == ai_player:
            return (r,c)
    for (r,c) in empty:
        tmp = copy.deepcopy(board_in)
        tmp[r][c] = opp
        if gomoku_check_win(tmp,5) == opp:
            return (r,c)
    best_score = -99999
    best_move = None
    def eval_line(line):
        score = 0
        for idx in range(len(line)):
            if line[idx]==0: continue
            me = line[idx]==ai_player
            c=1
            for i in range(idx+1,len(line)):
                if line[i]==line[idx]: c+=1
                else: break
            if me:
                if c==5: score+=100000
                elif c==4: score+=10000
                elif c==3: score+=1200
                elif c==2: score+=100
            else:
                if c==5: score-=120000
                elif c==4: score-=15000
                elif c==3: score-=1800
                elif c==2: score-=120
        return score
    for (r,c) in empty:
        temp = copy.deepcopy(board_in)
        temp[r][c]=ai_player
        s=0
        s += eval_line(temp[r])
        col = [temp[i][c] for i in range(sz)]
        s += eval_line(col)
        diag1 = []
        for i in range(-max(r,c),sz):
            nr=r+i; nc=c+i
            if 0<=nr<sz and 0<=nc<sz: diag1.append(temp[nr][nc])
        s+=eval_line(diag1)
        diag2 = []
        for i in range(-max(r, sz-1-c),sz):
            nr=r+i; nc=c-i
            if 0<=nr<sz and 0<=nc<sz: diag2.append(temp[nr][nc])
        s+=eval_line(diag2)
        dist = abs(r-sz/2)+abs(c-sz/2)
        s += (sz-dist)*2
        if s>best_score:
            best_score = s
            best_move = (r,c)
    return best_move

def ai_pick_gomoku(board_in, ai_player, diff):
    if diff=="low":
        return ai_low(board_in)
    elif diff=="mid":
        return ai_mid(board_in, ai_player)
    elif diff=="high":
        return ai_high(board_in, ai_player)

def reset_game(m):
    global board_size, cell, board, current_player, game_over, is_draw, selected_xq, xiangqi_winner
    board_size = m
    selected_xq = None
    xiangqi_winner = None
    is_draw = False
    game_over = False
    if game_type == "xiangqi":
        cell = min(WIDTH, HEIGHT - 140) // 10
        board = [row.copy() for row in XIANGQI_INIT]
        current_player = 1
    elif game_type == "go":
        cell = min(WIDTH, HEIGHT -140) // (board_size-1)
        board = [[0 for _ in range(board_size)] for _ in range(board_size)]
        current_player =1
    elif game_type == "gomoku":
        cell = min(WIDTH, HEIGHT -140) // (board_size-1)
        board = [[0 for _ in range(board_size)] for _ in range(board_size)]
        current_player =1

# =========绘制工具函数========
def draw_stone(surf, cx, cy, radius, is_black):
    if is_black:
        pygame.draw.circle(surf, (15,15,15), (cx+2, cy+2), radius)
        pygame.draw.circle(surf, (35,35,35), (cx, cy), radius)
        pygame.draw.circle(surf, (85,85,85), (cx-radius//3, cy-radius//3), radius//3)
    else:
        pygame.draw.circle(surf, (170,170,170), (cx+2, cy+2), radius)
        pygame.draw.circle(surf, (248,248,248), (cx, cy), radius)
        pygame.draw.circle(surf, (255,255,255), (cx-radius//3, cy-radius//3), radius//3)

def draw_button(rect, text_surface):
    pygame.draw.rect(screen,(35,70,130),rect.move(0,4),border_radius=14)
    pygame.draw.rect(screen,(60,110,185),rect,border_radius=14)
    text_rect = text_surface.get_rect(center=rect.center)
    screen.blit(text_surface, text_rect)

def draw_menu():
    screen.fill((12,12,22))
    title = font_big.render("Choose Game", True, (210,210,210))
    screen.blit(title, title.get_rect(centerx=WIDTH//2, y=40))
    t3 = font_mid.render("TicTacToe", True, (255,255,255))
    t4 = font_mid.render("Four InRow", True, (255,255,255))
    t5 = font_mid.render("Gomoku(五子棋)", True, (255,255,255))
    t_more = font_mid.render("More Games", True, (255,255,255))
    draw_button(btn_3, t3)
    draw_button(btn_4, t4)
    draw_button(btn_5, t5)
    draw_button(btn_more, t_more)

def draw_more_game():
    screen.fill((12,12,22))
    title = font_big.render("More Games", True, (210,210,210))
    screen.blit(title, title.get_rect(centerx=WIDTH//2,y=60))
    t_go = font_mid.render("Go (围棋)", True, (255,255,255))
    t_xiangqi = font_mid.render("Xiangqi (象棋)", True, (255,255,255))
    t_back = font_small.render("Back", True, (255,255,255))
    draw_button(btn_go, t_go)
    draw_button(btn_xiangqi, t_xiangqi)
    draw_button(btn_back_more, t_back)

def draw_mode_select():
    screen.fill((12,12,22))
    title = font_big.render("Select Play Mode", True, (210,210,210))
    screen.blit(title, title.get_rect(centerx=WIDTH//2,y=80))
    t_two = font_mid.render("Two Players", True, (255,255,255))
    t_ai = font_mid.render("Play vs AI", True, (255,255,255))
    draw_button(btn_two, t_two)
    draw_button(btn_ai, t_ai)
    score_bg = pygame.Rect(100,500,440,50)
    pygame.draw.rect(screen,(22,22,38),score_bg,border_radius=12)
    pygame.draw.rect(screen,(50,80,135),score_bg,2,border_radius=12)
    score_text = font_small.render(f"Score: Human {score_human} | AI {score_ai}", True, (180,180,180))
    screen.blit(score_text, score_text.get_rect(center=score_bg.center))

def draw_difficulty_select():
    screen.fill((12,12,22))
    title = font_big.render("Select AI Difficulty", True, (210,210,210))
    screen.blit(title, title.get_rect(centerx=WIDTH//2,y=60))
    t_low = font_mid.render("Low", True, (255,255,255))
    t_mid = font_mid.render("Medium", True, (255,255,255))
    t_high = font_mid.render("High", True, (255,255,255))
    t_back = font_small.render("Back", True, (255,255,255))
    draw_button(btn_diff_low, t_low)
    draw_button(btn_diff_mid, t_mid)
    draw_button(btn_diff_high, t_high)
    draw_button(btn_diff_back, t_back)

def draw_size_select():
    screen.fill((12,12,22))
    title = font_big.render("Board Size(Gomoku)", True, (210,210,210))
    screen.blit(title, title.get_rect(centerx=WIDTH//2,y=70))
    t9 = font_mid.render("9 × 9", True, (255,255,255))
    t13 = font_mid.render("13 × 13", True, (255,255,255))
    t15 = font_mid.render("15 × 15", True, (255,255,255))
    draw_button(btn_size9, t9)
    draw_button(btn_size13, t13)
    draw_button(btn_size15, t15)

def draw_game():
    global selected_xq
    screen.fill((24, 24, 36))
    offset_x = (WIDTH - (board_size-1)*cell) // 2
    offset_y = 20

    if game_type == "xiangqi":
        offset_x = (WIDTH - 9*cell)//2
        offset_y = 20
        board_rect = pygame.Rect(offset_x-14, offset_y-14, 9*cell+28,10*cell+28)
        pygame.draw.rect(screen,(55,38,24),board_rect,border_radius=12)
        pygame.draw.rect(screen,(145,102,55),board_rect,4,border_radius=12)
        for r in range(10):
            for c in range(9):
                x = offset_x + c*cell
                y = offset_y + r*cell
                pygame.draw.rect(screen,(80,60,42),(x,y,cell,cell),1)
        pygame.draw.rect(screen,(55,38,24),(offset_x, offset_y+4*cell,9*cell,cell))
        txt_river_left = font_mid.render("楚河",True,(220,185,145))
        txt_river_right = font_mid.render("汉界",True,(220,185,145))
        screen.blit(txt_river_left,txt_river_left.get_rect(centerx=offset_x+2.2*cell, y=offset_y+4*cell+6))
        screen.blit(txt_river_right,txt_river_right.get_rect(centerx=offset_x+6.8*cell, y=offset_y+4*cell+6))
        sx1 = offset_x + 3*cell
        sy1 = offset_y +0*cell
        sx2 = offset_x +5*cell
        sy2 = offset_y +2*cell
        pygame.draw.line(screen,(20,20,20),(sx1,sy1),(sx2,sy2),2)
        pygame.draw.line(screen,(20,20,20),(sx2,sy1),(sx1,sy2),2)
        sx1b = offset_x +3*cell
        sy1b = offset_y +7*cell
        sx2b = offset_x +5*cell
        sy2b = offset_y +9*cell
        pygame.draw.line(screen,(20,20,20),(sx1b,sy1b),(sx2b,sy2b),2)
        pygame.draw.line(screen,(20,20,20),(sx2b,sy1b),(sx1b,sy2b),2)

        for r in range(10):
            for c in range(9):
                p = board[r][c]
                if not p: continue
                cx = offset_x + c*cell + cell//2
                cy = offset_y + r*cell + cell//2
                rad = cell//2-5
                if xiangqi_is_red(p):
                    bg_color = (242,230,210)
                    text_color = (160,12,12)
                    shadow_color = (110,8,8)
                else:
                    bg_color = (235,230,220)
                    text_color = (10,10,10)
                    shadow_color = (40,40,40)
                pygame.draw.circle(screen,(30,30,30),(cx+2,cy+2),rad)
                pygame.draw.circle(screen, bg_color, (cx, cy), rad)
                pygame.draw.circle(screen, shadow_color, (cx, cy), rad,2)
                if selected_xq == (r,c):
                    for glow in range(1,4):
                        pygame.draw.circle(screen,(255,220,40),(cx,cy),rad+glow*2,1)
                ts = font_qizi.render(XIANGQI_PIECE_NAME[p], True, text_color)
                rc = ts.get_rect(center=(cx, cy))
                screen.blit(ts, rc)

    elif game_type=="go":
        board_rect = pygame.Rect(offset_x-14, offset_y-14, (board_size-1)*cell+28,(board_size-1)*cell+28)
        pygame.draw.rect(screen,(72,48,28),board_rect,border_radius=12)
        pygame.draw.rect(screen,(172,124,72),board_rect,4,border_radius=12)
        for i in range(board_size):
            pygame.draw.line(screen,(230,205,175),
                             (offset_x+i*cell, offset_y),
                             (offset_x+i*cell, offset_y+(board_size-1)*cell),2)
            pygame.draw.line(screen,(230,205,175),
                             (offset_x, offset_y+i*cell),
                             (offset_x+(board_size-1)*cell, offset_y+i*cell),2)
        star_points_13 = [(3,3),(3,6),(3,9),(6,3),(6,6),(6,9),(9,3),(9,6),(9,9)]
        for sr,sc in star_points_13:
            sx = offset_x + sc*cell
            sy = offset_y + sr*cell
            pygame.draw.circle(screen,(20,20,20),(sx,sy),4)
        for r in range(board_size):
            for c in range(board_size):
                val = board[r][c]
                if val==0: continue
                cx = offset_x + c*cell
                cy = offset_y + r*cell
                rad = cell//2-3
                draw_stone(screen, cx, cy, rad, is_black=(val==1))

    elif game_type=="gomoku":
        board_rect = pygame.Rect(offset_x-14, offset_y-14, (board_size-1)*cell+28,(board_size-1)*cell+28)
        pygame.draw.rect(screen,(62,52,42),board_rect,border_radius=12)
        pygame.draw.rect(screen,(135,122,105),board_rect,3,border_radius=12)
        for i in range(board_size):
            pygame.draw.line(screen,(195,185,170),
                             (offset_x+i*cell, offset_y),
                             (offset_x+i*cell, offset_y+(board_size-1)*cell),1)
            pygame.draw.line(screen,(195,185,170),
                             (offset_x, offset_y+i*cell),
                             (offset_x+(board_size-1)*cell, offset_y+i*cell),1)
        star_15 = [(3,3),(3,7),(3,11),(7,3),(7,7),(7,11),(11,3),(11,7),(11,11)]
        for sr,sc in star_15:
            sx = offset_x + sc*cell
            sy = offset_y + sr*cell
            pygame.draw.circle(screen,(25,25,25),(sx,sy),3)
        for r in range(board_size):
            for c in range(board_size):
                val = board[r][c]
                if val==0: continue
                cx = offset_x + c*cell
                cy = offset_y + r*cell
                rad = cell//2-3
                draw_stone(screen, cx, cy, rad, is_black=(val==1))

    # 底部状态栏，修复UnboundLocalError：txt预先初始化
    bottom_bar = pygame.Rect(0, HEIGHT - 100, WIDTH, 100)
    pygame.draw.rect(screen, (20,20,30), bottom_bar)
    pygame.draw.line(screen, (58, 88, 142), (0, HEIGHT-100), (WIDTH, HEIGHT-100),2)
    diff_text = font_small.render(f"Difficulty:{ai_difficulty.upper()}",True,(180,180,180))
    screen.blit(diff_text,(20, HEIGHT-88))
    score_text = font_small.render(f"Score: Human {score_human} | AI {score_ai}", True, (180,180,180))
    screen.blit(score_text, (240, HEIGHT -88))

    txt = None
    if not game_over:
        if play_mode == "two_player":
            if game_type=="xiangqi":
                txt = font_small.render(f"Turn: {'红方' if current_player==1 else '黑方'}", True,(200,200,200))
            elif game_type=="go":
                txt = font_small.render(f"Turn: {'黑棋' if current_player==1 else '白棋'}", True,(200,200,200))
            elif game_type=="gomoku":
                txt = font_small.render(f"Turn: {'黑棋' if current_player==1 else '白棋'}", True,(200,200,200))
    if txt is not None:
        screen.blit(txt, (460, HEIGHT -88))

    if game_over:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8,8,18,190))
        screen.blit(overlay, (0,0))
        popup = pygame.Rect(100, 220, 440, 220)
        pygame.draw.rect(screen, (30,30,50), popup, border_radius=16)
        pygame.draw.rect(screen, (60,100,170), popup, 3, border_radius=16)
        pygame.draw.rect(screen, (30, 90, 40), btn_again.move(2,2), border_radius=10)
        pygame.draw.rect(screen, (50,130,70), btn_again, border_radius=10)
        pygame.draw.rect(screen, (90, 40, 40), btn_back_game.move(2,2), border_radius=10)
        pygame.draw.rect(screen, (130,50,50), btn_back_game, border_radius=10)
        txt_again = font_small.render("Play Again", True, (255,255,255))
        txt_back = font_small.render("Back Menu", True, (255,255,255))
        screen.blit(txt_again, txt_again.get_rect(center=btn_again.center))
        screen.blit(txt_back, txt_back.get_rect(center=btn_back_game.center))
        if is_draw:
            res_text = font_big.render("Draw Game!", True, (255, 210, 0))
        else:
            if game_type == "xiangqi":
                if xiangqi_winner ==1:
                    res_text = font_big.render("红方胜利!", True, (220,30,30))
                else:
                    res_text = font_big.render("黑方胜利!", True, (0,0,0))
            else:
                res_text = font_big.render(f"{'黑方' if current_player==2 else '白方'} Win!", True, (0, 220, 255))
        screen.blit(res_text, res_text.get_rect(centerx=WIDTH//2,y=260))

# ----------------------主循环----------------------
running = True
while running:
    ai_move_ready = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            if state == STATE_MENU:
                if btn_3.collidepoint(mx, my):
                    game_type = "tictactoe"
                    state = STATE_MODE_SELECT
                elif btn_4.collidepoint(mx, my):
                    game_type = "connect4"
                    state = STATE_MODE_SELECT
                elif btn_5.collidepoint(mx, my):
                    game_type = "gomoku"
                    state = STATE_MODE_SELECT
                elif btn_more.collidepoint(mx,my):
                    state = STATE_MORE_GAME
            elif state == STATE_MORE_GAME:
                if btn_go.collidepoint(mx,my):
                    game_type = "go"
                    reset_game(13)
                    state = STATE_GAME
                elif btn_xiangqi.collidepoint(mx,my):
                    game_type = "xiangqi"
                    reset_game(10)
                    state = STATE_GAME
                elif btn_back_more.collidepoint(mx,my):
                    state = STATE_MENU
            elif state == STATE_MODE_SELECT:
                if btn_two.collidepoint(mx, my):
                    play_mode = "two_player"
                    if game_type =="gomoku":
                        state = STATE_SIZE_SELECT
                    else:
                        reset_game(13)
                        state = STATE_GAME
                elif btn_ai.collidepoint(mx, my):
                    play_mode = "ai_vs_human"
                    state = STATE_DIFFICULTY_SELECT
            elif state == STATE_DIFFICULTY_SELECT:
                if btn_diff_low.collidepoint(mx,my):
                    ai_difficulty="low"
                    if game_type=="gomoku":
                        state=STATE_SIZE_SELECT
                    else:
                        reset_game(13)
                        state=STATE_GAME
                elif btn_diff_mid.collidepoint(mx,my):
                    ai_difficulty="mid"
                    if game_type=="gomoku":
                        state=STATE_SIZE_SELECT
                    else:
                        reset_game(13)
                        state=STATE_GAME
                elif btn_diff_high.collidepoint(mx,my):
                    ai_difficulty="high"
                    if game_type=="gomoku":
                        state=STATE_SIZE_SELECT
                    else:
                        reset_game(13)
                        state=STATE_GAME
                elif btn_diff_back.collidepoint(mx,my):
                    state=STATE_MODE_SELECT
            elif state == STATE_SIZE_SELECT:
                if btn_size9.collidepoint(mx,my):
                    reset_game(9)
                    state = STATE_GAME
                elif btn_size13.collidepoint(mx,my):
                    reset_game(13)
                    state = STATE_GAME
                elif btn_size15.collidepoint(mx,my):
                    reset_game(15)
                    state = STATE_GAME
            elif state == STATE_GAME:
                if game_over:
                    if btn_again.collidepoint(mx, my):
                        reset_game(board_size)
                    elif btn_back_game.collidepoint(mx, my):
                        state = STATE_MENU
                else:
                    offset_x = (WIDTH - (board_size-1)*cell) // 2
                    offset_y = 20
                    if game_type=="xiangqi":
                        offset_x = (WIDTH - 9*cell)//2
                        offset_y = 20
                        cc = int(round((mx-offset_x)/cell))
                        rr = int(round((my-offset_y)/cell))
                        if xiangqi_in_board(rr,cc):
                            piece = board[rr][cc]
                            if selected_xq is None:
                                if piece:
                                    isred = xiangqi_is_red(piece)
                                    if (current_player==1 and isred) or (current_player==2 and not isred):
                                        selected_xq = (rr,cc)
                            else:
                                sr, sc = selected_xq
                                moves = xiangqi_get_moves(board,sr,sc)
                                if (rr,cc) in moves:
                                    captured_piece = board[rr][cc]
                                    board[rr][cc] = board[sr][sc]
                                    board[sr][sc] = ""

                                    win = False
                                    winner = None
                                    if captured_piece == "k":
                                        win = True
                                        winner = 1
                                    elif captured_piece == "K":
                                        win = True
                                        winner = 2
                                    if xiangqi_check_kings_face(board):
                                        win = True
                                        winner = current_player

                                    if win:
                                        game_over = True
                                        xiangqi_winner = winner
                                    else:
                                        current_player = 2 if current_player==1 else 1
                                    selected_xq = None
                                else:
                                    if piece:
                                        isred = xiangqi_is_red(piece)
                                        if (current_player==1 and isred) or (current_player==2 and not isred):
                                            selected_xq = (rr,cc)
                                        else:
                                            selected_xq = None
                                    else:
                                        selected_xq = None
                    elif game_type=="go":
                        c = int(round((mx-offset_x)/cell))
                        r = int(round((my-offset_y)/cell))
                        if 0<=r<board_size and 0<=c<board_size:
                            if go_try_play(board,r,c,current_player,board_size):
                                current_player = 2 if current_player==1 else 1
                    elif game_type=="gomoku":
                        c = int(round((mx-offset_x)/cell))
                        r = int(round((my-offset_y)/cell))
                        if 0<=r<board_size and 0<=c<board_size:
                            if board[r][c]==0:
                                board[r][c]=current_player
                                winner_gmk = gomoku_check_win(board,5)
                                if winner_gmk != 0:
                                    game_over = True
                                    if play_mode == "ai_vs_human":
                                        if winner_gmk == 1:
                                            score_human +=1
                                        else:
                                            score_ai +=1
                                elif is_board_full(board):
                                    game_over = True
                                    is_draw = True
                                if not game_over:
                                    current_player = 2 if current_player ==1 else 1
                                    ai_move_ready=True
    if state == STATE_GAME and play_mode=="ai_vs_human" and (not game_over) and ai_move_ready and game_type=="gomoku":
        ai_r, ai_c = ai_pick_gomoku(board,2,ai_difficulty)
        board[ai_r][ai_c]=2
        win_ai = gomoku_check_win(board,5)
        if win_ai!=0:
            game_over=True
            score_ai+=1
        elif is_board_full(board):
            game_over=True
            is_draw=True
        if not game_over:
            current_player=1

    if state == STATE_MENU:
        draw_menu()
    elif state == STATE_MORE_GAME:
        draw_more_game()
    elif state == STATE_MODE_SELECT:
        draw_mode_select()
    elif state == STATE_DIFFICULTY_SELECT:
        draw_difficulty_select()
    elif state == STATE_SIZE_SELECT:
        draw_size_select()
    elif state == STATE_GAME:
        draw_game()
    pygame.display.flip()
    clock.tick(30)
pygame.quit()

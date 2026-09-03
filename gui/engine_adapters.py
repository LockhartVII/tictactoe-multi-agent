"""Small protocol adapters for the native Go and Xiangqi engines."""

from pathlib import Path
import os
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def _engine_environment():
    env = os.environ.copy()
    candidates = [
        Path(sys.executable).parent / "Lib" / "site-packages" / "torch" / "lib",
        Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin"),
    ]
    existing = [str(path) for path in candidates if path.exists()]
    if existing:
        env["PATH"] = os.pathsep.join(existing + [env.get("PATH", "")])
    return env


class ProtocolError(RuntimeError):
    """Raised when an external engine cannot answer a protocol command."""


class KataGoAdapter:
    """Drive KataGo through GTP and keep the GUI board in sync."""

    def __init__(self, board_size=9):
        self.board_size = board_size
        runtime = ROOT / "engines" / "katago" / "runtime"
        executable = runtime / "katago.exe"
        model = ROOT / "models" / "go" / "kata9x9-b18c384nbt-20231025.bin.gz"
        config = runtime / "default_gtp.cfg"
        if not executable.exists() or not model.exists() or not config.exists():
            raise FileNotFoundError("KataGo runtime or 9x9 model is missing")
        self.process = subprocess.Popen(
            [str(executable), "gtp", "-config", str(config), "-model", str(model)],
            cwd=str(runtime),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=_engine_environment(),
            text=True,
            bufsize=1,
        )
        self._command("boardsize", str(board_size))
        self._command("clear_board")
        self._command("komi", "7.5")
        self._command("kata-time_settings", "none")

    def _command(self, command, *arguments):
        if self.process.poll() is not None:
            raise ProtocolError("KataGo has stopped")
        self.process.stdin.write(" ".join((command, *arguments)) + "\n")
        self.process.stdin.flush()
        lines = []
        for line in self.process.stdout:
            line = line.rstrip("\r\n")
            if not line:
                break
            lines.append(line)
        if lines and lines[0].startswith("?"):
            raise ProtocolError("KataGo: " + " ".join(lines))
        return lines

    @staticmethod
    def _gtp_column(column):
        # GTP skips the letter I.
        return chr(ord("A") + column + (1 if column >= 8 else 0))

    def play(self, colour, row, column):
        self._command("play", "B" if colour == 1 else "W", f"{self._gtp_column(column)}{self.board_size - row}")

    def play_pass(self, colour):
        self._command("play", "B" if colour == 1 else "W", "pass")

    def genmove(self, colour):
        lines = self._command("genmove", "B" if colour == 1 else "W")
        if not lines:
            return "pass"
        move = lines[-1].lstrip("=").strip().lower()
        if move == "pass" or len(move) < 2:
            return "pass"
        column = ord(move[0].upper()) - ord("A") - (1 if move[0].upper() > "I" else 0)
        row = self.board_size - int(move[1:])
        return row, column

    def close(self):
        if self.process.poll() is None:
            try:
                self._command("quit")
            except (OSError, ProtocolError):
                pass
            self.process.terminate()


class PikafishAdapter:
    """Drive Pikafish through UCI using the bundled NNUE network."""

    def __init__(self):
        runtime = ROOT / "engines" / "pikafish" / "runtime"
        executable = runtime / "Windows" / "pikafish-avx2.exe"
        network = runtime / "pikafish.nnue"
        if not executable.exists() or not network.exists():
            raise FileNotFoundError("Pikafish runtime or NNUE model is missing")
        self.process = subprocess.Popen(
            [str(executable)],
            cwd=str(runtime),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self._command("uci", "uciok")
        self._command("setoption name EvalFile value " + str(network))
        self._command("isready", "readyok")

    def _command(self, command, *until):
        if self.process.poll() is not None:
            raise ProtocolError("Pikafish has stopped")
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()
        lines = []
        targets = set(until)
        if not targets:
            return lines
        for line in self.process.stdout:
            line = line.rstrip("\r\n")
            lines.append(line)
            if any(line == target or line.startswith(target + " ") for target in targets):
                break
        return lines

    @staticmethod
    def _fen(board, current_player):
        fen_piece = {"h": "n", "e": "b", "H": "N", "E": "B"}
        rows = []
        for row in board:
            empty = 0
            encoded = []
            for piece in row:
                if not piece:
                    empty += 1
                else:
                    if empty:
                        encoded.append(str(empty))
                        empty = 0
                    encoded.append(fen_piece.get(piece, piece))
            if empty:
                encoded.append(str(empty))
            rows.append("".join(encoded))
        side = "w" if current_player == 1 else "b"
        return "/".join(rows) + f" {side} - - 0 1"

    @staticmethod
    def _square(row, column):
        return f"{chr(ord('a') + column)}{9 - row}"

    @staticmethod
    def _board_point(square):
        if len(square) < 2:
            return None
        column = ord(square[0].lower()) - ord("a")
        row = 9 - int(square[1])
        if 0 <= row < 10 and 0 <= column < 9:
            return row, column
        return None

    def best_move(self, board, current_player, movetime_ms=500):
        fen = self._fen(board, current_player)
        self._command("position fen " + fen)
        lines = self._command(f"go movetime {movetime_ms}", "bestmove")
        for line in reversed(lines):
            if line.startswith("bestmove "):
                move = line.split()[1]
                if move == "(none)":
                    return None
                source = self._board_point(move[:2])
                target = self._board_point(move[2:4])
                if source and target:
                    return source[0], source[1], target[0], target[1]
        return None

    def close(self):
        if self.process.poll() is None:
            try:
                self._command("quit")
            except (OSError, ProtocolError):
                pass
            self.process.terminate()

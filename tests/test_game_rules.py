import unittest

from gui.other_games import (
    OtherGamesController,
    go_area_score,
    go_play,
    go_position_key,
)


class GoRulesTests(unittest.TestCase):
    def test_capture(self):
        board = [[0, 1, 0], [1, 2, 0], [0, 1, 0]]
        history = {go_position_key(board)}
        self.assertTrue(go_play(board, 1, 2, 1, history))
        self.assertEqual(board[1][1], 0)

    def test_suicide_is_rejected(self):
        board = [[0, 1, 0], [1, 0, 1], [0, 1, 0]]
        self.assertFalse(go_play(board, 1, 1, 2, {go_position_key(board)}))

    def test_superko_is_rejected(self):
        board = [[0, 1, 2], [1, 2, 0], [0, 0, 0]]
        repeated = [[0, 1, 0], [1, 2, 1], [0, 0, 0]]
        history = {go_position_key(board), go_position_key(repeated)}
        self.assertFalse(go_play(board, 1, 2, 1, history))

    def test_two_passes_score_the_position(self):
        game = OtherGamesController()
        game.start("go", "human_vs_human", "mid", 9)
        game.pass_turn()
        self.assertFalse(game.game_over)
        game.pass_turn()
        self.assertTrue(game.game_over)
        self.assertEqual(game.go_result, "Black 0.0 · White 7.5")
        self.assertEqual(go_area_score(game.board), {1: 0.0, 2: 7.5})


class XiangqiDrawTests(unittest.TestCase):
    def test_threefold_repetition_is_a_draw(self):
        game = OtherGamesController()
        game.start("xiangqi", "human_vs_human", "mid", 9)
        moves = [(9, 0, 8, 0), (0, 0, 1, 0), (8, 0, 9, 0), (1, 0, 0, 0)] * 2
        for move in moves:
            game._apply_xiangqi_move(move)
        self.assertTrue(game.game_over)
        self.assertTrue(game.draw_game)
        self.assertEqual(game.xiangqi_result, "Threefold repetition")


if __name__ == "__main__":
    unittest.main()

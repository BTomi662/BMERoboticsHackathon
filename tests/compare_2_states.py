import sys
from pathlib import Path

# 1. Calculate paths relative to this test file
project_root = Path(__file__).resolve().parents[1]
src_directory = project_root / "src"

# 2. Append BOTH paths before importing
sys.path.append(str(project_root))
sys.path.append(str(src_directory))


def remove_action():

    b1 = board.GameBoard()
    b1.board[11].player = b1.player1
    b1.board[14].player = b1.player1
    b1.board[17].player = b1.player2
    b2 = board.GameBoard()
    b2.board[11].player = b2.player1
    b2.board[14].player = b2.player1

    print(b2.analyze_camera_step(b1.board))

    return "Passed" if b2.analyze_camera_step(b1.board)["action"] == "remove" else "Failed"


if __name__ == "__main__":
    import src.board as board
    remove_action()

from board import GameBoard  # Assuming your board code is in main_board.py
from engine import Engine         # Assuming your engine code is in engine.py


def get_human_piece_placement(board, player):
    """Prompts human to place a piece during Phase 1."""
    while True:
        try:
            nid = int(input(f"Phase 1 - Place piece. Enter Node ID (e.g., 11): "))
            # Changed board.EMPTY to None
            if nid in board.board and board.board[nid].player is None:
                return nid
            print("❌ Invalid or occupied node. Try again.")
        except ValueError:
            print("❌ Please enter a valid integer node ID.")


def get_human_move(board, player, phase):
    """Prompts human to move a piece during Phase 2 or 3."""
    phase_str = "Phase 2 (Slide)" if phase == 2 else "Phase 3 (Fly)"

    while True:
        try:
            inp = input(
                f"{phase_str} - Enter 'FROM TO' nodes (e.g., 11 12): ").strip()
            parts = inp.split()
            if len(parts) != 2:
                print("❌ Enter exactly two node IDs separated by a space.")
                continue

            from_nid, to_nid = int(parts[0]), int(parts[1])

            # Basic validation
            if from_nid not in board.board or to_nid not in board.board:
                print("❌ One or both Node IDs do not exist.")
                continue
            if board.board[from_nid].player != player:
                print("❌ You do not own the piece at the 'FROM' node.")
                continue
            # Changed board.EMPTY to None
            if board.board[to_nid].player is not None:
                print("❌ The 'TO' node is already occupied.")
                continue

            # Phase 2 specific neighbor validation
            if phase == 2 and board.board[to_nid] not in board.board[from_nid].neighbors.values():
                print(
                    "❌ Nodes are not adjacent! You can only slide to neighbors in Phase 2.")
                continue

            log.append(inp)

            return from_nid, to_nid
        except ValueError:
            print("❌ Please enter valid integer node IDs.")
    """Prompts human to move a piece during Phase 2 or 3."""
    phase_str = "Phase 2 (Slide)" if phase == 2 else "Phase 3 (Fly)"
    while True:
        try:
            inp = input(
                f"{phase_str} - Enter 'FROM TO' nodes (e.g., 11 12): ").strip()
            parts = inp.split()
            if len(parts) != 2:
                print("❌ Enter exactly two node IDs separated by a space.")
                continue

            from_nid, to_nid = int(parts[0]), int(parts[1])

            # Basic validation
            if from_nid not in board.board or to_nid not in board.board:
                print("❌ One or both Node IDs do not exist.")
                continue
            if board.board[from_nid].player != player:
                print("❌ You do not own the piece at the 'FROM' node.")
                continue
            if board.board[to_nid].player != board.EMPTY:
                print("❌ The 'TO' node is already occupied.")
                continue

            # Phase 2 specific neighbor validation
            if phase == 2 and board.board[to_nid] not in board.board[from_nid].neighbors.values():
                print(
                    "❌ Nodes are not adjacent! You can only slide to neighbors in Phase 2.")
                continue

            return from_nid, to_nid
        except ValueError:
            print("❌ Please enter valid integer node IDs.")


def handle_human_mill_removal(board, human_player, ai_player):
    """Prompts human to remove an AI piece if the human forms a mill."""
    all_protected = board._all_pieces_in_mills(ai_player)

    while True:
        try:
            r_nid = int(
                input(f"🔥 MILL FORMED! Choose one of {ai_player}'s pieces to REMOVE: "))
            if r_nid not in board.board or board.board[r_nid].player != ai_player:
                print(
                    f"❌ That node doesn't contain a piece belonging to {ai_player}.")
                continue

            if board.is_part_of_mill(r_nid, ai_player) and not all_protected:
                print(
                    f"❌ You cannot remove a piece inside {ai_player}'s mill unless ALL their pieces are in mills.")
                continue

            log.append(r_nid)

            return r_nid
        except ValueError:
            print("❌ Please enter a valid integer node ID.")


def main():
    print("Welcome to Nine Men's Morris Simulation!")

    # 1. Capture human player name at start
    while True:
        human_name = input("Enter Human Player Name: ").strip()
        if human_name and human_name.lower() != "joe":
            break
        print("❌ Name cannot be empty or 'Joe' (which is reserved for the AI).")

    # AI name is locked down as a constant str
    AI_NAME = "Joe"
    HUMAN_NAME = human_name
    log.append(
        f"Game started with Human Player: {HUMAN_NAME} and AI Player: {AI_NAME}")

    # 2. Initialize GameBoard with our names
    past_board = GameBoard()
    board = GameBoard()
    board.player1 = AI_NAME
    board.player2 = HUMAN_NAME

    # Sync the initial dictionaries inside the board setup
    board.unplaced_pieces = {AI_NAME: 9, HUMAN_NAME: 9}
    board.active_pieces = {AI_NAME: 0, HUMAN_NAME: 0}

    # 3. Spin up the Engine pointing to the correct targets
    ai_engine = Engine(ai_player=AI_NAME, human_player=HUMAN_NAME, max_depth=5)

    print("\n--- Game Initialized ---")
    print(f"Player 1 (AI): {AI_NAME} 🤖")
    print(f"Player 2 (Human): {HUMAN_NAME} 👤\n")

    # Main loop execution
    while True:
        board.display()

        # Check overall win states
        winner = board.check_win()
        if winner:
            message = f"🎉 GAME OVER! {winner} wins the game! 🎉"
            log.append(message)
            print(message)
            break

        # ==========================================
        # 👤 HUMAN TURN
        # ==========================================
        print(f"\n👉 {HUMAN_NAME}'s Turn (Human)")
        human_phase = board.get_game_phase(HUMAN_NAME)

        if human_phase == 1:
            to_nid = get_human_piece_placement(board, HUMAN_NAME)
            board.place_piece(to_nid, HUMAN_NAME)
            if board.is_part_of_mill(to_nid, HUMAN_NAME):
                r_nid = handle_human_mill_removal(board, HUMAN_NAME, AI_NAME)
                board.remove_piece(r_nid, AI_NAME)
        else:
            from_nid, to_nid = get_human_move(board, HUMAN_NAME, human_phase)
            board.move_piece(from_nid, to_nid, HUMAN_NAME)
            if board.is_part_of_mill(to_nid, HUMAN_NAME):
                r_nid = handle_human_mill_removal(board, HUMAN_NAME, AI_NAME)
                board.remove_piece(r_nid, AI_NAME)

        # Refresh map visibility
        board.display()

        winner = board.check_win()
        if winner:
            print(f"\n🎉 GAME OVER! {winner} wins the game! 🎉")
            break

        # ==========================================
        # 🤖 AI TURN ("Joe")
        # ==========================================
        print(f"\n🧠 {AI_NAME}'s Turn (AI Thinking...)")

        ai_action = ai_engine.get_best_move(board)

        if ai_action is None:
            message = f"🤖 {AI_NAME} has no legal moves left! {HUMAN_NAME} wins!"
            log.append(message)
            print(message)
            break

        message = f"🤖 {AI_NAME} Action Selected: {ai_action}"
        log.append(message)
        print(message)

        # Execute structural step
        if ai_action["from"] is None:
            board.place_piece(ai_action["to"], AI_NAME)
        else:
            board.move_piece(ai_action["from"], ai_action["to"], AI_NAME)

        # Execute deletion step if flagged by evaluation logic
        if ai_action["remove"] is not None:
            message = f"🔥 {AI_NAME} formed a mill and removed {HUMAN_NAME}'s piece at node: {ai_action['remove']}"
            log.append(message)
            print(message)
            board.remove_piece(ai_action["remove"], HUMAN_NAME)


if __name__ == "__main__":
    log = []
    main()
    print(log)

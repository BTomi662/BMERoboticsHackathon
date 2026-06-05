from board import GameBoard
from engine import Engine
import random as rnd


def get_board_state_dict(game_board):
    """Converts the current GameBoard object layout into a clean raw state dictionary."""
    return {node_id: node.player for node_id, node in game_board.board.items()}


def analyze_camera_step(prev_state, curr_state):
    """
    Compares the previous board state with the current camera state.
    Assumes exactly 1 atomic action has occurred.
    """
    gained = {}   # Nodes that went from Empty -> Occupied
    vacated = {}  # Nodes that went from Occupied -> Empty

    # Find the exact node that changed
    for node_id in prev_state.keys():
        prev_p = prev_state[node_id]
        curr_p = curr_state[node_id]

        if prev_p != curr_p:
            if prev_p is None and curr_p is not None:
                gained[node_id] = curr_p
            elif prev_p is not None and curr_p is None:
                vacated[node_id] = prev_p

    # Case 1: Placement (Phase 1)
    if len(gained) == 1 and len(vacated) == 0:
        to_node, player = list(gained.items())[0]
        return {"action": "place", "player": player, "to": to_node}

    # Case 2: Move (Phase 2 or 3)
    if len(gained) == 1 and len(vacated) == 1:
        to_node, player = list(gained.items())[0]
        from_node, _ = list(vacated.items())[0]
        return {"action": "move", "player": player, "from": from_node, "to": to_node}

    # Case 3: Piece Removal (Mill Capture)
    if len(gained) == 0 and len(vacated) == 1:
        at_node, removed_player = list(vacated.items())[0]
        return {"action": "remove", "player": removed_player, "at": at_node}

    return {"action": "none", "player": None}


def get_human_piece_placement(board, player):
    """Prompts human to place a piece during Phase 1."""
    while True:
        try:
            nid = int(input(f"Phase 1 - Place piece. Enter Node ID (e.g., 11): "))
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

    AI_NAME = "Joe"
    HUMAN_NAME = human_name
    log.append(
        f"Game started with Human Player: {HUMAN_NAME} and AI Player: {AI_NAME}")

    # 2. Initialize GameBoard
    board = GameBoard()
    board.player1 = AI_NAME
    board.player2 = HUMAN_NAME

    board.unplaced_pieces = {AI_NAME: 9, HUMAN_NAME: 9}
    board.active_pieces = {AI_NAME: 0, HUMAN_NAME: 0}

    # 3. Spin up the Engine
    ai_engine = Engine(ai_player=AI_NAME, human_player=HUMAN_NAME, max_depth=5)

    print("\n--- Game Initialized ---")
    print(f"Player 1 (AI): {AI_NAME} 🤖")
    print(f"Player 2 (Human): {HUMAN_NAME} 👤\n")

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
            # Atomic Step 1: Human Placement
            prev_state = get_board_state_dict(board)
            to_nid = get_human_piece_placement(board, HUMAN_NAME)
            board.place_piece(to_nid, HUMAN_NAME)

            # Verify via Camera Step Analyser
            curr_state = get_board_state_dict(board)
            camera_step = analyze_camera_step(prev_state, curr_state)
            log.append(f"Camera detected human action: {camera_step}")

            if board.is_part_of_mill(to_nid, HUMAN_NAME):
                board.display()
                # Atomic Step 2: Human Removal
                prev_state = get_board_state_dict(board)
                r_nid = handle_human_mill_removal(board, HUMAN_NAME, AI_NAME)
                board.remove_piece(r_nid, AI_NAME)

                # Verify via Camera Step Analyser
                curr_state = get_board_state_dict(board)
                camera_step = analyze_camera_step(prev_state, curr_state)
                log.append(f"Camera detected human action: {camera_step}")
        else:
            # Atomic Step 1: Human Move
            prev_state = get_board_state_dict(board)
            from_nid, to_nid = get_human_move(board, HUMAN_NAME, human_phase)
            board.move_piece(from_nid, to_nid, HUMAN_NAME)

            # Verify via Camera Step Analyser
            curr_state = get_board_state_dict(board)
            camera_step = analyze_camera_step(prev_state, curr_state)
            log.append(f"Camera detected human action: {camera_step}")

            if board.is_part_of_mill(to_nid, HUMAN_NAME):
                board.display()
                # Atomic Step 2: Human Removal
                prev_state = get_board_state_dict(board)
                r_nid = handle_human_mill_removal(board, HUMAN_NAME, AI_NAME)
                board.remove_piece(r_nid, AI_NAME)

                # Verify via Camera Step Analyser
                curr_state = get_board_state_dict(board)
                camera_step = analyze_camera_step(prev_state, curr_state)
                log.append(f"Camera detected human action: {camera_step}")

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

        # Atomic Step 1: AI Movement Execution
        prev_state = get_board_state_dict(board)
        if ai_action["from"] is None:
            board.place_piece(ai_action["to"], AI_NAME)
        else:
            board.move_piece(ai_action["from"], ai_action["to"], AI_NAME)

        # Verify via Camera Step Analyser
        curr_state = get_board_state_dict(board)
        camera_step = analyze_camera_step(prev_state, curr_state)
        log.append(f"Camera detected AI action: {camera_step}")

        # Atomic Step 2: AI Mill Removal Execution (If applicable)
        if ai_action["remove"] is not None:
            message = f"🔥 {AI_NAME} formed a mill and removed {HUMAN_NAME}'s piece at node: {ai_action['remove']}"
            log.append(message)
            print(message)

            prev_state = get_board_state_dict(board)
            board.remove_piece(ai_action["remove"], HUMAN_NAME)

            # Verify via Camera Step Analyser
            curr_state = get_board_state_dict(board)
            camera_step = analyze_camera_step(prev_state, curr_state)
            log.append(f"Camera detected AI action: {camera_step}")


if __name__ == "__main__":
    log = []
    main()
    print("\n--- ACTION LOG ---")
    for entry in log:
        print(entry)

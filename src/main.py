from board import GameBoard
from engine import Engine
import random as rnd
import camera_processor as cam


def get_board_state_dict(game_board):
    """Converts the current GameBoard object layout into a clean raw state dictionary."""
    return {node_id: node.player for node_id, node in game_board.board.items()}


def capture_camera_state(board):
    """
    Should return a raw state dictionary: {node_id: player_name_or_None}

    CRITICAL: Ensure that the strings representing your players ('player1', 'player2')
    are converted to match the runtime names ('Joe', 'name') configured in your board.
    """
    # Example format your CV data pipeline should return:
    # cv_raw_data = {11: "player1", 14: None, 17: "player2", ...}

    # This should return {node_id: player_name_or_None}
    camera_state = cam.get_camera_board_state()

    raise NotImplementedError(
        "Connect your OpenCV camera detection data dictionary here!")


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
    print("Welcome to Nine Men's Morris Camera-Driven System!")

    # 1. Capture human player name at start
    while True:
        human_name = input("Enter Human Player Name: ").strip()
        if human_name and human_name.lower() != "joe":
            break
        print("❌ Name cannot be empty or 'Joe' (reserved for AI).")

    AI_NAME = "Joe"
    HUMAN_NAME = human_name
    log = []

    log.append(f"Game started. Human: {HUMAN_NAME} | AI: {AI_NAME}")

    # 2. Initialize GameBoard
    board = GameBoard()
    board.player1 = AI_NAME
    board.player2 = HUMAN_NAME

    board.unplaced_pieces = {AI_NAME: 9, HUMAN_NAME: 9}
    board.active_pieces = {AI_NAME: 0, HUMAN_NAME: 0}

    # 3. Spin up the Engine
    ai_engine = Engine(ai_player=AI_NAME, human_player=HUMAN_NAME, max_depth=5)

    print("\n--- Game Initialized ---")

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
        # 👤 HUMAN TURN (Physical Action -> Camera Read)
        # ==========================================
        print(f"\n👉 {HUMAN_NAME}'s Turn (Human)")
        human_phase = board.get_game_phase(HUMAN_NAME)
        expected_action = "place" if human_phase == 1 else "move"

        while True:
            print(
                f"\n[Action Required]: Physically perform your **Phase {human_phase} {expected_action}**.")
            input(
                "👉 Press [Enter] AFTER you have completely finished moving your piece... ")

            prev_state = get_board_state_dict(board)
            try:
                curr_camera_state = capture_camera_state(board)
            except NotImplementedError:
                print(
                    "⚠️ Camera pipeline not connected! Reverting to manual debug simulation.")
                # Fallback safety handler for prototyping without camera attached
                to_nid = get_human_piece_placement(board, HUMAN_NAME) if human_phase == 1 else get_human_move(
                    board, HUMAN_NAME, human_phase)[1]
                if human_phase == 1:
                    board.place_piece(to_nid, HUMAN_NAME)
                break

            # Analyze what the camera physically detected
            detected = analyze_camera_step(prev_state, curr_camera_state)

            if detected["action"] != expected_action or detected["player"] != HUMAN_NAME:
                print(
                    f"❌ Camera Error: Expected a '{expected_action}' by {HUMAN_NAME}.")
                print(
                    f"   Detected instead: '{detected['action']}' by '{detected['player']}'.")
                print(
                    "👉 Please correct the physical board pieces and try scanning again.")
                continue

            # Dry-run validation through our core board rules logic
            if expected_action == "place":
                success = board.place_piece(detected["to"], HUMAN_NAME)
                to_nid = detected["to"]
            else:
                success = board.move_piece(
                    detected["from"], detected["to"], HUMAN_NAME)
                to_nid = detected["to"]

            if success:
                log.append(f"Camera verified human action: {detected}")
                print(f"✅ Physical action verified and accepted by game engine.")

                # Handle Mill Formation Capture Step
                if board.is_part_of_mill(to_nid, HUMAN_NAME):
                    board.display()
                    while True:
                        print(
                            f"🔥 MILL FORMED! Choose and physically REMOVE one of {AI_NAME}'s pieces.")
                        input(
                            "👉 Press [Enter] AFTER you have removed the piece... ")

                        prev_state_mill = get_board_state_dict(board)
                        curr_camera_state_mill = capture_camera_state(board)
                        detected_mill = analyze_camera_step(
                            prev_state_mill, curr_camera_state_mill)

                        if detected_mill["action"] == "remove" and detected_mill["player"] == AI_NAME:
                            # Validate rules (is it in a mill, etc.)
                            if board.remove_piece(detected_mill["at"], AI_NAME):
                                log.append(
                                    f"Camera verified mill removal: {detected_mill}")
                                print("✅ Removal verified successfully.")
                                break
                        print(
                            f"❌ Invalid removal. Please return the board state and remove a valid, unprotected piece.")
                break
            else:
                print(
                    "❌ Rule Violation: That move is illegal (e.g., non-adjacent or space occupied).")
                print(
                    "👉 Revert your physical piece to its original position and try a different move.")

        # Refresh map visibility after human movement settles
        board.display()

        winner = board.check_win()
        if winner:
            print(f"\n🎉 GAME OVER! {winner} wins the game! 🎉")
            break

        # ==========================================
        # 🤖 AI TURN (Engine Thinks -> Human Executes -> Camera Confirms)
        # ==========================================
        print(f"\n🧠 {AI_NAME}'s Turn (AI Thinking...)")
        ai_action = ai_engine.get_best_move(board)

        if ai_action is None:
            message = f"🤖 {AI_NAME} has no legal moves left! {HUMAN_NAME} wins!"
            log.append(message)
            print(message)
            break

        # Instruct the human player on how to move the piece for the AI
        print("\n--- 🤖 AI INSTRUCTIONS ---")
        if ai_action["from"] is None:
            print(
                f"👉 Please place an AI piece onto Node: **{ai_action['to']}**")
        else:
            print(
                f"👉 Please move the AI piece from Node **{ai_action['from']}** to Node **{ai_action['to']}**")

        if ai_action["remove"] is not None:
            print(
                f"🔥 AI FORMED A MILL! Also remove your own piece at Node: **{ai_action['remove']}**")
        print("--------------------------")

        # Atomic Step 1: Verify AI Movement Execution
        while True:
            input(
                "👉 Execute the AI's movement on the board, then press [Enter] to verify... ")

            prev_state = get_board_state_dict(board)
            curr_camera_state = capture_camera_state(board)
            detected = analyze_camera_step(prev_state, curr_camera_state)

            expected_type = "place" if ai_action["from"] is None else "move"

            if detected["action"] == expected_type and detected["player"] == AI_NAME:
                if expected_type == "place" and detected["to"] == ai_action["to"]:
                    board.place_piece(ai_action["to"], AI_NAME)
                elif expected_type == "move" and detected["from"] == ai_action["from"] and detected["to"] == ai_action["to"]:
                    board.move_piece(
                        ai_action["from"], ai_action["to"], AI_NAME)
                else:
                    print(
                        f"❌ Verification failed. You put the AI piece in the wrong place. It needs to go to {ai_action['to']}.")
                    continue

                log.append(
                    f"Camera verified AI movement execution: {detected}")
                print("✅ AI movement verified.")

                # Atomic Step 2: Verify AI Mill Removal Execution (If applicable)
                if ai_action["remove"] is not None:
                    while True:
                        print(
                            f"\n👉 Remember to remove your piece at Node **{ai_action['remove']}**.")
                        input(
                            "👉 Press [Enter] once you have physically removed it... ")

                        prev_state_rem = get_board_state_dict(board)
                        curr_camera_state_rem = capture_camera_state(board)
                        detected_rem = analyze_camera_step(
                            prev_state_rem, curr_camera_state_rem)

                        if detected_rem["action"] == "remove" and detected_rem["player"] == HUMAN_NAME and detected_rem["at"] == ai_action["remove"]:
                            board.remove_piece(ai_action["remove"], HUMAN_NAME)
                            log.append(
                                f"Camera verified AI mill removal execution: {detected_rem}")
                            print("✅ AI mill capture verified.")
                            break
                        print(
                            f"❌ Error: Camera didn't see the removal of your piece at node {ai_action['remove']}. Please check.")
                break
            else:
                print(
                    "❌ The camera did not detect the correct AI movement strategy. Please review the instructions.")

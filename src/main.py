import time
import threading

from pyparsing import line
from board import GameBoard
from engine import Engine
import random as rnd
import camera_processor as cam
import sys
from pathlib import Path
import os
from pathlib import Path
import sounddevice as sd
import soundfile as sf

VOICE_ACTOR = "batman"  # Default voice actor, can be changed at runtime


# 1. Calculate paths relative to this test file
project_root = Path(__file__).resolve().parents[1]
voice_directory = project_root / f"output/{VOICE_ACTOR}"

# 2. Append BOTH paths before importing
sys.path.append(str(project_root))
sys.path.append(str(voice_directory))


def get_board_state_dict(game_board):
    """Converts the current GameBoard object layout into a clean raw state dictionary."""
    return {node_id: node.player for node_id, node in game_board.board.items()}


def voice_chance(mood, custom_chance=None):
    """Plays a random voice line based on the given mood using sounddevice."""

    actor_folder = os.path.join("output", VOICE_ACTOR)

    chance = rnd.random() if custom_chance is None else custom_chance
    if chance < 0.1:
        print("No voice line this time.")
        return

    if not os.path.exists(actor_folder):
        print(f"⚠️ Error: The directory '{actor_folder}' could not be found.")
        return

    # Look for files starting with the mood prefix
    voicelines = []
    for file in os.listdir(actor_folder):
        if file.startswith(mood) and file.endswith(".wav"):
            voicelines.append(os.path.join(actor_folder, file))

    if voicelines:
        line = rnd.choice(voicelines)
        print(f"🎤 AI Voice Line: {line}")

        try:
            # 1. Load the data and sample rate (handles all WAV formats seamlessly)
            data, fs = sf.read(line)

            # 2. Play the audio asynchronously (doesn't block your hackathon code)
            sd.play(data, fs)

        except Exception as e:
            print(f"❌ Audio playback error: {e}")
    else:
        print(
            f"❓ No audio files found starting with '{mood}' in {actor_folder}")


def capture_camera_state(board):
    """
    Builds the camera state dynamically using the engine's current state
    as a trusted baseline, preventing random CV drops from breaking the game.
    """
    global GAMESTART
    raw_camera_state = cam.LATEST_BOARD_STATE

    # 1. Start with a perfect copy of the current trusted internal board state
    cleaned_state = get_board_state_dict(board)

    # 2. Convert raw camera entries to match runtime names safely
    camera_occupied_nodes = {}
    p1list, p2list = [], []
    for nid, val in raw_camera_state.items():
        if val == "player1":
            camera_occupied_nodes[int(nid)] = board.player1
            p1list.append(nid)
        elif val == "player2":
            camera_occupied_nodes[int(nid)] = board.player2
            p2list.append(nid)

    print(f"Camera detected AI pieces at nodes: {p1list}")
    print(f"Camera detected Player pieces at nodes: {p2list}")

    # 3. Get the active phase context to know what to look for
    # (Determines if we are checking the human's turn or the AI's turn)
    current_player = board.player1 if "AI Thinking" in log[-1] else board.player2

    # Let's inspect ONLY the nodes that the camera claims have active pieces.
    # If the camera detects a piece where the engine thought it was empty,
    # we trust the camera (detecting a Placement or the 'TO' target of a Move).
    for nid, player in camera_occupied_nodes.items():
        if cleaned_state.get(nid) is None:
            cleaned_state[nid] = player

    # 4. Handle Vacated Nodes (Moves/Removals) safely:
    # If a node was occupied in our engine, but it's missing from the camera data,
    # we ONLY clear it to None if it makes sense within the current game context
    # (i.e., it's a piece belonging to the active mover or a captured piece).
    for nid in list(cleaned_state.keys()):
        if cleaned_state[nid] is not None and nid not in camera_occupied_nodes:
            # Only vacate if it belongs to the player expected to move/be removed
            if cleaned_state[nid] == current_player or board.is_part_of_mill(nid, cleaned_state[nid]):
                cleaned_state[nid] = None

    if GAMESTART:
        GAMESTART = False

    return cleaned_state


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
            voice_chance("lose_piece")
            return r_nid
        except ValueError:
            print("❌ Please enter a valid integer node ID.")


def start_tracking():
    # Spin up the camera processing loops in the background
    camera_thread = threading.Thread(target=cam.main, daemon=True)
    camera_thread.start()


def main():
    print("Welcome to Nine Men's Morris Camera-Driven System!")

    start_tracking()
    time.sleep(5)

    # 1. Capture human player name at start
    while True:
        human_name = input("Enter Human Player Name: ").strip()
        if human_name and human_name.lower() != "joe":
            break
        print("❌ Name cannot be empty or 'Joe' (reserved for AI).")

    HUMAN_NAME = human_name

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
            if winner == HUMAN_NAME:
                voice_chance("lose", 1.0)
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

            # 👇 CHANGE: Capture the text typed into the prompt!
            debug_input = input(
                "👉 Press [Enter] AFTER moving, or type 'player_num node_id' to simulate (e.g., player2 11): ").strip()

            # 👇 NEW: If you type something, intercept it and update the mock camera state!
            if debug_input:
                try:
                    p_str, n_id = debug_input.split()
                    # Updates the camera dictionary directly before it gets read
                    cam.LATEST_BOARD_STATE[int(n_id)] = p_str
                except ValueError:
                    print("⚠️ Invalid debug format. Use: 'player1 23' or 'player2 11'")

            prev_state = get_board_state_dict(board)
            curr_camera_state = capture_camera_state(board)

            # ... rest of your code continues exactly the same ...
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

                # ==========================================
                # 🔥 HANDLE HUMAN MILL FORMATION REMOVAL
                # ==========================================
                if board.is_part_of_mill(to_nid, HUMAN_NAME):
                    board.display()
                    while True:
                        print(
                            f"🔥 MILL FORMED! Choose and physically REMOVE one of {AI_NAME}'s pieces.")

                        # 👇 CHANGE: Capture what you type in the terminal
                        debug_rem_input = input(
                            "👉 Press [Enter] AFTER you have removed the piece (or type the Node ID): ").strip()

                        # 👇 NEW: Handle simulation input by deleting the piece from the mock camera state
                        if debug_rem_input:
                            try:
                                target_node = int(debug_rem_input)
                                # To simulate a removal, we MUST remove it from the camera data dictionary
                                if target_node in cam.LATEST_BOARD_STATE:
                                    del cam.LATEST_BOARD_STATE[target_node]
                                    print(
                                        f"⚙️ [Debug Simulation] Removed piece from Node {target_node} in mock camera state.")
                                else:
                                    print(
                                        f"⚠️ Node {target_node} wasn't even occupied in the camera state!")
                            except ValueError:
                                print(
                                    "⚠️ Invalid format. Please enter a single numeric Node ID (e.g., 14).")
                                continue

                        prev_state_mill = get_board_state_dict(board)
                        curr_camera_state_mill = capture_camera_state(board)
                        detected_mill = analyze_camera_step(
                            prev_state_mill, curr_camera_state_mill)

                        # Check if the step analyzer correctly detected a removal of an AI piece
                        if detected_mill["action"] == "remove" and detected_mill["player"] == AI_NAME:
                            # Validate rules (e.g., ensuring you didn't pick a piece protected by an AI mill)
                            if board.remove_piece(detected_mill["at"], AI_NAME):
                                log.append(
                                    f"Camera verified mill removal: {detected_mill}")
                                print("✅ Removal verified successfully.")
                                voice_chance("lose_piece")
                                break

                        print(
                            f"❌ Invalid removal. Please return the board state and remove a valid, unprotected piece.")
                break
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
        log.append("AI Thinking")  # 👈 ADD THIS LINE HERE
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

        # =====================================================================
        # 🦾 ROBOTIC TRAJECTORY PATHFINDER GENERATION
        # =====================================================================
        print("\n🤖 [Robot Macro Control Script Sequences]:")

        # 1. Primary Move/Placement Action
        move_commands = board.pathfinder(
            ai_action["from"], ai_action["to"], is_removal=False)
        print(f"  ➡️ Move Sequence: {move_commands}")

        # 2. Secondary Opponent Capture Action
        if ai_action["remove"] is not None:
            remove_commands = board.pathfinder(
                None, ai_action["remove"], is_removal=True)
            print(f"  🔥 Capture/Removal Sequence: {remove_commands}")

        print("--------------------------")

        # Atomic Step 1: Verify AI Movement Execution
        while True:
            # Capture the string typed into the terminal for the AI's move
            debug_input = input(
                "👉 Execute the AI's movement on the board, then press [Enter] to verify... ").strip()

            # Inject simulated coordinates directly into the mock camera state
            if debug_input:
                try:
                    if debug_input.isdigit():
                        # Typing "11" automatically assigns it to the AI ("player1")
                        cam.LATEST_BOARD_STATE[int(debug_input)] = "player1"
                        print(
                            f"⚙️ [Debug Simulation] Placed AI piece on Node {debug_input} in mock camera state.")
                    else:
                        p_str, n_id = debug_input.split()
                        cam.LATEST_BOARD_STATE[int(n_id)] = p_str
                except ValueError:
                    print("⚠️ Invalid format. Type just the node number (e.g., 11)")
                    continue

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
                voice_chance("think")
                print("✅ AI movement verified.")

                # =============================================================
                # Atomic Step 2: Verify AI Mill Removal Execution (Fixed)
                # =============================================================
                if ai_action["remove"] is not None:
                    while True:
                        print(
                            f"\n🔥 AI FORMED A MILL! You must remove your own piece at Node: **{ai_action['remove']}**")

                        # 👇 CAPTURE THE REMOVAL SIMULATION NUMBER
                        debug_rem_input = input(
                            f"👉 Type the Node ID you are removing (Expected: {ai_action['remove']}) and press [Enter]: ").strip()

                        if debug_rem_input:
                            try:
                                target_node = int(debug_rem_input)
                                # To simulate a removal, we must delete it from the camera data dictionary
                                if target_node in cam.LATEST_BOARD_STATE:
                                    del cam.LATEST_BOARD_STATE[target_node]
                                    print(
                                        f"⚙️ [Debug Simulation] Removed human piece from Node {target_node} in mock camera state.")
                                else:
                                    print(
                                        f"⚠️ Node {target_node} wasn't marked as occupied in the camera state data.")
                            except ValueError:
                                print(
                                    "⚠️ Invalid format. Type the node number you removed.")
                                continue

                        prev_state_rem = get_board_state_dict(board)
                        curr_camera_state_rem = capture_camera_state(board)
                        detected_rem = analyze_camera_step(
                            prev_state_rem, curr_camera_state_rem)

                        # Validate that a removal action of a human piece was captured by the step analyzer
                        if detected_rem["action"] == "remove" and detected_rem["player"] == HUMAN_NAME and detected_rem["at"] == ai_action["remove"]:
                            board.remove_piece(ai_action["remove"], HUMAN_NAME)
                            log.append(
                                f"Camera verified AI mill removal execution: {detected_rem}")
                            print("✅ AI mill capture verified successfully.")
                            voice_chance("remove")
                            break
                        else:
                            print(
                                f"❌ Error: Camera didn't see the removal of your piece at node {ai_action['remove']}. Please try scanning again.")
                break
            else:
                print(
                    "❌ The camera did not detect the correct AI movement strategy. Please review the instructions.")


if __name__ == "__main__":
    GAMESTART = True
    VOICE_ACTOR = str(
        input("Choose AI Voice Actor (e.g., 'batman' or 'goth'): ")).strip().lower()
    AI_NAME = "Joe"
    log = []
    voice_chance("place", 1.0)  # Play a victory line at the start just for fun
    main()

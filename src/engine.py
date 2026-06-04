import numpy as np
import random


class Engine:
    def __init__(self, ai_player, human_player, max_depth=5):
        self.ai = ai_player
        self.human = human_player
        self.max_depth = max_depth

        # State tracking flags for lazy initialization
        self.initialized = False
        self.NODE_MAP = {}
        self.REV_NODE_MAP = {}
        self.MILLS = []
        self.NEIGHBORS = {}

        # Numeric matrix constants
        self.VAL_EMPTY = 0
        self.VAL_AI = 1
        self.VAL_HUMAN = 2

    def _lazy_init(self, game_board):
        """Dynamically builds lookup maps by reading the GameBoard's architecture."""
        # 1. Create a stable mapping of Node IDs to array indices (0-23)
        node_ids = [
            11, 12, 13,  # Row 1 (Top Outer)
            21, 22, 23,  # Row 2 (Top Middle)
            31, 32, 33,  # Row 3 (Top Inner)
            41, 42, 43,  # Row 4 (Left Crossbar)
            # Row 5 (Right Crossbar) -> Sits naturally right after row 4!
            51, 52, 53,
            61, 62, 63,  # Row 6 (Bottom Inner)
            71, 72, 73,  # Row 7 (Bottom Middle)
            81, 82, 83   # Row 8 (Bottom Outer)
        ]
        self.NODE_MAP = {node_id: i for i, node_id in enumerate(node_ids)}
        self.REV_NODE_MAP = {i: node_id for i, node_id in enumerate(node_ids)}

        # 2. Automatically translate the 16 Mills into array index tuples
        self.MILLS = [
            tuple(self.NODE_MAP[nid] for nid in mill)
            for mill in game_board.MILLS
        ]

        # 3. Automatically convert the bidirectional node graph into an adjacency list
        self.NEIGHBORS = {}
        for nid, node in game_board.board.items():
            current_idx = self.NODE_MAP[nid]
            neighbor_indices = []

            for neighbor_node in node.neighbors.values():
                if neighbor_node is not None:
                    # Reconstruct the neighbor's 2-digit ID using its row and index
                    neighbor_id = int(
                        f"{neighbor_node.row}{neighbor_node.node_index}")
                    neighbor_indices.append(self.NODE_MAP[neighbor_id])

            self.NEIGHBORS[current_idx] = neighbor_indices

        self.initialized = True

    def get_best_move(self, game_board):
        """API Entry Point."""
        # Configure internal lookups dynamically based on the passed board configuration
        if not self.initialized:
            self._lazy_init(game_board)

        # 1. Map current GameBoard OOP structures to the fast flat NumPy state
        board_array = np.zeros(24, dtype=np.int8)
        for nid, node in game_board.board.items():
            idx = self.NODE_MAP[nid]
            if node.player == self.ai:
                board_array[idx] = self.VAL_AI
            elif node.player == self.human:
                board_array[idx] = self.VAL_HUMAN

        ai_unplaced = game_board.unplaced_pieces[self.ai]
        human_unplaced = game_board.unplaced_pieces[self.human]
        ai_active = game_board.active_pieces[self.ai]
        human_active = game_board.active_pieces[self.human]

        # 2. Run the decision matrix calculations
        legal_moves = self._generate_legal_moves(
            board_array, self.VAL_AI, ai_unplaced, ai_active, human_active)
        if not legal_moves:
            return None

        best_score = float('-inf')
        best_move = random.choice(legal_moves)
        alpha = float('-inf')
        beta = float('inf')

        for move in legal_moves:
            sim_board, next_unplaced, next_active, next_h_active = self._simulate_move(
                board_array, move, self.VAL_AI, ai_unplaced, ai_active, human_active
            )
            score = self._minimax(sim_board, self.max_depth - 1, alpha, beta, False,
                                  next_unplaced, human_unplaced, next_active, next_h_active)

            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, best_score)

        # 3. Translate C-level indices back to the board's native 2-digit coordinate space
        from_idx, to_idx, r_idx = best_move
        return {
            "from": self.REV_NODE_MAP[from_idx] if from_idx is not None else None,
            "to": self.REV_NODE_MAP[to_idx],
            "remove": self.REV_NODE_MAP[r_idx] if r_idx is not None else None
        }

    def _minimax(self, board, depth, alpha, beta, is_maximizing, ai_unplaced, human_unplaced, ai_active, human_active):
        if ai_unplaced == 0 and ai_active < 3:
            return -10000 - depth
        if human_unplaced == 0 and human_active < 3:
            return 10000 + depth
        if depth == 0:
            return self._evaluate_board(board, ai_unplaced, human_unplaced, ai_active, human_active)

        if is_maximizing:
            legal_moves = self._generate_legal_moves(
                board, self.VAL_AI, ai_unplaced, ai_active, human_active)
            if not legal_moves:
                return -10000
            max_eval = float('-inf')
            for move in legal_moves:
                sim_board, next_ai_unplaced, next_ai_active, next_human_active = self._simulate_move(
                    board, move, self.VAL_AI, ai_unplaced, ai_active, human_active
                )
                evaluation = self._minimax(sim_board, depth - 1, alpha, beta, False,
                                           next_ai_unplaced, human_unplaced, next_ai_active, next_human_active)
                max_eval = max(max_eval, evaluation)
                alpha = max(alpha, evaluation)
                if beta <= alpha:
                    break
            return max_eval
        else:
            legal_moves = self._generate_legal_moves(
                board, self.VAL_HUMAN, human_unplaced, human_active, ai_active)
            if not legal_moves:
                return 10000
            min_eval = float('inf')
            for move in legal_moves:
                sim_board, next_human_unplaced, next_human_active, next_ai_active = self._simulate_move(
                    board, move, self.VAL_HUMAN, human_unplaced, human_active, ai_active
                )
                evaluation = self._minimax(sim_board, depth - 1, alpha, beta, True,
                                           ai_unplaced, next_human_unplaced, next_ai_active, next_human_active)
                min_eval = min(min_eval, evaluation)
                beta = min(beta, evaluation)
                if beta <= alpha:
                    break
            return min_eval

    def _generate_legal_moves(self, board, player, unplaced, active, opp_active):
        moves = []
        opponent = self.VAL_HUMAN if player == self.VAL_AI else self.VAL_AI
        empty_indices = np.where(board == self.VAL_EMPTY)[0]
        player_indices = np.where(board == player)[0]

        phase = 1 if unplaced > 0 else (3 if active == 3 else 2)

        base_actions = []
        if phase == 1:
            for idx in empty_indices:
                base_actions.append((None, idx))
        elif phase == 2:
            for idx in player_indices:
                for neighbor in self.NEIGHBORS[idx]:
                    if board[neighbor] == self.VAL_EMPTY:
                        base_actions.append((idx, neighbor))
        elif phase == 3:
            for idx in player_indices:
                for target in empty_indices:
                    base_actions.append((idx, target))

        for from_idx, to_idx in base_actions:
            temp_board = board.copy()
            if from_idx is None:
                temp_board[to_idx] = player
            else:
                temp_board[from_idx] = self.VAL_EMPTY
                temp_board[to_idx] = player

            if self._is_idx_in_mill(temp_board, to_idx, player):
                opp_indices = np.where(temp_board == opponent)[0]
                removable = [i for i in opp_indices if not self._is_idx_in_mill(
                    temp_board, i, opponent)]

                if not removable:
                    removable = list(opp_indices)

                if removable:
                    for r_idx in removable:
                        moves.append((from_idx, to_idx, r_idx))
                else:
                    moves.append((from_idx, to_idx, None))
            else:
                moves.append((from_idx, to_idx, None))

        return moves

    def _simulate_move(self, board, move, player, unplaced, active, opp_active):
        from_idx, to_idx, r_idx = move
        new_board = board.copy()

        if from_idx is None:
            new_board[to_idx] = player
            unplaced -= 1
            active += 1
        else:
            new_board[from_idx] = self.VAL_EMPTY
            new_board[to_idx] = player

        if r_idx is not None:
            new_board[r_idx] = self.VAL_EMPTY
            opp_active -= 1

        return new_board, unplaced, active, opp_active

    def _is_idx_in_mill(self, board, idx, player):
        for m in self.MILLS:
            if idx in m:
                if board[m[0]] == player and board[m[1]] == player and board[m[2]] == player:
                    return True
        return False

    def _evaluate_board(self, board, ai_unplaced, human_unplaced, ai_active, human_active):
        score = ((ai_active + ai_unplaced) -
                 (human_active + human_unplaced)) * 500

        if ai_unplaced > 0:
            for m in self.MILLS:
                slice_vals = board[list(m)]
                ai_count = np.sum(slice_vals == self.VAL_AI)
                human_count = np.sum(slice_vals == self.VAL_HUMAN)
                if ai_count == 2 and human_count == 0:
                    score += 50
                if human_count == 2 and ai_count == 0:
                    score -= 45

        return score

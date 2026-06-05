import numpy as np
import random


class Engine:
    """Minimax-based AI engine for Nine Men's Morris.

    This class provides a Minimax search with alpha-beta pruning to compute
    the best move for an AI player given a GameBoard instance. It lazily
    initializes lookup tables (node index maps, mills, neighbor lists) from
    the provided GameBoard structure on first use, and represents the board
    internally as a flat NumPy array for fast evaluation and move generation.

    Parameters
    - ai_player: identifier/object used by GameBoard to mark the AI's pieces
    - human_player: identifier/object used by GameBoard to mark the human's pieces
    - max_depth: search depth limit for Minimax (default: 5)
    """

    def __init__(self, ai_player, human_player, max_depth=5):
        """Initialize Engine.

        Args:
            ai_player: Identifier used by GameBoard to mark the AI's pieces.
            human_player: Identifier used by GameBoard to mark the human's pieces.
            max_depth: Depth limit for the minimax search.
        """
        # parameters
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
        """Lazily build internal lookup structures from a GameBoard.

        This reads the GameBoard's node layout, mills and neighbor links and
        converts them into structures optimized for the engine's internal
        NumPy-based representation.

        Args:
            game_board: A GameBoard instance exposing `board` and `MILLS`.
        """
        self.NODE_MAP = {
            11: 0,  14: 1,  17: 2,
            22: 3,  24: 4,  26: 5,
            33: 6,  34: 7,  35: 8,
            41: 9,  42: 10, 43: 11,
            45: 12, 46: 13, 47: 14,
            53: 15, 54: 16, 55: 17,
            62: 18, 64: 19, 66: 20,
            71: 21, 74: 22, 77: 23
        }
        self.REV_NODE_MAP = {v: k for k, v in self.NODE_MAP.items()}

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
        """Compute the best move for the AI on the given GameBoard.

        This method lazily initializes lookup tables, converts the object
        oriented GameBoard into a flat NumPy array, generates legal moves,
        runs minimax with alpha-beta pruning, and returns the chosen move in
        the board's original 2-digit coordinate format.

        Args:
            game_board: The current GameBoard instance.

        Returns:
            A dict with keys `from`, `to`, and `remove` containing 2-digit
            board coordinates, or `None` when no move is available.
        """
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
        """Minimax search with alpha-beta pruning.

        Args:
            board: NumPy array representing the board state.
            depth: Remaining search depth.
            alpha: Alpha bound for pruning.
            beta: Beta bound for pruning.
            is_maximizing: True when maximizing for AI, False when minimizing.
            ai_unplaced: Number of AI pieces not yet placed.
            human_unplaced: Number of human pieces not yet placed.
            ai_active: Number of AI pieces currently on board.
            human_active: Number of human pieces currently on board.

        Returns:
            Numeric evaluation score for the position.
        """
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
        """Generate all legal moves for `player` from `board`.

        Handles placement (phase 1), sliding (phase 2) and flying (phase 3).

        Args:
            board: NumPy array with current occupancy.
            player: Numeric value identifying the moving player.
            unplaced: Number of unplaced pieces the player still has.
            active: Number of player's pieces currently on the board.
            opp_active: Number of opponent's active pieces (used for phases).

        Returns:
            A list of moves as tuples `(from_idx, to_idx, remove_idx)` where
            `from_idx` is None for placement moves and `remove_idx` is None
            when no capture occurs.
        """
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
        """Apply `move` to a copy of `board` and update counts.

        Args:
            board: NumPy array of current board.
            move: Tuple `(from_idx, to_idx, remove_idx)` describing the move.
            player: Numeric player value placing/moving the piece.
            unplaced: Player's unplaced pieces count.
            active: Player's active pieces count.
            opp_active: Opponent's active pieces count.

        Returns:
            Tuple `(new_board, new_unplaced, new_active, new_opp_active)`.
        """
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
        """Check whether the piece at `idx` is part of a mill for `player`.

        Args:
            board: NumPy array of the board.
            idx: Index to test.
            player: Numeric player value.

        Returns:
            True if the given index is currently inside a completed mill.
        """
        for m in self.MILLS:
            if idx in m:
                if board[m[0]] == player and board[m[1]] == player and board[m[2]] == player:
                    return True
        return False

    def _evaluate_board(self, board, ai_unplaced, human_unplaced, ai_active, human_active):
        """Heuristic evaluation of `board` from AI's perspective.

        The evaluation prioritizes material (active + unplaced count) and
        gives bonuses/penalties for two-in-a-row potentials when pieces are
        still unplaced.

        Args:
            board: NumPy array representing the board.
            ai_unplaced: Number of AI pieces not yet placed.
            human_unplaced: Number of human pieces not yet placed.
            ai_active: Number of AI pieces currently on board.
            human_active: Number of human pieces currently on board.

        Returns:
            Integer score where higher is better for the AI.
        """
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

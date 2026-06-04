from nodes import Node


class GameBoard:
    def __init__(self):
        self.board = {}
        self.player1 = "JOE"
        self.player2 = "MIS"

        # Track pieces left to be dropped onto the board (Phase 1)
        self.unplaced_pieces = {self.player1: 9, self.player2: 9}
        # Track active pieces physically alive on the board (Phase 2 & 3)
        self.active_pieces = {self.player1: 0, self.player2: 0}

        # Initialize nodes
        for row in range(1, 9):
            for node in range(1, 4):
                node_id = int(f"{row}{node}")
                self.board[node_id] = Node(row, node)

# =====================================================================
        # ALL HORIZONTAL CONNECTIONS (Left to Right rows)
        # =====================================================================
        # Row 1 (Top Outer)
        self._connect(11, "right", 12)
        self._connect(12, "right", 13)

        # Row 2 (Top Middle)
        self._connect(21, "right", 22)
        self._connect(22, "right", 23)

        # Row 3 (Top Inner)
        self._connect(31, "right", 32)
        self._connect(32, "right", 33)

        # Row 4 (Left Crossbar)
        self._connect(41, "right", 42)
        self._connect(42, "right", 43)

        # Row 5 (Right Crossbar)
        self._connect(51, "right", 52)
        self._connect(52, "right", 53)

        # Row 6 (Bottom Inner)
        self._connect(61, "right", 62)
        self._connect(62, "right", 63)

        # Row 7 (Bottom Middle)
        self._connect(71, "right", 72)
        self._connect(72, "right", 73)

        # Row 8 (Bottom Outer)
        self._connect(81, "right", 82)
        self._connect(82, "right", 83)

        # =====================================================================
        # ALL VERTICAL CONNECTIONS (Top to Bottom columns)
        # =====================================================================
        # Far Left Column
        self._connect(11, "down", 41)
        self._connect(41, "down", 81)

        # Mid-Left Column
        self._connect(21, "down", 42)
        self._connect(42, "down", 71)

        # Near Left Column
        self._connect(31, "down", 43)
        self._connect(43, "down", 61)

        # Absolute Center Top Column
        self._connect(12, "down", 22)
        self._connect(22, "down", 32)

        # Absolute Center Bottom Column
        self._connect(62, "down", 72)
        self._connect(72, "down", 82)

        # Near Right Column
        self._connect(33, "down", 51)
        self._connect(51, "down", 63)

        # Mid-Right Column
        # Middle square top right down to right crossbar middle
        self._connect(23, "down", 52)
        self._connect(52, "down", 73)

        # Far Right Column
        self._connect(13, "down", 53)
        self._connect(53, "down", 83)
        # Definitive list of all 16 Mills on a Nine Men's Morris Board
        self.MILLS = [
            # Horizontal Mills
            [11, 12, 13], [21, 22, 23], [31, 32, 33],
            [41, 42, 43], [61, 62, 63],
            [51, 52, 53], [71, 72, 73], [81, 82, 83],
            # Vertical Mills
            [11, 41, 81], [21, 42, 71], [31, 43, 61],
            [12, 22, 32], [62, 72, 82],
            [33, 51, 63], [23, 52, 73], [13, 53, 83]
        ]

    def _connect(self, node1_id, direction, node2_id):
        """Helper to create bidirectional graph links cleanly."""
        opposite = {"up": "down", "down": "up",
                    "left": "right", "right": "left"}
        self.board[node1_id].neighbors[direction] = self.board[node2_id]
        self.board[node2_id].neighbors[opposite[direction]
                                       ] = self.board[node1_id]

    def get_game_phase(self, player):
        """Returns 1 (Drop), 2 (Move), or 3 (Fly) for the given player."""
        if self.unplaced_pieces[player] > 0:
            return 1
        if self.active_pieces[player] == 3:
            return 3
        return 2

    def place_piece(self, node_id, player):
        if node_id in self.board and self.board[node_id].player is None:
            if self.unplaced_pieces[player] > 0:
                self.board[node_id].player = player
                self.unplaced_pieces[player] -= 1
                self.active_pieces[player] += 1
                return True
        return False

    def move_piece(self, from_node_id, to_node_id, player):
        if from_node_id not in self.board or to_node_id not in self.board:
            return False

        from_node = self.board[from_node_id]
        to_node = self.board[to_node_id]

        if from_node.player != player or to_node.player is not None:
            return False

        phase = self.get_game_phase(player)

        # In Phase 2, target must be an adjacent neighbor. In Phase 3, you can fly anywhere.
        if phase == 2 and to_node not in from_node.neighbors.values():
            return False

        to_node.player = from_node.player
        from_node.player = None
        return True

    def remove_piece(self, node_id, opponent_player):
        """Removes an opponent's piece if it's eligible."""
        if node_id in self.board and self.board[node_id].player == opponent_player:
            # Rule check: You can't remove a piece in a mill unless ALL opponent pieces are in mills
            if self.is_part_of_mill(node_id, opponent_player) and not self._all_pieces_in_mills(opponent_player):
                return False

            self.board[node_id].player = None
            self.active_pieces[opponent_player] -= 1
            return True
        return False

    def is_part_of_mill(self, node_id, player):
        """Checks if a node currently forms a mill for a player."""
        for mill in self.MILLS:
            if node_id in mill:
                if all(self.board[n].player == player for n in mill):
                    return True
        return False

    def _all_pieces_in_mills(self, player):
        """Helper to verify if every single piece of a player is locked in a mill."""
        player_nodes = [nid for nid, node in self.board.items()
                        if node.player == player]
        return all(self.is_part_of_mill(nid, player) for nid in player_nodes)

    def check_win(self):
        # Phase 1 safe-check: Players can't lose from low piece counts during the dropping phase
        if self.unplaced_pieces[self.player1] == 0 and self.active_pieces[self.player1] < 3:
            return self.player2
        if self.unplaced_pieces[self.player2] == 0 and self.active_pieces[self.player2] < 3:
            return self.player1

        # AI tip: A player also loses if they have no legal moves remaining.
        return None

    def display(self):
        def p(node_id):
            player = self.board[node_id].player
            if player is None:
                return "-"
            return "J" if player == self.player1 else "M"

        print(f"""
        {p(11)}-----------{p(12)}-----------{p(13)}
        |           |           |
        |   {p(21)}-------{p(22)}-------{p(23)}   |
        |   |       |       |   |
        |   |   {p(31)}---{p(32)}---{p(33)}   |   |
        |   |   |       |   |   |
        {p(41)}---{p(42)}---{p(43)}       {p(51)}---{p(52)}---{p(53)}
        |   |   |       |   |   |
        |   |   {p(61)}---{p(62)}---{p(63)}   |   |
        |   |       |       |   |
        |   {p(71)}-------{p(72)}-------{p(73)}   |
        |           |           |
        {p(81)}-----------{p(82)}-----------{p(83)}
            """)

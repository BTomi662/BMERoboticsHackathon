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

       # Initialize nodes according to the ASCII blueprint
        # Row 1: 11, 41, 71
        # Row 2: 22, 42, 62
        # Row 3: 33, 43, 53
        # Row 4: 14, 24, 34, 54, 64, 74
        # Row 5: 35, 45, 55
        # Row 6: 26, 46, 66
        # Row 7: 17, 47, 77
        for row, cols in [(1, [1, 4, 7]), (2, [2, 4, 6]), (3, [3, 4, 5]),
                          (4, [1, 2, 3, 5, 6, 7]),
                          (5, [3, 4, 5]), (6, [2, 4, 6]), (7, [1, 4, 7])]:
            for col in cols:
                node_id = int(f"{row}{col}")
                self.board[node_id] = Node(row, col)

        # =====================================================================
        # ALL HORIZONTAL CONNECTIONS (Left to Right rows)
        # =====================================================================
        # Row 1 (Top Outer)
        self._connect(11, "right", 41)
        self._connect(41, "right", 71)

        # Row 2 (Top Middle)
        self._connect(22, "right", 42)
        self._connect(42, "right", 62)

        # Row 3 (Top Inner)
        self._connect(33, "right", 43)
        self._connect(43, "right", 53)

        # Row 4 (Left & Right Mid-line Crossbars)
        self._connect(14, "right", 24)
        self._connect(24, "right", 34)
        # Note: Central gap between 34 and 54 is empty space!
        self._connect(54, "right", 64)
        self._connect(64, "right", 74)

        # Row 5 (Bottom Inner)
        self._connect(35, "right", 45)
        self._connect(45, "right", 55)

        # Row 6 (Bottom Middle)
        self._connect(26, "right", 46)
        self._connect(46, "right", 66)

        # Row 7 (Bottom Outer)
        self._connect(17, "right", 47)
        self._connect(47, "right", 77)

        # =====================================================================
        # ALL VERTICAL CONNECTIONS (Top to Bottom columns)
        # =====================================================================
        # Column 1 (Far Left Vertical)
        self._connect(11, "down", 14)
        self._connect(14, "down", 17)

        # Column 2 (Mid-Left Vertical)
        self._connect(22, "down", 24)
        self._connect(24, "down", 26)

        # Column 3 (Near Left Vertical)
        self._connect(33, "down", 34)
        self._connect(34, "down", 35)

        # Column 4 (Center Left Crossbar down)
        self._connect(41, "down", 42)
        self._connect(42, "down", 43)

        # Column 4 (Center Right Crossbar down)
        self._connect(45, "down", 46)
        self._connect(46, "down", 47)

        # Column 5 (Near Right Vertical)
        self._connect(53, "down", 54)
        self._connect(54, "down", 55)

        # Column 6 (Mid-Right Vertical)
        self._connect(62, "down", 64)
        self._connect(64, "down", 66)

        # Column 7 (Far Right Vertical)
        self._connect(71, "down", 74)
        self._connect(74, "down", 77)

        # =====================================================================
        # 16 MILLS MAPPING (Matches updated alignment)
        # =====================================================================
        self.MILLS = [
            # Horizontal Mills (Row-by-Row left-to-right triplets)
            [11, 41, 71], [22, 42, 62], [33, 43, 53],
            [14, 24, 34], [54, 64, 74],
            [35, 45, 55], [26, 46, 66], [17, 47, 77],

            # Vertical Mills (Column-by-Column top-to-bottom triplets)
            [11, 14, 17], [22, 24, 26], [33, 34, 35],
            [41, 42, 43], [45, 46, 47],
            [53, 54, 55], [62, 64, 66], [71, 74, 77]
        ]

    @classmethod
    def from_camera_state(cls, camera_state, player1="player1", player2="player2"):
        """Build a GameBoard instance from the camera output dictionary."""
        game_board = cls()
        game_board.player1 = player1
        game_board.player2 = player2

        for node in game_board.board.values():
            node.player = None

        active_counts = {player1: 0, player2: 0}

        for node_id, camera_player in camera_state.items():
            if node_id not in game_board.board:
                continue

            if camera_player == "player1":
                board_player = player1
            elif camera_player == "player2":
                board_player = player2
            else:
                continue

            game_board.board[node_id].player = board_player
            active_counts[board_player] += 1

        game_board.active_pieces = active_counts
        game_board.unplaced_pieces = {
            player1: 9 - active_counts[player1],
            player2: 9 - active_counts[player2],
        }

        return game_board

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

    def analyze_camera_step(self, prev_state):
        """
        Compares the previous board state with the current camera state.
        Assumes exactly 1 atomic action has occurred.
        """
        gained = {}   # Nodes that went from Empty -> Occupied
        vacated = {}  # Nodes that went from Occupied -> Empty

        # Find the exact node that changed
        for node_id in prev_state.keys():
            # FIX: Extract the .player property from the node objects
            prev_p = prev_state[node_id].player
            curr_p = self.board[node_id].player

            if prev_p != curr_p:
                if prev_p is None and curr_p is not None:
                    gained[node_id] = curr_p
                elif prev_p is not None and curr_p is None:
                    vacated[node_id] = prev_p

        # Case 1: Placement (Phase 1)
        if len(gained) == 1 and len(vacated) == 0:
            to_node, player = list(gained.items())[0]
            return {
                "action": "place",
                "player": player,
                "to": to_node
            }

        # Case 2: Move (Phase 2 or 3)
        if len(gained) == 1 and len(vacated) == 1:
            to_node, player = list(gained.items())[0]
            from_node, _ = list(vacated.items())[0]
            return {
                "action": "move",
                "player": player,
                "from": from_node,
                "to": to_node
            }

        # Case 3: Piece Removal (Mill Capture)
        if len(gained) == 0 and len(vacated) == 1:
            at_node, removed_player = list(vacated.items())[0]
            return {
                "action": "remove",
                "player": removed_player,
                "at": at_node
            }

        # No changes detected
        return {"action": "none", "player": None}

    def display(self):
        def p(node_id):
            player = self.board[node_id].player
            if player is None:
                return "-"
            return "J" if player == self.player1 else "M"

        print(f"""
        {p(11)}-----------{p(41)}-----------{p(71)}
        |           |           |
        |   {p(22)}-------{p(42)}-------{p(62)}   |
        |   |       |       |   |
        |   |   {p(33)}---{p(43)}---{p(53)}   |   |
        |   |   |       |   |   |
        {p(14)}---{p(24)}---{p(34)}       {p(54)}---{p(64)}---{p(74)}
        |   |   |       |   |   |
        |   |   {p(35)}---{p(45)}---{p(55)}   |   |
        |   |       |       |   |
        |   {p(26)}-------{p(46)}-------{p(66)}   |
        |           |           |
        {p(17)}-----------{p(47)}-----------{p(77)}
            """)


if __name__ == "__main__":
    pass

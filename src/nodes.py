class Node:
    def __init__(self, row, node_index):
        self.row = row
        self.node_index = node_index
        self.neighbors = {"up": None, "right": None,
                          "down": None, "left": None}
        self.player = None  # Holds string name of the player or None

"""
problem.py

Formal problem formulation for the Treasure Hunt Grid World (CSAI 301).

A state is the 4-tuple (row, col, 0, 0). Only the position is significant; the
last two fields are kept as zeros so the interface stays compatible with the
rest of the project. Treasure collection and key ownership are not part of the
objective: the agent wins as soon as it reaches the exit cell 'E'.

The map is generated deterministically, so every run uses exactly the same
problem instance.
"""

from collections import deque


def _build_default_map(rows=40, cols=40):
    """
    Build the default 40x40 grid as a list of strings.

    A regular wall lattice gives a fully connected maze of 1,101 walkable
    cells, which puts the state space inside the required 1,000-10,000 range.
    Sand and mud are placed with a fixed arithmetic rule (no random generator),
    so the map is identical on every run.

    Cell legend:
        P start     E exit      # wall
        . grass=1   S sand=3    M mud=5
        0..3 decorative treasure markers (cost 1, not part of the goal)
    """
    grid = [
        [
            "#" if ((c % 4 == 3 and r % 4 != 2) or (r % 4 == 3 and c % 4 != 2))
            else "."
            for c in range(cols)
        ]
        for r in range(rows)
    ]

    grid[0][0] = "P"
    grid[rows - 1][cols - 1] = "E"

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] != ".":
                continue
            marker = r * 7 + c * 13
            if marker % 17 == 0:
                grid[r][c] = "S"
            elif marker % 19 == 0:
                grid[r][c] = "M"

    for (r, c), label in [((5, 5), "0"), ((17, 25), "1"),
                          ((29, 9), "2"), ((34, 33), "3")]:
        if grid[r][c] in {".", "S", "M"}:
            grid[r][c] = label

    return ["".join(row) for row in grid]


class TreasureHuntProblem:
    """
    Encapsulates the grid world: state space, actions, transition model,
    step costs, and goal test.
    """

    DEFAULT_MAP = _build_default_map()

    def __init__(self, grid_lines=None):
        """
        Args:
            grid_lines: optional custom map as a list of equal-length strings.
                        Defaults to the generated 40x40 map.
        """
        self.grid = [list(row) for row in (grid_lines or self.DEFAULT_MAP)]
        self.rows = len(self.grid)
        self.cols = len(self.grid[0])

        if not self.grid or any(len(row) != self.cols for row in self.grid):
            raise ValueError("The map must be non-empty and rectangular.")

        # Cost of entering each cell type.
        self.step_costs = {
            ".": 1, "P": 1, "E": 1, "K": 1, "D": 1,
            "0": 1, "1": 1, "2": 1, "3": 1,
            "S": 3, "M": 5,
        }

        self.start_pos = None
        self.exit_pos = None
        self.key_pos = None
        self.door_pos = None
        self.treasures = {}

        self._parse_entities()

        if self.start_pos is None:
            raise ValueError("The map must contain a start cell 'P'.")
        if self.exit_pos is None:
            raise ValueError("The map must contain an exit cell 'E'.")

    def _parse_entities(self):
        """Locate the special cells in the grid."""
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.grid[r][c]
                if cell == "P":
                    self.start_pos = (r, c)
                elif cell == "E":
                    self.exit_pos = (r, c)
                elif cell == "K":
                    self.key_pos = (r, c)
                elif cell == "D":
                    self.door_pos = (r, c)
                elif cell in {"0", "1", "2", "3"}:
                    self.treasures[(r, c)] = int(cell)

    def get_initial_state(self):
        """Return the initial state at the start cell: (row, col, 0, 0)."""
        r, c = self.start_pos
        return (r, c, 0, 0)

    def is_goal(self, state):
        """Return True when the agent reaches the exit cell."""
        r, c, _treasure_mask, _has_key = state
        return (r, c) == self.exit_pos

    def get_successors(self, state):
        """
        Generate all legal transitions from a state.

        Actions are tried in the fixed order UP, DOWN, LEFT, RIGHT. A move is
        legal only if the target cell is inside the grid and is not a wall.

        Returns:
            A list of (action_name, next_state, step_cost) tuples.
        """
        r, c, _treasure_mask, _has_key = state

        actions = [
            ("UP", -1, 0),
            ("DOWN", 1, 0),
            ("LEFT", 0, -1),
            ("RIGHT", 0, 1),
        ]

        successors = []
        for action, dr, dc in actions:
            nr, nc = r + dr, c + dc

            if not (0 <= nr < self.rows and 0 <= nc < self.cols):
                continue
            if self.grid[nr][nc] == "#":
                continue

            next_state = (nr, nc, 0, 0)
            step_cost = self.step_costs[self.grid[nr][nc]]
            successors.append((action, next_state, step_cost))

        return successors

    def count_reachable_states(self):
        """Count distinct states reachable from the start using BFS."""
        start = self.get_initial_state()
        seen = {start}
        queue = deque([start])

        while queue:
            state = queue.popleft()
            for _action, next_state, _cost in self.get_successors(state):
                if next_state not in seen:
                    seen.add(next_state)
                    queue.append(next_state)

        return len(seen)

    def get_state_space_stats(self):
        """Return grid and state-space statistics for the report."""
        total_cells = self.rows * self.cols
        wall_cells = sum(row.count("#") for row in self.grid)
        walkable_cells = total_cells - wall_cells

        return {
            "rows": self.rows,
            "cols": self.cols,
            "total_cells": total_cells,
            "wall_cells": wall_cells,
            "walkable_cells": walkable_cells,
            "treasure_count": len(self.treasures),
            # With a position-only state model, each walkable cell is one state.
            "theoretical_states": walkable_cells,
            "reachable_states": self.count_reachable_states(),
        }

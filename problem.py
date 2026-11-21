"""
problem.py
Formal problem formulation for Treasure Hunt Grid World (CSAI 301 - Phase I).

Updated objective:
    The agent wins immediately upon reaching Exit E.

Search state:
    s = (row, col, 0, 0)

The 4-value tuple is retained for compatibility with the existing project,
but treasure collection and key ownership are no longer part of the search
state because they do not affect the goal or legal movement.
"""

from collections import deque


class TreasureHuntProblem:
    """Grid world, transition model, step costs, and goal test."""

    DEFAULT_MAP = [
        "P..#...SS....0.",
        ".#.#.#.SM.###..",
        ".#...#....#1...",
        ".###.####.#.##.",
        "............SS.",
        "##.###.####.SM.",
        ".....#....#....",
        "####.#.##.###.#",
        ".......#.......",
        ".#####.#.#####.",
        "...2.#....SS...",
        "####.####.SM.##",
        "..............E",
        ".######.#######",
        "............3..",
    ]

    def __init__(self, grid_lines=None):
        self.grid = [list(row) for row in (grid_lines or self.DEFAULT_MAP)]
        self.rows = len(self.grid)
        self.cols = len(self.grid[0])

        if not self.grid or any(len(row) != self.cols for row in self.grid):
            raise ValueError("The map must be non-empty and rectangular.")

        self.step_costs = {
            ".": 1,
            "P": 1,
            "E": 1,
            "K": 1,
            "D": 1,
            "0": 1,
            "1": 1,
            "2": 1,
            "3": 1,
            "S": 3,
            "M": 5,
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
        """Locate Start, Exit, Key, Door, and Treasures."""
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
        """
        Initial state.
        Keep the 4-field tuple for compatibility:
        (row, col, unused_treasure_mask, unused_key_flag).
        """
        r, c = self.start_pos
        return (r, c, 0, 0)

    def is_goal(self, state):
        """Goal test: win as soon as the agent reaches Exit E."""
        r, c, _treasure_mask, _has_key = state
        return (r, c) == self.exit_pos

    def get_successors(self, state):
        """
        Return valid transitions as:
            (action_name, next_state, step_cost)

        Movement order is deterministic: UP, DOWN, LEFT, RIGHT.
        The door is traversable; key and treasure collection are not required.
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

            cell = self.grid[nr][nc]

            if cell == "#":
                continue

            # Treasure and key fields are kept as zero because they are
            # intentionally irrelevant to the updated objective.
            next_state = (nr, nc, 0, 0)
            step_cost = self.step_costs[cell]

            successors.append((action, next_state, step_cost))

        return successors

    def count_reachable_states(self):
        """Count unique reachable position-based states from the start."""
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
        """Return map statistics for the updated position-only state model."""
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
            # Each walkable coordinate corresponds to one search state.
            "theoretical_states": walkable_cells,
            "reachable_states": self.count_reachable_states(),
        }

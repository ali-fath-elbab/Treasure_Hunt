"""
Game.py
Live Pygame visualisation of the uninformed search algorithms on the
Treasure Hunt grid defined in problem.py.

The problem model (grid, actions, step costs, goal test) lives in problem.py,
so the animation and the experimental results use exactly the same problem.
"""

import time
import heapq
from collections import deque

import pygame

from problem import TreasureHuntProblem

# =========================
# Initialize Pygame
# =========================
pygame.init()

problem = TreasureHuntProblem()
ROWS, COLS = problem.rows, problem.cols

CELL_SIZE = 14
GRID_X, GRID_Y = 32, 118
WIDTH, HEIGHT = 980, 720

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Treasure Hunt - Search Visualizer")
clock = pygame.time.Clock()

# =========================
# Palette
# =========================
BG = (14, 22, 31)
TITLE_BG = (25, 45, 62)
PANEL = (28, 43, 57)
BOX = (36, 55, 71)
BORDER = (52, 75, 94)
TEXT = (225, 238, 247)
MUTED = (145, 165, 182)
TEAL = (55, 195, 190)
TEAL_DARK = (40, 150, 150)
ORANGE = (240, 145, 75)

# Grid colours
WALL = (32, 44, 56)
OPEN = (86, 116, 145)
EXPLORED = (62, 112, 158)
PATH = (255, 218, 70)
AGENT = (255, 150, 60)
SAND = (170, 150, 110)
MUD = (130, 100, 78)
START_COLOR = (60, 210, 130)
GOAL_COLOR = (245, 245, 245)

# =========================
# Fonts
# =========================
def _font(size, bold=False):
    for name in ("arial", "consolas", "dejavusans"):
        try:
            f = pygame.font.SysFont(name, size, bold=bold)
            if f:
                return f
        except Exception:
            pass
    return pygame.font.Font(None, size)


font_small = _font(13)
font_body = _font(15, True)
font_label = _font(14, True)
font_header = _font(26, True)
font_title = _font(15, True)
font_stat = _font(20, True)

START = problem.get_initial_state()

# =========================
# Game State
# =========================
algorithm = "BFS"
explored = []
path = []
yielded_cells = set()

running_search = False
paused = False
search_finished = False

nodes_expanded = 0
nodes_generated = 0
max_frontier = 0
path_cost = 0
execution_time = 0

steps_per_frame = 3
search_generator = None
search_start_time = 0

# =========================
# Buttons
# =========================
PX = 616
ALGO_RECTS = {
    name: pygame.Rect(634 + i * 79, 148, 71, 32)
    for i, name in enumerate(["BFS", "DFS", "UCS", "IDS"])
}
PLAY_RECT = pygame.Rect(634, 190, 97, 36)
PAUSE_RECT = pygame.Rect(739, 190, 97, 36)
RESET_RECT = pygame.Rect(844, 190, 97, 36)
MINUS_RECT = pygame.Rect(634, 270, 40, 32)
SPEED_RECT = pygame.Rect(680, 270, 228, 32)
PLUS_RECT = pygame.Rect(914, 270, 40, 32)

# =========================
# Helpers
# =========================
def cell_of(state):
    return (state[0], state[1])


def emit(state):
    """Yield a frame only on the first visit to a cell (keeps IDS watchable)."""
    coord = cell_of(state)
    if coord in yielded_cells:
        return False
    yielded_cells.add(coord)
    return True


def reconstruct_path(parent, current):
    result = [current]
    while current in parent:
        current = parent[current]
        result.append(current)
    result.reverse()
    return result


def reset_search():
    global running_search, paused, search_finished
    global nodes_expanded, nodes_generated, max_frontier, path_cost
    global explored, path, yielded_cells, search_generator

    running_search = False
    paused = False
    search_finished = False
    nodes_expanded = 0
    nodes_generated = 0
    max_frontier = 0
    path_cost = 0
    explored = []
    path = []
    yielded_cells = set()
    search_generator = None


# =========================
# Search Algorithms
# =========================
def bfs():
    global nodes_expanded, nodes_generated, max_frontier

    frontier = deque([START])
    parent = {}
    visited = {START}
    nodes_generated = 1

    while frontier:
        max_frontier = max(max_frontier, len(frontier))
        current = frontier.popleft()
        nodes_expanded += 1

        if emit(current):
            explored.append(current)
            yield current

        if problem.is_goal(current):
            return reconstruct_path(parent, current)

        for _action, nxt, _cost in problem.get_successors(current):
            nodes_generated += 1
            if nxt not in visited:
                visited.add(nxt)
                parent[nxt] = current
                frontier.append(nxt)

    return []


def dfs():
    global nodes_expanded, nodes_generated, max_frontier

    frontier = [START]
    parent = {}
    visited = {START}
    nodes_generated = 1

    while frontier:
        max_frontier = max(max_frontier, len(frontier))
        current = frontier.pop()
        nodes_expanded += 1

        if emit(current):
            explored.append(current)
            yield current

        if problem.is_goal(current):
            return reconstruct_path(parent, current)

        for _action, nxt, _cost in reversed(problem.get_successors(current)):
            nodes_generated += 1
            if nxt not in visited:
                visited.add(nxt)
                parent[nxt] = current
                frontier.append(nxt)

    return []


def ucs():
    global nodes_expanded, nodes_generated, max_frontier

    counter = 0
    frontier = [(0, counter, START)]
    parent = {}
    best_cost = {START: 0}
    nodes_generated = 1

    while frontier:
        max_frontier = max(max_frontier, len(frontier))
        cost, _, current = heapq.heappop(frontier)

        if cost > best_cost.get(current, float("inf")):
            continue

        nodes_expanded += 1
        if emit(current):
            explored.append(current)
            yield current

        if problem.is_goal(current):
            return reconstruct_path(parent, current)

        for _action, nxt, step_cost in problem.get_successors(current):
            nodes_generated += 1
            new_cost = cost + step_cost
            if new_cost < best_cost.get(nxt, float("inf")):
                best_cost[nxt] = new_cost
                parent[nxt] = current
                counter += 1
                heapq.heappush(frontier, (new_cost, counter, nxt))

    return []


def ids(max_depth=250):
    global nodes_expanded, nodes_generated, max_frontier

    for depth_limit in range(max_depth + 1):
        frontier = [(START, 0)]
        parent = {}
        min_depth = {START: 0}
        nodes_generated += 1

        while frontier:
            max_frontier = max(max_frontier, len(frontier))
            current, depth = frontier.pop()
            nodes_expanded += 1

            if emit(current):
                explored.append(current)
                yield current

            if problem.is_goal(current):
                return reconstruct_path(parent, current)

            if depth < depth_limit:
                for _action, nxt, _cost in reversed(problem.get_successors(current)):
                    nodes_generated += 1
                    next_depth = depth + 1
                    if next_depth < min_depth.get(nxt, float("inf")):
                        min_depth[nxt] = next_depth
                        parent[nxt] = current
                        frontier.append((nxt, next_depth))

    return []


ALGORITHMS = {"BFS": bfs, "DFS": dfs, "UCS": ucs, "IDS": ids}


def start_search():
    global running_search, paused, search_finished
    global path_cost, search_generator, search_start_time

    reset_search()
    search_generator = ALGORITHMS[algorithm]()
    search_start_time = time.perf_counter()
    running_search = True


# =========================
# Drawing helpers
# =========================
def panel(rect, color=PANEL, radius=12, border=BORDER):
    pygame.draw.rect(screen, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(screen, border, rect, width=1, border_radius=radius)


def button(rect, label, color, active=False, text_color=TEXT):
    pygame.draw.rect(screen, color, rect, border_radius=8)
    if active:
        pygame.draw.rect(screen, (255, 255, 255), rect, width=2, border_radius=8)
    surf = font_body.render(label, True, text_color)
    screen.blit(surf, (rect.centerx - surf.get_width() // 2,
                       rect.centery - surf.get_height() // 2))


def text_at(text, x, y, color=TEXT, f=font_small):
    screen.blit(f.render(str(text), True, color), (x, y))


def stat_box(rect, label, value):
    panel(rect, BOX, radius=8)
    text_at(label, rect.x + 10, rect.y + 7, MUTED, font_small)
    text_at(value, rect.x + 10, rect.y + 25, TEXT, font_stat)


def draw_title_bar():
    pygame.draw.rect(screen, TITLE_BG, (0, 0, WIDTH, 42))
    text_at("Treasure Hunt - Search Visualizer", 20, 12, TEXT, font_title)
    badge = pygame.Rect(WIDTH - 104, 9, 84, 24)
    pygame.draw.rect(screen, (35, 60, 76), badge, border_radius=12)
    pygame.draw.circle(screen, TEAL, (badge.x + 14, badge.centery), 5)
    text_at("Ready", badge.x + 26, badge.y + 4, TEXT, font_small)


def draw_grid():
    panel(pygame.Rect(20, 106, 584, 594))
    path_coords = {cell_of(s) for s in path}
    explored_coords = {cell_of(s) for s in explored}

    for r in range(ROWS):
        for c in range(COLS):
            rect = pygame.Rect(GRID_X + c * CELL_SIZE, GRID_Y + r * CELL_SIZE,
                               CELL_SIZE, CELL_SIZE)
            ch = problem.grid[r][c]

            if ch == "#":
                color = WALL
            elif (r, c) in path_coords:
                color = PATH
            elif (r, c) in explored_coords:
                color = EXPLORED
            elif ch == "S":
                color = SAND
            elif ch == "M":
                color = MUD
            else:
                color = OPEN

            pygame.draw.rect(screen, color, rect)
            if ch in {"0", "1", "2", "3"}:
                pygame.draw.circle(screen, PATH, rect.center, max(2, CELL_SIZE // 3))

    def marker(coord, color, radius):
        r, c = coord
        center = (GRID_X + c * CELL_SIZE + CELL_SIZE // 2,
                  GRID_Y + r * CELL_SIZE + CELL_SIZE // 2)
        pygame.draw.circle(screen, (0, 0, 0), center, radius + 1)
        pygame.draw.circle(screen, color, center, radius)

    marker(cell_of(START), START_COLOR, 5)
    marker(problem.exit_pos, GOAL_COLOR, 5)
    if explored:
        marker(cell_of(explored[-1]), AGENT, 5)


def draw_controls():
    panel(pygame.Rect(PX, 106, 344, 594))

    text_at("Algorithm", 634, 124, TEXT, font_label)
    for name, rect in ALGO_RECTS.items():
        button(rect, name, TEAL if name == algorithm else BOX)

    button(PLAY_RECT, "Play", TEAL, text_color=(10, 30, 35))
    button(PAUSE_RECT, "Pause", ORANGE if paused else BOX,
           text_color=(20, 20, 20) if paused else TEXT)
    button(RESET_RECT, "Reset", ORANGE, text_color=(30, 18, 10))

    text_at("Speed (events per frame)", 634, 246, MUTED, font_small)
    button(MINUS_RECT, "-", BOX)
    panel(SPEED_RECT, BOX, radius=8)
    surf = font_body.render(str(steps_per_frame), True, TEXT)
    screen.blit(surf, (SPEED_RECT.centerx - surf.get_width() // 2,
                       SPEED_RECT.centery - surf.get_height() // 2))
    button(PLUS_RECT, "+", BOX)

    text_at("Search statistics", 634, 320, TEXT, font_label)
    stat_box(pygame.Rect(634, 344, 150, 52), "Expanded", f"{nodes_expanded:,}")
    stat_box(pygame.Rect(792, 344, 150, 52), "Generated", f"{nodes_generated:,}")
    stat_box(pygame.Rect(634, 404, 150, 52), "Frontier", f"{max_frontier:,}")
    stat_box(pygame.Rect(792, 404, 150, 52), "Max frontier", f"{max_frontier:,}")

    text_at("Solution", 634, 470, TEXT, font_label)
    stat_box(pygame.Rect(634, 494, 150, 52), "Path length", str(len(path) - 1 if path else 0))
    stat_box(pygame.Rect(792, 494, 150, 52), "Path cost", str(path_cost))
    stat_box(pygame.Rect(634, 554, 150, 52), "Execution time", f"{execution_time:.3f} s")
    stat_box(pygame.Rect(792, 554, 150, 52), "Visited cells", str(len(explored)))

    # Legend
    ly = 624
    legend = [
        (OPEN, "Open"), (EXPLORED, "Explored"), (PATH, "Path"),
        (AGENT, "Agent"), (SAND, "Sand (3)"), (MUD, "Mud (5)"),
    ]
    for i, (color, label) in enumerate(legend):
        x = 634 + (i % 3) * 104
        y = ly + (i // 3) * 26
        pygame.draw.rect(screen, color, (x, y + 2, 14, 14), border_radius=3)
        text_at(label, x + 20, y + 1, MUTED, font_small)

    status = "Ready" if not running_search and not search_finished else (
        "Running" if running_search and not paused else (
            "Paused" if paused else "Found"))
    text_at(f"Status: {status}", 634, 682, TEAL if status in ("Ready", "Found") else MUTED, font_small)


def draw_header():
    text_at("Treasure Hunt", 20, 54, TEXT, font_header)
    text_at("Select algorithm to visualize.", 20, 86, MUTED, font_small)


# =========================
# Main Loop
# =========================
def main():
    global algorithm, paused, search_generator, path, path_cost
    global search_finished, running_search, steps_per_frame, execution_time

    running = True
    while running:
        screen.fill(BG)
        draw_title_bar()
        draw_header()
        draw_grid()
        draw_controls()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos
                for name, rect in ALGO_RECTS.items():
                    if rect.collidepoint(pos):
                        algorithm = name
                        reset_search()
                if PLAY_RECT.collidepoint(pos):
                    start_search()
                if PAUSE_RECT.collidepoint(pos):
                    paused = not paused
                if RESET_RECT.collidepoint(pos):
                    reset_search()
                if MINUS_RECT.collidepoint(pos):
                    steps_per_frame = max(1, steps_per_frame - 1)
                if PLUS_RECT.collidepoint(pos):
                    steps_per_frame = min(20, steps_per_frame + 1)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_UP:
                    steps_per_frame = min(20, steps_per_frame + 1)
                elif event.key == pygame.K_DOWN:
                    steps_per_frame = max(1, steps_per_frame - 1)

        if running_search and not paused and not search_finished:
            for _ in range(steps_per_frame):
                try:
                    next(search_generator)
                except StopIteration as exc:
                    path = exc.value if exc.value else []
                    path_cost = sum(
                        problem.step_costs[problem.grid[s[0]][s[1]]] for s in path[1:]
                    )
                    execution_time = time.perf_counter() - search_start_time
                    search_finished = True
                    running_search = False
                    break

        pygame.display.flip()
        clock.tick(15)

    pygame.quit()


if __name__ == "__main__":
    main()

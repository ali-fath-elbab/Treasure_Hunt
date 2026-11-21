"""
Game.py
Live Pygame visualisation of the uninformed search algorithms on the
Treasure Hunt grid defined in problem.py.

The problem model (grid, actions, step costs, goal test) lives in problem.py,
so the animation and the experimental results use exactly the same problem.

UI: clean dark desktop-style dashboard (cards, status pill, stat tiles).
"""

import ctypes
import heapq
import sys
import time
from collections import deque

import pygame

from problem import TreasureHuntProblem

# Keep the window crisp on high-DPI Windows screens
if sys.platform == "win32":
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# ---------------------------------------------------------------------
# Window and theme
# ---------------------------------------------------------------------

WIDTH, HEIGHT = 1200, 730
FPS = 60

BG = (18, 22, 29)
CARD_BG = (26, 31, 40)
BORDER = (45, 52, 64)
TEXT = (230, 235, 242)
MUTED = (140, 150, 165)

BLUE = (74, 134, 214)
GREEN = (52, 168, 120)
ORANGE = (222, 155, 60)
RED = (210, 88, 94)
DISABLED = (34, 39, 49)
DISABLED_TEXT = (90, 99, 114)
NEUTRAL = (38, 44, 55)
TILE_BG = (32, 38, 49)

FLOOR = (34, 40, 51)
<<<<<<< HEAD
SAND = (179, 139, 66)      # Sand - Cost 3
MUD = (133, 91, 69)        # Mud - Cost 5
=======
SAND = (179, 139, 66)      # Sand - cost 3
MUD = (133, 91, 69)        # Mud  - cost 5
>>>>>>> Dimensions
WALL = (10, 13, 18)
GRID_LINE = (46, 53, 66)
EXPLORED = (70, 130, 200)
PATH = (52, 190, 150)
PATH_LINE = (110, 236, 196)

<<<<<<< HEAD
TERRAIN_COLORS = {
    ".": FLOOR,
    "P": FLOOR,
    "E": FLOOR,
    "K": FLOOR,
    "D": FLOOR,

    "0": FLOOR,
    "1": FLOOR,
    "2": FLOOR,
    "3": FLOOR,

    "S": SAND,
    "M": MUD,

    "#": WALL,
}

ALGORITHMS = {"BFS": bfs, "DFS": dfs, "UCS": ucs, "IDS": ids}

=======
>>>>>>> Dimensions
pygame.init()
problem = TreasureHuntProblem()
ROWS, COLS = problem.rows, problem.cols

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Treasure Hunt - Search Visualizer")
clock = pygame.time.Clock()

FONT_NAMES = "segoeui,helvetica,arial"
font = pygame.font.SysFont(FONT_NAMES, 16)
small = pygame.font.SysFont(FONT_NAMES, 14)
tiny = pygame.font.SysFont(FONT_NAMES, 13)
heading = pygame.font.SysFont(FONT_NAMES, 18, bold=True)
title_font = pygame.font.SysFont(FONT_NAMES, 28, bold=True)
number_font = pygame.font.SysFont(FONT_NAMES, 24, bold=True)
button_font = pygame.font.SysFont(FONT_NAMES, 15, bold=True)

START = problem.get_initial_state()


# ---------------------------------------------------------------------
# Layout (everything is derived from a few numbers so nothing overlaps)
# ---------------------------------------------------------------------

HEADER_H = 84
MARGIN = 32
GRID_X = MARGIN
GRID_Y = HEADER_H + 26

PANEL_MIN_W = 380
CELL = max(
    4,
    min(
        40,
        (WIDTH - 2 * MARGIN - 40 - PANEL_MIN_W) // COLS,
        (HEIGHT - GRID_Y - 80) // ROWS,
    ),
)
GRID_W = COLS * CELL
GRID_H = ROWS * CELL

SIDE_X = GRID_X + GRID_W + 40
SIDE_Y = GRID_Y - 5
SIDE_W = WIDTH - SIDE_X - MARGIN
SIDE_H = HEIGHT - SIDE_Y - 30

PAD = 24
INNER_X = SIDE_X + PAD
INNER_W = SIDE_W - 2 * PAD
GAP = 10


def split_row(count, y, h, x=INNER_X, width=INNER_W, gap=GAP):
    """Split a row into `count` equal rectangles."""
    w = (width - gap * (count - 1)) // count
    return [pygame.Rect(x + i * (w + gap), y, w, h) for i in range(count)]


# Section 1: algorithm
ALGO_LABEL_Y = SIDE_Y + 20
ALGO_NAMES = ["BFS", "DFS", "UCS", "IDS"]
ALGO_RECTS = dict(zip(ALGO_NAMES, split_row(4, SIDE_Y + 54, 38)))

# Section 2: controls
PLAY_RECT, PAUSE_RECT, RESET_RECT = split_row(3, SIDE_Y + 108, 40)

# Section 3: speed
SPEED_Y = SIDE_Y + 166
RIGHT_EDGE = INNER_X + INNER_W
PLUS_RECT = pygame.Rect(RIGHT_EDGE - 32, SPEED_Y, 32, 32)
MINUS_RECT = pygame.Rect(RIGHT_EDGE - 120, SPEED_Y, 32, 32)

SEP_1 = SIDE_Y + 218
STATS_Y = SEP_1 + 16
TILE_H = 60
TILE_Y = STATS_Y + 34
SEP_2 = TILE_Y + 2 * TILE_H + GAP + 16
SOLUTION_Y = SEP_2 + 14
DETAILS_Y = SOLUTION_Y + 36


# ---------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------

algorithm = "BFS"
explored = []
path = []
yielded_cells = set()

running_search = False
paused = False
search_finished = False
error_message = None

nodes_expanded = 0
nodes_generated = 0
frontier_size = 0
max_frontier = 0
path_cost = 0
execution_time = 0.0

steps_per_frame = 3
search_generator = None
search_start_time = 0.0


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

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
    global running_search, paused, search_finished, error_message
    global nodes_expanded, nodes_generated, frontier_size, max_frontier
    global path_cost, execution_time
    global explored, path, yielded_cells, search_generator

    running_search = False
    paused = False
    search_finished = False
    error_message = None
    nodes_expanded = 0
    nodes_generated = 0
    frontier_size = 0
    max_frontier = 0
    path_cost = 0
    execution_time = 0.0
    explored = []
    path = []
    yielded_cells = set()
    search_generator = None


# ---------------------------------------------------------------------
# Search algorithms
# ---------------------------------------------------------------------

def bfs():
    global nodes_expanded, nodes_generated, frontier_size, max_frontier

    frontier = deque([START])
    parent = {}
    visited = {START}
    nodes_generated = 1

    while frontier:
        frontier_size = len(frontier)
        max_frontier = max(max_frontier, frontier_size)
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
    global nodes_expanded, nodes_generated, frontier_size, max_frontier

    frontier = [START]
    parent = {}
    visited = {START}
    nodes_generated = 1

    while frontier:
        frontier_size = len(frontier)
        max_frontier = max(max_frontier, frontier_size)
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
    global nodes_expanded, nodes_generated, frontier_size, max_frontier

    counter = 0
    frontier = [(0, counter, START)]
    parent = {}
    best_cost = {START: 0}
    nodes_generated = 1

    while frontier:
        frontier_size = len(frontier)
        max_frontier = max(max_frontier, frontier_size)
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
    global nodes_expanded, nodes_generated, frontier_size, max_frontier

    for depth_limit in range(max_depth + 1):
        frontier = [(START, 0)]
        parent = {}
        min_depth = {START: 0}
        nodes_generated += 1

        while frontier:
            frontier_size = len(frontier)
            max_frontier = max(max_frontier, frontier_size)
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
    global running_search, search_generator, search_start_time

    reset_search()
    search_generator = ALGORITHMS[algorithm]()
    search_start_time = time.perf_counter()
    running_search = True


def update_search():
    global path, path_cost, execution_time
    global search_finished, running_search, error_message

    if not running_search or paused or search_finished:
        return

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
        except Exception as exc:
            error_message = str(exc)
            search_finished = True
            running_search = False
            break


# ---------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------

def draw_text(value, x, y, color=TEXT, face=font):
    surface = face.render(str(value), True, color)
    screen.blit(surface, (x, y))
    return surface.get_width()


def draw_text_centered(value, rect, color=TEXT, face=font):
    surface = face.render(str(value), True, color)
    screen.blit(
        surface,
        (rect.centerx - surface.get_width() // 2,
         rect.centery - surface.get_height() // 2),
    )


def card(rect, fill=CARD_BG, outline=BORDER, radius=12):
    pygame.draw.rect(screen, fill, rect, border_radius=radius)
    pygame.draw.rect(screen, outline, rect, width=1, border_radius=radius)


def button(label, rect, fill, text_color=TEXT, enabled=True):
    if not enabled:
        fill, text_color = DISABLED, DISABLED_TEXT
    pygame.draw.rect(screen, fill, rect, border_radius=8)
    draw_text_centered(label, rect, text_color, button_font)


def blend(a, b, amount):
    return tuple(int(a[i] * (1 - amount) + b[i] * amount) for i in range(3))


def separator(y):
    pygame.draw.line(screen, BORDER, (INNER_X, y), (INNER_X + INNER_W, y), 1)


# ---------------------------------------------------------------------
# Maze
# ---------------------------------------------------------------------

def cell_center(row, col):
    return (GRID_X + col * CELL + CELL // 2, GRID_Y + row * CELL + CELL // 2)


def draw_maze():
    path_cells = {cell_of(s) for s in path}
    explored_cells = {cell_of(s) for s in explored}

    outer = pygame.Rect(GRID_X - 5, GRID_Y - 5, GRID_W + 10, GRID_H + 10)
    card(outer, CARD_BG, BORDER, 8)

    draw_lines = CELL >= 8
    for row in range(ROWS):
        for col in range(COLS):
            ch = problem.grid[row][col]
            rect = pygame.Rect(GRID_X + col * CELL, GRID_Y + row * CELL, CELL, CELL)

            if ch == "#":
                fill = WALL
            else:
                fill = SAND if ch == "S" else MUD if ch == "M" else FLOOR
                if (row, col) in explored_cells:
                    fill = blend(fill, EXPLORED, 0.45)
                if (row, col) in path_cells:
                    fill = blend(fill, PATH, 0.72)

            pygame.draw.rect(screen, fill, rect)
            if draw_lines:
                pygame.draw.rect(screen, GRID_LINE, rect, width=1)


    if len(path) > 1:
        points = [cell_center(s[0], s[1]) for s in path]
        pygame.draw.lines(screen, PATH_LINE, False, points, max(2, CELL // 8))

    radius = max(4, min(10, CELL // 2 - 1))

    start = cell_center(*cell_of(START))
    pygame.draw.circle(screen, GREEN, start, radius)
    pygame.draw.circle(screen, (255, 255, 255), start, radius, 2)

    goal = cell_center(*problem.exit_pos)
    pygame.draw.circle(screen, ORANGE, goal, radius)
    pygame.draw.circle(screen, (255, 255, 255), goal, radius, 2)

    if running_search and explored:
        current = cell_center(*cell_of(explored[-1]))
        r = max(3, radius - 3)
        pygame.draw.circle(screen, RED, current, r)
        pygame.draw.circle(screen, (255, 255, 255), current, r, 2)


def draw_legend():
    y = GRID_Y + GRID_H + 22
    entries = [
        ("dot", GREEN, "Start"),
        ("dot", ORANGE, "Goal"),
        ("dot", RED, "Current"),
        ("box", blend(FLOOR, EXPLORED, 0.5), "Explored"),
        ("box", PATH, "Path"),
        ("box", SAND, "Sand (3)"),
        ("box", MUD, "Mud (5)"),
    ]

    x = GRID_X
    limit = GRID_X + max(GRID_W, 480)
    for kind, color, label in entries:
        item_w = 20 + small.size(label)[0] + 22
        if x + item_w > limit and x != GRID_X:
            x = GRID_X
            y += 24
        if kind == "dot":
            pygame.draw.circle(screen, color, (x + 6, y + 8), 6)
        else:
            pygame.draw.rect(screen, color, (x, y + 2, 13, 13), border_radius=3)
            pygame.draw.rect(screen, GRID_LINE, (x, y + 2, 13, 13), 1, border_radius=3)
        draw_text(label, x + 20, y, MUTED, tiny)
        x += item_w


# ---------------------------------------------------------------------
# Header and right panel
# ---------------------------------------------------------------------

def draw_header():
    pygame.draw.rect(screen, CARD_BG, (0, 0, WIDTH, HEADER_H))
    pygame.draw.line(screen, BORDER, (0, HEADER_H - 1), (WIDTH, HEADER_H - 1), 1)

    draw_text("Treasure Hunt", MARGIN, 14, TEXT, title_font)
    draw_text("Search algorithm visualizer", MARGIN + 2, 52, MUTED, small)

    if running_search and paused:
        status, status_color = "Paused", ORANGE
    elif running_search:
        status, status_color = "Searching", BLUE
    elif search_finished and error_message:
        status, status_color = "Error", RED
    elif search_finished and path:
        status, status_color = "Goal reached", GREEN
    elif search_finished:
        status, status_color = "No solution", RED
    else:
        status, status_color = "Ready", MUTED

    label_w = small.size(status)[0]
    pill_w = label_w + 54
    pill = pygame.Rect(WIDTH - MARGIN - pill_w, 25, pill_w, 34)
    pygame.draw.rect(screen, NEUTRAL, pill, border_radius=17)
    pygame.draw.circle(screen, status_color, (pill.x + 18, pill.centery), 5)
    draw_text(status, pill.x + 32, pill.y + 8, TEXT, small)


def draw_right_panel():
    card(pygame.Rect(SIDE_X, SIDE_Y, SIDE_W, SIDE_H))

    # Algorithm selection
    draw_text("Algorithm", INNER_X, ALGO_LABEL_Y, TEXT, heading)
    for name, rect in ALGO_RECTS.items():
        if name == algorithm:
            button(name, rect, BLUE, (255, 255, 255))
        else:
            button(name, rect, NEUTRAL, TEXT)

    # Main controls
    button("Play", PLAY_RECT, GREEN, (255, 255, 255), enabled=not running_search)
    button("Resume" if paused else "Pause", PAUSE_RECT, ORANGE, (255, 255, 255),
           enabled=running_search)
    button("Reset", RESET_RECT, RED, (255, 255, 255))

    # Speed
    draw_text("Speed", INNER_X, SPEED_Y + 5, TEXT, heading)
    draw_text("events per frame", INNER_X + 66, SPEED_Y + 9, MUTED, tiny)
    button("-", MINUS_RECT, NEUTRAL)
    button("+", PLUS_RECT, NEUTRAL)
    value_rect = pygame.Rect(MINUS_RECT.right, SPEED_Y,
                             PLUS_RECT.x - MINUS_RECT.right, 32)
    draw_text_centered(steps_per_frame, value_rect, TEXT, button_font)

    separator(SEP_1)

    # Statistics
    draw_text("Search statistics", INNER_X, STATS_Y, TEXT, heading)
    metrics = [
        ("Expanded", f"{nodes_expanded:,}"),
        ("Generated", f"{nodes_generated:,}"),
        ("Frontier", f"{frontier_size:,}"),
        ("Max frontier", f"{max_frontier:,}"),
    ]

    tile_w = (INNER_W - GAP) // 2
    for index, (label, value) in enumerate(metrics):
        x = INNER_X + (index % 2) * (tile_w + GAP)
        y = TILE_Y + (index // 2) * (TILE_H + GAP)
        tile = pygame.Rect(x, y, tile_w, TILE_H)
        card(tile, TILE_BG, BORDER, 9)
        draw_text(label, x + 14, y + 8, MUTED, small)
        draw_text(value, x + 14, y + 28, TEXT, number_font)

    separator(SEP_2)

    # Solution
    draw_text("Solution", INNER_X, SOLUTION_Y, TEXT, heading)
    details = [
        ("Path length", max(len(path) - 1, 0)),
        ("Path cost", path_cost),
        ("Execution time", f"{execution_time * 1000:.3f} ms"),
        ("Visited cells", len(explored)),
    ]

    col_w = INNER_W // 2
    for index, (label, value) in enumerate(details):
        x = INNER_X + (index % 2) * col_w
        y = DETAILS_Y + (index // 2) * 28
        draw_text(label, x, y, MUTED, small)
        draw_text(value, x + 112, y, TEXT, small)

    # Result message
    if search_finished:
        msg_y = SIDE_Y + SIDE_H - 36
        if error_message:
            draw_text("Error: " + error_message[:55], INNER_X, msg_y, RED, small)
        elif path:
            draw_text("The exit has been reached.", INNER_X, msg_y, GREEN, small)
        else:
            draw_text("No route to the exit was found.", INNER_X, msg_y, RED, small)


# ---------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------

def main():
    global algorithm, paused, steps_per_frame

    running = True
    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos

                for name, rect in ALGO_RECTS.items():
                    if rect.collidepoint(pos) and name != algorithm:
                        algorithm = name
                        reset_search()

                if PLAY_RECT.collidepoint(pos) and not running_search:
                    start_search()
                elif PAUSE_RECT.collidepoint(pos) and running_search:
                    paused = not paused
                elif RESET_RECT.collidepoint(pos):
                    reset_search()
                elif MINUS_RECT.collidepoint(pos):
                    steps_per_frame = max(1, steps_per_frame - 1)
                elif PLUS_RECT.collidepoint(pos):
                    steps_per_frame = min(40, steps_per_frame + 1)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and running_search:
                    paused = not paused
                elif event.key == pygame.K_UP:
                    steps_per_frame = min(40, steps_per_frame + 1)
                elif event.key == pygame.K_DOWN:
                    steps_per_frame = max(1, steps_per_frame - 1)

        update_search()

        screen.fill(BG)
        draw_header()
        draw_maze()
        draw_legend()
        draw_right_panel()

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
"""
Game.py
Live Pygame visualisation of uninformed, heuristic, and local search algorithms on the
Treasure Hunt grid defined in problem.py.

Algorithms supported:
  1. Uninformed: BFS, DFS, UCS, IDS
  2. Heuristic: Greedy Best-First, A*
  3. Local Search: Hill Climbing, Simulated Annealing, Genetic Algorithm

The problem model (grid, actions, step costs, goal test) lives in problem.py,
so the animation and the experimental results use exactly the same problem.

UI: clean dark desktop-style dashboard (cards, status pill, stat tiles).
"""

import ctypes
import heapq
import math
import random
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

WIDTH, HEIGHT = 1200, 750
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
PURPLE = (157, 78, 221)
CYAN = (6, 214, 160)
DISABLED = (34, 39, 49)
DISABLED_TEXT = (90, 99, 114)
NEUTRAL = (38, 44, 55)
TILE_BG = (32, 38, 49)

FLOOR = (34, 40, 51)
SAND = (179, 139, 66)      # Sand - cost 3
MUD = (133, 91, 69)        # Mud  - cost 5
WALL = (10, 13, 18)
GRID_LINE = (46, 53, 66)
EXPLORED = (70, 130, 200)
PATH = (52, 190, 150)
PATH_LINE = (110, 236, 196)

pygame.init()
problem = TreasureHuntProblem()
ROWS, COLS = problem.rows, problem.cols

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Treasure Hunt - Multi-Algorithm Search Visualizer")
clock = pygame.time.Clock()

FONT_NAMES = "segoeui,helvetica,arial"
font = pygame.font.SysFont(FONT_NAMES, 16)
small = pygame.font.SysFont(FONT_NAMES, 14)
tiny = pygame.font.SysFont(FONT_NAMES, 12)
heading = pygame.font.SysFont(FONT_NAMES, 17, bold=True)
title_font = pygame.font.SysFont(FONT_NAMES, 26, bold=True)
number_font = pygame.font.SysFont(FONT_NAMES, 22, bold=True)
button_font = pygame.font.SysFont(FONT_NAMES, 14, bold=True)
algo_btn_font = pygame.font.SysFont(FONT_NAMES, 12, bold=True)

START = problem.get_initial_state()


# ---------------------------------------------------------------------
# Layout (everything is derived from a few numbers so nothing overlaps)
# ---------------------------------------------------------------------

HEADER_H = 80
MARGIN = 30
GRID_X = MARGIN
GRID_Y = HEADER_H + 24

PANEL_MIN_W = 400
CELL = max(
    4,
    min(
        40,
        (WIDTH - 2 * MARGIN - 40 - PANEL_MIN_W) // COLS,
        (HEIGHT - GRID_Y - 70) // ROWS,
    ),
)
GRID_W = COLS * CELL
GRID_H = ROWS * CELL

SIDE_X = GRID_X + GRID_W + 36
SIDE_Y = GRID_Y - 5
SIDE_W = WIDTH - SIDE_X - MARGIN
SIDE_H = HEIGHT - SIDE_Y - 25

PAD = 20
INNER_X = SIDE_X + PAD
INNER_W = SIDE_W - 2 * PAD
GAP = 8


def split_row(count, y, h, x=INNER_X, width=INNER_W, gap=GAP):
    """Split a row into `count` equal rectangles."""
    w = (width - gap * (count - 1)) // count
    return [pygame.Rect(x + i * (w + gap), y, w, h) for i in range(count)]


# Section 1: algorithm selector
ALGO_LABEL_Y = SIDE_Y + 14

UNINFORMED_NAMES = ["BFS", "DFS", "UCS", "IDS"]
HEURISTIC_NAMES = ["Greedy", "A*"]
LOCAL_NAMES = ["Hill Climbing", "Sim. Annealing", "Genetic Algo"]

UNINFORMED_RECTS = dict(zip(UNINFORMED_NAMES, split_row(4, SIDE_Y + 36, 26)))
HEURISTIC_RECTS = dict(zip(HEURISTIC_NAMES, split_row(2, SIDE_Y + 68, 26)))
LOCAL_RECTS = dict(zip(LOCAL_NAMES, split_row(3, SIDE_Y + 100, 26)))

ALGO_RECTS = {}
ALGO_RECTS.update(UNINFORMED_RECTS)
ALGO_RECTS.update(HEURISTIC_RECTS)
ALGO_RECTS.update(LOCAL_RECTS)

# Section 2: controls
PLAY_RECT, PAUSE_RECT, RESET_RECT = split_row(3, SIDE_Y + 138, 34)

# Section 3: speed
SPEED_Y = SIDE_Y + 182
RIGHT_EDGE = INNER_X + INNER_W
PLUS_RECT = pygame.Rect(RIGHT_EDGE - 30, SPEED_Y, 30, 28)
MINUS_RECT = pygame.Rect(RIGHT_EDGE - 110, SPEED_Y, 30, 28)

SEP_1 = SIDE_Y + 222
STATS_Y = SEP_1 + 12
TILE_H = 54
TILE_Y = STATS_Y + 28
SEP_2 = TILE_Y + 2 * TILE_H + GAP + 12
SOLUTION_Y = SEP_2 + 10
DETAILS_Y = SOLUTION_Y + 28


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


def h_manhattan(state):
    return abs(state[0] - problem.exit_pos[0]) + abs(state[1] - problem.exit_pos[1])


def emit(state):
    """Yield a frame only on the first visit to a cell (keeps visualizer smooth)."""
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


def prune_loops(path_states):
    """Eliminates loops/cycles from a state sequence."""
    seen = {}
    pruned = []
    for s in path_states:
        coord = cell_of(s)
        if coord in seen:
            idx = seen[coord]
            for removed in pruned[idx + 1:]:
                rem_c = cell_of(removed)
                if rem_c in seen and seen[rem_c] > idx:
                    del seen[rem_c]
            pruned = pruned[:idx + 1]
        else:
            seen[coord] = len(pruned)
            pruned.append(s)
    return pruned


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


def greedy():
    """Greedy Best-First Search visualizer generator."""
    global nodes_expanded, nodes_generated, frontier_size, max_frontier

    counter = 0
    frontier = [(h_manhattan(START), counter, START)]
    parent = {}
    visited = {START}
    nodes_generated = 1

    while frontier:
        frontier_size = len(frontier)
        max_frontier = max(max_frontier, frontier_size)
        _h_val, _, current = heapq.heappop(frontier)
        nodes_expanded += 1

        if emit(current):
            explored.append(current)
            yield current

        if problem.is_goal(current):
            return reconstruct_path(parent, current)

        for _action, nxt, _step_cost in problem.get_successors(current):
            nodes_generated += 1
            if nxt not in visited:
                visited.add(nxt)
                parent[nxt] = current
                counter += 1
                heapq.heappush(frontier, (h_manhattan(nxt), counter, nxt))

    return []


def astar():
    """A* Search visualizer generator."""
    global nodes_expanded, nodes_generated, frontier_size, max_frontier

    counter = 0
    frontier = [(h_manhattan(START), counter, 0, START)]
    parent = {}
    best_g = {START: 0}
    nodes_generated = 1

    while frontier:
        frontier_size = len(frontier)
        max_frontier = max(max_frontier, frontier_size)
        f_cost, _, g_cost, current = heapq.heappop(frontier)

        if g_cost > best_g.get(current, float("inf")):
            continue

        nodes_expanded += 1
        if emit(current):
            explored.append(current)
            yield current

        if problem.is_goal(current):
            return reconstruct_path(parent, current)

        for _action, nxt, step_cost in problem.get_successors(current):
            nodes_generated += 1
            new_g = g_cost + step_cost
            if new_g < best_g.get(nxt, float("inf")):
                best_g[nxt] = new_g
                parent[nxt] = current
                counter += 1
                f_score = new_g + h_manhattan(nxt)
                heapq.heappush(frontier, (f_score, counter, new_g, nxt))

    return []


def hill_climbing():
    """Hill Climbing with Random Restarts visualizer generator."""
    global nodes_expanded, nodes_generated, frontier_size, max_frontier

    frontier_size = 1
    max_frontier = 1
    random.seed(42)

    for restart in range(50):
        curr = START
        run_path = [curr]
        run_visited = {curr}

        if emit(curr):
            explored.append(curr)
            yield curr

        while True:
            nodes_expanded += 1
            if problem.is_goal(curr):
                return run_path

            successors = problem.get_successors(curr)
            nodes_generated += len(successors)
            valid = [item for item in successors if item[1] not in run_visited]
            if not valid:
                break

            min_h = min(h_manhattan(item[1]) for item in valid)
            if min_h > h_manhattan(curr):
                # Local minimum trapped
                break

            candidates = [item[1] for item in valid if h_manhattan(item[1]) == min_h]
            nxt = random.choice(candidates) if len(candidates) > 1 and restart > 0 else candidates[0]

            curr = nxt
            run_visited.add(curr)
            run_path.append(curr)

            if emit(curr):
                explored.append(curr)
                yield curr

            if problem.is_goal(curr):
                return run_path

    return []


def simulated_annealing():
    """Simulated Annealing visualizer generator."""
    global nodes_expanded, nodes_generated, frontier_size, max_frontier

    curr = START
    path_seq = [curr]
    T = 30.0
    alpha = 0.9992
    t_min = 1e-4
    frontier_size = 1
    max_frontier = 1
    random.seed(42)

    if emit(curr):
        explored.append(curr)
        yield curr

    for _ in range(25000):
        nodes_expanded += 1
        if problem.is_goal(curr):
            return prune_loops(path_seq)

        successors = problem.get_successors(curr)
        nodes_generated += len(successors)
        if not successors:
            break

        _act, nxt, _cost = random.choice(successors)
        delta = h_manhattan(nxt) - h_manhattan(curr)

        if delta <= 0 or (T > t_min and random.random() < math.exp(-delta / T)):
            curr = nxt
            path_seq.append(curr)
            if emit(curr):
                explored.append(curr)
                yield curr

        T = max(t_min, T * alpha)

    return prune_loops(path_seq)


def genetic_algo():
    """Genetic Algorithm generation-by-generation visualizer generator."""
    global nodes_expanded, nodes_generated, frontier_size, max_frontier

    random.seed(42)
    pop_size = 60
    generations = 120
    chrom_len = 140
    mutation_rate = 0.20

    actions = ["UP", "DOWN", "LEFT", "RIGHT"]
    act_map = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}

    frontier_size = pop_size
    max_frontier = pop_size

    def simulate(chrom):
        r, c = problem.start_pos
        st = [(r, c, 0, 0)]
        for act in chrom:
            dr, dc = act_map[act]
            nr, nc = r + dr, c + dc
            if 0 <= nr < problem.rows and 0 <= nc < problem.cols and problem.grid[nr][nc] != "#":
                r, c = nr, nc
                st.append((r, c, 0, 0))
                if (r, c) == problem.exit_pos:
                    return True, st
        return False, st

    def fitness(chrom):
        reached, st = simulate(chrom)
        d = abs(st[-1][0] - problem.exit_pos[0]) + abs(st[-1][1] - problem.exit_pos[1])
        if reached:
            return 100000.0 - len(st)
        return 1000.0 / (1.0 + d)

    def make_ind():
        curr = problem.get_initial_state()
        chrom = []
        for _ in range(chrom_len):
            succs = problem.get_successors(curr)
            if not succs:
                chrom.append(random.choice(actions))
                continue
            weights = [2.5 if a in ("DOWN", "RIGHT") else 0.8 for a, _s, _c in succs]
            chosen = random.choices(succs, weights=weights)[0]
            chrom.append(chosen[0])
            curr = chosen[1]
            if problem.is_goal(curr):
                break
        while len(chrom) < chrom_len:
            chrom.append(random.choice(["DOWN", "RIGHT", "UP", "LEFT"]))
        return chrom

    population = [make_ind() for _ in range(pop_size)]
    nodes_generated = pop_size

    best_chrom = None
    best_fit = -1

    for gen in range(generations):
        nodes_expanded += 1
        fits = [fitness(ind) for ind in population]

        for ind, fit in zip(population, fits):
            if fit > best_fit:
                best_fit = fit
                best_chrom = ind

        reached, best_states = simulate(best_chrom)

        for s in best_states:
            if emit(s):
                explored.append(s)
                yield s

        if reached:
            return prune_loops(best_states)

        new_pop = [best_chrom]
        while len(new_pop) < pop_size:
            p1 = max(random.sample(list(zip(population, fits)), 3), key=lambda x: x[1])[0]
            p2 = max(random.sample(list(zip(population, fits)), 3), key=lambda x: x[1])[0]
            pt = random.randint(1, chrom_len - 1)
            child = p1[:pt] + p2[pt:]
            if random.random() < mutation_rate:
                m_idx = random.randint(0, chrom_len - 1)
                child[m_idx] = random.choice(actions)
            new_pop.append(child)
            nodes_generated += 1
        population = new_pop

    _, final_states = simulate(best_chrom)
    return prune_loops(final_states)


ALGORITHMS = {
    "BFS": bfs,
    "DFS": dfs,
    "UCS": ucs,
    "IDS": ids,
    "Greedy": greedy,
    "A*": astar,
    "Hill Climbing": hill_climbing,
    "Sim. Annealing": simulated_annealing,
    "Genetic Algo": genetic_algo,
}


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


def card(rect, fill=CARD_BG, outline=BORDER, radius=10):
    pygame.draw.rect(screen, fill, rect, border_radius=radius)
    pygame.draw.rect(screen, outline, rect, width=1, border_radius=radius)


def button(label, rect, fill, text_color=TEXT, enabled=True, face=button_font):
    if not enabled:
        fill, text_color = DISABLED, DISABLED_TEXT
    pygame.draw.rect(screen, fill, rect, border_radius=6)
    draw_text_centered(label, rect, text_color, face)


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
    y = GRID_Y + GRID_H + 18
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
        item_w = 20 + small.size(label)[0] + 18
        if x + item_w > limit and x != GRID_X:
            x = GRID_X
            y += 22
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

    draw_text("Treasure Hunt", MARGIN, 12, TEXT, title_font)
    draw_text("Uninformed, Heuristic & Local Search Visualizer", MARGIN + 2, 46, MUTED, small)

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
    pill_w = label_w + 50
    pill = pygame.Rect(WIDTH - MARGIN - pill_w, 22, pill_w, 32)
    pygame.draw.rect(screen, NEUTRAL, pill, border_radius=16)
    pygame.draw.circle(screen, status_color, (pill.x + 16, pill.centery), 5)
    draw_text(status, pill.x + 28, pill.y + 7, TEXT, small)


def draw_right_panel():
    card(pygame.Rect(SIDE_X, SIDE_Y, SIDE_W, SIDE_H))

    # Section 1: Algorithm selection
    draw_text("Search Algorithm", INNER_X, ALGO_LABEL_Y, TEXT, heading)

    for name, rect in ALGO_RECTS.items():
        if name == algorithm:
            color = CYAN if name in HEURISTIC_NAMES else (PURPLE if name in LOCAL_NAMES else BLUE)
            button(name, rect, color, (255, 255, 255), face=algo_btn_font)
        else:
            button(name, rect, NEUTRAL, TEXT, face=algo_btn_font)

    # Section 2: Main controls
    button("Play", PLAY_RECT, GREEN, (255, 255, 255), enabled=not running_search)
    button("Resume" if paused else "Pause", PAUSE_RECT, ORANGE, (255, 255, 255), enabled=running_search)
    button("Reset", RESET_RECT, RED, (255, 255, 255))

    # Section 3: Speed control
    draw_text("Speed", INNER_X, SPEED_Y + 4, TEXT, heading)
    draw_text("steps/frame", INNER_X + 62, SPEED_Y + 7, MUTED, tiny)
    button("-", MINUS_RECT, NEUTRAL)
    button("+", PLUS_RECT, NEUTRAL)
    value_rect = pygame.Rect(MINUS_RECT.right, SPEED_Y, PLUS_RECT.x - MINUS_RECT.right, 28)
    draw_text_centered(steps_per_frame, value_rect, TEXT, button_font)

    separator(SEP_1)

    # Section 4: Statistics
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
        card(tile, TILE_BG, BORDER, 8)
        draw_text(label, x + 12, y + 6, MUTED, tiny)
        draw_text(value, x + 12, y + 24, TEXT, number_font)

    separator(SEP_2)

    # Section 5: Solution
    draw_text("Solution", INNER_X, SOLUTION_Y, TEXT, heading)
    details = [
        ("Path length", max(len(path) - 1, 0)),
        ("Path cost", path_cost),
        ("Execution time", f"{execution_time * 1000:.2f} ms"),
        ("Visited cells", len(explored)),
    ]

    col_w = INNER_W // 2
    for index, (label, value) in enumerate(details):
        x = INNER_X + (index % 2) * col_w
        y = DETAILS_Y + (index // 2) * 24
        draw_text(label, x, y, MUTED, tiny)
        draw_text(value, x + 105, y, TEXT, small)

    # Result message
    if search_finished:
        msg_y = SIDE_Y + SIDE_H - 30
        if error_message:
            draw_text("Error: " + error_message[:45], INNER_X, msg_y, RED, small)
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

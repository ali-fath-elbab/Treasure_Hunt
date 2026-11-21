"""
Game.py
Live Pygame visualisation of uninformed, heuristic, and local search algorithms on the
Treasure Hunt grid defined in problem.py.

Algorithms supported:
  1. Uninformed: BFS, DFS, UCS, IDS
  2. Heuristic: Greedy Best-First, A*
  3. Local Search: Hill Climbing, Simulated Annealing, Genetic Algorithm

Features:
  - Custom image support: drop your own PNG into assets/agent.png (or agent.png)
    and assets/goal.png (or goal.png).
  - Animated walk: after a solution path is found, the agent icon/sprite smoothly
    walks along the entire path to the goal.
  - Replay walk button: click "Walk" anytime to replay the agent traversing the path.

UI: clean dark desktop-style dashboard (cards, status pill, stat tiles).
"""

import ctypes
import heapq
import math
import os
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
button_font = pygame.font.SysFont(FONT_NAMES, 13, bold=True)
algo_btn_font = pygame.font.SysFont(FONT_NAMES, 12, bold=True)

START = problem.get_initial_state()


# ---------------------------------------------------------------------
# Layout (derived from window dimensions)
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

# Section 2: controls (Play, Pause, Walk, Reset)
PLAY_RECT, PAUSE_RECT, WALK_RECT, RESET_RECT = split_row(4, SIDE_Y + 138, 34)

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
# Sprites & Custom Image Loader
# ---------------------------------------------------------------------

AGENT_CANDIDATES = [
    "assets/agent.png",
    "assets/player.png",
    "assets/character.png",
    "assets/icon.png",
    "agent.png",
    "player.png",
    "character.png",
]

GOAL_CANDIDATES = [
    "assets/goal.png",
    "assets/treasure.png",
    "assets/exit.png",
    "goal.png",
    "treasure.png",
    "exit.png",
]

agent_sprite = None
goal_sprite = None
agent_mini = None
goal_mini = None


def load_sprite(candidates, size):
    """Loads and smoothly scales the first found candidate image."""
    for path_str in candidates:
        if os.path.isfile(path_str):
            try:
                surf = pygame.image.load(path_str).convert_alpha()
                return pygame.transform.smoothscale(surf, size)
            except Exception as e:
                print(f"Error loading image {path_str}: {e}")
    return None


def reload_sprites():
    global agent_sprite, goal_sprite, agent_mini, goal_mini
    size = (max(8, CELL), max(8, CELL))
    agent_sprite = load_sprite(AGENT_CANDIDATES, size)
    goal_sprite = load_sprite(GOAL_CANDIDATES, size)
    if agent_sprite:
        agent_mini = pygame.transform.smoothscale(agent_sprite, (14, 14))
    if goal_sprite:
        goal_mini = pygame.transform.smoothscale(goal_sprite, (14, 14))


reload_sprites()


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

# Animated walk state
agent_walking = False
agent_path_index = 0
walk_progress = 0.0

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
    """Yield a frame only on the first visit to a cell."""
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
    global agent_walking, agent_path_index, walk_progress

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
    agent_walking = False
    agent_path_index = 0
    walk_progress = 0.0


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
    global agent_walking, agent_path_index, walk_progress

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

            # Automatically start walking along the discovered path to the goal
            if path:
                agent_walking = True
                agent_path_index = 0
                walk_progress = 0.0
            break
        except Exception as exc:
            error_message = str(exc)
            search_finished = True
            running_search = False
            break


def update_agent_walk():
    """Smoothly moves the agent icon/sprite along the path to the exit."""
    global agent_walking, agent_path_index, walk_progress

    if not agent_walking or paused or not path or len(path) <= 1:
        return

    # Walking speed scales with the user speed setting
    speed = max(0.15, min(1.2, steps_per_frame * 0.10))
    walk_progress += speed

    if walk_progress >= 1.0:
        advance = int(walk_progress)
        agent_path_index = min(len(path) - 1, agent_path_index + advance)
        walk_progress -= advance

        if agent_path_index >= len(path) - 1:
            agent_walking = False
            walk_progress = 0.0


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
# Maze & Character rendering
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

    # 1. Goal (Custom sprite or glowing star/circle)
    goal_center = cell_center(*problem.exit_pos)
    if goal_sprite:
        screen.blit(
            goal_sprite,
            (GRID_X + problem.exit_pos[1] * CELL, GRID_Y + problem.exit_pos[0] * CELL),
        )
    else:
        pygame.draw.circle(screen, ORANGE, goal_center, radius)
        pygame.draw.circle(screen, (255, 255, 255), goal_center, radius, 2)

    # 2. Start marker (always visible)
    start_center = cell_center(*cell_of(START))
    pygame.draw.circle(screen, GREEN, start_center, max(3, radius - 2))
    pygame.draw.circle(screen, (255, 255, 255), start_center, max(3, radius - 2), 1)

    # 3. Determine Agent Position (during idle, exploring, or walking along path)
    if path:
        if agent_walking and len(path) > 1 and agent_path_index < len(path) - 1:
            s0 = path[agent_path_index]
            s1 = path[agent_path_index + 1]
            r = s0[0] + (s1[0] - s0[0]) * walk_progress
            c = s0[1] + (s1[1] - s0[1]) * walk_progress
            agent_cx = GRID_X + c * CELL + CELL / 2.0
            agent_cy = GRID_Y + r * CELL + CELL / 2.0
        else:
            target_idx = min(agent_path_index, len(path) - 1)
            agent_cx, agent_cy = cell_center(*cell_of(path[target_idx]))
    elif running_search and explored:
        # During exploration: the agent sprite IS the active explorer traversing the maze
        agent_cx, agent_cy = cell_center(*cell_of(explored[-1]))
    else:
        # Idle at start
        agent_cx, agent_cy = cell_center(*cell_of(START))

    # 4. Render the Agent (Image sprite ALWAYS takes priority over the icon!)
    if agent_sprite:
        screen.blit(
            agent_sprite,
            (int(agent_cx - CELL / 2.0), int(agent_cy - CELL / 2.0)),
        )
    else:
        color = RED if running_search else CYAN
        pygame.draw.circle(screen, color, (int(agent_cx), int(agent_cy)), radius)
        pygame.draw.circle(screen, (255, 255, 255), (int(agent_cx), int(agent_cy)), radius, 2)


def draw_legend():
    y = GRID_Y + GRID_H + 18
    entries = [
        ("agent", CYAN, "Agent"),
        ("goal", ORANGE, "Goal"),
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

        if kind == "agent" and agent_mini:
            screen.blit(agent_mini, (x, y + 1))
        elif kind == "goal" and goal_mini:
            screen.blit(goal_mini, (x, y + 1))
        elif kind in ("agent", "goal"):
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

    if agent_walking:
        status, status_color = "Walking to Goal", CYAN
    elif running_search and paused:
        status, status_color = "Paused", ORANGE
    elif running_search:
        status, status_color = "Searching", BLUE
    elif search_finished and error_message:
        status, status_color = "Error", RED
    elif search_finished and path and agent_path_index >= len(path) - 1:
        status, status_color = "Goal Reached!", GREEN
    elif search_finished and path:
        status, status_color = "Path Found", GREEN
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

    # Section 2: Main controls (Play, Pause, Walk, Reset)
    button("Play", PLAY_RECT, GREEN, (255, 255, 255), enabled=not running_search)
    button("Resume" if paused else "Pause", PAUSE_RECT, ORANGE, (255, 255, 255),
           enabled=(running_search or agent_walking))
    button("Walk", WALK_RECT, CYAN, (255, 255, 255), enabled=(bool(path) and not running_search))
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
        elif agent_walking:
            draw_text("Agent walking along path...", INNER_X, msg_y, CYAN, small)
        elif path:
            draw_text("The exit has been reached.", INNER_X, msg_y, GREEN, small)
        else:
            draw_text("No route to the exit was found.", INNER_X, msg_y, RED, small)


# ---------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------

def main():
    global algorithm, paused, steps_per_frame
    global agent_walking, agent_path_index, walk_progress

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
                elif PAUSE_RECT.collidepoint(pos) and (running_search or agent_walking):
                    paused = not paused
                elif WALK_RECT.collidepoint(pos) and path:
                    agent_walking = True
                    agent_path_index = 0
                    walk_progress = 0.0
                    paused = False
                elif RESET_RECT.collidepoint(pos):
                    reset_search()
                elif MINUS_RECT.collidepoint(pos):
                    steps_per_frame = max(1, steps_per_frame - 1)
                elif PLUS_RECT.collidepoint(pos):
                    steps_per_frame = min(40, steps_per_frame + 1)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if running_search or agent_walking:
                        paused = not paused
                elif event.key in (pygame.K_w, pygame.K_RETURN) and path and not running_search:
                    agent_walking = True
                    agent_path_index = 0
                    walk_progress = 0.0
                    paused = False
                elif event.key == pygame.K_UP:
                    steps_per_frame = min(40, steps_per_frame + 1)
                elif event.key == pygame.K_DOWN:
                    steps_per_frame = max(1, steps_per_frame - 1)

        update_search()
        update_agent_walk()

        screen.fill(BG)
        draw_header()
        draw_maze()
        draw_legend()
        draw_right_panel()

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()

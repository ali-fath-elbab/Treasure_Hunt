"""
Game.py
Clean desktop-style Treasure Hunt search visualizer.
Uses the existing problem.py and uninformed.py implementations.
"""

import ctypes
import queue
import sys
import threading

import pygame

from problem import TreasureHuntProblem
from uninformed import bfs, dfs, ucs, ids

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
SAND = (179, 139, 66)      # Sand - Cost 3
MUD = (133, 91, 69)        # Mud - Cost 5
WALL = (10, 13, 18)
GRID_LINE = (46, 53, 66)
EXPLORED = (70, 130, 200)
PATH = (52, 190, 150)
PATH_LINE = (110, 236, 196)

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

pygame.init()
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


# ---------------------------------------------------------------------
# Project state
# ---------------------------------------------------------------------

problem = TreasureHuntProblem()
selected_algorithm = "BFS"
events = queue.Queue()

running_search = False
paused = False
finished = False
error_message = None

visited_counts = {}
current_state = problem.get_initial_state()
solution_states = []
solution_actions = []

nodes_expanded = 0
nodes_generated = 0
frontier_size = 0
max_frontier_size = 0
path_cost = 0
execution_time_ms = 0.0

speed = 3


# ---------------------------------------------------------------------
# Layout (everything is derived from a few numbers so nothing overlaps)
# ---------------------------------------------------------------------

HEADER_H = 84
MARGIN = 32
CELL = 40

GRID_X = MARGIN
GRID_Y = HEADER_H + 26
GRID_W = problem.cols * CELL
GRID_H = problem.rows * CELL

SIDE_X = GRID_X + GRID_W + 40
SIDE_Y = GRID_Y - 5
SIDE_W = WIDTH - SIDE_X - MARGIN
SIDE_H = GRID_H + 10

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
algo_rects = split_row(4, SIDE_Y + 54, 38)
ALGO_RECTS = dict(zip(ALGORITHMS.keys(), algo_rects))

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
# Search functions
# ---------------------------------------------------------------------

def clear_search_display():
    global paused, finished, error_message
    global current_state, solution_states, solution_actions
    global nodes_expanded, nodes_generated, frontier_size
    global max_frontier_size, path_cost, execution_time_ms

    if running_search:
        return

    while True:
        try:
            events.get_nowait()
        except queue.Empty:
            break

    visited_counts.clear()
    current_state = problem.get_initial_state()
    solution_states = []
    solution_actions = []
    nodes_expanded = 0
    nodes_generated = 0
    frontier_size = 0
    max_frontier_size = 0
    path_cost = 0
    execution_time_ms = 0.0
    paused = False
    finished = False
    error_message = None


def start_search():
    global running_search, paused, finished, error_message

    if running_search:
        return

    clear_search_display()
    paused = False
    finished = False
    error_message = None
    running_search = True

    algorithm = ALGORITHMS[selected_algorithm]

    def trace(state, expanded_count, current_frontier):
        events.put(("visit", state, expanded_count, current_frontier))

    def worker():
        try:
            result = algorithm(problem, trace=trace)
            events.put(("done", result))
        except Exception as exc:
            events.put(("error", str(exc)))

    threading.Thread(target=worker, daemon=True).start()


def update_search():
    global current_state, nodes_expanded, frontier_size
    global nodes_generated, max_frontier_size, path_cost
    global execution_time_ms, solution_states, solution_actions
    global running_search, finished, error_message

    if paused:
        return

    for _ in range(speed):
        try:
            item = events.get_nowait()
        except queue.Empty:
            break

        if item[0] == "visit":
            _, state, expanded, frontier = item
            current_state = state
            nodes_expanded = expanded
            frontier_size = frontier
            position = (state[0], state[1])
            visited_counts[position] = visited_counts.get(position, 0) + 1
            max_frontier_size = max(max_frontier_size, frontier_size)

        elif item[0] == "done":
            result = item[1]
            running_search = False
            finished = True
            nodes_generated = result["nodes_generated"]
            nodes_expanded = result["nodes_expanded"]
            max_frontier_size = result["max_frontier_size"]
            path_cost = result["path_cost"]
            execution_time_ms = result["execution_time_ms"]
            solution_states = result["path_states"]
            solution_actions = result["path_actions"]
            if solution_states:
                current_state = solution_states[-1]

        elif item[0] == "error":
            error_message = item[1]
            running_search = False
            finished = True


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
    path_cells = {(s[0], s[1]) for s in solution_states}

    outer = pygame.Rect(GRID_X - 5, GRID_Y - 5, GRID_W + 10, GRID_H + 10)
    card(outer, CARD_BG, BORDER, 8)

    for row in range(problem.rows):
        for col in range(problem.cols):
            cell_value = problem.grid[row][col]
            rect = pygame.Rect(GRID_X + col * CELL, GRID_Y + row * CELL, CELL, CELL)

            fill = TERRAIN_COLORS.get(cell_value, FLOOR)

            if (row, col) in visited_counts and cell_value != "#":
                count = visited_counts[(row, col)]
                fill = blend(fill, EXPLORED, min(0.62, 0.22 + count * 0.035))

            if (row, col) in path_cells and cell_value not in {"P", "E"}:
                fill = blend(fill, PATH, 0.72)

            pygame.draw.rect(screen, fill, rect)
            pygame.draw.rect(screen, GRID_LINE, rect, width=1)

            if cell_value in ("K", "D"):
                draw_text_centered(cell_value, rect, MUTED, small)

    if len(solution_states) > 1:
        points = [cell_center(s[0], s[1]) for s in solution_states]
        pygame.draw.lines(screen, PATH_LINE, False, points, 3)

    start = cell_center(*problem.start_pos)
    pygame.draw.circle(screen, GREEN, start, 10)
    pygame.draw.circle(screen, (255, 255, 255), start, 10, 2)

    goal = cell_center(*problem.exit_pos)
    pygame.draw.circle(screen, ORANGE, goal, 10)
    pygame.draw.circle(screen, (255, 255, 255), goal, 10, 2)

    if running_search and current_state is not None:
        current = cell_center(current_state[0], current_state[1])
        pygame.draw.circle(screen, RED, current, 7)
        pygame.draw.circle(screen, (255, 255, 255), current, 7, 2)


def draw_legend():
    y = GRID_Y + GRID_H + 22
    entries = [
        ("dot", GREEN, "Start"),
        ("dot", ORANGE, "Goal"),
        ("dot", RED, "Current"),
        ("box", blend(FLOOR, EXPLORED, 0.5), "Explored"),
        ("box", PATH, "Path"),
    ]

    x = GRID_X
    for kind, color, label in entries:
        if kind == "dot":
            pygame.draw.circle(screen, color, (x + 6, y + 8), 6)
        else:
            pygame.draw.rect(screen, color, (x, y + 2, 13, 13), border_radius=3)
            pygame.draw.rect(screen, GRID_LINE, (x, y + 2, 13, 13), 1, border_radius=3)
        width = draw_text(label, x + 20, y, MUTED, tiny)
        x += 20 + width + 22


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
    elif finished and error_message:
        status, status_color = "Error", RED
    elif finished and solution_states:
        status, status_color = "Goal reached", GREEN
    elif finished:
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
        if name == selected_algorithm:
            button(name, rect, BLUE, (255, 255, 255), enabled=True)
            if running_search:
                pass
        else:
            button(name, rect, NEUTRAL, TEXT, enabled=not running_search)

    # Main controls
    button("Play", PLAY_RECT, GREEN, (255, 255, 255), enabled=not running_search)
    button("Resume" if paused else "Pause", PAUSE_RECT, ORANGE, (255, 255, 255),
           enabled=running_search)
    button("Reset", RESET_RECT, RED, (255, 255, 255), enabled=not running_search)

    # Speed
    draw_text("Speed", INNER_X, SPEED_Y + 5, TEXT, heading)
    draw_text("events per frame", INNER_X + 66, SPEED_Y + 9, MUTED, tiny)
    button("-", MINUS_RECT, NEUTRAL)
    button("+", PLUS_RECT, NEUTRAL)
    value_rect = pygame.Rect(MINUS_RECT.right, SPEED_Y, PLUS_RECT.x - MINUS_RECT.right, 32)
    draw_text_centered(speed, value_rect, TEXT, button_font)

    separator(SEP_1)

    # Statistics
    draw_text("Search statistics", INNER_X, STATS_Y, TEXT, heading)
    metrics = [
        ("Expanded", nodes_expanded),
        ("Generated", nodes_generated),
        ("Frontier", frontier_size),
        ("Max frontier", max_frontier_size),
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
        ("Path length", len(solution_actions)),
        ("Path cost", path_cost),
        ("Execution time", f"{execution_time_ms:.3f} ms"),
        ("Visited cells", len(visited_counts)),
    ]

    col_w = INNER_W // 2
    for index, (label, value) in enumerate(details):
        x = INNER_X + (index % 2) * col_w
        y = DETAILS_Y + (index // 2) * 28
        draw_text(label, x, y, MUTED, small)
        draw_text(value, x + 112, y, TEXT, small)

    # Result message
    if finished:
        msg_y = SIDE_Y + SIDE_H - 36
        if error_message:
            draw_text("Error: " + error_message[:55], INNER_X, msg_y, RED, small)
        elif solution_states:
            draw_text("The exit has been reached.", INNER_X, msg_y, GREEN, small)
        else:
            draw_text("No route to the exit was found.", INNER_X, msg_y, RED, small)


# ---------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------

def main():
    global selected_algorithm, paused, speed

    running = True
    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos

                if not running_search:
                    for name, rect in ALGO_RECTS.items():
                        if rect.collidepoint(pos):
                            selected_algorithm = name
                            clear_search_display()

                if PLAY_RECT.collidepoint(pos):
                    start_search()
                elif PAUSE_RECT.collidepoint(pos) and running_search:
                    paused = not paused
                elif RESET_RECT.collidepoint(pos):
                    clear_search_display()
                elif MINUS_RECT.collidepoint(pos):
                    speed = max(1, speed - 1)
                elif PLUS_RECT.collidepoint(pos):
                    speed = min(40, speed + 1)

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
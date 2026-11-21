"""
informed.py
From-scratch implementations of heuristic (informed) search algorithms:
Greedy Best-First Search (GBFS) and A* Search.

Heuristic functions:
    manhattan_distance(state, goal_pos)
    euclidean_distance(state, goal_pos)

Interface matches uninformed.py:
    get_initial_state()
    is_goal(state)
    get_successors(state)

Optional trace callback:
    trace(state, expanded_count, frontier_size)
"""

import heapq
import math
import time


def manhattan_distance(state, goal_pos):
    """
    Manhattan distance heuristic h(n) = |r - r_goal| + |c - c_goal|.
    Admissible and consistent on a 4-connected grid world with min step cost >= 1.
    """
    r, c = state[0], state[1]
    gr, gc = goal_pos[0], goal_pos[1]
    return abs(r - gr) + abs(c - gc)


def euclidean_distance(state, goal_pos):
    """
    Euclidean distance heuristic h(n) = sqrt((r - gr)^2 + (c - gc)^2).
    Admissible and consistent since Euclidean distance <= Manhattan distance <= true cost.
    """
    r, c = state[0], state[1]
    gr, gc = goal_pos[0], goal_pos[1]
    return math.hypot(r - gr, c - gc)


def _build_result(
    algorithm,
    found,
    path_actions,
    path_states,
    path_cost,
    nodes_generated,
    nodes_expanded,
    max_frontier_size,
    start_time,
    visited_coords,
):
    """Build a standardized result dictionary matching uninformed.py."""
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    return {
        "algorithm": algorithm,
        "found": found,
        "path_actions": path_actions,
        "path_states": path_states,
        "path_cost": path_cost,
        "nodes_generated": nodes_generated,
        "nodes_expanded": nodes_expanded,
        "max_frontier_size": max_frontier_size,
        "execution_time_ms": elapsed_ms,
        "visited_coords": visited_coords,
    }


def greedy_best_first(problem, heuristic=None, trace=None):
    """
    Greedy Best-First Search (GBFS).
    Expands the node with the lowest heuristic value h(n) to the goal.
    Evaluation function: f(n) = h(n).
    Fast and goal-directed, but neither complete on infinite graphs nor cost-optimal.
    """
    if heuristic is None:
        heuristic = lambda s: manhattan_distance(s, problem.exit_pos)

    start_time = time.perf_counter()
    initial_state = problem.get_initial_state()

    counter = 0
    # Priority queue item: (h(state), counter, state, actions, states, cost)
    frontier = [(heuristic(initial_state), counter, initial_state, [], [initial_state], 0)]
    visited = {initial_state}
    visited_coords = {}

    nodes_generated = 1
    nodes_expanded = 0
    max_frontier_size = 1

    while frontier:
        max_frontier_size = max(max_frontier_size, len(frontier))
        _h_val, _tie, state, actions, states, cost = heapq.heappop(frontier)
        nodes_expanded += 1

        coord = (state[0], state[1])
        visited_coords[coord] = visited_coords.get(coord, 0) + 1

        if trace is not None:
            trace(state, nodes_expanded, len(frontier))

        if problem.is_goal(state):
            return _build_result(
                "Greedy Best-First", True, actions, states, cost,
                nodes_generated, nodes_expanded, max_frontier_size,
                start_time, visited_coords
            )

        for action, next_state, step_cost in problem.get_successors(state):
            nodes_generated += 1

            if next_state not in visited:
                visited.add(next_state)
                counter += 1
                heapq.heappush(
                    frontier,
                    (
                        heuristic(next_state),
                        counter,
                        next_state,
                        actions + [action],
                        states + [next_state],
                        cost + step_cost,
                    ),
                )

    return _build_result(
        "Greedy Best-First", False, [], [], 0,
        nodes_generated, nodes_expanded, max_frontier_size,
        start_time, visited_coords
    )


def astar(problem, heuristic=None, trace=None):
    """
    A* Search.
    Evaluation function: f(n) = g(n) + h(n), where:
        g(n) is the exact cost from the start state to node n,
        h(n) is the estimated cost from node n to the goal.
    With an admissible and consistent heuristic (like Manhattan distance),
    A* is complete and strictly cost-optimal.
    """
    if heuristic is None:
        heuristic = lambda s: manhattan_distance(s, problem.exit_pos)

    start_time = time.perf_counter()
    initial_state = problem.get_initial_state()

    counter = 0
    h_start = heuristic(initial_state)
    # Priority queue item: (f_score, counter, g_score, state, actions, states)
    frontier = [(h_start, counter, 0, initial_state, [], [initial_state])]
    best_g = {initial_state: 0}
    visited_coords = {}

    nodes_generated = 1
    nodes_expanded = 0
    max_frontier_size = 1

    while frontier:
        max_frontier_size = max(max_frontier_size, len(frontier))
        f_cost, _tie, g_cost, state, actions, states = heapq.heappop(frontier)

        # Ignore outdated entries with higher path cost than known best
        if g_cost > best_g.get(state, float("inf")):
            continue

        nodes_expanded += 1
        coord = (state[0], state[1])
        visited_coords[coord] = visited_coords.get(coord, 0) + 1

        if trace is not None:
            trace(state, nodes_expanded, len(frontier))

        if problem.is_goal(state):
            return _build_result(
                "A*", True, actions, states, g_cost,
                nodes_generated, nodes_expanded, max_frontier_size,
                start_time, visited_coords
            )

        for action, next_state, step_cost in problem.get_successors(state):
            nodes_generated += 1
            new_g = g_cost + step_cost

            if new_g < best_g.get(next_state, float("inf")):
                best_g[next_state] = new_g
                counter += 1
                f_score = new_g + heuristic(next_state)
                heapq.heappush(
                    frontier,
                    (
                        f_score,
                        counter,
                        new_g,
                        next_state,
                        actions + [action],
                        states + [next_state],
                    ),
                )

    return _build_result(
        "A*", False, [], [], 0,
        nodes_generated, nodes_expanded, max_frontier_size,
        start_time, visited_coords
    )


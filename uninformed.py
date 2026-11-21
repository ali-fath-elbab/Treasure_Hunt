"""
uninformed.py

From-scratch implementations of the four uninformed search algorithms used in
CSAI 301 Phase I:

    bfs  - Breadth-First Search
    dfs  - Depth-First Search
    ucs  - Uniform-Cost Search
    ids  - Iterative Deepening Search

All algorithms share the same problem interface:

    problem.get_initial_state()
    problem.is_goal(state)
    problem.get_successors(state)   -> (action, next_state, step_cost)

Each function returns a dictionary with the solution path and the measured
metrics (nodes generated/expanded, peak frontier size, running time, and a
per-coordinate visit count used by the visualisation).

An optional trace callback may be supplied:

    trace(state, expanded_count, frontier_size)
"""

from collections import deque
import heapq
import time


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
    """Assemble the standard result dictionary used by every algorithm."""
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


def bfs(problem, trace=None):
    """
    Breadth-First Search using a FIFO queue.

    Explores states in non-decreasing depth order. Complete and optimal in the
    number of steps, but not guaranteed to minimise weighted path cost.

    Returns the standard result dictionary.
    """
    start_time = time.perf_counter()
    initial_state = problem.get_initial_state()

    frontier = deque([(initial_state, [], [initial_state], 0)])
    discovered = {initial_state}
    visited_coords = {}

    nodes_generated = 1
    nodes_expanded = 0
    max_frontier_size = 1

    while frontier:
        max_frontier_size = max(max_frontier_size, len(frontier))
        state, actions, states, cost = frontier.popleft()
        nodes_expanded += 1

        coord = (state[0], state[1])
        visited_coords[coord] = visited_coords.get(coord, 0) + 1

        if trace is not None:
            trace(state, nodes_expanded, len(frontier))

        if problem.is_goal(state):
            return _build_result(
                "BFS", True, actions, states, cost,
                nodes_generated, nodes_expanded, max_frontier_size,
                start_time, visited_coords,
            )

        for action, next_state, step_cost in problem.get_successors(state):
            nodes_generated += 1
            if next_state not in discovered:
                discovered.add(next_state)
                frontier.append((
                    next_state,
                    actions + [action],
                    states + [next_state],
                    cost + step_cost,
                ))

    return _build_result(
        "BFS", False, [], [], 0,
        nodes_generated, nodes_expanded, max_frontier_size,
        start_time, visited_coords,
    )


def dfs(problem, trace=None):
    """
    Depth-First Search using a LIFO stack.

    States are marked as discovered when pushed, which prevents duplicate stack
    entries and guarantees termination on this finite state space. Complete on
    finite graphs, but not optimal.

    Returns the standard result dictionary.
    """
    start_time = time.perf_counter()
    initial_state = problem.get_initial_state()

    frontier = [initial_state]
    discovered = {initial_state}
    parent = {}
    visited_coords = {}

    nodes_generated = 1
    nodes_expanded = 0
    max_frontier_size = 1

    while frontier:
        max_frontier_size = max(max_frontier_size, len(frontier))
        state = frontier.pop()
        nodes_expanded += 1

        coord = (state[0], state[1])
        visited_coords[coord] = visited_coords.get(coord, 0) + 1

        if trace is not None:
            trace(state, nodes_expanded, len(frontier))

        if problem.is_goal(state):
            # Rebuild the path from the parent pointers stored during expansion.
            path_states = [state]
            path_actions = []
            path_cost = 0
            current = state
            while current != initial_state:
                previous, action, step_cost = parent[current]
                path_actions.append(action)
                path_cost += step_cost
                path_states.append(previous)
                current = previous
            path_states.reverse()
            path_actions.reverse()

            return _build_result(
                "DFS", True, path_actions, path_states, path_cost,
                nodes_generated, nodes_expanded, max_frontier_size,
                start_time, visited_coords,
            )

        # Reverse the successors so UP is the first one popped from the stack.
        for action, next_state, step_cost in reversed(problem.get_successors(state)):
            nodes_generated += 1
            if next_state not in discovered:
                discovered.add(next_state)
                parent[next_state] = (state, action, step_cost)
                frontier.append(next_state)

    return _build_result(
        "DFS", False, [], [], 0,
        nodes_generated, nodes_expanded, max_frontier_size,
        start_time, visited_coords,
    )


def ucs(problem, trace=None):
    """
    Uniform-Cost Search (Dijkstra's algorithm on the implicit state graph).

    The frontier is a min-heap ordered by cumulative path cost g(n). Outdated
    heap entries are skipped when a cheaper route to that state was already
    found. Complete and optimal for positive step costs.

    Returns the standard result dictionary.
    """
    start_time = time.perf_counter()
    initial_state = problem.get_initial_state()

    counter = 0
    frontier = [(0, counter, initial_state, [], [initial_state])]
    best_cost = {initial_state: 0}
    visited_coords = {}

    nodes_generated = 1
    nodes_expanded = 0
    max_frontier_size = 1

    while frontier:
        max_frontier_size = max(max_frontier_size, len(frontier))
        cost, _tie_breaker, state, actions, states = heapq.heappop(frontier)

        if cost > best_cost.get(state, float("inf")):
            continue

        nodes_expanded += 1
        coord = (state[0], state[1])
        visited_coords[coord] = visited_coords.get(coord, 0) + 1

        if trace is not None:
            trace(state, nodes_expanded, len(frontier))

        if problem.is_goal(state):
            return _build_result(
                "UCS", True, actions, states, cost,
                nodes_generated, nodes_expanded, max_frontier_size,
                start_time, visited_coords,
            )

        for action, next_state, step_cost in problem.get_successors(state):
            nodes_generated += 1
            new_cost = cost + step_cost
            if new_cost < best_cost.get(next_state, float("inf")):
                best_cost[next_state] = new_cost
                counter += 1
                heapq.heappush(
                    frontier,
                    (new_cost, counter, next_state,
                     actions + [action], states + [next_state]),
                )

    return _build_result(
        "UCS", False, [], [], 0,
        nodes_generated, nodes_expanded, max_frontier_size,
        start_time, visited_coords,
    )


def ids(problem, max_depth=250, trace=None):
    """
    Iterative Deepening Search.

    Repeatedly runs depth-limited DFS with increasing depth limits. Within each
    iteration, a state is re-expanded only if a shallower route to it is found,
    which prevents cycles while preserving minimum-step optimality.

    Args:
        problem: the TreasureHuntProblem instance.
        max_depth: safety cap on the depth limit.
        trace: optional callback trace(state, expanded_count, frontier_size).

    Returns the standard result dictionary with totals accumulated over all
    depth-limited iterations.
    """
    start_time = time.perf_counter()
    initial_state = problem.get_initial_state()

    total_nodes_generated = 0
    total_nodes_expanded = 0
    overall_max_frontier = 1
    visited_coords = {}

    for depth_limit in range(max_depth + 1):
        stack = [(initial_state, [], [initial_state], 0, 0)]
        min_depth_in_iter = {initial_state: 0}
        total_nodes_generated += 1

        while stack:
            overall_max_frontier = max(overall_max_frontier, len(stack))
            state, actions, states, cost, depth = stack.pop()
            total_nodes_expanded += 1

            coord = (state[0], state[1])
            visited_coords[coord] = visited_coords.get(coord, 0) + 1

            if trace is not None:
                trace(state, total_nodes_expanded, len(stack))

            if problem.is_goal(state):
                return _build_result(
                    "IDS", True, actions, states, cost,
                    total_nodes_generated, total_nodes_expanded,
                    overall_max_frontier, start_time, visited_coords,
                )

            if depth < depth_limit:
                for action, next_state, step_cost in reversed(
                    problem.get_successors(state)
                ):
                    total_nodes_generated += 1
                    next_depth = depth + 1
                    if next_depth < min_depth_in_iter.get(next_state, float("inf")):
                        min_depth_in_iter[next_state] = next_depth
                        stack.append((
                            next_state,
                            actions + [action],
                            states + [next_state],
                            cost + step_cost,
                            next_depth,
                        ))

    return _build_result(
        "IDS", False, [], [], 0,
        total_nodes_generated, total_nodes_expanded,
        overall_max_frontier, start_time, visited_coords,
    )

"""
uninformed.py
From-scratch implementations of uninformed search algorithms:
BFS, DFS, UCS, and IDS.

All algorithms use the same problem interface:
    get_initial_state()
    is_goal(state)
    get_successors(state)

Optional trace callback:
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
    """Build a standardized result dictionary."""
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
    Breadth-First Search.
    Complete and optimal in number of steps when all actions have equal cost.
    It is not guaranteed to minimize weighted path cost.
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
                start_time, visited_coords
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
        start_time, visited_coords
    )


def dfs(problem, trace=None):
    """
    Depth-First Search.
    Complete on this finite state space, but not optimal.
    States are marked discovered when pushed to avoid duplicate stack entries.
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
                start_time, visited_coords
            )

        # Reverse so UP is the first successor removed from the LIFO stack.
        for action, next_state, step_cost in reversed(
            problem.get_successors(state)
        ):
            nodes_generated += 1

            if next_state not in discovered:
                discovered.add(next_state)
                parent[next_state] = (state, action, step_cost)
                frontier.append(next_state)

    return _build_result(
        "DFS", False, [], [], 0,
        nodes_generated, nodes_expanded, max_frontier_size,
        start_time, visited_coords
    )


def ucs(problem, trace=None):
    """
    Uniform-Cost Search (Dijkstra's algorithm on the implicit state graph).
    Complete and optimal for positive step costs.
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

        # Ignore outdated entries in the priority queue.
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
                start_time, visited_coords
            )

        for action, next_state, step_cost in problem.get_successors(state):
            nodes_generated += 1
            new_cost = cost + step_cost

            if new_cost < best_cost.get(next_state, float("inf")):
                best_cost[next_state] = new_cost
                counter += 1
                heapq.heappush(
                    frontier,
                    (
                        new_cost,
                        counter,
                        next_state,
                        actions + [action],
                        states + [next_state],
                    ),
                )

    return _build_result(
        "UCS", False, [], [], 0,
        nodes_generated, nodes_expanded, max_frontier_size,
        start_time, visited_coords
    )


def ids(problem, max_depth=250, trace=None):
    """
    Iterative Deepening Search.
    Repeats depth-limited DFS with increasing limits.
    Optimal in number of steps for unit-step depth, not weighted path cost.
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
                    overall_max_frontier, start_time, visited_coords
                )

            if depth < depth_limit:
                for action, next_state, step_cost in reversed(
                    problem.get_successors(state)
                ):
                    total_nodes_generated += 1
                    next_depth = depth + 1

                    if next_depth < min_depth_in_iter.get(
                        next_state, float("inf")
                    ):
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
        overall_max_frontier, start_time, visited_coords
    )

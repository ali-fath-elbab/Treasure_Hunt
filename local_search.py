"""
local_search.py
From-scratch implementations of local search algorithms:
1. Hill Climbing (Steepest Ascent / Random Restart)
2. Simulated Annealing
3. Genetic Algorithm

All algorithms conform to the standard project interface and return the
standardized result dictionary format matching uninformed.py and informed.py.
"""

import math
import random
import time
from informed import manhattan_distance


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


def prune_loops(path_states, path_actions=None):
    """
    Eliminates loops/cycles from a state sequence.
    If a state repeats at index j > i, slices out the cycle (i, j].
    """
    seen = {}
    pruned_states = []
    pruned_actions = []

    for idx, state in enumerate(path_states):
        coord = (state[0], state[1])
        if coord in seen:
            cut_idx = seen[coord]
            # Remove states that are being spliced out from lookup table
            for removed in pruned_states[cut_idx + 1:]:
                rem_c = (removed[0], removed[1])
                if rem_c in seen and seen[rem_c] > cut_idx:
                    del seen[rem_c]
            pruned_states = pruned_states[:cut_idx + 1]
            if path_actions is not None:
                pruned_actions = pruned_actions[:cut_idx]
        else:
            seen[coord] = len(pruned_states)
            pruned_states.append(state)
            if path_actions is not None and idx > 0 and (idx - 1) < len(path_actions):
                pruned_actions.append(path_actions[idx - 1])

    if path_actions is not None:
        return pruned_states, pruned_actions
    return pruned_states


def hill_climbing(problem, heuristic=None, max_restarts=50, max_steps=1000, trace=None, seed=42):
    """
    Hill Climbing search.
    In standard form (steepest descent on heuristic h(n)), it greedily moves to the
    neighbor with lowest h(n). If it hits a local minimum or plateau (no neighbor improves),
    it uses Random Restarts from the initial state with stochastic tie-breaking to escape.
    """
    if heuristic is None:
        heuristic = lambda s: manhattan_distance(s, problem.exit_pos)

    if seed is not None:
        random.seed(seed)

    start_time = time.perf_counter()
    initial_state = problem.get_initial_state()

    total_nodes_generated = 1
    total_nodes_expanded = 0
    visited_coords = {}

    best_path_states = []
    best_path_actions = []
    best_cost = float("inf")
    found_goal = False

    for restart in range(max_restarts + 1):
        curr = initial_state
        run_states = [curr]
        run_actions = []
        run_visited = {curr}
        run_cost = 0

        c_init = (curr[0], curr[1])
        visited_coords[c_init] = visited_coords.get(c_init, 0) + 1

        for _ in range(max_steps):
            total_nodes_expanded += 1
            if trace is not None:
                trace(curr, total_nodes_expanded, 1)

            if problem.is_goal(curr):
                found_goal = True
                best_path_states = run_states
                best_path_actions = run_actions
                best_cost = run_cost
                break

            successors = problem.get_successors(curr)
            total_nodes_generated += len(successors)

            # Filter successors not already in the current run trajectory
            valid_succs = [item for item in successors if item[1] not in run_visited]
            if not valid_succs:
                # Dead end
                break

            min_h = min(heuristic(item[1]) for item in valid_succs)
            curr_h = heuristic(curr)

            # Candidates that achieve the best heuristic among successors
            candidates = [item for item in valid_succs if heuristic(item[1]) == min_h]

            if min_h > curr_h:
                # Local minimum: all legal unvisited neighbors are strictly worse
                # On restart 0, we observe the classic local minimum trap!
                if restart == max_restarts:
                    break
                break

            # Pick a candidate (stochastic tie-breaking on restarts)
            if len(candidates) > 1 and restart > 0:
                action, next_state, step_cost = random.choice(candidates)
            else:
                action, next_state, step_cost = candidates[0]

            curr = next_state
            run_visited.add(curr)
            run_states.append(curr)
            run_actions.append(action)
            run_cost += step_cost

            coord = (curr[0], curr[1])
            visited_coords[coord] = visited_coords.get(coord, 0) + 1

        if found_goal:
            break

    # If goal was reached, compute accurate path cost
    if found_goal:
        path_cost = sum(
            problem.step_costs[problem.grid[s[0]][s[1]]]
            for s in best_path_states[1:]
        )
    else:
        path_cost = best_cost if best_cost != float("inf") else 0

    return _build_result(
        "Hill Climbing",
        found_goal,
        best_path_actions,
        best_path_states,
        path_cost,
        total_nodes_generated,
        total_nodes_expanded,
        max_frontier_size=1,
        start_time=start_time,
        visited_coords=visited_coords,
    )


def simulated_annealing(
    problem,
    heuristic=None,
    t_init=30.0,
    alpha=0.9992,
    t_min=1e-4,
    max_steps=20000,
    trace=None,
    seed=42,
):
    """
    Simulated Annealing search.
    A local search algorithm that escapes local minima by accepting downhill
    (worse) transitions with probability P = exp(-delta_E / T), where delta_E
    is the increase in heuristic distance and T is the temperature.
    Temperature cools down after each step: T = max(t_min, T * alpha).
    """
    if heuristic is None:
        heuristic = lambda s: manhattan_distance(s, problem.exit_pos)

    if seed is not None:
        random.seed(seed)

    start_time = time.perf_counter()
    curr = problem.get_initial_state()

    path_states = [curr]
    path_actions = []
    visited_coords = {}

    nodes_generated = 1
    nodes_expanded = 0
    T = t_init
    found_goal = False

    coord = (curr[0], curr[1])
    visited_coords[coord] = 1

    for step in range(max_steps):
        nodes_expanded += 1
        if trace is not None:
            trace(curr, nodes_expanded, 1)

        if problem.is_goal(curr):
            found_goal = True
            break

        successors = problem.get_successors(curr)
        nodes_generated += len(successors)

        if not successors:
            break

        # Pick a random neighbor
        action, nxt, _step_cost = random.choice(successors)
        delta_e = heuristic(nxt) - heuristic(curr)

        # Accept if improvement (delta_e <= 0) or probabilistically via Boltzmann distribution
        if delta_e <= 0 or (T > t_min and random.random() < math.exp(-delta_e / T)):
            curr = nxt
            path_states.append(curr)
            path_actions.append(action)
            c = (curr[0], curr[1])
            visited_coords[c] = visited_coords.get(c, 0) + 1

        T = max(t_min, T * alpha)

    if found_goal:
        # Prune loops for clean direct path
        pruned_states, pruned_actions = prune_loops(path_states, path_actions)
        path_cost = sum(
            problem.step_costs[problem.grid[s[0]][s[1]]]
            for s in pruned_states[1:]
        )
    else:
        pruned_states = path_states
        pruned_actions = path_actions
        path_cost = 0

    return _build_result(
        "Simulated Annealing",
        found_goal,
        pruned_actions,
        pruned_states,
        path_cost,
        nodes_generated,
        nodes_expanded,
        max_frontier_size=1,
        start_time=start_time,
        visited_coords=visited_coords,
    )


def genetic_algorithm(
    problem,
    pop_size=60,
    generations=120,
    chrom_len=140,
    mutation_rate=0.20,
    trace=None,
    seed=42,
):
    """
    Genetic Algorithm (GA) for path planning.
    - Chromosome: An action sequence ['UP', 'DOWN', 'LEFT', 'RIGHT']
    - Fitness Function: Rewards reaching the exit, proximity to the goal,
      and penalizes path cost and wall collisions.
    - Operators: Tournament Selection, 1-Point Crossover, Random Mutation, Elitism.
    """
    if seed is not None:
        random.seed(seed)

    start_time = time.perf_counter()
    actions = ["UP", "DOWN", "LEFT", "RIGHT"]
    act_map = {
        "UP": (-1, 0),
        "DOWN": (1, 0),
        "LEFT": (0, -1),
        "RIGHT": (0, 1),
    }

    start_pos = problem.start_pos
    exit_pos = problem.exit_pos
    visited_coords = {}

    def simulate(chromosome):
        """Simulate an action sequence from start, returning trajectory metrics."""
        r, c = start_pos
        states = [(r, c, 0, 0)]
        taken_actions = []
        cost = 0
        walls = 0

        for act in chromosome:
            dr, dc = act_map[act]
            nr, nc = r + dr, c + dc

            if 0 <= nr < problem.rows and 0 <= nc < problem.cols and problem.grid[nr][nc] != "#":
                r, c = nr, nc
                cell_cost = problem.step_costs[problem.grid[r][c]]
                cost += cell_cost
                next_state = (r, c, 0, 0)
                states.append(next_state)
                taken_actions.append(act)

                visited_coords[(r, c)] = visited_coords.get((r, c), 0) + 1

                if (r, c) == exit_pos:
                    return True, states, taken_actions, cost, walls
            else:
                walls += 1

        return False, states, taken_actions, cost, walls

    def calc_fitness(chromosome):
        reached, states, _acts, cost, walls = simulate(chromosome)
        last_r, last_c = states[-1][0], states[-1][1]
        dist = abs(last_r - exit_pos[0]) + abs(last_c - exit_pos[1])

        if reached:
            # Huge bonus for reaching goal, minus cost penalty
            return 100000.0 - cost * 5.0
        # Fitness inversely proportional to Manhattan distance to goal
        return (2000.0 / (1.0 + dist)) - (walls * 0.5)

    def make_individual():
        """Generates an individual using a goal-biased exploratory walk."""
        curr = problem.get_initial_state()
        chrom = []
        for _ in range(chrom_len):
            succs = problem.get_successors(curr)
            if not succs:
                chrom.append(random.choice(actions))
                continue
            # Weight movement towards Down and Right since exit is at (rows-1, cols-1)
            weights = [2.5 if a in ("DOWN", "RIGHT") else 0.8 for a, _s, _c in succs]
            chosen = random.choices(succs, weights=weights)[0]
            chrom.append(chosen[0])
            curr = chosen[1]
            if problem.is_goal(curr):
                break
        while len(chrom) < chrom_len:
            chrom.append(random.choice(["DOWN", "RIGHT", "UP", "LEFT"]))
        return chrom

    # Initialize population
    population = [make_individual() for _ in range(pop_size)]
    nodes_generated = pop_size
    nodes_expanded = 0

    best_chrom = None
    best_fitness_score = -float("inf")
    found_goal = False

    for gen in range(generations):
        nodes_expanded += 1
        fitness_scores = [calc_fitness(ind) for ind in population]

        for ind, score in zip(population, fitness_scores):
            if score > best_fitness_score:
                best_fitness_score = score
                best_chrom = ind

        reached, states, acts, cost, _ = simulate(best_chrom)
        if trace is not None and states:
            trace(states[-1], nodes_expanded, pop_size)

        if reached:
            found_goal = True
            break

        # Elitism: retain top individual
        new_population = [best_chrom]

        # Selection & Reproduction
        while len(new_population) < pop_size:
            # Tournament selection (sample 3)
            candidates1 = random.sample(list(zip(population, fitness_scores)), 3)
            parent1 = max(candidates1, key=lambda x: x[1])[0]

            candidates2 = random.sample(list(zip(population, fitness_scores)), 3)
            parent2 = max(candidates2, key=lambda x: x[1])[0]

            # 1-Point Crossover
            crossover_point = random.randint(1, chrom_len - 1)
            child = parent1[:crossover_point] + parent2[crossover_point:]

            # Mutation
            if random.random() < mutation_rate:
                mutation_idx = random.randint(0, chrom_len - 1)
                child[mutation_idx] = random.choice(actions)

            new_population.append(child)
            nodes_generated += 1

        population = new_population

    reached, best_states, best_actions, _raw_cost, _ = simulate(best_chrom)

    if reached:
        pruned_states, pruned_actions = prune_loops(best_states, best_actions)
        path_cost = sum(
            problem.step_costs[problem.grid[s[0]][s[1]]]
            for s in pruned_states[1:]
        )
    else:
        pruned_states = best_states
        pruned_actions = best_actions
        path_cost = 0

    return _build_result(
        "Genetic Algorithm",
        reached,
        pruned_actions,
        pruned_states,
        path_cost,
        nodes_generated,
        nodes_expanded,
        max_frontier_size=pop_size,
        start_time=start_time,
        visited_coords=visited_coords,
    )


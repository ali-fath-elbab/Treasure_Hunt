# Treasure Hunt Grid World — Search & Optimization Algorithms

An artificial intelligence grid world benchmark featuring **uninformed search**, **heuristic (informed) search**, and **local search / evolutionary algorithms** with comparative empirical benchmarking and live Pygame visualization.

---

## 1. Problem Formulation

- **Environment**: A deterministic 40x40 grid world (1,600 total cells, 1,101 walkable cells, 499 walls).
- **Start State**: Cell $(0, 0)$ designated as `P`.
- **Goal State**: Cell $(39, 39)$ designated as `E`.
- **Transitions**: 4-connected cardinal movements: `UP`, `DOWN`, `LEFT`, `RIGHT`.
- **Terrain Step Costs**:
  - Empty Floor (`.`): $1$
  - Sand (`S`): $3$
  - Mud (`M`): $5$
  - Wall (`#`): Impassable

---

## 2. Implemented Search Algorithms

### A. Uninformed Search (`uninformed.py`)
1. **Breadth-First Search (BFS)**
   - Queue (FIFO) frontier.
   - Guaranteed step-optimal on unweighted unit steps.
2. **Depth-First Search (DFS)**
   - Stack (LIFO) frontier with cycle detection.
   - Memory-light on tree structures, but non-optimal and explores deep corridors first.
3. **Uniform-Cost Search (UCS)**
   - Priority queue ordered by cumulative path cost $g(n)$.
   - Strictly cost-optimal for non-negative step costs.
4. **Iterative Deepening Search (IDS)**
   - Successive depth-limited DFS passes.
   - Step-optimal with low memory footprint $O(bd)$.

### B. Heuristic (Informed) Search (`informed.py`)
1. **Heuristic Evaluation**:
   - **Manhattan Distance**: $h(n) = |r_n - r_{goal}| + |c_n - c_{goal}|$.
     - **Admissibility**: Because minimum step cost is $1$, $h(n) \le h^*(n)$ (never overestimates).
     - **Consistency (Monotonicity)**: Adjacent steps change Manhattan distance by at most $1$, so $h(n) \le c(n, n') + h(n')$.
   - **Euclidean Distance**: $h(n) = \sqrt{(r_n - r_{goal})^2 + (c_n - c_{goal})^2}$.
2. **Greedy Best-First Search (GBFS)**
   - Frontier prioritized purely by heuristic $f(n) = h(n)$.
   - Drastically prunes search space, rapidly finding a path toward the exit.
3. **A\* Search**
   - Frontier prioritized by total estimated cost: $f(n) = g(n) + h(n)$.
   - With admissible and consistent heuristics, guarantees **strictly optimal path cost** while pruning unpromising branches.

### C. Local Search & Evolutionary Optimization (`local_search.py`)
1. **Hill Climbing (Steepest Descent with Random Restarts)**
   - Greedily transitions to the neighbor with lowest $h(n)$.
   - Demonstrates the classic **local minimum / plateau** trap on pure greedy descent, and escapes using **Random Restarts** with stochastic tie-breaking.
2. **Simulated Annealing (SA)**
   - Escapes local minima by accepting downhill transitions probabilistically via the Boltzmann criterion:
     $$P(\text{accept}) = \exp\left(-\frac{\Delta E}{T}\right)$$
   - Uses geometric temperature cooling: $T \leftarrow \max(T_{min}, T \times \alpha)$.
   - Applies loop pruning to extract a direct path.
3. **Genetic Algorithm (GA)**
   - **Chromosome Representation**: An action sequence of directions `['UP', 'DOWN', 'LEFT', 'RIGHT']`.
   - **Fitness Function**: Rewards goal arrival, proximity to exit $(1 / (1 + d))$, and penalizes path cost and wall bumps.
   - **Operators**: Tournament selection, 1-point crossover, random mutation, and elitism.

---

## 3. Empirical Comparison & Benchmark Results

Run on the standard 40x40 deterministic Treasure Hunt map:

| Algorithm | Category | Found | Steps | Path Cost | Nodes Generated | Nodes Expanded | Max Frontier / Pop | Time (ms) | Optimality Guarantee |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **BFS** | Uninformed | True | 78 | 102 | 3,163 | 1,101 | 38 | ~3.1 ms | Optimal step count |
| **DFS** | Uninformed | True | 386 | 516 | 1,602 | 557 | 364 | ~1.5 ms | None |
| **UCS** | Uninformed | True | 80 | **88** | 3,163 | 1,101 | 46 | ~4.8 ms | **Cost-optimal** |
| **IDS** | Uninformed | True | 78 | 102 | 916,254 | 332,916 | 72 | ~1,090 ms | Optimal step count |
| **Greedy Best-First** | Heuristic | True | 78 | 102 | **242** | **88** | 68 | **~0.39 ms** | None (heuristic trade-off) |
| **A\*** | Heuristic | True | 80 | **88** | 2,972 | 1,028 | 201 | ~4.6 ms | **Cost-optimal** |
| **Hill Climbing** | Local Search | True | 78 | 102 | 1,164 | 393 | 1 | ~1.7 ms | Local optimum / restart |
| **Simulated Annealing** | Local Search | True | 142 | 186 | 4,856 | 1,594 | 1 | ~5.7 ms | Asymptotic global optimum |
| **Genetic Algorithm** | Local Search | True | 82 | 106 | 296 | 5 gen | 60 | ~53 ms | Population heuristic |

---

## 4. Key Takeaways & Theoretical Analysis

1. **Cost Optimality**:
   - Both **UCS** and **A\*** achieve the minimum possible weighted path cost (**88**), proving the theoretical optimality guarantees of A* when paired with an admissible and consistent heuristic.
2. **Search Effort**:
   - **Greedy Best-First Search** expands only **88 nodes** (a 92% reduction compared to BFS/UCS with 1,101 expanded nodes) and finishes in under 0.4 ms.
3. **Local Search Trade-offs**:
   - **Deterministic Hill Climbing** gets trapped at local minima due to dead-end wall configurations, highlighting the necessity of **Random Restarts** or **Stochastic Tie-Breaking**.
   - **Simulated Annealing** successfully climbs out of traps through temperature-controlled stochastic exploration.
   - **Genetic Algorithm** explores global path candidate topologies simultaneously, converging in just a few generations.

---

## 5. How to Run

### Command-Line Benchmark & Plot Generation
```bash
python main.py
```
Outputs generated in `./results/`:
- `results/all_algorithms_metrics.csv` — Full quantitative comparison table.
- `results/explored_paths.png` — 3x3 subplot grid showing explored state heatmaps and solution paths.
- `results/metrics_comparison.png` — 2x2 comparison bar charts across cost, search effort, memory, and runtime.

### Interactive Pygame Visualizer Dashboard
```bash
python Game.py
```
- Select any of the 9 search algorithms.
- Click **Play**, **Pause**, or **Reset**.
- Adjust exploration playback speed dynamically using `+` and `-` buttons or `UP`/`DOWN` arrow keys.

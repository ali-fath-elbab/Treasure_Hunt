# CSAI 301: Treasure Hunt Grid World — Search & Optimization

A modular Python implementation and empirical benchmark suite evaluating classical **Uninformed Search**, **Informed Heuristic Search**, and **Trajectory-Based Local Search** algorithms on a deterministic $40 \times 40$ weighted grid-world environment.

---

## 📋 Overview

The **Treasure Hunt Problem** models an autonomous agent navigating a fully observable, deterministic $40 \times 40$ lattice ($1,600$ total cells; $1,101$ reachable walkable states) from start position `P = (0, 0)` to exit cell `E = (39, 39)`. The environment combines structural wall partitions with heterogeneous terrain penalties (Grass, Sand, and Mud), creating an explicit trade-off between **minimum-step paths** and **minimum-cost paths**.

### Key Capabilities
* **Deterministic Environment (`problem.py`)**: Reproducible $40 \times 40$ chamber lattice with fixed terrain generation and exact state-space statistics.
* **From-Scratch Search Engines (`uninformed.py`)**: Instrumented implementations of **BFS**, **DFS**, **UCS**, and **IDS** tracking path steps, weighted path cost, generated/expanded nodes, peak frontier memory, execution time, and cell visitation heatmaps.
* **Automated Benchmarking & Visualization (`main.py`, `visualizer.py`)**: Exports quantitative metrics to CSV and generates high-resolution spatial trajectory maps and log-scale performance comparisons.
* **Heuristic & Local Search Framework**: Formalized admissible Manhattan ($h_1$) and terrain/gate-aware ($h_2, h_3$) heuristics alongside path-space Hill-Climbing and Simulated Annealing setups.

---

## 🗂️ Repository Structure

```text
├── main.py                              # Experiment runner, console summary, and artifact exporter
├── problem.py                           # TreasureHuntProblem formulation, transition model, and map generator
├── uninformed.py                        # From-scratch BFS, DFS, UCS, and IDS implementations
├── visualizer.py                        # Plotting utilities for heatmaps, paths, and metric bar charts
├── treasure_hunt_search_report.html     # Comprehensive technical report (heuristics, local search & analysis)
├── results/
│   ├── phase1_metrics.csv               # Tabular performance metrics across all algorithms
│   ├── explored_paths.png               # 2x2 grid of solution trajectories and node expansion heatmaps
│   └── metrics_comparison.png           # 2x2 bar chart comparing cost, expansions, frontier size, and runtime
└── README.md                            # Project documentation
```

---

## 🗺️ Environment & State Space Formulation

* **Grid Dimensions**: $40 \times 40$ ($1,600$ total cells)
* **Walkable / Reachable States**: $1,101$ cells ($499$ impassable wall cells `#`)
* **State Encoding**: $s = (r, c, 0, 0)$ representing the agent's row and column coordinates
* **Action Space**: Deterministic cardinal ordering `UP`, `DOWN`, `LEFT`, `RIGHT`
* **Goal Test**: Terminates immediately upon entering `E = (39, 39)`

### Terrain & Step Costs

| Symbol | Terrain Type | Step Cost $c(s, a, s')$ | Deterministic Assignment Rule |
| :--- | :--- | :---: | :--- |
| `.`, `P`, `E`, `0–3` | Grass / Start / Exit / Markers | `1` | Default walkable floor cells |
| `S` | Sand | `3` | Assigned where $(7r + 13c) \bmod 17 = 0$ |
| `M` | Mud | `5` | Assigned where $(7r + 13c) \bmod 19 = 0$ |
| `#` | Impassable Wall | $\infty$ | $(c \bmod 4 = 3 \land r \bmod 4 \neq 2) \lor (r \bmod 4 = 3 \land c \bmod 4 \neq 2)$ |

---

## 🚀 Getting Started

### Prerequisites
* **Python 3.8+**
* **Matplotlib** (required for `visualizer.py` chart generation)

Install dependencies if needed:
```bash
pip install matplotlib
```

### Running the Experiments
Execute `main.py` from the root directory to run all search algorithms, print the state-space summary and metrics table to the console, and regenerate the output files in `./results/`:

```bash
python main.py
```

---

## 📊 Experimental Summary

| Algorithm | Found | Steps | Path Cost | Nodes Generated | Nodes Expanded | Max Frontier | Time (ms) | Optimality Property |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **BFS** | True | `78` | `102` | `2,374` | `1,101` | `38` | `7.510` | Step-optimal (unweighted) |
| **DFS** | True | `386` | `516` | `1,210` | `557` | `364` | `3.492` | Suboptimal (greedy depth-first) |
| **UCS** | True | `80` | **`88`** | `2,374` | `1,101` | `46` | `9.633` | **Cost-optimal** (weighted) |
| **IDS** | True | `78` | `102` | `709,221` | `332,916` | `72` | `2,306.062` | Step-optimal (high re-expansion) |

### Key Analytical Takeaways
1. **Step vs. Cost Trade-off**: **BFS** and **IDS** find the shortest-hop route (`78` steps) along the left perimeter, incurring a cost of `102` due to Sand and Mud tiles. **UCS** takes `2` additional steps (`80` steps) to weave through interior chambers and bypass high-penalty tiles, achieving the global minimum cost of **`88`**.
2. **Memory & Expansion Behavior**: **DFS** achieves the fastest runtime (`3.492 ms`) and fewest expansions (`557`) via deep vertical sweeps, at the expense of a heavily inflated path (`386` steps, cost `516`) and the largest peak frontier (`364` nodes).
3. **Cyclic Graph Overhead in IDS**: Iterative depth-bounding up to depth $d = 78$ causes repeated re-expansion of shallow states (`332,916` total expansions), making IDS roughly $239\times$ slower than UCS on this lattice.
4. **Heuristics & Local Search**: Equipping A* with the admissible Manhattan heuristic $h_1(r, c) = |r - 39| + |c - 39|$ preserves the optimal cost of `88` while pruning backward expansions. For trajectory-based local search initialized at the `78`-step BFS path, **Simulated Annealing** or multi-step subpath splicing is required to cross the $+2$-step barrier toward the `80`-step global optimum.
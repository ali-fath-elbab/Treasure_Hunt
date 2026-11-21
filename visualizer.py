"""
visualizer.py
Generates visual plots for search algorithm experiments:
    1. Grid heatmap of explored states and solution paths for all algorithms.
    2. 2x2 comparison bar chart comparing Path Cost, Nodes Expanded, Max Frontier Size, and Runtime.
"""

import math
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, LogNorm
from matplotlib.patches import Patch


def _get_algorithm_color(algo_name):
    """Assign colors by algorithm family for clear visual distinction."""
    algo_lower = algo_name.lower()
    if "bfs" in algo_lower:
        return "#457b9d"
    elif "dfs" in algo_lower:
        return "#e76f51"
    elif "ucs" in algo_lower:
        return "#2a9d8f"
    elif "ids" in algo_lower:
        return "#f4a261"
    elif "greedy" in algo_lower:
        return "#06d6a0"
    elif "a*" in algo_lower or "astar" in algo_lower:
        return "#118ab2"
    elif "hill" in algo_lower:
        return "#e63946"
    elif "anneal" in algo_lower:
        return "#9d4edd"
    elif "genetic" in algo_lower:
        return "#f72585"
    return "#6c757d"


def plot_explored_and_paths(problem, results, output_path="results/explored_paths.png"):
    """Draws a subplot grid showing terrain, explored heatmap, and solution path for all algorithms."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Encode terrain numerically for base layer:
    # 0 = Grass/Entity (cost 1), 1 = Sand (cost 3), 2 = Mud (cost 5), 3 = Wall
    terrain_map = np.zeros((problem.rows, problem.cols), dtype=int)
    for r in range(problem.rows):
        for c in range(problem.cols):
            cell = problem.grid[r][c]
            if cell == "#":
                terrain_map[r, c] = 3
            elif cell == "S":
                terrain_map[r, c] = 1
            elif cell == "M":
                terrain_map[r, c] = 2
            else:
                terrain_map[r, c] = 0

    terrain_cmap = ListedColormap(["#eef7ea", "#f6e5b8", "#c9a684", "#2b2d42"])

    n_results = len(results)
    if n_results <= 4:
        n_rows, n_cols = 2, 2
        figsize = (15, 13.5)
    elif n_results <= 6:
        n_rows, n_cols = 2, 3
        figsize = (18, 12)
    elif n_results <= 9:
        n_rows, n_cols = 3, 3
        figsize = (19, 17)
    else:
        n_cols = 3
        n_rows = math.ceil(n_results / 3)
        figsize = (18, 5.5 * n_rows)

    # Shared heat scale so all heatmaps are directly comparable
    max_heat = max(
        [max(res["visited_coords"].values(), default=1) for res in results] or [1]
    )

    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    axes = np.array(axes).flatten()
    heat_image = None

    for idx, res in enumerate(results):
        ax = axes[idx]
        ax.imshow(terrain_map, cmap=terrain_cmap, vmin=0, vmax=3)

        # Overlay explored cells heatmap
        heat = np.zeros((problem.rows, problem.cols), dtype=float)
        for (r, c), count in res["visited_coords"].items():
            heat[r, c] = count
        masked_heat = np.ma.masked_where(heat == 0, heat)
        heat_image = ax.imshow(
            masked_heat,
            cmap="Blues",
            alpha=0.6,
            norm=LogNorm(vmin=1, vmax=max_heat),
        )

        # Draw grid lines
        ax.set_xticks(np.arange(-0.5, problem.cols, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, problem.rows, 1), minor=True)
        ax.grid(which="minor", color="#cccccc", linestyle="-", linewidth=0.3)
        ax.tick_params(which="minor", bottom=False, left=False)
        ax.tick_params(which="major", labelsize=7)

        # Annotate special entities (P, E, K, D, 0..3)
        for r in range(problem.rows):
            for c in range(problem.cols):
                cell = problem.grid[r][c]
                if cell in {"P", "E", "K", "D", "0", "1", "2", "3"}:
                    label = f"T{cell}" if cell in {"0", "1", "2", "3"} else cell
                    ax.text(
                        c,
                        r,
                        label,
                        ha="center",
                        va="center",
                        fontsize=6.5 if problem.rows >= 35 else 8,
                        fontweight="bold",
                        color="#111111",
                    )

        # Draw solution path
        if res["found"] and res["path_states"]:
            path_rows = [s[0] for s in res["path_states"]]
            path_cols = [s[1] for s in res["path_states"]]
            ax.plot(
                path_cols,
                path_rows,
                color="#e63946",
                linewidth=2.0,
                marker="o",
                markersize=2.5,
                label="Solution Path",
            )
            ax.plot(
                path_cols[0],
                path_rows[0],
                marker="s",
                markersize=7,
                color="#2a9d8f",
                markeredgecolor="black",
                linestyle="None",
                label="Start",
            )
            ax.plot(
                path_cols[-1],
                path_rows[-1],
                marker="*",
                markersize=11,
                color="#ffd166",
                markeredgecolor="black",
                linestyle="None",
                label="Goal",
            )

        steps = len(res["path_actions"])
        ax.set_title(
            f"{res['algorithm']}\nCost: {res['path_cost']} | Steps: {steps} | Expanded: {res['nodes_expanded']}",
            fontsize=9.5,
            fontweight="bold",
        )

    # Hide unused subplots
    for unused_idx in range(n_results, len(axes)):
        axes[unused_idx].axis("off")

    fig.suptitle(
        f"Treasure Hunt ({problem.rows}x{problem.cols}): Explored States & Solution Paths Comparison",
        fontsize=14,
        fontweight="bold",
    )

    fig.subplots_adjust(left=0.04, right=0.91, top=0.93, bottom=0.08, wspace=0.15, hspace=0.25)

    if heat_image is not None:
        cax = fig.add_axes([0.93, 0.25, 0.015, 0.5])
        cbar = fig.colorbar(heat_image, cax=cax, orientation="vertical")
        cbar.set_label("Times cell was visited/expanded (log scale)", fontsize=9)

    terrain_handles = [
        Patch(facecolor="#eef7ea", edgecolor="black", label="Floor (cost 1)"),
        Patch(facecolor="#f6e5b8", edgecolor="black", label="Sand (cost 3)"),
        Patch(facecolor="#c9a684", edgecolor="black", label="Mud (cost 5)"),
        Patch(facecolor="#2b2d42", edgecolor="black", label="Wall (blocked)"),
        plt.Line2D([], [], color="#e63946", linewidth=2.0, marker="o", markersize=3, label="Solution Path"),
        plt.Line2D([], [], color="#2a9d8f", marker="s", markersize=7, linestyle="None", markeredgecolor="black", label="Start (P)"),
        plt.Line2D([], [], color="#ffd166", marker="*", markersize=11, linestyle="None", markeredgecolor="black", label="Exit (E)"),
    ]
    fig.legend(
        handles=terrain_handles,
        loc="lower center",
        ncol=7,
        fontsize=8.5,
        frameon=False,
        bbox_to_anchor=(0.5, 0.01),
    )
    plt.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_metrics_comparison(results, output_path="results/metrics_comparison.png"):
    """Generates a 2x2 comparison bar chart across all search algorithms."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    algos = [r["algorithm"] for r in results]
    colors = [_get_algorithm_color(name) for name in algos]

    metrics = [
        ("path_cost", "Total Path Cost (Lower = Cheaper)", "Cost"),
        ("nodes_expanded", "Search Effort / Nodes Expanded (Lower = Faster)", "Nodes / Iterations"),
        ("max_frontier_size", "Peak Memory / Max Frontier Size (Lower = Lighter)", "Nodes / Population"),
        ("execution_time_ms", "Execution Time (ms)", "Milliseconds"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for idx, (key, title, ylabel) in enumerate(metrics):
        ax = axes[idx]
        values = [r[key] for r in results]
        x_positions = np.arange(len(algos))

        bars = ax.bar(x_positions, values, color=colors, edgecolor="#222222", width=0.55)

        # If data spans multiple orders of magnitude, use a log scale
        positive = [v for v in values if v > 0]
        use_log = bool(positive) and (max(positive) / (min(positive) if min(positive) > 0 else 1) > 20)
        if use_log:
            ax.set_yscale("log")

        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_ylabel(f"{ylabel} (log scale)" if use_log else ylabel, fontsize=9.5)
        ax.set_xticks(x_positions)
        ax.set_xticklabels(algos, rotation=25, ha="right", fontsize=8.5)
        ax.grid(axis="y", linestyle="--", alpha=0.5, which="both")

        for bar, val in zip(bars, values):
            label = f"{val:.2f}" if isinstance(val, float) else f"{val}"
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height(),
                label,
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
            )

    plt.suptitle("Comprehensive Performance Comparison: Uninformed vs. Heuristic vs. Local Search", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(output_path, dpi=200)
    plt.close(fig)

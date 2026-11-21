"""
main.py

Entry point for the CSAI 301 Phase I experiments.

Runs the four uninformed search algorithms (BFS, DFS, UCS, IDS) on the
Treasure Hunt problem, prints a comparison table to the terminal, and writes
three deliverables to results/:

    phase1_metrics.csv     - measured performance of each algorithm
    explored_paths.png     - explored cells and solution path per algorithm
    metrics_comparison.png - bar charts comparing the four algorithms

Run with:  python main.py
"""

import csv
import os

from problem import TreasureHuntProblem
from uninformed import bfs, dfs, ucs, ids
from visualizer import plot_explored_and_paths, plot_metrics_comparison


def export_csv(results, filepath="results/phase1_metrics.csv"):
    """
    Write the measured metrics to a CSV file for the report tables.

    Args:
        results: list of result dictionaries returned by the search algorithms.
        filepath: destination path; parent directories are created if needed.
    """
    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)

    fieldnames = [
        "Algorithm",
        "Found",
        "Steps",
        "Path_Cost",
        "Nodes_Generated",
        "Nodes_Expanded",
        "Max_Frontier_Size",
        "Execution_Time_ms",
    ]

    with open(filepath, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            writer.writerow({
                "Algorithm": result["algorithm"],
                "Found": result["found"],
                "Steps": len(result["path_actions"]),
                "Path_Cost": result["path_cost"],
                "Nodes_Generated": result["nodes_generated"],
                "Nodes_Expanded": result["nodes_expanded"],
                "Max_Frontier_Size": result["max_frontier_size"],
                "Execution_Time_ms": round(result["execution_time_ms"], 4),
            })


def main():
    """Run the full Phase I experiment and produce all output files."""
    problem = TreasureHuntProblem()
    stats = problem.get_state_space_stats()

    # Describe the formal model before showing the search results.
    print("=" * 72)
    print("CSAI 301 - PHASE I: TREASURE HUNT PROBLEM & STATE SPACE")
    print("=" * 72)
    print(
        f"Grid Dimensions       : {stats['rows']} x {stats['cols']} "
        f"({stats['total_cells']} total cells)"
    )
    print(
        f"Walkable Cells        : {stats['walkable_cells']} "
        f"(Walls: {stats['wall_cells']})"
    )
    print(
        f"Theoretical State Bound: {stats['theoretical_states']} states "
        "(one position-based state per walkable cell)"
    )
    print(f"Exact Reachable States : {stats['reachable_states']} states")
    print(f"Initial State         : {problem.get_initial_state()}")
    print(f"Exit Position         : {problem.exit_pos}")
    print("=" * 72)

    # Every algorithm solves the same problem instance.
    algorithms = [bfs, dfs, ucs, ids]
    results = [algorithm(problem) for algorithm in algorithms]

    header = (
        f"{'Algo':<6} | {'Found':<5} | {'Steps':<5} | {'Cost':<5} | "
        f"{'Generated':<9} | {'Expanded':<8} | {'MaxFront':<8} | "
        f"{'Time (ms)':<9}"
    )
    print("\n" + header)
    print("-" * len(header))

    for result in results:
        print(
            f"{result['algorithm']:<6} | "
            f"{str(result['found']):<5} | "
            f"{len(result['path_actions']):<5} | "
            f"{result['path_cost']:<5} | "
            f"{result['nodes_generated']:<9} | "
            f"{result['nodes_expanded']:<8} | "
            f"{result['max_frontier_size']:<8} | "
            f"{result['execution_time_ms']:<9.3f}"
        )

    # The cheapest successful run is the cost-optimal reference (UCS).
    successful_results = [r for r in results if r["found"]]
    if successful_results:
        optimal_cost = min(r["path_cost"] for r in successful_results)
        print(
            "\nNote: The goal is reached immediately when the agent enters Exit E. "
            "BFS and IDS are optimal in number of steps; UCS is optimal in "
            "weighted path cost."
        )
        print(f"Lowest weighted path cost among successful results = {optimal_cost}.")
    else:
        print("\nNo algorithm found a path to the exit.")

    export_csv(results, "results/phase1_metrics.csv")
    plot_explored_and_paths(problem, results, "results/explored_paths.png")
    plot_metrics_comparison(results, "results/metrics_comparison.png")

    print("\nSaved outputs to ./results/:")
    print("  - results/phase1_metrics.csv")
    print("  - results/explored_paths.png")
    print("  - results/metrics_comparison.png")


if __name__ == "__main__":
    main()

from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

COMPARISONS_CSV = Path(__file__).parent / "comparisons.csv"
MAX_ITERS = 10_000
TOL = 1e-10
MAX_FIL_PER_APP = 100_000
MIN_FIL_PER_VOTE = 500

POWER_LAW_ALPHA = 0.8
POWER_LAW_TOP_N = 30
BUDGET_FIL = 510_000


def load_results(path: Path) -> list[tuple[str, str, str]]:
    """Return a list of (project_a, project_b, winner_name)."""
    rows: list[tuple[str, str, str]] = []
    with path.open(newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            a = row["project_a"].strip()
            b = row["project_b"].strip()
            winner_key = row.get("winner", "").strip()
            winner_name = row.get("winner_name", "").strip()

            if winner_name:
                winner = winner_name
            elif winner_key == "project_a":
                winner = a
            elif winner_key == "project_b":
                winner = b
            else:
                raise ValueError(f"Unrecognized winner fields in row: {row}")

            if winner not in {a, b}:
                raise ValueError(f"Winner {winner!r} not in pair ({a!r}, {b!r})")

            rows.append((a, b, winner))
    if not rows:
        raise ValueError("No comparison data found.")
    return rows


def build_win_matrix(
    results: list[tuple[str, str, str]],
) -> tuple[dict[str, dict[str, int]], dict[str, tuple[int, int]]]:
    """Create a wins matrix and per-project (wins, total) counts."""
    wins: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    records: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))

    for a, b, winner in results:
        if winner == a:
            wins[a][b] += 1
            w, t = records[a]
            records[a] = (w + 1, t + 1)
            w, t = records[b]
            records[b] = (w, t + 1)
        else:
            wins[b][a] += 1
            w, t = records[b]
            records[b] = (w + 1, t + 1)
            w, t = records[a]
            records[a] = (w, t + 1)

        # ensure all participants exist in the mapping
        wins[a]
        wins[b]
        records[a]
        records[b]
    return wins, records


def bradley_terry(
    wins: dict[str, dict[str, int]],
    max_iters: int = MAX_ITERS,
    tol: float = TOL,
) -> dict[str, float]:
    """
    Fit a Bradley-Terry model with the standard MM update.

    Abilities are returned as positive scores normalized to sum to 1.
    """
    players = sorted(wins.keys())
    scores = {player: 1.0 for player in players}

    for _ in range(max_iters):
        new_scores: dict[str, float] = {}
        for i in players:
            wins_i = sum(wins[i].values())
            if wins_i == 0:
                # keep a tiny mass so it does not collapse to zero
                new_scores[i] = 1e-12
                continue

            denom = 0.0
            for j in players:
                if i == j:
                    continue
                n_ij = wins[i].get(j, 0) + wins[j].get(i, 0)
                if n_ij == 0:
                    continue
                denom += n_ij / (scores[i] + scores[j])

            new_scores[i] = wins_i / denom if denom > 0 else 1e-12

        total = sum(new_scores.values())
        if total <= 0:
            raise RuntimeError("Failed to normalize Bradley-Terry scores.")
        for k in new_scores:
            new_scores[k] /= total

        delta = max(abs(new_scores[k] - scores[k]) for k in players)
        scores = new_scores
        if delta < tol:
            break

    return scores


def rank_scores(scores: dict[str, float]) -> list[tuple[str, float]]:
    """Return scores sorted descending (rank, score)."""
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


def powerlaw_allocations(
    ranked: list[tuple[str, float]],
    alpha: float = POWER_LAW_ALPHA,
    top_n: int = POWER_LAW_TOP_N,
    max_fil: int = MAX_FIL_PER_APP,
    min_fil: int = MIN_FIL_PER_VOTE,
    budget_fil: int = BUDGET_FIL,
) -> dict[str, int]:
    """
    Allocate FIL with a Zipf/power-law decay anchored to a total budget.

    Steps:
    - Compute weights = 1 / rank^alpha for the top_n items.
    - Scale weights so their sum equals budget_fil.
    - Clamp each to [min_fil, max_fil]; values below min_fil become 0 (no vote).
    """
    allocations: dict[str, int] = {}
    consider = ranked[:top_n]
    weights = [1 / (idx**alpha) for idx in range(1, len(consider) + 1)]
    weight_sum = sum(weights) or 1.0
    scale = budget_fil / weight_sum

    for idx, (name, _score) in enumerate(consider, start=1):
        raw = scale * weights[idx - 1]
        alloc = int(round(raw))
        if alloc < min_fil:
            allocations[name] = 0
        else:
            allocations[name] = min(max_fil, alloc)

    # Everyone beyond top_n gets zero.
    for name, _score in ranked[top_n:]:
        allocations[name] = 0

    return allocations


def write_csv(
    ranked: list[tuple[str, float]],
    records: dict[str, tuple[int, int]],
    allocations: dict[str, int],
    file: Path | None = None,
) -> None:
    """
    Emit a machine-readable leaderboard with allocations.

    Columns: rank, project, score, rating_log, wins, total, winrate, allocation_fil
    """
    output = sys.stdout if file is None else file.open("w", newline="")
    close_after = file is not None

    try:
        writer = csv.writer(output)
        writer.writerow([
            "rank",
            "project",
            "score",
            "rating_log",
            "wins",
            "total",
            "winrate",
            "allocation_fil",
        ])

        for idx, (name, score) in enumerate(ranked, start=1):
            wins, total = records.get(name, (0, 0))
            winrate = wins / total if total else 0.0
            rating = math.log(score)
            alloc = allocations.get(name, 0)
            writer.writerow([
                idx,
                name,
                f"{score:.6f}",
                f"{rating:.3f}",
                wins,
                total,
                f"{winrate:.3f}",
                alloc,
            ])
    finally:
        if close_after:
            output.close()


def main() -> None:
    results = load_results(COMPARISONS_CSV)
    wins, records = build_win_matrix(results)
    scores = bradley_terry(wins)
    ranked = rank_scores(scores)
    allocations = powerlaw_allocations(ranked)
    write_csv(ranked, records, allocations)


if __name__ == "__main__":
    main()

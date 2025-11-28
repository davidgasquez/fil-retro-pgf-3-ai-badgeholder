import csv
import json
import os
import random
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable

from tqdm import tqdm

APPLICATIONS_DIR = Path(__file__).parent / "applications"
CODEX_HOME = Path(__file__).parent / "badgeholder"
SCHEMA_PATH = CODEX_HOME / "schema.json"
OUTPUT_CSV = Path(__file__).parent / "comparisons.csv"
MIN_APPEARANCES = 10
SEED = 100
MAX_WORKERS = 20


def load_projects(directory: Path) -> dict[str, dict]:
    """Return a mapping of project_name to the full JSON payload."""
    projects: dict[str, dict] = {}
    for path in sorted(directory.glob("*.json")):
        with path.open() as f:
            data = json.load(f)
        name = data.get("project_name")
        if not name:
            raise ValueError(f"Missing project_name in {path}")
        if name in projects:
            raise ValueError(f"Duplicate project_name detected: {name}")
        projects[name] = data
    if len(projects) < 2:
        raise ValueError("Need at least two projects to generate pairs.")
    return projects


def rotate_roster(roster: list[str | None]) -> list[str | None]:
    """Rotate all elements except the first one step to the right."""
    if len(roster) <= 2:
        return roster
    rest = roster[1:]
    rest = rest[-1:] + rest[:-1]
    return [roster[0], *rest]


def generate_pairs(
    projects: Iterable[str],
    min_appearances: int = MIN_APPEARANCES,
    seed: int = SEED,
) -> list[tuple[str, str]]:
    """
    Generate pairs until each project appears at least `min_appearances` times.

    Uses a seeded shuffle for deterministic randomness and a round-robin style
    rotation to balance participation across rounds.
    """

    roster: list[str | None] = list(projects)
    rng = random.Random(seed)
    rng.shuffle(roster)

    if len(roster) % 2 == 1:
        roster.append(None)  # bye slot for odd counts

    counts = {name: 0 for name in roster if name is not None}
    pairs: list[tuple[str, str]] = []
    round_number = 0
    max_rounds = (min_appearances + 1) * len(roster)

    while min(counts.values()) < min_appearances:
        half = len(roster) // 2
        first_half = roster[:half]
        second_half = list(reversed(roster[half:]))

        for left, right in zip(first_half, second_half):
            if left is None or right is None:
                continue
            if rng.random() < 0.5:
                left, right = right, left  # deterministic side shuffle
            pairs.append((left, right))
            counts[left] += 1
            counts[right] += 1

        round_number += 1
        if round_number > max_rounds:
            raise RuntimeError("Unable to satisfy pairing requirement.")
        roster = rotate_roster(roster)

    return pairs


def build_prompt(project_a: dict, project_b: dict) -> str:
    """Format the prompt expected by codex exec."""
    project_a_json = json.dumps(project_a, indent=2)
    project_b_json = json.dumps(project_b, indent=2)
    return (
        "Which project has been more impactful for Filecoin?\n"
        "<projects>\n"
        "<project_a>\n"
        f"{project_a_json}\n"
        "</project_a>\n"
        "<project_b>\n"
        f"{project_b_json}\n"
        "</project_b>\n"
        "</projects>"
    )


def call_codex(prompt: str) -> dict:
    """Execute codex with the given prompt and return the parsed JSON response."""
    env = os.environ.copy()
    env["CODEX_HOME"] = str(CODEX_HOME)
    result = subprocess.run(
        [
            "codex",
            "exec",
            "--output-schema",
            str(SCHEMA_PATH),
            prompt,
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"codex exec failed with exit code {result.returncode}: {result.stderr.strip()}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Failed to parse codex output as JSON: {exc}\nOutput:\n{result.stdout}"
        ) from exc


def main() -> None:
    projects = load_projects(APPLICATIONS_DIR)
    pairs = generate_pairs(projects)

    def evaluate_pair(pair: tuple[str, str]) -> tuple[str, str, str, str]:
        name_a, name_b = pair
        prompt = build_prompt(projects[name_a], projects[name_b])
        response = call_codex(prompt)
        winner_key = response.get("winner")
        if winner_key not in {"project_a", "project_b"}:
            raise ValueError(f"Unexpected winner value: {winner_key!r}")
        winner_name = name_a if winner_key == "project_a" else name_b
        return name_a, name_b, winner_key, winner_name

    with OUTPUT_CSV.open("w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["project_a", "project_b", "winner", "winner_name"])
        csvfile.flush()
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            with tqdm(total=len(pairs), desc="Comparisons", unit="pair") as progress:
                for name_a, name_b, winner_key, winner_name in executor.map(
                    evaluate_pair, pairs
                ):
                    writer.writerow([name_a, name_b, winner_key, winner_name])
                    csvfile.flush()
                    progress.update(1)


if __name__ == "__main__":
    main()

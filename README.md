# Filecoin RetroPGF 3 AI Badgeholder 🗳️

An experimental AI–powered badgeholder that ranks Filecoin RetroPGF 3 applications from pairwise AI comparisons.

## 🏆 Allocation

| Rank | Project                                                                                                       | Allocation (FIL) |
| ---- | ------------------------------------------------------------------------------------------------------------- | ---------------- |
| 1    | FilOz – Advancing the Filecoin Protocol                                                                       | 93,287           |
| 2    | Lotus, Builtin Actors, and ref-FVM - Core Filecoin Protocol Implementations                                   | 53,580           |
| 3    | drand - the distributed randomness beacon project powering the League of Entropy and Filecoin Leader Election | 38,737           |
| 4    | FIP 100 Research & Development                                                                                | 30,773           |
| 5    | Boost                                                                                                         | 25,742           |
| 6    | go-libp2p                                                                                                     | 22,249           |
| 7    | Forest                                                                                                        | 19,667           |
| 8    | Chain.Love                                                                                                    | 17,675           |
| 9    | Blockscout Open Source Filecoin Explorer                                                                      | 16,085           |
| 10   | Filecoin Spark                                                                                                | 14,785           |
| 11   | Filecoin Client Implementation - Venus                                                                        | 13,700           |
| 12   | Boxo and Kubo                                                                                                 | 12,778           |
| 13   | Curio Storage                                                                                                 | 11,986           |
| 14   | MechaFIL-JAX                                                                                                  | 11,296           |
| 15   | Filecoin Deal Tool - Droplet                                                                                  | 10,689           |
| 16   | Spacescope: API service for the Filecoin ecosystem                                                            | 10,151           |
| 17   | IPFS Public Utilities                                                                                         | 9,671            |
| 18   | Filecoin Data Portal                                                                                          | 9,239            |
| 19   | Filecoin Community Service -VenusHub                                                                          | 8,847            |
| 20   | Secured Finance                                                                                               | 8,492            |
| 21   | Drips                                                                                                         | 8,167            |
| 22   | iso-filecoin                                                                                                  | 7,868            |
| 23   | FIL-B (FIL Builders) DX and Community                                                                         | 7,593            |
| 24   | Lighthouse                                                                                                    | 7,339            |
| 25   | Curio Smart Cordon & Restart System                                                                           | 7,103            |
| 26   | Axelar Network                                                                                                | 6,884            |
| 27   | CIDgravity Filecoin Gateway                                                                                   | 6,679            |
| 28   | FIP Editors - Filecoin Improvement Proposal Governance                                                        | 6,488            |
| 29   | Multichain Storage                                                                                            | 6,308            |
| 30   | Filecoin BigQuery Data Repository                                                                             | 6,139            |

## 🔀 How it works

- Each application lives as a JSON file in `applications/`.
- The `vote.py` script [runs a bunch of pairwise comparisons](https://davidgasquez.com/ranking-with-agents/). For each pair it asks `codex` to choose the more impactful project (prompt in `badgeholder/AGENTS.md`).
- The `rank.py` script reads `comparisons.csv` and builds a win matrix to fit a Bradley–Terry model. The model gives us a ranking of all the applications. We then apply a Zipf law distribution for the final fIL allocation.

## ▶️ Usage

You can replicate a similar `comparisons.csv`. You'll need [`codex` CLI](https://developers.openai.com/codex/cli/) and Python (best with [uv](https://docs.astral.sh/uv/)).

1. Generate comparisons with `uv run vote.py`
2. Compute leaderboard + FIL allocations as CSV with `uv run rank.py > leaderboard.csv`

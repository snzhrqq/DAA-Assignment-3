"""Benchmark Kruskal vs Prim on the SAME graphs at three sizes.

Run from the repository root:
    python tests/benchmark.py

Timing boundary (identical for both methods): only the call
algorithms.kruskal(request) / algorithms.prim(request) is timed with
time.perf_counter(). JSON parsing, I/O and graph generation are excluded;
each method's own work (sorting + DSU, or adjacency lists + heap) is included.
One untimed warm-up call per method and size, then 5 timed runs; median reported.
Results are checked for equal optimal cost / components and a valid forest first.
"""

import json
import pathlib
import platform
import random
import statistics
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "Python"))
sys.path.insert(0, str(ROOT / "tests"))

import algorithms                      # noqa: E402
from validator import validate         # noqa: E402

SEED = 12345
SIZES = [(10_000, 25_000), (50_000, 125_000), (100_000, 250_000)]
RUNS = 5


def make_graph(n, m, rnd):
    # a random spanning path keeps the graph connected; the rest are random edges
    perm = list(range(n))
    rnd.shuffle(perm)
    edges = [[perm[i], perm[i + 1], rnd.randint(-10**9, 10**9)] for i in range(n - 1)]
    while len(edges) < m:
        edges.append([rnd.randrange(n), rnd.randrange(n), rnd.randint(-10**9, 10**9)])
    return edges


def main():
    rnd = random.Random(SEED)
    print(f"Python {platform.python_version()} on {platform.platform()}, "
          f"CPU: {platform.processor() or platform.machine()}")
    print(f"seed={SEED}, timer=time.perf_counter, warm-up=1, runs={RUNS}\n")
    rows = []
    for n, m in SIZES:
        req_k = {"task": "kruskal", "n": n, "edges": make_graph(n, m, rnd)}
        req_p = {"task": "prim", "n": n, "edges": req_k["edges"]}   # same graph
        k, p = algorithms.kruskal(req_k), algorithms.prim(req_p)    # warm-up + check
        assert validate(req_k, k)[0] and validate(req_p, p)[0]
        assert k["cost"] == p["cost"] and k["components"] == p["components"]
        times = {"kruskal": [], "prim": []}
        for _ in range(RUNS):
            for name, fn, req in (("kruskal", algorithms.kruskal, req_k),
                                  ("prim", algorithms.prim, req_p)):
                t0 = time.perf_counter()
                fn(req)
                times[name].append((time.perf_counter() - t0) * 1000)
        row = {"n": n, "m": m, "cost": k["cost"],
               "kruskal_ms": [round(t, 1) for t in times["kruskal"]],
               "prim_ms": [round(t, 1) for t in times["prim"]],
               "kruskal_median": round(statistics.median(times["kruskal"]), 1),
               "prim_median": round(statistics.median(times["prim"]), 1)}
        rows.append(row)
        print(json.dumps(row))
    print("\n| n | m | Kruskal runs (ms) | Kruskal median | Prim runs (ms) | Prim median |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['n']} | {r['m']} | {', '.join(map(str, r['kruskal_ms']))} | "
              f"{r['kruskal_median']} | {', '.join(map(str, r['prim_ms']))} | {r['prim_median']} |")


if __name__ == "__main__":
    main()

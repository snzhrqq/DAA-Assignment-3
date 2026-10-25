"""My own tests for Assignment 3.

Run from the repository root:
    python tests/run_tests.py

Parts:
  A. Hand-made boundary cases (tests/cases.json) sent to the real program
     (src/Python/main.py) TWICE in one process -> checks state reset.
  B. The validator accepts alternative valid answers and rejects invalid witnesses.
  C. Direct calls of the route helper reconstruct_route.
  D. Full-limit and deep-chain inputs (seeded), timed end-to-end.
Actual outputs are written to tests/actual_outputs.jsonl.
"""

import json
import pathlib
import random
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "Python"))
sys.path.insert(0, str(ROOT / "tests"))

import algorithms                      # noqa: E402
from validator import validate         # noqa: E402

MAIN = [sys.executable, str(ROOT / "src" / "Python" / "main.py")]
failures = 0


def report(ok, label, detail=""):
    global failures
    if not ok:
        failures += 1
    print(("PASS " if ok else "FAIL ") + label + (f"  ({detail})" if detail and not ok else ""))


def run_program(requests):
    data = "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in requests)
    start = time.perf_counter()
    res = subprocess.run(MAIN, input=data, capture_output=True, text=True,
                         encoding="utf-8", timeout=120)
    elapsed = time.perf_counter() - start
    if res.returncode != 0:
        raise SystemExit(res.stderr)
    return [json.loads(line) for line in res.stdout.splitlines()], elapsed


# Fields whose value is unique for a correct program (others are checked semantically).
UNIQUE = {"dsu": ["states"], "kruskal": ["cost", "components"], "prim": ["cost", "components"],
          "scc": [], "topo": ["acyclic"], "dag": ["acyclic", "distance"]}


def part_a():
    print("== A. boundary cases, batch sent twice in one process ==")
    cases = json.loads((ROOT / "tests" / "cases.json").read_text(encoding="utf-8"))
    requests = [c["input"] for c in cases] * 2
    answers, _ = run_program(requests)
    with open(ROOT / "tests" / "actual_outputs.jsonl", "w", encoding="utf-8") as f:
        for c, a in zip(cases, answers):
            f.write(json.dumps({"name": c["name"], "actual": a}, separators=(",", ":")) + "\n")
    for k, (c, a) in enumerate(zip(cases * 2, answers)):
        tag = ("run1 " if k < len(cases) else "run2 ") + c["name"]
        ok_expected, why_e = validate(c["input"], c["expected"])   # expected answer is itself valid
        ok_actual, why_a = validate(c["input"], a)
        same = all(a.get(f) == c["expected"].get(f) for f in UNIQUE[c["input"]["task"]])
        report(ok_expected and ok_actual and same, tag,
               f"expected-valid={why_e}; actual={why_a}; unique-fields-match={same}")
    first, second = answers[:len(cases)], answers[len(cases):]
    report(first == second, "state reset: both runs give identical outputs")


def part_b():
    print("== B. validator: alternative valid answers / invalid witnesses ==")
    tri = {"task": "prim", "n": 3, "edges": [[0, 0, -100], [0, 1, 5], [0, 1, -2], [1, 2, 7], [2, 1, 7], [0, 2, 10]]}
    report(validate(tri, {"cost": 5, "edge_ids": [4, 2], "components": 1})[0],
           "forest: alternative tied edge id4 accepted")
    report(not validate(tri, {"cost": -95, "edge_ids": [0, 2, 3], "components": 1})[0],
           "forest: self-loop / too many edges rejected")
    report(not validate(tri, {"cost": 12, "edge_ids": [3, 5], "components": 1})[0],
           "forest: valid tree but not optimal rejected")

    s = {"task": "scc", "n": 6, "edges": [[0, 1], [1, 2], [2, 0], [2, 3], [3, 4], [4, 3], [4, 5]]}
    report(validate(s, {"component": [7, 7, 7, 3, 3, 100], "condensation": [[3, 100], [7, 3]]})[0],
           "scc: other labels and pair order accepted")
    report(not validate(s, {"component": [7, 7, 7, 3, 3, 100], "condensation": [[7, 3], [3, 100], [7, 3]]})[0],
           "scc: duplicate condensation pair rejected")
    report(not validate(s, {"component": [0, 0, 0, 0, 0, 1], "condensation": [[0, 1]]})[0],
           "scc: merged non-strongly-connected vertices rejected")

    t = {"task": "topo", "n": 4, "edges": [[0, 1], [0, 2], [1, 3], [2, 3]]}
    report(validate(t, {"acyclic": True, "order": [0, 1, 2, 3]})[0], "topo: alternative order accepted")
    report(not validate(t, {"acyclic": True, "order": [1, 0, 2, 3]})[0], "topo: backward edge rejected")

    d = {"task": "dag", "n": 4, "source": 0, "edges": [[0, 1, 2], [0, 1, 2], [0, 2, 1], [1, 3, 1], [2, 3, 2]]}
    report(validate(d, {"acyclic": True, "distance": [0, 2, 1, 3], "parent_edge": [-1, 1, 2, 4]})[0],
           "dag: other parallel edge (id1) and other tied route (id4) accepted")
    report(not validate(d, {"acyclic": True, "distance": [0, 2, 1, 3], "parent_edge": [-1, 0, 2, 2]})[0],
           "dag: parent edge that does not end at the vertex rejected")
    report(not validate(d, {"acyclic": True, "distance": [0, 2, 1, -1], "parent_edge": [-1, 0, 2, 3]})[0],
           "dag: wrong distance rejected")


def part_c():
    print("== C. route helper reconstruct_route (direct calls) ==")
    ex = {"task": "dag", "n": 5, "source": 0, "edges": [[0, 1, 3], [0, 2, 8], [1, 2, -7], [2, 3, 4]]}
    r = algorithms.dag(ex)
    E, P = ex["edges"], r["parent_edge"]

    def show(req, res, target):
        route = algorithms.reconstruct_route(req["edges"], res["parent_edge"], req["source"], target)
        ids, total = [], 0
        if route:
            for v in route[1:]:
                i = res["parent_edge"][v]
                ids.append(i)
                total += req["edges"][i][2]
        print(f"   reconstruct_route(target={target}) -> {route}; edge ids {ids}; weight {total}")
        return route, ids, total

    route, ids, total = show(ex, r, 3)
    report(route == [0, 1, 2, 3] and ids == [0, 2, 3] and total == r["distance"][3] == 0,
           "reachable target 3: route [0,1,2,3], ids [0,2,3], weight 0 = distance")
    report(show(ex, r, 0)[0] == [0], "source target: [0]")
    report(show(ex, r, 4)[0] is None, "unreachable target 4: None (documented no-route value)")

    tie = {"task": "dag", "n": 4, "source": 0, "edges": [[0, 1, 2], [0, 1, 2], [0, 2, 1], [1, 3, 1], [2, 3, 2]]}
    rt = algorithms.dag(tie)
    route, ids, total = show(tie, rt, 3)
    ok = route[0] == 0 and route[-1] == 3 and total == rt["distance"][3] == 3
    ok = ok and all(tie["edges"][i][0] == a and tie["edges"][i][1] == b
                    for i, a, b in zip(ids, route, route[1:]))
    report(ok, "tied/parallel edges: route goes source->target along chosen edges, weight 3")


def part_d():
    print("== D. full limits and deep chains (seed 2026) ==")
    rnd = random.Random(2026)
    N, M = 100000, 250000
    big = []
    big.append(("dsu n=1e5 q=2.5e5", {"task": "dsu", "n": N,
                "operations": [[rnd.randrange(N), rnd.randrange(N)] for _ in range(M)]}))
    w_edges = [[rnd.randrange(N), rnd.randrange(N), rnd.randint(-10**9, 10**9)] for _ in range(M)]
    big.append(("kruskal n=1e5 m=2.5e5", {"task": "kruskal", "n": N, "edges": w_edges}))
    big.append(("prim n=1e5 m=2.5e5", {"task": "prim", "n": N, "edges": w_edges}))
    chain = [[i, i + 1] for i in range(N - 1)]
    big.append(("scc deep chain + back edge (1 SCC)", {"task": "scc", "n": N, "edges": chain + [[N - 1, 0]]}))
    big.append(("scc deep chain (n SCCs)", {"task": "scc", "n": N, "edges": chain}))
    big.append(("topo deep chain", {"task": "topo", "n": N, "edges": chain}))
    big.append(("topo random DAG m=2.5e5", {"task": "topo", "n": N,
                "edges": [sorted(rnd.sample(range(N), 2)) for _ in range(M)]}))
    big.append(("dag deep chain weights -1e9", {"task": "dag", "n": N, "source": 0,
                "edges": [[i, i + 1, -10**9] for i in range(N - 1)]}))
    dag_edges = []
    for _ in range(M):
        a, b = sorted(rnd.sample(range(N), 2))
        dag_edges.append([a, b, rnd.randint(-10**9, 10**9)])
    big.append(("dag random m=2.5e5 + unreachable cycle", {"task": "dag", "n": N, "source": 0,
                "edges": dag_edges + [[N - 1, N - 2, 1], [N - 2, N - 1, 1]]}))

    for label, req in big:
        (ans,), secs = run_program([req])
        if req["task"] in ("dsu", "kruskal", "prim", "topo", "dag") or req["n"] <= 400:
            ok, why = validate(req, ans)
        else:
            ok, why = True, "ok"
        if label.startswith("scc deep chain + back"):
            ok = len(set(ans["component"])) == 1 and ans["condensation"] == []
        if label == "scc deep chain (n SCCs)":
            ok = len(set(ans["component"])) == N and len(ans["condensation"]) == N - 1
        if label == "dag deep chain weights -1e9":
            ok = ok and ans["distance"][-1] == -(N - 1) * 10**9
        if label.startswith("dag random"):
            ok = ans == {"acyclic": False, "distance": [], "parent_edge": []}
        report(ok and secs < 20, f"{label}: {secs:.2f} s (limit 20 s)", why)


if __name__ == "__main__":
    part_a()
    part_b()
    part_c()
    part_d()
    print(f"\n{'ALL TESTS PASSED' if failures == 0 else str(failures) + ' FAILURE(S)'}")
    sys.exit(1 if failures else 0)

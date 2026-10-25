# Assignment 3 — Analysis

Language: **Python 3.12+** (`submission.json`: `{"language": "Python"}`).
Implementation: `src/Python/algorithms.py`. Entry point (unchanged): `src/Python/main.py`.

## Build, run and test commands

Run everything from the repository root (Python needs no compilation):

```sh
python tools/run.py --setup                        # launch / ping check
python tools/run.py --check                        # 36 public cases, batch repeated twice
python tools/run.py --input tests/my_cases.jsonl   # my boundary inputs -> actual JSON lines
python tests/run_tests.py                          # my tests: expected vs actual, validator, route helper, limits
python tests/benchmark.py                          # Kruskal vs Prim benchmark
```

Files in `tests/`:

| File | Content |
|---|---|
| `cases.json` | 26 boundary cases: input, justification (`why`) and one expected answer |
| `my_cases.jsonl` | the same inputs as JSON Lines for `tools/run.py --input` |
| `my_cases_actual.jsonl` | actual output of `tools/run.py --input tests/my_cases.jsonl` |
| `actual_outputs.jsonl` | actual outputs captured by `run_tests.py` |
| `validator.py` | independent semantic checker (brute force / Bellman-Ford / Kahn / reachability) |
| `run_tests.py` | parts A–D described in section 8 |
| `test_output.txt` | full log of the last `python tests/run_tests.py` run |
| `benchmark.py`, `benchmark_output.txt` | benchmark script and its recorded output |

## 1. State reset and deep DFS

**State reset.** Every method creates all of its arrays (parent, size, adjacency lists, visited/state, heap, distances) as *local variables* inside the function call. No module-level mutable data is used, so nothing can survive from one request to the next. This is verified by sending the whole batch of my cases twice in one process (`run_tests.py`, part A) and by `tools/run.py --check`, which also repeats its batch; both runs give identical outputs.

**Deep DFS.** Python's default recursion limit (~1000) would fail on a chain of 100 000 vertices, so every DFS is *iterative*. The explicit stack stores pairs `[vertex, next_neighbour_index]`. When a vertex is resumed, it continues from the saved index, so each adjacency list is scanned once in total (no rescanning). The stack depth is at most `n`, i.e. `O(n)` memory. Deep chains of 100 000 vertices are tested for `scc`, `topo` and `dag` (part D).

## 2. DSU (`dsu`)

**Steps.** `parent[v] = v`, `size[v] = 1`, `components = n`, `largest = 1` (0 when `n = 0`). For each operation `[u, v]`: `find` both roots; if equal (repeated union or self-union) nothing changes; otherwise attach the smaller-size root under the larger one, add sizes, decrement `components`, update `largest`. Append `[components, largest]`.

**`find`** walks to the root, then makes a second pass that points every vertex on the path directly to the root (path compression). Union by **size** is used, so the size array is also the component size — no separate rank is needed.

**Invariant.** After processing the first `k` operations, the sets of the DSU are exactly the connected components of the graph formed by those `k` edges; `size[r]` is the number of vertices in the set of root `r`; `components` is the number of roots; `largest = max size[r]`. `largest` never decreases because sets only merge.

**Correctness.** Union merges exactly the two components joined by the new edge, and changes nothing when the endpoints are already connected, so the invariant is preserved; the state appended after each operation is therefore correct.

**Boundary cases.** `n = 0` → `states = []`; self-unions and repeated unions; `n = 1`.

**Complexity.** `O(n + q·α(n))` amortised time, `O(n + q)` memory including `states`.

## 3. Kruskal (`kruskal`)

**Steps.** Sort edge **IDs** by weight (the edges themselves are not moved, so original IDs are kept). Scan in increasing weight; skip self-loops; accept edge `i` only if `find(u) != find(v)` (then union). Stop early once `n − 1` edges are chosen. `components` is the DSU counter at the end (isolates included).

**Invariant.** The accepted edges always form a forest that is contained in some minimum spanning forest.

**Correctness (cut property).** When edge `(u, v)` with `find(u) != find(v)` is examined, it is a minimum-weight edge crossing the cut between `u`'s current tree and the rest, because every lighter edge was already examined and either accepted or rejected as inside a tree. A minimum edge across a cut belongs to some minimum spanning forest, so accepting it keeps the invariant. Rejected edges would close a cycle. At the end the DSU sets equal the connected components, so the result is a spanning forest with exactly `n − c` edges and minimum cost. Negative weights do not matter: the cut property only compares weights.

**Boundary cases.** `n = 0`, isolates, self-loops (never selected), parallel and equal-weight edges (any tie is fine), negative weights, totals above 32 bits (Python integers).

**Complexity.** Sorting `O(m log(m+1))`, DSU `O(n + m·α(n))` → `O(n + m log(m+1))` time, `O(n + m)` memory.

## 4. Prim (`prim`)

**Steps.** Build adjacency lists `(weight, neighbour, edge_id)` without self-loops. For every vertex not yet in a tree, **restart**: count one more component, mark it, push its incident edges into a lazy min-heap. Pop the lightest edge; if its far end is already in the tree it is stale and skipped; otherwise add the vertex, the cost and the edge ID, and push its edges to vertices outside the tree.

**Invariant.** The marked vertices of the current component and the chosen edges form a tree that is part of some minimum spanning forest; the heap contains (possibly stale) every edge from the tree to the outside.

**Correctness.** The non-stale popped edge is the lightest edge crossing the cut (current tree, rest of the component), so by the cut property it can be added. When the heap is empty, the whole component is spanned; the outer loop restarts in each unvisited vertex, so every component (including isolates) is spanned and counted exactly once.

**Complexity.** Lazy heap: each edge is pushed at most twice → `O(n + m log(m+1))` time, `O(n + m)` memory.

## 5. Kosaraju SCC (`scc`)

**Steps.** (1) Iterative DFS over the original graph from every unvisited vertex, recording vertices in finish order. (2) Build the transposed graph. (3) Process vertices in **decreasing** finish order; each still-unlabelled vertex starts a DFS on the transpose and gives one new label to everything it reaches. (4) Condensation: for each edge with different endpoint labels, add `(label_u, label_v)` to a hash set the first time it appears.

**Invariant.** When the second pass starts at vertex `s` (the unlabelled vertex with the largest finish time), the component of `s` is a *source* among the not-yet-labelled components of the condensation of the original graph, i.e. a *sink* in the transpose, so the DFS on the transpose from `s` reaches exactly the vertices of `s`'s SCC.

**Correctness.** That is the standard Kosaraju argument: the vertex with the largest finish time lies in a source SCC of the condensation; in the transpose no edge leaves this SCC towards unlabelled components, so each second-pass DFS labels exactly one SCC. The condensation keeps only edges between different labels and the set removes duplicates, so every cross pair appears exactly once and internal edges, self-loops and duplicate edges are excluded.

**Boundary cases.** `n = 0`, isolates (own SCC each), self-loops, duplicate edges, deep chains with and without a back edge.

**Complexity.** `O(n + m)` expected time (hash set), `O(n + m)` memory (graph, transpose, stack, set).

## 6. Topological order (`topo`)

**Steps.** States `UNVISITED / ACTIVE / FINISHED`. From every unvisited vertex run the iterative DFS; mark a vertex `ACTIVE` on entry and `FINISHED` when all its neighbours are done, appending it to the finish list. If an edge leads to an `ACTIVE` vertex, return `acyclic=false, order=[]` immediately. An edge to a `FINISHED` vertex is fine. At the end reverse the finish list.

**Invariant.** The `ACTIVE` vertices are exactly the vertices on the current DFS path (the stack), in path order.

**Correctness.** An edge `u → w` with `w` ACTIVE means `w` is an ancestor of `u` on the stack, so `w ⇝ u → w` is a directed cycle. Conversely, if there is a cycle, the first vertex of the cycle to be visited stays ACTIVE until the rest of the cycle is explored, so the edge that closes the cycle reaches an ACTIVE vertex. Without a cycle, for every edge `u → w`, `w` finishes before `u` (it is either finished already or visited and finished while `u` is active), so in the reversed finish order `u` comes before `w`. All components are visited by the outer loop.

**Boundary cases.** `n = 0` → `true, []`; isolates; self-loop (`u → u` sees itself ACTIVE); a cycle in a different component; duplicate edges.

**Complexity.** `O(n + m)` time and memory; the saved neighbour index guarantees each adjacency list is scanned once.

## 7. DAG shortest paths (`dag`) and the route helper

**Steps.** (1) Run the same three-state DFS on the **whole** graph; if any cycle exists (even unreachable from the source) return `false, [], []`. (2) `distance = [None]*n` (`None` = unreachable → JSON `null`), `parent_edge = [-1]*n`, `distance[source] = 0`. (3) Visit vertices in topological order; skip vertices whose distance is `None` (never relax from unreachable vertices); for each outgoing edge `i = (u, v, w)` relax `if distance[v] is None or distance[u] + w < distance[v]` and store `parent_edge[v] = i` (the edge ID, not the predecessor vertex).

**Invariant.** When vertex `u` is processed in topological order, `distance[u]` is already final, because every edge into `u` comes from a vertex earlier in the order that was already processed.

**Correctness.** By induction over the topological order: the last edge `(x, u)` of a shortest path to `u` is relaxed when `x` is processed, and `distance[x]` was final at that moment, so `distance[u]` becomes the shortest distance; it can never become smaller than the true optimum because every value is the length of a real path. `parent_edge[u]` is the edge that produced the final value, so it ends at `u`, satisfies `distance[x] + w = distance[u]`, and following parents strictly moves backwards in the topological order until the source. Negative weights are fine because there is no cycle. `None` is used instead of `-1` because `-1` can be a real distance.

**Boundary cases.** `n = 1`; source with distance 0 and parent −1; unreachable vertices (`null`, −1); a real distance of −1; a cycle unreachable from the source; self-loop; tied routes and parallel edges; source ≠ 0; totals beyond 32 bits.

**Complexity.** `O(n + m)` time and memory.

### Route helper `reconstruct_route(edges, parent_edge, source, target)`

Returns `[source]` when `target == source`; returns **`None`** when the target is unreachable (no route — my documented choice); otherwise walks `v ← edges[parent_edge[v]][0]` from the target to the source and reverses the list. Time and output space `O(L)` for a route of `L` vertices.

Actual calls (from `python tests/run_tests.py`, part C):

| Graph | Target | Result | Selected edge IDs | Total weight = distance? |
|---|---|---|---|---|
| README example `[[0,1,3],[0,2,8],[1,2,-7],[2,3,4]]`, source 0 | 3 (reachable) | `[0, 1, 2, 3]` | `[0, 2, 3]` | 3 − 7 + 4 = **0** = distance[3] ✓ |
| same | 0 (source) | `[0]` | `[]` | 0 = distance[0] ✓ |
| same | 4 (unreachable) | `None` | — | distance[4] = null ✓ |
| tied/parallel `[[0,1,2],[0,1,2],[0,2,1],[1,3,1],[2,3,2]]`, source 0 | 3 | `[0, 2, 3]` | `[2, 4]` | 1 + 2 = **3** = distance[3] ✓ |

Direction check: every selected edge `i` goes from `route[k]` to `route[k+1]` (`edges[i][0]`, `edges[i][1]`), which the test asserts. In the tied case the route via vertex 1 (`[0,1,3]`, cost 3, through parallel edge 0 or 1) is equally valid; my validator accepts it (part B).

## 8. Testing

* **Public checks**: `python tools/run.py --check` → all 36 cases PASS, and the state-reset batch PASS.
* **Part A — 26 boundary cases** (`tests/cases.json`), each with a written justification of the expected answer. Every expected answer is itself checked by the validator; the actual answer must be valid **and** match the unique fields (DSU states, MST cost and components, `acyclic`, DAG distances). The batch is sent twice in one process: both runs are identical (state reset).
* **Part B — the checker itself**: accepts alternative valid answers (other tied MST edge, other SCC labels and pair order, other topological order, other parallel/tied parent edges) and rejects invalid witnesses (self-loop/extra edge in a forest, non-optimal tree, duplicate condensation pair, wrongly merged SCC, backward edge in an order, parent edge not ending at its vertex, wrong distance).
* **Part C — route helper** (table above).
* **Part D — full limits and deep chains** (seed 2026): DSU `n=100000, q=250000`; Kruskal and Prim `n=100000, m=250000` with weights in `[−10⁹, 10⁹]`; SCC deep chain with and without a back edge; topo deep chain and random DAG with `m=250000`; DAG deep chain with weights −10⁹ (distance −99 999 000 000 000, far beyond 32 bits); random DAG plus a cycle unreachable from the source. All valid and each well under the 20 s batch limit (0.1–1.6 s end-to-end in my run).

The validator is independent of the solution: MST optimum by brute force over edge subsets (≤ 12 edges) or a separate Kruskal; SCC membership by pairwise reachability (n ≤ 400) and exact condensation set; cycles by Kahn's algorithm; DAG distances by Bellman–Ford plus tight-parent and chain-to-source checks.

## 9. Benchmark: Kruskal vs Prim

**Setup.** `python tests/benchmark.py`. Graphs: random connected undirected graphs (random spanning path + random edges, weights uniform in `[−10⁹, 10⁹]`), generator `random.Random(12345)`; **the same edge list** is given to both methods. Correctness is verified first: both results pass the validator and have equal cost and component count. Timer `time.perf_counter()`; one untimed warm-up call per method and size; 5 timed runs; median reported. **Timing boundary:** only the function call is timed (sorting + DSU for Kruskal; building adjacency lists + heap for Prim); JSON parsing, input/output and graph generation are excluded for both. No compilation (Python).

**Environment.** Python 3.13.16 (CPython), Linux x86_64 (cloud container), Intel Xeon @ 2.10 GHz, 2 vCPUs, 7 GB RAM.

| n | m | Kruskal runs (ms) | Kruskal median | Prim runs (ms) | Prim median |
|---|---|---|---|---|---|
| 10 000 | 25 000 | 31.1, 32.0, 31.4, 27.8, 27.6 | **31.1** | 61.7, 62.2, 63.2, 61.5, 73.8 | **62.2** |
| 50 000 | 125 000 | 239.0, 214.7, 239.3, 243.3, 280.2 | **239.3** | 599.4, 724.0, 559.8, 522.1, 537.0 | **559.8** |
| 100 000 | 250 000 | 559.6, 577.6, 585.2, 572.8, 588.0 | **577.6** | 1294.8, 1348.1, 1497.9, 1393.4, 1354.8 | **1354.8** |

**Observations.** On these sparse graphs (m = 2.5 n) Kruskal was about 2–2.4× faster at every size. Both grew roughly in proportion to `m log m` (×5 edges → ×7.7 time for Kruskal, ×9 for Prim; ×2 edges → ×2.4 for both), consistent with the `O(n + m log m)` bounds. A likely reason for the constant-factor gap: Kruskal's `sorted` runs in optimised C code over one list, while Prim builds `2m` adjacency tuples and performs up to `2m` Python-level `heappush`/`heappop` calls.

**Limitations.** One machine, one random graph per size, one graph family (sparse, connected, random weights); medians of 5 runs reduce but do not remove noise from a shared cloud CPU. These measurements are evidence, not a proof — the asymptotic argument is in sections 3–4. On dense graphs (m close to n²) an indexed-heap Prim could behave differently.

## 10. Sources and AI assistance

* Algorithms follow standard course material (DSU, Kruskal, Prim, Kosaraju, DFS topological sort, DAG shortest paths) and the assignment README.
* **AI assistance:** Claude (Anthropic) was used to draft the Python implementation, the test scripts, the benchmark script and this analysis, and to explain the algorithms. I verified the work by reading every function, running `tools/run.py --setup` and `--check`, running `tests/run_tests.py` and `tests/benchmark.py`, and checking the hand-made expected answers and route-helper results myself.
* No other external code was used.

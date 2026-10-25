"""Independent semantic validators for my own tests.

They do not trust the solution: MST optimum cost is recomputed by a
brute-force / reference method, SCCs by pairwise reachability, topological
orders by checking every edge, and DAG distances by Bellman-Ford.
Each validator returns (ok, reason).
"""

from itertools import combinations


# ---------- small reference helpers ----------

def _reach(n, adj, s):
    seen = [False] * n
    seen[s] = True
    stack = [s]
    while stack:
        v = stack.pop()
        for w in adj[v]:
            if not seen[w]:
                seen[w] = True
                stack.append(w)
    return seen


def _components_undirected(n, edges):
    parent = list(range(n))

    def root(v):
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v

    c = n
    for e in edges:
        a, b = root(e[0]), root(e[1])
        if a != b:
            parent[a] = b
            c -= 1
    return c


def reference_mst_cost(n, edges):
    """Brute force for tiny graphs, otherwise a simple reference Kruskal."""
    c = _components_undirected(n, edges)
    need = n - c
    if len(edges) <= 12:
        best = None
        for subset in combinations(range(len(edges)), need):
            chosen = [edges[i] for i in subset]
            if any(e[0] == e[1] for e in chosen):
                continue
            if _components_undirected(n, chosen) == c:
                cost = sum(e[2] for e in chosen)
                best = cost if best is None else min(best, cost)
        return (best if best is not None else 0), c
    parent = list(range(n))

    def root(v):
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v

    cost = 0
    for u, v, w in sorted(edges, key=lambda e: e[2]):
        a, b = root(u), root(v)
        if a != b:
            parent[a] = b
            cost += w
    return cost, c


# ---------- validators ----------

def check_dsu(req, ans):
    n, ops = req["n"], req["operations"]
    if n * max(len(ops), 1) > 200000:
        return _check_dsu_fast(req, ans)
    parent = list(range(n))

    def root(v):
        while parent[v] != v:
            v = parent[v]
        return v

    expected = []
    for u, v in ops:
        a, b = root(u), root(v)
        if a != b:
            parent[a] = b
        sizes = {}
        for x in range(n):
            r = root(x)
            sizes[r] = sizes.get(r, 0) + 1
        expected.append([len(sizes), max(sizes.values()) if sizes else 0])
    if ans.get("states") != expected:
        return False, "states differ from naive recomputation"
    return True, "ok"


def _check_dsu_fast(req, ans):
    """Large inputs: reference union-find with a size histogram."""
    n, ops = req["n"], req["operations"]
    parent = list(range(n))
    size = [1] * n
    count_of_size = {1: n} if n else {}
    comps, expected = n, []

    def root(v):
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v

    largest = 1 if n else 0
    for u, v in ops:
        a, b = root(u), root(v)
        if a != b:
            for s in (size[a], size[b]):
                count_of_size[s] -= 1
            parent[a] = b
            size[b] += size[a]
            count_of_size[size[b]] = count_of_size.get(size[b], 0) + 1
            comps -= 1
            largest = max(largest, size[b])
        expected.append([comps, largest])
    return (ans.get("states") == expected), "states differ from reference"


def check_forest(req, ans):
    n, edges = req["n"], req["edges"]
    ids = ans.get("edge_ids")
    if not isinstance(ids, list) or len(set(ids)) != len(ids):
        return False, "edge_ids missing or repeated"
    if any(not (0 <= i < len(edges)) for i in ids):
        return False, "edge id out of range"
    chosen = [edges[i] for i in ids]
    if any(e[0] == e[1] for e in chosen):
        return False, "self-loop selected"
    best, c = reference_mst_cost(n, edges)
    if ans.get("components") != c:
        return False, f"components {ans.get('components')} != {c}"
    if len(ids) != n - c:
        return False, f"forest needs {n - c} edges, got {len(ids)}"
    if _components_undirected(n, chosen) != c:
        return False, "selected edges contain a cycle or do not span"
    if sum(e[2] for e in chosen) != ans.get("cost"):
        return False, "cost is not the sum of selected weights"
    if ans["cost"] != best:
        return False, f"cost {ans['cost']} is not optimal ({best})"
    return True, "ok"


def check_scc(req, ans):
    n, edges = req["n"], req["edges"]
    comp, cond = ans.get("component"), ans.get("condensation")
    if not isinstance(comp, list) or len(comp) != n:
        return False, "component has wrong length"
    if any(not isinstance(x, int) or x < 0 for x in comp):
        return False, "labels must be nonnegative integers"
    if n <= 400:  # exact membership via pairwise reachability
        adj = [[] for _ in range(n)]
        for u, v in edges:
            adj[u].append(v)
        reach = [_reach(n, adj, s) for s in range(n)]
        for a in range(n):
            for b in range(n):
                same = reach[a][b] and reach[b][a]
                if same != (comp[a] == comp[b]):
                    return False, f"vertices {a},{b} wrongly grouped"
    want = {(comp[u], comp[v]) for u, v in edges if comp[u] != comp[v]}
    got = [tuple(p) for p in cond]
    if len(got) != len(set(got)) or set(got) != want:
        return False, "condensation is not the exact set of cross pairs"
    return True, "ok"


def _has_cycle(n, edges):
    indeg = [0] * n
    adj = [[] for _ in range(n)]
    for e in edges:
        adj[e[0]].append(e[1])
        indeg[e[1]] += 1
    queue = [v for v in range(n) if indeg[v] == 0]
    seen = 0
    while queue:
        v = queue.pop()
        seen += 1
        for w in adj[v]:
            indeg[w] -= 1
            if indeg[w] == 0:
                queue.append(w)
    return seen != n  # Kahn's algorithm as an independent cycle test


def check_topo(req, ans):
    n, edges = req["n"], req["edges"]
    cyclic = _has_cycle(n, edges)
    if ans.get("acyclic") is not (not cyclic):
        return False, "acyclic flag is wrong"
    order = ans.get("order")
    if cyclic:
        return (order == []), "order must be empty for a cycle"
    if sorted(order) != list(range(n)):
        return False, "order is not a permutation"
    pos = [0] * n
    for i, v in enumerate(order):
        pos[v] = i
    for u, v in edges:
        if pos[u] >= pos[v]:
            return False, f"edge {u}->{v} goes backwards"
    return True, "ok"


def check_dag(req, ans):
    n, s, edges = req["n"], req["source"], req["edges"]
    if _has_cycle(n, edges):
        ok = ans.get("acyclic") is False and ans.get("distance") == [] \
            and ans.get("parent_edge") == []
        return ok, "cycle must give false and empty arrays"
    if ans.get("acyclic") is not True:
        return False, "graph is acyclic"
    dist, par = ans.get("distance"), ans.get("parent_edge")
    if len(dist) != n or len(par) != n:
        return False, "arrays must have length n"
    # Bellman-Ford reference distances.
    ref = [None] * n
    ref[s] = 0
    for _ in range(max(n - 1, 0)):
        changed = False
        for u, v, w in edges:
            if ref[u] is not None and (ref[v] is None or ref[u] + w < ref[v]):
                ref[v] = ref[u] + w
                changed = True
        if not changed:
            break
    if dist != ref:
        return False, "distances differ from Bellman-Ford"
    for v in range(n):
        if v == s or ref[v] is None:
            if par[v] != -1:
                return False, f"parent_edge[{v}] must be -1"
            continue
        i = par[v]
        if not (0 <= i < len(edges)):
            return False, f"bad parent id for {v}"
        u, to, w = edges[i]
        if to != v or ref[u] is None or ref[u] + w != ref[v]:
            return False, f"parent edge of {v} is not tight"
    # Following parents must reach the source. Each tight parent edge strictly
    # moves to a vertex earlier in some topological order, so chains cannot
    # loop; memoise vertices already known to reach the source (O(n) total).
    good = [False] * n
    good[s] = True
    for v in range(n):
        if ref[v] is None:
            continue
        path, x = [], v
        while not good[x] and len(path) <= n:
            path.append(x)
            x = edges[par[x]][0]
        if not good[x]:
            return False, f"parent chain of {v} does not reach source"
        for y in path:
            good[y] = True
    return True, "ok"


CHECKERS = {
    "dsu": check_dsu, "kruskal": check_forest, "prim": check_forest,
    "scc": check_scc, "topo": check_topo, "dag": check_dag,
}


def validate(req, ans):
    return CHECKERS[req["task"]](req, ans)

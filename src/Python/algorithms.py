"""Graph algorithms for Assignment 3 (Campus festival).

All depth-first searches are iterative (explicit stacks), so deep graphs
such as a chain of 100000 vertices never hit Python's recursion limit.
Every function builds its own local data structures, so no state survives
between requests.
"""

import heapq


# ---------------------------------------------------------------------------
# Disjoint-set union (used by `dsu` and by `kruskal`)
# ---------------------------------------------------------------------------

class DisjointSet:
    """Union by size + path compression."""

    def __init__(self, n):
        self.parent = list(range(n))   # parent[v] == v  ->  v is a root
        self.size = [1] * n            # size[root] = number of vertices in its set
        self.components = n
        self.largest = 1 if n > 0 else 0

    def find(self, v):
        # 1st pass: walk up to the root.
        root = v
        while self.parent[root] != root:
            root = self.parent[root]
        # 2nd pass: path compression - point every vertex on the path to root.
        while self.parent[v] != root:
            next_v = self.parent[v]
            self.parent[v] = root
            v = next_v
        return root

    def union(self, u, v):
        """Merge the sets of u and v. Return True if they were different."""
        ru = self.find(u)
        rv = self.find(v)
        if ru == rv:
            return False                       # already connected / self-union
        if self.size[ru] < self.size[rv]:      # union by size: small under large
            ru, rv = rv, ru
        self.parent[rv] = ru
        self.size[ru] += self.size[rv]
        self.components -= 1
        if self.size[ru] > self.largest:
            self.largest = self.size[ru]
        return True


def dsu(request):
    """DSU with path compression and union by size; return states."""
    n = request["n"]
    operations = request["operations"]

    sets = DisjointSet(n)
    states = []
    for u, v in operations:
        sets.union(u, v)
        states.append([sets.components, sets.largest])
    return {"states": states}


# ---------------------------------------------------------------------------
# Minimum spanning forest
# ---------------------------------------------------------------------------

def kruskal(request):
    """Separate Kruskal implementation; return cost, edge_ids, components."""
    n = request["n"]
    edges = request["edges"]

    # Sort edge IDs (not edges) by weight, so original IDs are preserved.
    order = sorted(range(len(edges)), key=lambda i: edges[i][2])

    sets = DisjointSet(n)
    cost = 0
    edge_ids = []
    for i in order:
        u, v, w = edges[i]
        if u == v:
            continue                  # a self-loop never joins two trees
        if sets.union(u, v):          # accept only if find(u) != find(v)
            cost += w
            edge_ids.append(i)
            if len(edge_ids) == n - 1:
                break                 # a spanning tree is already complete

    return {"cost": cost, "edge_ids": edge_ids, "components": sets.components}


def prim(request):
    """Separate Prim implementation; restart for every unvisited component."""
    n = request["n"]
    edges = request["edges"]

    # Adjacency lists: adj[u] = list of (weight, neighbour, edge_id).
    adj = [[] for _ in range(n)]
    for i, (u, v, w) in enumerate(edges):
        if u == v:
            continue                  # self-loops are never useful
        adj[u].append((w, v, i))
        adj[v].append((w, u, i))

    in_tree = [False] * n
    cost = 0
    edge_ids = []
    components = 0

    for start in range(n):            # restart in every component
        if in_tree[start]:
            continue
        components += 1
        in_tree[start] = True
        heap = list(adj[start])       # lazy heap of candidate edges (w, to, id)
        heapq.heapify(heap)
        while heap:
            w, v, i = heapq.heappop(heap)
            if in_tree[v]:
                continue              # stale entry: both ends already in tree
            in_tree[v] = True
            cost += w
            edge_ids.append(i)
            for item in adj[v]:
                if not in_tree[item[1]]:
                    heapq.heappush(heap, item)

    return {"cost": cost, "edge_ids": edge_ids, "components": components}


# ---------------------------------------------------------------------------
# Helpers for directed graphs
# ---------------------------------------------------------------------------

def _adjacency(n, edges):
    adj = [[] for _ in range(n)]
    for e in edges:
        adj[e[0]].append(e[1])
    return adj


def _finish_order(n, adj):
    """Iterative DFS over all vertices; return vertices in finish order.

    The stack keeps (vertex, index of next neighbour) so a suspended vertex
    continues where it stopped and never rescans neighbours.
    """
    visited = [False] * n
    order = []
    for start in range(n):
        if visited[start]:
            continue
        visited[start] = True
        stack = [[start, 0]]
        while stack:
            top = stack[-1]
            v, k = top
            neighbours = adj[v]
            if k < len(neighbours):
                top[1] = k + 1
                w = neighbours[k]
                if not visited[w]:
                    visited[w] = True
                    stack.append([w, 0])
            else:
                stack.pop()
                order.append(v)       # v finished
    return order


# ---------------------------------------------------------------------------
# Strongly connected components (Kosaraju)
# ---------------------------------------------------------------------------

def scc(request):
    """Kosaraju with two DFS passes; return component and condensation."""
    n = request["n"]
    edges = request["edges"]

    adj = _adjacency(n, edges)
    radj = [[] for _ in range(n)]     # transposed graph
    for u, v in edges:
        radj[v].append(u)

    # Pass 1: finish order on the original graph.
    order = _finish_order(n, adj)

    # Pass 2: DFS on the transpose in decreasing finish order.
    component = [-1] * n
    label = 0
    for start in reversed(order):
        if component[start] != -1:
            continue
        component[start] = label
        stack = [start]
        while stack:
            v = stack.pop()
            for u in radj[v]:
                if component[u] == -1:
                    component[u] = label
                    stack.append(u)
        label += 1

    # Condensation: every distinct cross-component pair once.
    seen = set()
    condensation = []
    for u, v in edges:
        a = component[u]
        b = component[v]
        if a != b and (a, b) not in seen:
            seen.add((a, b))
            condensation.append([a, b])

    return {"component": component, "condensation": condensation}


# ---------------------------------------------------------------------------
# Topological order (three-state DFS)
# ---------------------------------------------------------------------------

UNVISITED, ACTIVE, FINISHED = 0, 1, 2


def _topological_order(n, adj):
    """Return (acyclic, order). order is empty when a cycle exists."""
    state = [UNVISITED] * n
    finished = []
    for start in range(n):
        if state[start] != UNVISITED:
            continue
        state[start] = ACTIVE
        stack = [[start, 0]]
        while stack:
            top = stack[-1]
            v, k = top
            neighbours = adj[v]
            if k < len(neighbours):
                top[1] = k + 1
                w = neighbours[k]
                if state[w] == ACTIVE:
                    return False, []          # back edge -> directed cycle
                if state[w] == UNVISITED:
                    state[w] = ACTIVE
                    stack.append([w, 0])
                # FINISHED neighbour: already placed, not a cycle
            else:
                stack.pop()
                state[v] = FINISHED
                finished.append(v)
    finished.reverse()                        # reverse finish order
    return True, finished


def topo(request):
    """Three-state DFS and reverse finish order; return acyclic and order."""
    n = request["n"]
    edges = request["edges"]

    acyclic, order = _topological_order(n, _adjacency(n, edges))
    return {"acyclic": acyclic, "order": order}


# ---------------------------------------------------------------------------
# DAG shortest paths + route helper
# ---------------------------------------------------------------------------

def dag(request):
    """Whole-graph cycle check and DAG relaxation; add your own route helper."""
    n = request["n"]
    source = request["source"]
    edges = request["edges"]

    acyclic, order = _topological_order(n, _adjacency(n, edges))
    if not acyclic:                       # cycle anywhere, even unreachable
        return {"acyclic": False, "distance": [], "parent_edge": []}

    out = [[] for _ in range(n)]          # out[u] = list of edge IDs from u
    for i, e in enumerate(edges):
        out[e[0]].append(i)

    distance = [None] * n                 # None = unreachable (JSON null)
    parent_edge = [-1] * n
    distance[source] = 0

    for u in order:
        if distance[u] is None:
            continue                      # never relax from unreachable vertices
        du = distance[u]
        for i in out[u]:
            _, v, w = edges[i]
            if distance[v] is None or du + w < distance[v]:
                distance[v] = du + w
                parent_edge[v] = i

    return {"acyclic": True, "distance": distance, "parent_edge": parent_edge}


def reconstruct_route(edges, parent_edge, source, target):
    """Rebuild the vertex sequence source -> target from parent_edge IDs.

    Returns [source] for target == source, and None when target is
    unreachable (its parent_edge is -1 and it is not the source).
    Runs in O(L) for a route of L vertices.
    """
    if target == source:
        return [source]
    if parent_edge[target] == -1:
        return None                       # no route
    route = [target]
    v = target
    while v != source:
        u = edges[parent_edge[v]][0]      # the edge ends at v, starts at u
        route.append(u)
        v = u
    route.reverse()
    return route

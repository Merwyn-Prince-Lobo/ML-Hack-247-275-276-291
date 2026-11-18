from dataclasses import dataclass
from pathlib import Path
import heapq
import numpy as np
from scipy.spatial import cKDTree

FEATURES = ['distance_m', 'heading_disagreement', 'projection_fraction', 'segment_length_m',
            'speed_mps', 'time_gap_s', 'distance_rank', 'distance_above_best_m',
            'previous_distance_m', 'next_distance_m', 'heading_available']
EARTH = 6371008.8

@dataclass
class Trip:
    trip_id: str
    gps: np.ndarray
    nodes: np.ndarray
    arcs: np.ndarray
    xy: np.ndarray
    points: np.ndarray

def load_trip(folder):
    folder = Path(folder)
    def read(ext, dtype=float):
        a = np.loadtxt(folder / (folder.name + '.' + ext), dtype=dtype, ndmin=2)
        if not np.isfinite(a).all():
            raise ValueError(f'{ext}: non-finite values')
        return a
    gps, nodes, arcs = read('track'), read('nodes'), read('arcs', np.int64)
    if gps.shape[1] != 3 or nodes.shape[1] != 2 or arcs.shape[1] != 2:
        raise ValueError('Expected track=3, nodes=2, arcs=2 columns')
    if len(gps) < 2 or len(arcs) < 1 or (np.diff(gps[:, 2]) < 0).any():
        raise ValueError('Need >=2 ordered observations and nonempty road network')
    if arcs.min() < 0 or arcs.max() >= len(nodes):
        raise ValueError('Arc references an invalid node')
    if (np.abs(nodes[:, 0]) > 180).any() or (np.abs(nodes[:, 1]) > 90).any():
        raise ValueError('Invalid geographic coordinates')
    if (np.abs(gps[:, 0]) > 180).any() or (np.abs(gps[:, 1]) > 90).any():
        raise ValueError('Invalid GPS coordinates')
    origin = nodes.mean(axis=0)
    scale = EARTH * np.pi / 180 * np.array([np.cos(np.deg2rad(origin[1])), 1])
    return Trip(folder.name, gps, nodes, arcs, (nodes-origin)*scale, (gps[:, :2]-origin)*scale)

def project(points, a, b):
    delta = b-a
    frac = np.clip(np.sum((points-a)*delta, axis=-1) / np.maximum(np.sum(delta*delta, axis=-1), 1e-12), 0, 1)
    snapped = a + frac[..., None]*delta
    return np.linalg.norm(points-snapped, axis=-1), frac, snapped

def candidates(trip, k=8):
    """Exact top-k segment search using midpoint radius bounds (no route labels)."""
    a, b = trip.xy[trip.arcs[:, 0]], trip.xy[trip.arcs[:, 1]]
    mid, length = (a+b)/2, np.linalg.norm(b-a, axis=1)
    k = min(k, len(a))
    tree = cKDTree(mid)
    _, seed = tree.query(trip.points, k=k)
    seed = np.asarray(seed).reshape(len(trip.points), k)
    ds, _, _ = project(trip.points[:, None, :], a[seed], b[seed])
    # Any segment closer than the seed kth distance has its midpoint within
    # kth distance + half the longest segment. This ensures exact retrieval.
    pools = tree.query_ball_point(trip.points, ds.max(axis=1)+length.max()/2+1e-6)
    ids = np.empty((len(trip.points), k), dtype=int)
    for t, pool in enumerate(pools):
        pool = np.asarray(pool)
        d, _, _ = project(trip.points[t], a[pool], b[pool])
        ids[t] = pool[np.lexsort((pool, d))[:k]]
    dist, frac, snap = project(trip.points[:, None, :], a[ids], b[ids])
    delta = np.gradient(trip.points, axis=0)
    norm = np.linalg.norm(delta, axis=1)
    direction = b[ids]-a[ids]
    cosine = np.sum(delta[:, None, :]*direction, axis=2)/np.maximum(norm[:, None]*length[ids], 1e-9)
    dt = np.maximum(np.r_[1, np.diff(trip.gps[:, 2])], 1)
    speed = np.r_[0, np.linalg.norm(np.diff(trip.points, axis=0), axis=1)]/dt
    prev = np.vstack([trip.points[0], trip.points[:-1]])
    nex = np.vstack([trip.points[1:], trip.points[-1]])
    pd, _, _ = project(prev[:, None, :], a[ids], b[ids])
    nd, _, _ = project(nex[:, None, :], a[ids], b[ids])
    x = np.stack([dist, 1-cosine, frac, length[ids], np.broadcast_to(speed[:, None], dist.shape),
                  np.broadcast_to(dt[:, None], dist.shape), np.broadcast_to(np.arange(k), dist.shape),
                  dist-dist[:, :1], pd, nd, np.broadcast_to((norm > 2)[:, None], dist.shape)], axis=-1)
    return {'ids': ids, 'x': x.astype(np.float32), 'frac': frac, 'snap': snap, 'length': length}

def reference_labels(trip, folder):
    """Weak observation labels: monotone alignment to ordered reference arcs.

    Supervision/evaluation only. Never used by candidates() or decode().
    Repeated route arcs remain separate positions during dynamic programming.
    """
    route = np.loadtxt(Path(folder)/(trip.trip_id+'.route'), dtype=np.int64, ndmin=1)
    if not len(route) or route.min() < 0 or route.max() >= len(trip.arcs):
        raise ValueError('Invalid reference route')
    a, b = trip.xy[trip.arcs[route, 0]], trip.xy[trip.arcs[route, 1]]
    d, _, _ = project(trip.points[:, None, :], a[None, :], b[None, :])
    cost = np.minimum(d, 2000)**2
    back = np.zeros(cost.shape, dtype=np.int32)
    score = cost[0].copy()
    for t in range(1, len(cost)):
        # Cumulative minimum enforces chronology without assuming 1 GPS row/arc.
        idx = np.minimum.accumulate(score)
        best = np.zeros(len(route), dtype=np.int32)
        best[1:] = np.where(score[1:] < idx[:-1], np.arange(1, len(route)), 0)
        best = np.maximum.accumulate(best)
        back[t] = best
        score = cost[t]+idx
    pos = np.empty(len(cost), dtype=int)
    pos[-1] = score.argmin()
    for t in range(len(cost)-1, 0, -1):
        pos[t-1] = back[t, pos[t]]
    return route[pos], d[np.arange(len(d)), pos], route

def probabilities(model, x):
    p = model.predict_proba(x.reshape(-1, x.shape[-1]))[:, 1].reshape(x.shape[:2])
    p = np.clip(p, 1e-8, 1)
    return p/p.sum(axis=1, keepdims=True)

class Network:
    def __init__(self, trip):
        self.trip = trip
        self.length = np.linalg.norm(trip.xy[trip.arcs[:, 1]]-trip.xy[trip.arcs[:, 0]], axis=1)
        self.adj = [[] for _ in trip.nodes]
        for arc, (u, v) in enumerate(trip.arcs):
            self.adj[u].append((int(v), float(self.length[arc]), arc))
        self.cache = {}

    def search(self, source, limit):
        key = (int(source), float(limit))
        if key in self.cache:
            return self.cache[key]
        dist, parent, queue = {int(source): 0.}, {}, [(0., int(source))]
        while queue:
            value, u = heapq.heappop(queue)
            if value > dist[u]:
                continue
            for v, weight, arc in self.adj[u]:
                alt = value+weight
                if alt <= limit and alt < dist.get(v, np.inf):
                    dist[v], parent[v] = alt, (u, arc)
                    heapq.heappush(queue, (alt, v))
        if len(self.cache) > 10000:
            self.cache.clear()
        self.cache[key] = (dist, parent)
        return dist, parent

    def transition(self, left, right, lf, rf, limit):
        if left == right and rf >= lf:
            return (rf-lf)*self.length[left]
        u, v = self.trip.arcs[left, 1], self.trip.arcs[right, 0]
        dist, _ = self.search(u, limit)
        return (1-lf)*self.length[left]+dist.get(int(v), np.inf)+rf*self.length[right]

def decode(trip, c, p, beta=30., gap_s=60., disconnect_penalty=18.):
    net = Network(trip)
    n, k = p.shape
    score, back = np.log(p[0]), np.zeros((n, k), dtype=int)
    resets = []
    for t in range(1, n):
        dt = trip.gps[t, 2]-trip.gps[t-1, 2]
        observed = np.linalg.norm(trip.points[t]-trip.points[t-1])
        if dt > gap_s or dt <= 0:
            resets.append(t)
            back[t] = score.argmax()
            score = score.max()+np.log(p[t])
            continue
        limit = float(max(300, observed*3+100, dt*50))
        transition = np.empty((k, k))
        for i in range(k):
            for j in range(k):
                road = net.transition(c['ids'][t-1, i], c['ids'][t, j], c['frac'][t-1, i], c['frac'][t, j], limit)
                transition[i, j] = -abs(road-observed)/beta if np.isfinite(road) else -disconnect_penalty
        values = score[:, None]+transition
        back[t] = values.argmax(axis=0)
        score = values.max(axis=0)+np.log(p[t])
        score -= score.max()
    choice = np.empty(n, dtype=int)
    choice[-1] = score.argmax()
    for t in range(n-1, 0, -1):
        choice[t-1] = back[t, choice[t]]
    return c['ids'][np.arange(n), choice], choice, resets

def route_geometry(trip, ids):
    """Connect selected directed arcs where reachable; retain explicit breaks."""
    net, lines, breaks, route = Network(trip), [], [], []
    for arc in ids:
        arc = int(arc)
        if route and arc == route[-1]:
            continue
        if route:
            source, target = trip.arcs[route[-1], 1], trip.arcs[arc, 0]
            dist, parent = net.search(source, 5000.)
            if int(target) in dist:
                bridge, node = [], int(target)
                while node != source:
                    node, edge = parent[node]
                    bridge.append(edge)
                for edge in reversed(bridge):
                    route.append(edge)
                    lines.append(trip.nodes[trip.arcs[edge]].tolist())
            else:
                breaks.append(len(route))
        route.append(arc)
        lines.append(trip.nodes[trip.arcs[arc]].tolist())
    return route, lines, breaks

def continuity(trip, ids):
    net = Network(trip)
    good, total = 0, 0
    for t in range(1, len(ids)):
        dt = trip.gps[t, 2]-trip.gps[t-1, 2]
        if dt <= 0 or dt > 60:
            continue
        total += 1
        observed = np.linalg.norm(trip.points[t]-trip.points[t-1])
        limit = float(max(300, observed*3+100, dt*50))
        left, right = int(ids[t-1]), int(ids[t])
        _, lf, _ = project(trip.points[t-1], trip.xy[trip.arcs[left, 0]], trip.xy[trip.arcs[left, 1]])
        _, rf, _ = project(trip.points[t], trip.xy[trip.arcs[right, 0]], trip.xy[trip.arcs[right, 1]])
        good += np.isfinite(net.transition(left, right, lf, rf, limit))
    return float(good/total) if total else 1.

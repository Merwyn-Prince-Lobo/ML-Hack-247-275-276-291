import csv
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from .experiments import DATA, RESULTS, write_json
from .core import load_trip

def main():
    RESULTS.mkdir(exist_ok=True)
    rows = []
    for split in ['train', 'student_test']:
        for folder in sorted((DATA/split).iterdir()):
            if not folder.is_dir():
                continue
            t = load_trip(folder)
            gaps = np.diff(t.gps[:, 2])
            graph = coo_matrix((np.ones(len(t.arcs)), (t.arcs[:, 0], t.arcs[:, 1])), shape=(len(t.nodes), len(t.nodes))).tocsr()
            components = connected_components(graph, directed=True, connection='weak', return_labels=False)
            degree = np.bincount(t.arcs.ravel(), minlength=len(t.nodes))
            rows.append(dict(split=split, trip_id=t.trip_id, observations=len(t.gps), nodes=len(t.nodes), arcs=len(t.arcs),
                missing_values=0, duplicate_timestamps=int((gaps == 0).sum()), gaps_over_1s=int((gaps > 1).sum()),
                max_gap_seconds=float(gaps.max()), median_gap_seconds=float(np.median(gaps)), one_second_steps=int((gaps == 1).sum()),
                weak_components=int(components), isolated_nodes=int((degree == 0).sum()),
                gps_distance_m=float(np.linalg.norm(np.diff(t.points, axis=0), axis=1).sum()),
                longitude_min=float(t.gps[:, 0].min()), longitude_max=float(t.gps[:, 0].max()),
                latitude_min=float(t.gps[:, 1].min()), latitude_max=float(t.gps[:, 1].max()),
                reference_arcs=int(np.loadtxt(folder/(t.trip_id+'.route'), ndmin=1).size),
                bytes=sum(p.stat().st_size for p in folder.iterdir() if p.is_file())))
    with (RESULTS/'inventory.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    summary = {}
    for split in ['train', 'student_test']:
        part = [r for r in rows if r['split'] == split]
        summary[split] = {'trips': len(part), 'observations': sum(r['observations'] for r in part),
            'missing_values': sum(r['missing_values'] for r in part), 'max_gap_seconds': max(r['max_gap_seconds'] for r in part),
            'one_second_fraction': sum(r['one_second_steps'] for r in part)/sum(r['observations']-1 for r in part),
            'total_isolated_nodes': sum(r['isolated_nodes'] for r in part),
            'trips_with_multiple_components': sum(r['weak_components'] > 1 for r in part)}
    write_json(RESULTS/'eda.json', summary)
    print(summary, flush=True)

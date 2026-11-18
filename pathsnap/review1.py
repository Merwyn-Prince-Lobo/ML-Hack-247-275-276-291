"""Export inspectable Review 1 evidence from a supplied TRAINING trip."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
import folium
from .core import load_trip, candidates, reference_labels, Network, FEATURES

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'data'/'Student folder'
RESULTS = ROOT/'results'

def write_csv(path, header, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)

def main(trip_id='00000003', data_dir=None, results_dir=None):
    if len(trip_id) != 8 or not trip_id.isascii() or not trip_id.isdigit():
        raise ValueError('Choose an eight-digit training trip ID')
    folder = Path(data_dir if data_dir is not None else DATA)/'train'/trip_id
    trip = load_trip(folder)
    c = candidates(trip)
    labels, alignment_distance, reference_route = reference_labels(trip, folder)
    net = Network(trip)
    graph = coo_matrix((np.ones(len(trip.arcs)), (trip.arcs[:, 0], trip.arcs[:, 1])), shape=(len(trip.nodes), len(trip.nodes))).tocsr()
    components, component_ids = connected_components(graph, directed=True, connection='weak')
    degree = np.bincount(trip.arcs.ravel(), minlength=len(trip.nodes))
    out = Path(results_dir if results_dir is not None else RESULTS)/'review1'/trip_id
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out/'nodes.csv', ['node_id','longitude','latitude','x_m','y_m','weak_component_id','incident_arc_count'],
        ([i,*trip.nodes[i],*trip.xy[i],component_ids[i],degree[i]] for i in range(len(trip.nodes))))
    write_csv(out/'arcs.csv', ['arc_id','from_node_id','to_node_id','length_m'],
        ([i,*trip.arcs[i],net.length[i]] for i in range(len(trip.arcs))))
    gaps = np.r_[np.nan, np.diff(trip.gps[:, 2])]
    write_csv(out/'gps_projected.csv', ['observation_id','longitude','latitude','timestamp_s','x_m','y_m','raw_time_gap_s'],
        ([i,*trip.gps[i],*trip.points[i],'' if i == 0 else gaps[i]] for i in range(len(trip.gps))))
    chosen = set(np.unique(np.linspace(0,len(trip.gps)-1,min(200,len(trip.gps)),dtype=int)).tolist())
    write_csv(out/'candidate_features.csv', ['observation_id','candidate_arc_id','used_for_training',*FEATURES,'weak_binary_label'],
        ([t,int(arc),int(t in chosen),*c['x'][t,j],int(arc == labels[t])]
         for t in range(len(trip.gps)) for j,arc in enumerate(c['ids'][t])))
    write_csv(out/'weak_reference_labels.csv', ['observation_id','derived_reference_arc_id','alignment_distance_m'],
        ([t,int(labels[t]),alignment_distance[t]] for t in range(len(labels))))
    active = np.flatnonzero([bool(edges) for edges in net.adj])[:12]
    lines = ['Directed adjacency list: source_node -> (destination_node, length_m, arc_id)',
             'Only the first 12 nodes with outgoing arcs are printed. The graph contains every supplied arc.']
    for u in active:
        lines.append(f'{u} -> '+', '.join(f'({v}, {distance:.3f} m, arc {arc})' for v,distance,arc in net.adj[u]))
    (out/'adjacency_sample.txt').write_text('\n'.join(lines),encoding='utf-8')
    summary = dict(partition='train',trip_id=trip_id,observations=len(trip.gps),nodes=len(trip.nodes),
        directed_arcs=len(trip.arcs),weak_components=int(components),isolated_nodes=int((degree == 0).sum()),
        missing_numeric_values=int(sum(np.isnan(a).sum() for a in [trip.gps,trip.nodes])),
        duplicate_timestamps=int((gaps[1:] == 0).sum()),largest_time_gap_s=float(gaps[1:].max()),
        candidate_count_per_observation=c['ids'].shape[1],candidate_feature_rows=int(np.prod(c['ids'].shape)),
        features=FEATURES,training_observations=len(chosen),training_candidate_rows=len(chosen)*c['ids'].shape[1],
        candidate_miss_rate=float((~(c['ids'] == labels[:,None]).any(axis=1)).mean()),
        label_note='Weak labels from ordered reference route; used only for training/evaluation.',
        projection='Local equirectangular metric approximation about network mean coordinates.',
        checks='Finite values, expected columns, coordinate ranges, arc bounds, timestamp ordering; no imputation required.')
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    # Overview plus detailed directed candidate graph, all from actual geometry.
    t=len(trip.gps)//2
    ids=c['ids'][t]
    fig,axes=plt.subplots(1,2,figsize=(13,5.5))
    ax=axes[0]
    ax.add_collection(LineCollection(trip.xy[trip.arcs],colors='#a5afbc',linewidths=.45))
    ax.scatter(trip.points[:,0],trip.points[:,1],s=3,color='#1976c7',label='Raw GPS projected into metres')
    ax.autoscale();ax.set_aspect('equal');ax.set_title(f'Training trip {trip_id}: full road graph');ax.legend(fontsize=8)
    ax=axes[1]
    points=trip.xy[trip.arcs[ids]].reshape(-1,2)
    low=np.minimum(points.min(axis=0),trip.points[t])-25
    high=np.maximum(points.max(axis=0),trip.points[t])+25
    ax.add_collection(LineCollection(trip.xy[trip.arcs],colors='#d2d8df',linewidths=.7))
    for j,arc in enumerate(ids):
        u,v=trip.arcs[arc];a,b=trip.xy[[u,v]]
        ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',color=plt.cm.tab10(j),lw=2,connectionstyle=f'arc3,rad={.08 if j%2 else -.08}'))
        mid=(a+b)/2
        ax.annotate(f'arc {arc}',mid,xytext=(4,5+j%3*9),textcoords='offset points',fontsize=7,color=plt.cm.tab10(j))
    for node in np.unique(trip.arcs[ids]):
        point=trip.xy[node];ax.scatter(*point,s=18,color='#25354c');ax.annotate(f'node {node}',point,xytext=(3,-12),textcoords='offset points',fontsize=7)
    ax.scatter(*trip.points[t],s=90,marker='*',color='#e33b44',zorder=5,label=f'GPS observation {t}')
    ax.set_xlim(low[0],high[0]);ax.set_ylim(low[1],high[1]);ax.set_aspect('equal');ax.set_title('Directed candidate arcs: arrows show allowed direction');ax.legend(fontsize=8)
    for ax in axes:ax.set_xlabel('Local x (m)');ax.set_ylabel('Local y (m)');ax.grid(alpha=.15)
    fig.tight_layout();fig.savefig(out/'road_graph.png',dpi=160);plt.close(fig)
    m=folium.Map(location=trip.gps[:,:2].mean(axis=0)[::-1].tolist(),zoom_start=14)
    roads=folium.FeatureGroup(name='Directed road arcs (click for IDs)')
    for arc,(u,v) in enumerate(trip.arcs):
        folium.PolyLine(trip.nodes[[u,v],::-1].tolist(),color='#68788c',weight=2,
            tooltip=f'arc {arc}: node {u} -> node {v}; {net.length[arc]:.1f} m').add_to(roads)
    roads.add_to(m)
    nodes=folium.FeatureGroup(name='Nodes (click for IDs)',show=False)
    for node,point in enumerate(trip.nodes):
        folium.CircleMarker(point[::-1].tolist(),radius=2,color='#34495e',tooltip=f'node {node}').add_to(nodes)
    nodes.add_to(m)
    gps=folium.FeatureGroup(name='Original GPS observations')
    for i,point in enumerate(trip.gps):
        folium.CircleMarker(point[:2][::-1].tolist(),radius=2,color='#1976c7',tooltip=f'observation {i}; timestamp {point[2]}').add_to(gps)
    gps.add_to(m)
    folium.LayerControl().add_to(m)
    m.fit_bounds([trip.gps[:,:2].min(axis=0)[::-1].tolist(),trip.gps[:,:2].max(axis=0)[::-1].tolist()])
    m.save(str(out/'road_graph_map.html'))
    # Export invariants verify correspondence to original IDs and feature schema.
    assert sum(map(len,net.adj)) == len(trip.arcs)
    assert c['x'].shape == (*c['ids'].shape,len(FEATURES))
    print(json.dumps(summary,indent=2))
    print('\nGRAPH CONSTRUCTION SAMPLE\n'+'\n'.join(lines))
    print(f'\nReview 1 evidence saved to: {out}')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trip', default='00000003', help='Eight-digit training trip ID')
    parser.add_argument('--data-dir', type=Path, default=DATA,
                        help='Dataset directory containing the train folder')
    parser.add_argument('--results-dir', type=Path, default=RESULTS,
                        help='Directory for generated Review 1 evidence')
    args = parser.parse_args()
    main(args.trip, args.data_dir, args.results_dir)

# Person 2: geometry, directed graph and feature evidence

Contributor: N A Manasa (Person 2)  
Date: 18 November 2026

## Contribution and provenance

This branch follows Person 1's dataset/EDA commit `41439cc`.
The geometry and feature implementation was inherited from the existing
AI-assisted PathSnap workspace. The commits record its introduction into the
team repository, an exporter improvement, and generated evidence; they do not
claim that this implementation was originally written independently by Person 2.

The exporter was changed with Codex assistance to remove its import of
`DATA` and `RESULTS` from Person 3's `experiments.py`. It now defines the same
repository-relative defaults locally and supports `--trip`, `--data-dir`, and
`--results-dir` through `python -m pathsnap.review1`. Existing callers of
`main(trip_id)` remain supported. No feature definitions or model results were
changed, and no models were trained in this session.

The verification below was executed by Codex in this workspace. The contributor
copied and committed files sequentially and inspected the printed summary.

## Scope and pipeline

- `pathsnap/core.py`: `load_trip`, `project`, `candidates`, `reference_labels`,
  and `Network`, plus inherited decoder primitives.
- `pathsnap/review1.py`: inspectable graph, candidate-feature and weak-label exports.
- `results/review1/00000003/`: evidence for one supplied training trip.

`load_trip` validates finite values, column counts, geographic bounds, arc node
references and ordered timestamps. It subtracts the network's mean longitude
and latitude, then uses a local equirectangular approximation to obtain metres.

`project` clips the point-to-segment projection fraction to [0, 1]. `candidates`
uses a midpoint KD-tree radius bound and exact segment-distance ranking to
select up to eight candidates. Ties are ordered by original arc ID.

`Network` stores each supplied directed arc as an outgoing adjacency entry
`source -> (destination, length_m, arc_id)`. Reverse arcs are not invented.
`reference_labels` aligns observations monotonically to the ordered route;
these are weak labels, not independently verified observation-level truth.
Candidate generation does not read the reference route.

## Eleven feature meanings

| Feature | Meaning |
|---|---|
| `distance_m` | GPS-to-candidate segment distance in metres |
| `heading_disagreement` | One minus movement/arc direction cosine; 0 aligned, 2 opposite |
| `projection_fraction` | Clipped position along the directed segment |
| `segment_length_m` | Candidate segment length |
| `speed_mps` | Previous displacement divided by bounded time gap; first value is zero |
| `time_gap_s` | Previous timestamp gap bounded below by one second; first value is one |
| `distance_rank` | Zero-based candidate distance rank |
| `distance_above_best_m` | Distance minus nearest candidate distance |
| `previous_distance_m` | Previous observation's distance to this candidate |
| `next_distance_m` | Next observation's distance to this candidate |
| `heading_available` | Movement-gradient magnitude exceeds two metres; a heuristic flag |

Arc IDs and labels are metadata, not model input features. Exports contain
unscaled features. Scaling belongs in the relevant model-training pipeline.

## Commands executed and observed results

From the cloned repository, Codex checked the standalone CLI help and ran:

```powershell
python -B -c "import sys; sys.path.append('../.deps'); from pathsnap.review1 import main; main('00000003', '../data/Student folder', '../tmp/person2-validation')"
```

The local `.deps` directory was used for installed libraries; it was not copied
or committed. Output was generated outside the clone, then selected evidence
files were copied into `results/review1/00000003/` in separate commits.

| Observed quantity | Value |
|---|---:|
| GPS observations | 821 |
| Nodes | 9,138 |
| Directed arcs | 18,028 |
| Weakly connected components | 42 |
| Isolated nodes | 0 |
| Candidates per observation | 8 |
| Candidate rows | 6,568 |
| Features per candidate | 11 |
| Marked training observations | 200 |
| Marked training candidate rows | 1,600 |
| Candidate miss rate against weak labels | 0.0085261876 (about 0.85%) |

The exporter completed its adjacency-count and feature-shape assertions.
A separate standard-library CSV check verified all table row counts, all arc
lengths against exported node coordinates, candidate groups of eight with
unique IDs and ranks 0 through 7, training-selection counts, and every binary
label against the exported weak reference label. These checks passed.

## Independently calculated feature row

Observation 0, candidate arc 9853, runs from node 5049 to node 5048.
Using the exported node and GPS metric coordinates, the check calculated:

```text
d = segment_end - segment_start
fraction = clip(dot(GPS - segment_start, d) / dot(d, d), 0, 1)
distance = norm(GPS - (segment_start + fraction * d))

Calculated fraction: 0.6711139791951775
CSV fraction:        0.67111397
Calculated distance: 1.1725376753405152 m
CSV distance:        1.1725377 m
```

The values agree within float32 rounding. Rank is 0 and distance above best
is 0, so this is the nearest candidate. Its weak binary label is nevertheless
0: nearest-road selection does not necessarily match the aligned reference.
The first observation's speed of 0 and time gap of 1 are initialization
conventions, not a measured prior movement interval.

## Reproduction after installing dependencies

Required exporter libraries: NumPy, SciPy, Matplotlib and Folium. From the
repository root, with the supplied dataset available in the parent workspace:

```powershell
python -m pathsnap.review1 --trip 00000003 --data-dir '../data/Student folder'
```

This writes to `results/review1/00000003/` by default. A fresh machine must
install the libraries and provide the original dataset. The optional generated
`road_graph_map.html` is not included in this branch; the PNG and CSV evidence
are available offline. Inspect Git status before staging regenerated outputs.

## Limitations and handoff

- The metric projection is a local approximation.
- Next-observation context makes these features an offline method.
- `heading_available` does not suppress the heading-disagreement value.
- Time gaps influence features; this change does not improve heading handling
  around gaps or claim an ablation result.
- Verification covers one demonstration trip and structural/numerical checks;
  it does not establish classifier accuracy or exhaustive correctness.
- Weak label agreement is not independent ground truth. Missing reference arcs
  from the candidate set limit possible agreement.
- The 200-observation selection flag describes the intended sampling rule;
  exporting it does not mean training was executed here.

Person 3 can use the unchanged core feature definitions for grouped model
experiments. Person 4 owns shared entry-point, integration and packaging work.

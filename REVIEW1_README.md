# PathSnap - Review 1 preparation and demonstration

This is the single preparation guide for Review 1: problem understanding, dataset understanding, EDA, preprocessing, graph construction, feature engineering, model choices, model selection and training. It includes the exact files to show, commands to run, measured results and viva answers.

The explanations describe the implementation in this repository. Example scenarios are illustrative; tables explicitly described as results come from executed experiments. Use this guide to understand the reasoning and explain it in your own words. Codex assisted with implementation, execution and documentation; follow the event's disclosure requirements.

## 1. What to demonstrate in Review 1

| Review topic | What we need to explain | Evidence to show |
|---|---|---|
| Problem understanding | Why noisy GPS does not directly identify a road; point matching versus route reconstruction | Road graph image and original input files |
| Dataset understanding | Meaning of track, nodes, arcs and reference route; local identifiers and unequal row counts | Original trip files and exported node/arc tables |
| EDA | Missing values, trip sizes, time gaps, network sizes and connectivity | `results/inventory.csv`, `results/eda.json` |
| Preprocessing | Validation, metric coordinates, timestamps and graph representation | `pathsnap/core.py`, projected GPS CSV and adjacency sample |
| Feature engineering | Observation-candidate rows and all eleven features | `candidates()` and exported candidate-feature table |
| Model choices | Why five distinct models; assumptions, objectives and alternatives | `model_factory()` and comparison table |
| Training and selection | Sampling, grouped folds, metrics and selection evidence | `results/protocol.json`, `results/models.json` and comparison plot |

The Review 1 demonstration can run without retraining a classifier. The complete project also includes tuning, decoding, API and UI; those are later-stage context unless the reviewer asks.

## 2. Run the Review 1 demonstration

### 2.1 Use this existing workspace

Open PowerShell and run:

```powershell
Set-Location -LiteralPath 'D:\sem 5\ML\Hackathon'
python run.py explore
python run.py review1 --trip 00000003
```

The first command audits all 80 training and 10 student-test trips. The second directly processes training trip `00000003`, constructs its graph and candidate features, and exports inspectable evidence. It does not load or retrain a classifier. Allow time for the large Folium HTML file to finish writing.

Expected evidence for this demonstration trip:

| Item | Actual value |
|---|---:|
| GPS observations | 821 |
| Nodes | 9,138 |
| Directed arcs | 18,028 |
| Weakly connected components | 42 |
| Isolated nodes | 0 |
| Largest time gap | 2 seconds |
| Candidate segments per observation | 8 |
| Exported candidate-feature rows | 6,568 |
| Sampled observations used for fitting | 200 |
| Candidate rows belonging to fitting sample | 1,600 |

Open the graph image and numerical summary:

```powershell
Invoke-Item '.\results\review1\00000003\road_graph.png'
Get-Content '.\results\review1\00000003\summary.json'
```

Open the interactive geographical graph:

```powershell
Invoke-Item '.\results\review1\00000003\road_graph_map.html'
```

The Folium page needs internet for its JavaScript and background map tiles. The PNG, CSV and TXT evidence works offline. In Folium, hover over a road to inspect its arc ID, source/destination nodes and length. Enable the node layer to inspect node IDs.

### 2.2 Fresh-computer installation, if necessary

Python 3.11 was used. From the extracted project root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run.py explore
.venv\Scripts\python.exe run.py review1 --trip 00000003
```

The existing workspace has optional downloaded packages under `.deps/`, which `run.py` appends to its search path. A fresh installation uses the listed pip requirements. If using a source-only checkout, extract the supplied dataset so it has this layout:

```text
data/Student folder/train/00000003/00000003.track
data/Student folder/train/00000003/00000003.nodes
data/Student folder/train/00000003/00000003.arcs
data/Student folder/train/00000003/00000003.route
data/Student folder/student_test/...
```

## 3. Problem statement and our understanding

### 3.1 The problem in plain language

GPS observations are measured vehicle positions. They are not exact road identifiers. Measurement error can place a vehicle beside its actual road, on a parallel road, or near an intersection where several segments are plausible.

PathSnap uses the observed trajectory and a directed road network to estimate which road segments explain the journey.

There are two related tasks:

1. **Observation-level map matching:** choose a road segment for each GPS observation.
2. **Route reconstruction:** use sequential and graph information to produce a coherent route.

The classifier scores individual candidate segments. The later decoder considers sequences of those candidates.

### 3.2 Why nearest-road matching is insufficient

Illustrative scenario: a main road and service road run alongside each other. GPS error makes some points closer to the service road even though the vehicle stayed on the main road. Independent nearest-road choices might alternate between roads or imply impossible direction changes.

Distance remains useful, but direction, neighbouring observations and connectivity provide additional evidence. We do not assume the nearest road is always wrong; we recognise that distance alone cannot resolve every ambiguity.

### 3.3 Inputs, outputs and boundaries

Inputs to prediction are GPS coordinates/timestamps and the supplied road nodes/arcs. Outputs include one predicted local arc ID per observation and reconstructed road geometry. Reference routes are used for supervised development and evaluation; they are not inputs to the prediction procedure.

This is an offline trajectory matcher. Features use neighbouring observations, including the next observation. We do not claim the current feature pipeline is causal streaming inference.

### 3.4 Opening explanation for the review

> PathSnap matches noisy vehicle GPS observations to a directed road network. We treat map matching as candidate suitability scoring, because proximity alone can be misleading around parallel roads and intersections. We first validate and inspect the data, construct metric geometry and a road graph, then create features for observation-candidate pairs. We compare five classifiers using trip-grouped validation before selecting a model. The sequential stage subsequently uses those scores and road connectivity to reconstruct a more coherent route.

## 4. Understand the four raw file types

| File | Columns/content | Meaning |
|---|---|---|
| `.track` | Longitude, latitude, timestamp in seconds | Chronological GPS observations |
| `.nodes` | Longitude, latitude | Coordinates of road-network vertices |
| `.arcs` | Source-node ID, destination-node ID | Directed segments connecting vertices |
| `.route` | Ordered arc IDs | Supplied reference road sequence |

Files have no header row. Node and arc IDs are zero-based row indices. For example, arc ID 0 refers to the first row of the `.arcs` file. Its two values refer to rows in `.nodes`.

An arc `u -> v` does not imply `v -> u`. A reverse arc must be explicitly supplied.

Two relationships must be understood:

- GPS observations and route entries are not paired by row number. Many observations can occur on one arc, and several arcs can be crossed between observations.
- Arc IDs are local to a trip's network. The same numeric ID in another trip need not mean the same geographical road. We therefore avoid treating the numeric IDs as a global shared multiclass target.

The supplied archives contain 80 training trips and 10 student-test trips. The ten reserved evaluator trips were not supplied in this workspace and were not used.

## 5. EDA: actual findings, interpretation and consequences

EDA means exploratory data analysis: inspect the data before choosing transformations and modelling assumptions. Its source is `pathsnap/explore.py`.

### 5.1 Dataset and trip sizes

| Property | Training | Student-test |
|---|---:|---:|
| Trips | 80 | 10 |
| GPS observations | 208,417 | 19,160 |
| Minimum observations per trip | 361 | 262 |
| Median observations per trip | 1,529 | 1,420 |
| Maximum observations per trip | 19,313 | 3,958 |

**Interpretation:** Long trips could dominate a row-based training dataset. Our fixed budget of 200 observations per training trip bounds fitting cost and gives trips similar representation. This is a design response to the size variation, not proof that 200 is optimal. Validation uses every observation.

### 5.2 Missing values and timestamp duplicates

Both partitions have zero missing numeric values and zero duplicate timestamps. Input validation also checks finite numbers, coordinate plausibility, timestamp ordering and node-reference bounds.

**Interpretation:** Imputation was unnecessary for the supplied data. Numerically complete data can still contain GPS measurement error; these checks do not prove that every position is physically accurate.

### 5.3 Sampling intervals and gaps

| Property | Training | Student-test |
|---|---:|---:|
| Intervals exactly 1 second | 96.50% | 98.62% |
| Trips with at least one gap above 60 seconds | 22 | 1 |
| Largest interval | 153,064 seconds | 210 seconds |

The largest training gap is in trip `00000090`, approximately 42 hours and 31 minutes.

**Interpretation:** One-second sampling is common but cannot be assumed universally. Movement must be interpreted with elapsed time. We retain timestamps, construct gap/speed features and reset the decoder across gaps above 60 seconds. The reset threshold is a chosen heuristic, not an EDA-proven optimum.

### 5.4 Graph connectivity

| Property | Training | Student-test |
|---|---:|---:|
| Trips with multiple weak components | 79 of 80 | 10 of 10 |
| Minimum weak components per network | 1 | 5 |
| Maximum weak components per network | 421 | 100 |
| Isolated nodes | 0 | 0 |

A weak component is a connected group when direction is temporarily ignored. Multiple weak components indicate disconnected groups even before considering one-way restrictions. No isolated nodes means each node touches at least one arc; it does not mean all nodes belong to one connected network.

**Interpretation:** Route reconstruction must handle unreachable transitions explicitly. It cannot assume every nearby road is reachable from the previous road. We preserve graph direction, search for valid paths and record breaks where display reconstruction cannot connect selected roads.

### 5.5 Network sizes

| Property | Training range | Student-test range |
|---|---:|---:|
| Nodes per trip | 299-155,003 | 1,770-26,635 |
| Directed arcs per trip | 649-307,392 | 3,577-56,027 |

**Interpretation:** Exhaustively scoring all roads for every observation would be expensive on large networks. Spatial candidate retrieval reduces the scoring problem to a fixed number of candidates per observation.

### 5.6 Representation findings

The files provide route sequences rather than direct observation labels, so label alignment is necessary. Local arc IDs motivate candidate suitability scoring rather than a shared global road-ID classifier.

### 5.7 Evidence and commands

```powershell
Get-Content '.\results\eda.json'

Import-Csv '.\results\inventory.csv' |
    Select-Object -First 10 |
    Format-Table trip_id,observations,nodes,arcs,missing_values,max_gap_seconds,weak_components -AutoSize
```

`inventory.csv` contains one row per trip, including file bytes, observation count, graph size, time-gap statistics, geographic bounds and connectivity. `eda.json` contains partition-level summaries. Ranges and medians above are calculated from the inventory.

Model accuracy and the winning algorithm are experimental findings, not EDA findings. We have not quantified the true GPS error distribution, proved every feature useful, or proved the supplied reference route is error-free.

## 6. Preprocessing: what we actually did

### 6.1 Read and validate

`load_trip()` in `pathsnap/core.py` reads the files and checks:

- Expected column counts: track=3, nodes=2, arcs=2.
- Finite numeric values.
- Longitude within [-180, 180] and latitude within [-90, 90].
- Arc endpoint indices within the available node range.
- At least two GPS observations and a nonempty road network.
- Nondecreasing timestamps.

Malformed inputs fail explicitly. We do not silently manufacture coordinates or road connections.

### 6.2 Missing values and retained observations

No missing-value imputation was required. We retain stationary observations because they can represent real stops. We do not blindly delete repeated positions, resample to an artificial 1 Hz grid, apply a Kalman filter or smooth every trajectory. The present pipeline does not remove all GPS noise before modelling.

### 6.3 Convert geographical angles into local metre coordinates

Longitude and latitude are angular coordinates. Euclidean differences in degrees are not appropriate physical distances because longitude scale changes with latitude.

We use a local equirectangular approximation about the mean network coordinates:

```text
x = R * cos(latitude_origin) * (longitude - longitude_origin)
y = R * (latitude - latitude_origin)
```

Angles in these equations are radians; `R = 6,371,008.8 m`. The code equivalently converts degree differences using `pi/180`.

This enables distances and segment lengths in approximate metres. It is a local approximation, not an exact global projected CRS. Original longitude/latitude is retained for geographical display.

Show the transformation output:

```powershell
Import-Csv '.\results\review1\00000003\gps_projected.csv' |
    Select-Object -First 5 |
    Format-Table observation_id,longitude,latitude,x_m,y_m,raw_time_gap_s -AutoSize
```

The first exported time gap is blank because no earlier observation exists. This is an undefined derived field, not a missing raw timestamp.

### 6.4 Time differences and observed speed

For consecutive points, raw time difference is `timestamp[t] - timestamp[t-1]`. Observed speed uses projected displacement divided by a numerically bounded interval. In the feature code, time intervals are lower-bounded at one second; the first feature interval is set to one and the first speed to zero. This is a defensive convention, not a claim of physically measured first-point speed.

Long gaps remain in the data. The sequential decoder resets above 60 seconds or at nonpositive intervals. Centred heading features can still be unreliable around gaps; the current feature code does not independently suppress all gap-adjacent heading estimates.

### 6.5 Learned scaling

Logistic Regression and Gaussian Naive Bayes use a `StandardScaler` inside a scikit-learn pipeline:

```text
standardised_value = (value - training_mean) / training_standard_deviation
```

Scaling is fitted only on each fold's training rows, then applied to validation rows. The three tree-based models do not use this scaler. The exported `candidate_features.csv` contains engineered, unscaled feature values.

## 7. Road graph construction and how to show it

### 7.1 Graph representation

The road network is a directed weighted graph `G = (V, E)`:

- `V`: node rows with geographical/projected coordinates.
- `E`: arc rows with a source and destination.
- Weight: approximate endpoint-to-endpoint segment length in metres.

`Network.__init__()` in `pathsnap/core.py` creates the adjacency list. The key operation is:

```python
self.adj[u].append((int(v), float(self.length[arc]), arc))
```

This stores an outgoing destination, length and original arc ID under source node `u`. It does not automatically insert a reverse edge.

The EDA also builds a sparse adjacency matrix in `pathsnap/explore.py` for connectivity analysis. These are two representations of the supplied graph for different tasks.

### 7.2 Actual adjacency output

```powershell
Get-Content '.\results\review1\00000003\adjacency_sample.txt'
```

One actual entry is:

```text
0 -> (7838, 153.193 m, arc 0), (3594, 12.439 m, arc 1), (154, 14.264 m, arc 2)
```

Explain it as: node 0 has three outgoing road arcs. Arc 0 goes from node 0 to node 7838 and is approximately 153.193 metres long. The file prints a sample; the in-memory graph contains every supplied arc.

### 7.3 Graph evidence

| Output | What to explain |
|---|---|
| `road_graph.png` | Left: full metric graph and GPS. Right: one GPS point and labelled candidate arcs with directional arrows. Colours distinguish candidates, not predictions. |
| `road_graph_map.html` | Geographic roads/GPS; hover for IDs and use layer controls for nodes |
| `nodes.csv` | Original IDs, longitude/latitude, projected x/y, component IDs and incident arc count |
| `arcs.csv` | Arc ID, source node, destination node and calculated length |
| `adjacency_sample.txt` | Inspectable outgoing-neighbour representation |

Use the image together with the tables: the picture explains geometry, while the CSVs show how IDs and directed connections are represented numerically.

## 8. Candidate generation

### 8.1 Why generate candidates?

The true road is usually expected to be among nearby segments, but scoring every road in a large network for every point is costly. We select up to eight nearest directed segments by point-to-segment projection distance. If a valid network has fewer than eight arcs, we use all its arcs. Empty networks fail input validation.

### 8.2 Point-to-segment distance

For GPS point `P` and segment endpoints `A`, `B`:

```text
u = clip(dot(P-A, B-A) / squared_length(B-A), 0, 1)
Q = A + u*(B-A)
distance = norm(P-Q)
```

`Q` is the nearest projected point. `u=0` means the segment start, `u=1` the end, and intermediate values lie inside the segment. Clipping prevents projection onto an infinite extension beyond the road endpoints. A numerical denominator floor handles zero-length geometry.

### 8.3 Why a midpoint KD-tree alone is insufficient

A long segment can pass close to a GPS point even when its midpoint is far away. We use a midpoint KD-tree for an initial set, calculate its exact projection distances, expand the midpoint search radius by half the longest segment length, and rerank the resulting pool by exact segment distance. The radius follows a triangle-inequality bound. Equal distances are resolved by arc ID.

Eight is a fixed computational budget, not a proven optimum. The student-test mean-trip candidate miss rate was approximately 0.392%. For the individual demonstration training trip it is approximately 0.853%; these values describe different data and should not be confused.

A candidate miss means the derived reference arc is absent from the set. The scorer cannot choose an absent arc. We retain those cases in evaluation and do not insert the reference candidate using label information.

## 9. Deriving observation-level labels

### 9.1 Why labels need alignment

The supplied reference is an ordered arc sequence, not one label per GPS row. An illustrative reference `5 -> 9 -> 12` might align to observations as `5, 5, 5, 9, 9, 12`. This is an example, not an actual experiment trace.

### 9.2 Monotone alignment

`reference_labels()` computes the distance from every GPS point to each position in the reference route, then uses dynamic programming:

```text
D[t, j] = cost[t, j] + minimum(D[t-1, h] for h <= j)
```

This permits staying on an arc or progressing through the ordered route, but prevents moving backwards through reference positions. Repeated occurrences of the same arc keep separate route positions. Initial and final positions are unconstrained.

The cost is squared distance after capping distance at 2,000 metres. This is a chosen heuristic, not a tuned optimal cap. Backtracking produces a derived arc ID per observation.

### 9.3 Label qualification and isolation

These are **weak labels**, since the source does not provide independently verified point-level truth. Reference inaccuracies, intersections, stationary observations and route ambiguities can affect them.

For training, a candidate receives binary label 1 if its arc matches the derived label; otherwise 0. A missing reference candidate leaves all candidates negative for that observation.

Candidates and features use GPS/nodes/arcs, not reference labels. The Review 1 exporter deliberately adds weak labels to a training-inspection CSV. That labelled training export is not an evaluator-UI response. The API performs prediction before loading reference data for optional server-side scoring.

## 10. The eleven engineered features

The feature names are listed in `FEATURES` near the beginning of `pathsnap/core.py`. Their calculations and the final `np.stack(...)` are inside `candidates()` in that same file. Do not run `core.py` directly expecting printed outputs; use the Review 1 command.

| # | Code name | Calculation/meaning | Reason for inclusion |
|---|---|---|---|
| 1 | `distance_m` | Current point-to-segment projection distance | Spatial compatibility |
| 2 | `heading_disagreement` | `1 - cosine` between estimated movement and directed segment | Directional compatibility, including opposite-direction roads |
| 3 | `projection_fraction` | Clipped projection fraction along segment | Position relative to segment endpoints |
| 4 | `segment_length_m` | Projected endpoint-to-endpoint length | Geometric context for candidate interpretation |
| 5 | `speed_mps` | Previous displacement / bounded elapsed time | Movement context |
| 6 | `time_gap_s` | Previous interval, lower-bounded at one second | Sampling context and irregular gaps |
| 7 | `distance_rank` | Zero-based distance rank among candidates | Relative proximity |
| 8 | `distance_above_best_m` | Candidate distance minus closest candidate distance | Strength of spatial evidence against an alternative |
| 9 | `previous_distance_m` | Previous GPS observation's distance to this segment | Local trajectory context |
| 10 | `next_distance_m` | Next GPS observation's distance to this segment | Upcoming movement context; makes this offline |
| 11 | `heading_available` | Positional-gradient magnitude above 2 m per observation-index step | Context for low-movement heading reliability |

### 10.1 Heading interpretation

For `1-cos(theta)`, approximately 0 means aligned, 1 perpendicular, and 2 opposite. The movement vector comes from positional gradients. It is not an independently measured compass heading. The availability flag is a heuristic; it does not remove the heading value when movement is small. First/last neighbouring positions use boundary conventions in the code.

### 10.2 Why relative distance helps

Illustrative candidate distances `5, 6, 7 m` describe a more ambiguous spatial choice than `5, 40, 90 m`, despite an identical best distance. Distance-above-best makes the cost of choosing an alternative explicit.

### 10.3 Shared context and feature interactions

Speed and time gap are shared by candidates belonging to the same observation. Their usefulness is primarily contextual. Nonlinear trees can combine them with candidate-specific geometry. A linear model has limited ability to use shared context to change the relative ordering. We do not claim these features alone identify a road.

### 10.4 What feature engineering does not prove

These are motivated features, not individually proven improvements. No feature-ablation study has been performed. We have not established causal effects, calibrated heading reliability or independent contributions for all eleven features.

### 10.5 Show actual feature rows

```powershell
Import-Csv '.\results\review1\00000003\candidate_features.csv' |
    Select-Object -First 8 |
    Format-Table observation_id,candidate_arc_id,distance_m,heading_disagreement,weak_binary_label -AutoSize
```

The first eight rows describe eight candidate roads for observation 0. The complete CSV has all eleven features plus observation/candidate IDs, `used_for_training` and `weak_binary_label`. The IDs and labels are metadata/targets, not extra model-input features.

## 11. Why candidate classification instead of global road classification?

Each learning example is an observation-candidate pair with eleven inputs and one binary label. The model learns suitability relationships rather than memorising a shared vocabulary of local arc numbers.

Illustrative example:

| Observation | Candidate arc | Distance | Heading disagreement | Label |
|---|---:|---:|---:|---:|
| A | 120 | 4 m | 1.8 | 0 |
| A | 341 | 7 m | 0.1 | 1 |
| A | 765 | 15 m | 0.4 | 0 |

These numbers are a teaching example. The slightly farther candidate may be preferable when it agrees with movement. The actual model learns from examples; we do not hardcode the example as a rule.

The training objective is binary classification, not a dedicated learning-to-rank objective. At inference we score candidates, clip positive scores for numerical stability and normalise within each observation. The highest score is the classifier-only selection; the decoder can choose another candidate based on sequence compatibility.

## 12. The five models: motivation, mechanism and configuration

We compared five distinct algorithms to test different assumptions: a linear probabilistic baseline, a simple generative baseline, a nonlinear single tree, a bagged ensemble and a boosted ensemble. We did not select the winner before running the comparison.

### 12.1 Logistic Regression

- **Mechanism:** `P(y=1 | x) = sigmoid(w*x + b)`; learns feature weights.
- **Objective:** binary logistic loss with L2 regularisation.
- **Configuration:** StandardScaler, `C=1`, `max_iter=500`, seed 352.
- **Why considered:** a compact baseline for whether a linear combination of engineered features suffices.
- **Strengths:** relatively simple, efficient, produces positive-class scores.
- **Limitations:** a linear decision function cannot automatically capture arbitrary feature interactions. Shared per-observation context is especially limited for candidate ordering.
- **Observed CV Macro F1:** 0.6938.

`C` controls inverse regularisation strength: smaller values apply stronger regularisation. `max_iter` limits optimisation iterations; it is not a neural-network epoch count.

### 12.2 Gaussian Naive Bayes

- **Mechanism:** combines class priors with class-conditional Gaussian feature likelihoods using Bayes' rule.
- **Objective/estimation:** estimates Gaussian means/variances and class priors; it is not trained by iterative gradient descent here.
- **Configuration:** StandardScaler, `var_smoothing=1e-9`.
- **Why considered:** a lightweight probabilistic comparison with different assumptions.
- **Strengths:** straightforward and inexpensive to fit.
- **Limitations:** conditional independence is questionable because distance, rank and related distance features are correlated. Gaussian assumptions may also be restrictive. Scaling does not make features independent.
- **Observed CV Macro F1:** 0.6645; it also had the poorest student-test log loss among the five models.

This supports saying its assumptions were less suitable in this experiment, not that Naive Bayes is universally unsuitable.

### 12.3 Decision Tree

- **Mechanism:** recursively partitions feature space using threshold decisions.
- **Objective:** greedy Gini impurity reduction.
- **Configuration:** `max_depth=12`, `min_samples_leaf=20`, seed 352.
- **Why considered:** tests nonlinear thresholds and interactions without requiring feature scaling.
- **Strengths:** flexible nonlinear rules; a useful comparison with linear scoring.
- **Limitations:** a single tree can be unstable and its leaf probabilities can be extreme.
- **Observed CV Macro F1:** 0.7083.

Depth limits tree complexity; minimum leaf size stops leaves from being supported by too few candidate examples. We have not manually transcribed its learned decision rules.

### 12.4 Random Forest

- **Mechanism:** learns bootstrapped, feature-randomised trees and averages their probability estimates.
- **Objective:** individual trees use Gini-based splitting; ensemble prediction averages trees.
- **Configuration:** 64 trees, `max_depth=16`, `min_samples_leaf=8`, `max_features=0.8`, seed 352.
- **Why considered:** retains nonlinear modelling while reducing reliance on a single tree.
- **Strengths:** can model interactions and smooth some single-tree instability.
- **Limitations:** larger storage/scoring requirements; averaging does not guarantee calibration or eliminate overfitting.
- **Observed CV Macro F1:** 0.7342, higher than the single tree.

### 12.5 Histogram Gradient Boosting

- **Mechanism:** adds trees sequentially to improve the current model's loss. A learning rate controls correction size. Histogram bins make numerical split search efficient.
- **Objective:** binary log loss.
- **Initial configuration:** `max_iter=100`, `max_leaf_nodes=15`, `learning_rate=0.1`, `l2_regularization=1`, seed 352.
- **Why considered:** our inputs are numerical tabular features with plausible nonlinear interactions.
- **Strengths:** flexible corrections and efficient numerical-feature handling.
- **Limitations:** configuration affects performance; weak labels can contain noise that a flexible model may fit.
- **Observed CV Macro F1:** 0.7369, the highest baseline score.

Maximum iterations limits boosting rounds, maximum leaves controls tree complexity, learning rate controls update size, and L2 regularisation penalises large leaf values. The fitted baseline completed 100 rounds; the tuned model completed 156.

The library's automatic early stopping was enabled. It uses internal validation within the supplied fitting data; that internal split is not the external trip-grouped validation used to compare models. We do not claim the internal early-stopping holdout itself was trip-grouped.

## 13. Why not other models?

We prioritised a manageable comparison of distinct algorithms on the engineered feature representation. Untested alternatives are not proven inferior.

| Alternative | Why it was not prioritised |
|---|---|
| Nearest road alone | Does not learn how distance should interact with direction or neighbouring movement; a useful future explicit baseline |
| K-nearest neighbours | Requires a justified feature-space metric/scaling and searching retained training examples during prediction |
| RBF SVM | Kernel fitting can be expensive at the candidate-example count; probability estimation adds decisions |
| MLP | Valid alternative, but introduces architecture, optimisation and regularisation choices; simpler tabular baselines were tested first |
| LSTM/Transformer | Requires a more involved sequence representation and training design; our implementation separates scoring from graph decoding |
| Graph neural network | Potentially relevant, but requires graph-specific representations/training across varying networks |
| K-means/DBSCAN | Clusters do not directly provide the desired supervised candidate labels; additional mapping is required |
| XGBoost/LightGBM/CatBoost | Reasonable extensions; this comparison already includes a histogram boosting model, but these libraries were not benchmarked |

Review answer: "We chose a set that tests different assumptions and complexity levels. We selected among models we actually evaluated. We do not claim an untested model could not improve the result."

## 14. Training examples, sampling and class imbalance

For each of the 80 training trips we use 200 uniformly spaced observations. All supplied training trips have at least 200 observations.

```text
80 trips * 200 observations = 16,000 sampled observations
16,000 observations * 8 candidates = 128,000 candidate rows
X shape = (128000, 11)
y shape = (128000,)
```

Actual sampled labels:

| Label | Candidate examples |
|---|---:|
| Positive / matches weak reference | 15,546 |
| Negative / does not match | 112,454 |

There are 454 sampled training observations without a positive candidate. This is a sampled-training statistic, not the student-test miss rate.

An all-negative classifier would reach approximately 87.85% binary candidate accuracy while providing no meaningful positive candidate identification. Consequently, binary row accuracy is not the primary selection metric. It is also different from observation-level Top-1 accuracy.

Uniform sampling controls cost and balances trip contributions; it can discard useful fitting observations. We do not claim that every raw training observation was used to fit the classifiers. All observations in held-out validation trips and student-test trips are evaluated.

## 15. Grouped cross-validation and leakage prevention

### 15.1 Three-fold GroupKFold

All candidate rows from a trip share that trip's group ID. The three validation folds contain 27, 27 and 26 trips. In each fold, the model is fitted on the other trips and evaluated on every observation in the held-out trips.

Why not a random row split? Candidate rows from one GPS observation and neighbouring observations are strongly related. A random split could distribute nearly identical situations across fitting and validation, making the evaluation easier than held-out-trip matching.

### 15.2 Training pipeline

For each of the five models:

1. Construct sampled candidate features, binary targets and trip groups from the 80 training trips.
2. Fit each of three grouped folds. Fit any scaler only on that fold's training rows.
3. Score every observation in the held-out trips and record per-trip metrics.
4. Average trip Macro F1 within each fold, then average the three fold scores.
5. Refit the baseline on the complete sampled training arrays.
6. Evaluate the fitted baseline on all ten supplied student-test trips.
7. Save its configuration, CV results, student-test results and trained artifact.

Seed 352 is used for the configured model/search randomness. Some estimators are deterministic without an explicit random seed. Exact timing depends on hardware and scheduling.

### 15.3 Boundaries and limitations

- No trip is split across the external CV fitting and validation partitions.
- Learned scaling is not fitted on the held-out fold.
- Reserved evaluator data is absent and unused.
- Reference information is legitimate supervised training/evaluation information; it is excluded from inference features.
- Different trips may cover overlapping geography. Trip grouping is not a proof of performance in an unseen city.
- Student-test data is development data. Decoder settings were later selected on it, so those decoder scores are development estimates.

## 16. Metrics and model selection

### 16.1 Top-1 accuracy

For each observation, select the highest-scoring candidate and compare its local arc ID with the derived reference arc. Average correctness within a trip, then average across student-test trips.

### 16.2 Precision, recall and Macro F1

For each local arc class:

```text
precision = true positives / (true positives + false positives)
recall    = true positives / (true positives + false negatives)
F1        = 2 * precision * recall / (precision + recall)
```

Macro F1 averages class F1 values, giving each evaluated arc equal weight within the trip. We use the union of predicted and derived-reference arc IDs. Undefined values are treated as zero by the configured metric. Then trip scores are averaged; CV additionally averages the three fold means.

This matters because many observations may lie on a long segment while only a few lie on a short connector. Accuracy can overlook poor recovery of the less frequent segments.

### 16.3 Candidate probability normalisation and log loss

The binary model supplies a positive-class score for each candidate. We clip scores to at least `1e-8` and normalise within each observation:

```text
candidate_mass[j] = positive_score[j] / sum(positive_scores)
```

Log loss measures `-log(mass_assigned_to_reference)`. A missing reference receives `1e-15` for scoring, so the case remains penalised. Mean trip losses are averaged. These normalised scores are useful emission masses, not established perfectly calibrated mutually exclusive posteriors.

### 16.4 Actual baseline comparison

| Model | Grouped CV Macro F1 | Student-test Top-1 | Student-test Macro F1 | Student-test log loss |
|---|---:|---:|---:|---:|
| Logistic Regression | 0.6938 | 0.8601 | 0.7108 | 0.6801 |
| Gaussian Naive Bayes | 0.6645 | 0.8383 | 0.6851 | 1.1712 |
| Decision Tree | 0.7083 | 0.8688 | 0.7398 | 0.8110 |
| Random Forest | 0.7342 | 0.8749 | 0.7567 | 0.4936 |
| Histogram Gradient Boosting | **0.7369** | **0.8757** | **0.7616** | **0.4847** |

Higher F1/accuracy is better; lower log loss is better. Scores use derived point labels, not independently verified observation truth.

The code selects the family with the highest grouped CV Macro F1. Student-test performance is recorded as additional development evidence. Histogram boosting leads Random Forest by only about 0.0026 absolute CV F1, so we do not claim overwhelming superiority or statistical significance.

### 16.5 What the results suggest

The tree ensembles outperform the linear and Gaussian baselines on held-out trip F1. This is consistent with useful nonlinear relationships in the engineered representation. It does not prove which feature caused the improvement. Gaussian Naive Bayes has poor relative probability loss, while the single tree's loss is worse than the ensembles despite reasonable Top-1 accuracy.

Do not diagnose "no overfitting" just because student-test results are higher than CV. The partitions differ. Do not compare training binary candidate accuracy directly with validation arc Macro F1 as though they were the same metric. No artificial epoch-wise training curves were generated for these models.

Show the comparison:

```powershell
Invoke-Item '.\results\figures\model_comparison.png'
Get-Content '.\results\protocol.json'
```

`results/models.json` retains configurations, fold scores, per-trip metrics and supporting results. `artifacts/` contains the five fitted baseline models.

## 17. Tuning and later-stage context, if asked

After selecting histogram boosting, ten actual Optuna TPE trials optimised the same trip-grouped CV Macro F1. Three startup trials were followed by outcome-dependent proposals. The objective did not use student-test labels.

| Parameter | Search range | Selected value |
|---|---|---:|
| Learning rate | Logarithmic 0.025-0.25 | 0.11608 |
| Maximum leaves | Integer 7-31 | 26 |
| L2 regularisation | Logarithmic 0.01-10 | 2.32516 |
| Maximum iterations | Integer 60-160 | 156 |

CV Macro F1 rose from 0.7369 to 0.7382. This is a small measured improvement. Trial records are in `results/bayesian_trials.csv` and `results/bayesian_search.sqlite3`. The final configuration is in `artifacts/config.json`.

Later, HMM-style Viterbi decoding uses candidate arcs as states, normalised classifier scores as emissions, and directed path/displacement compatibility as transition potentials. These are unnormalised transition potentials, not claimed calibrated Markov probabilities. It resets at large gaps and permits penalised disconnected transitions.

| Student-test measure | Tuned classifier | Tuned classifier + decoder |
|---|---:|---:|
| Top-1 accuracy | 0.8763 | 0.8682 |
| Macro F1 | 0.7625 | 0.8191 |
| Directed continuity | 0.9738 | 0.9951 |

The decoder improves F1/continuity but reduces Top-1 accuracy. Its beta was chosen on student-test development data. Continuity here is bounded directed reachability between consecutive nongap assignments; it is not proof of exact physical reconstruction. Keep these later-stage experiments separate from the EDA findings.

## 18. Which source file and output to show

| Item | Source / function | Output evidence |
|---|---|---|
| Input parsing and validation | `pathsnap/core.py`: `load_trip()` | `gps_projected.csv`, `summary.json`, console |
| Coordinate projection | `pathsnap/core.py`: `load_trip()` | `nodes.csv`, `gps_projected.csv` |
| Point-to-segment projection | `pathsnap/core.py`: `project()` | Projection fractions/distances in feature CSV |
| Road graph | `pathsnap/core.py`: `Network.__init__()` | `arcs.csv`, `adjacency_sample.txt`, `road_graph.png` |
| Connectivity audit | `pathsnap/explore.py`: `main()` | `inventory.csv`, `eda.json` |
| Candidates and eleven features | `pathsnap/core.py`: `candidates()` | `candidate_features.csv` |
| Derived reference labels | `pathsnap/core.py`: `reference_labels()` | `weak_reference_labels.csv` |
| Observation sampling / arrays | `pathsnap/experiments.py`: `training_arrays()` | `used_for_training` column and protocol |
| Model configurations | `pathsnap/experiments.py`: `model_factory()` | `models.json`, saved artifacts |
| Cross-validation / selection | `pathsnap/experiments.py`: `main()` | `protocol.json`, `models.json` |
| Review demonstration exports | `pathsnap/review1.py`: `main()` | `results/review1/00000003/` |
| Comparison plots | `pathsnap/visuals.py`: `main()` | `results/figures/model_comparison.png` |

All Review 1 trip-specific outputs are under:

```text
D:\sem 5\ML\Hackathon\results\review1\00000003
```

The exporter includes all 821 observations for inspection. Filter `used_for_training=1` to inspect the sampled fitting examples. Node/arc IDs remain the original local IDs. The exporter checks that adjacency entries account for every supplied arc and that feature shape matches the eleven-feature schema. Export row counts were checked after execution.

## 19. Suggested live demonstration order

1. **Explain the problem:** noisy GPS, road ambiguity and route consistency.
2. **Show one original trip:** explain track/nodes/arcs/route and their different row meanings.
3. **Show `eda.json` and `inventory.csv`:** counts, no imputation needed, time gaps, disconnected graphs and varying sizes.
4. **Run `python run.py review1 --trip 00000003`:** show actual execution and output location.
5. **Open `road_graph.png`:** full graph on the left, directed candidate graph on the right.
6. **Show `arcs.csv` and `adjacency_sample.txt`:** explain an actual source/destination/length entry.
7. **Show `gps_projected.csv`:** connect geographical coordinates to metre-based features.
8. **Open `core.py` at `FEATURES` and `candidates()`:** explain how eleven values become one candidate row.
9. **Show eight feature rows for one observation:** explain metadata, features, target and fitting-sample indicator.
10. **Show `model_factory()`, protocol and comparison plot:** justify the five models, trip grouping and evidence-based selection.

If time is short, prioritise the graph image, feature CSV, EDA summary and model-comparison plot. Do not spend the review retraining just to produce already saved results.

## 20. Reproduction commands beyond the live demonstration

Run these only when you intend to regenerate experiments and dependent outputs:

```powershell
Set-Location -LiteralPath 'D:\sem 5\ML\Hackathon'
python run.py explore
python run.py train --trials 10
python -c "import run; from pathsnap.visuals import main; main()"
```

Training rewrites comparison outputs and refits models. It uses cached preprocessing under `cache/`. Move/remove stale caches after changing input files, features or label-alignment code. The existing Bayesian SQLite study resumes, so a rerun with ten completed trials does not necessarily launch ten new trials. Use a separate fresh results/study setup for a genuinely new search, particularly after changing the family, folds or search space.

`python run.py verify` runs the algorithm/API tests. The existing four tests passed, including directed graph behaviour and reference-isolated inference. Windows sandbox restrictions can block local sockets used by the API test client; ordinary local execution needs local socket access. These are verification results, not proof of an error-free implementation on all unseen data.

## 21. Likely viva questions and defensible answers

### Why do we need ML if we can calculate distance?

Distance is one signal. Direction and neighbouring movement can distinguish candidates with similar distances. The model learns combinations from examples. We have not measured an explicit nearest-road-only baseline, so we should not invent a numerical improvement over it.

### Are we predicting coordinates or road IDs?

The classifier predicts binary candidate suitability. We preserve candidate-to-local-arc correspondence, then select an arc and derive geometry. We do not train a latitude/longitude regressor.

### Why do we not use arc IDs as numeric input features?

Their values are local row identifiers, not meaningful continuous measurements. Numeric proximity between IDs does not imply spatial proximity. They identify the output candidate rather than being one of the eleven features.

### Does zero missing data mean the dataset is clean?

It means the checked fields contain no missing numeric values. GPS error, route-label limitations, time gaps and connectivity issues remain.

### How can there be no isolated nodes but many components?

Every node can have at least one neighbour while separate groups remain disconnected. Two disconnected road clusters each containing several connected nodes have no isolated nodes.

### Why not simply sort or resample the timestamps?

Chronology and actual gaps contain information. The loader rejects backwards timestamps rather than silently rearranging questionable input. We retain gaps and do not invent one-second observations through interpolation.

### What happens if the reference arc is not among eight candidates?

No candidate is labelled positive for that observation. It remains a candidate miss in evaluation. Neither the classifier nor the fixed-candidate decoder can recover an arc absent from its state set.

### Are the labels ground truth for every GPS point?

No. The source gives a reference route. Our point labels are derived by monotone alignment and can be imperfect. Results must be interpreted against those weak labels.

### Is reference alignment the same as the prediction decoder?

No. Alignment derives supervision from a known ordered reference route. Prediction decoding does not know that route; it uses candidate scores and road connectivity. Using the known reference during prediction would invalidate the evaluation.

### Why not use random train/test rows?

Rows from the same observation/trip are correlated. Grouping by trip keeps them out of both sides of the external validation split. A separate geographical holdout would be needed to investigate unseen-region generalisation.

### Why Macro F1 rather than binary accuracy?

Most candidate rows are negative, so binary accuracy can be high without useful matching. Arc Macro F1 gives less frequent road classes a role in selection. We also report Top-1 accuracy and log loss rather than relying on a single number.

### Did the final model win because it had the highest training accuracy?

No. The family was selected using held-out-trip CV Macro F1. Training candidate accuracy is only a diagnostic and has different meaning from point-level arc F1.

### Are the eleven features proven necessary?

No. Their choices are motivated by geometry/movement. A controlled ablation study is needed to measure independent contributions. That experiment was not performed.

### Why does next-observation distance not count as leakage?

The intended input is an already available full trajectory, so future GPS observations are available during offline matching. It would be inappropriate for a causal real-time claim. Future reference labels are not feature inputs.

### Can we claim the model generalises to any city?

No. We evaluated held-out trips from the supplied data. Different trips may overlap geographically, and reserved evaluator trips were unavailable. The candidate representation is designed to transfer across local networks, but universal generalisation is not established.

### What would we improve next?

Evaluate a nearest-road baseline, perform feature-group ablations, investigate alternative candidate counts, examine weak-label failures, test geographical holdouts, and evaluate the eventual reserved data without using it for development. These are proposed experiments, not completed results.

## 22. Short presentation script

> Our task is to reconstruct vehicle routes by matching noisy GPS observations to a directed road network. A GPS point can be close to several roads, so we combine spatial proximity with movement and later sequence consistency.
>
> We inspected 80 training and 10 student-test trips. The data had no missing numeric values, so imputation was unnecessary. However, trip sizes varied substantially, most road graphs were disconnected, and some timestamps had large gaps. We retained those properties and designed explicit handling rather than assuming uniform sampling and a fully connected graph.
>
> We converted coordinates into a local metric representation, constructed directed weighted adjacency lists and generated eight nearest segment candidates per observation. For each observation-candidate pair we engineered eleven geometric and movement features.
>
> Since road IDs are local to each trip, we train a binary suitability scorer rather than a global road-ID classifier. Reference files provide ordered arc sequences, so our point labels are derived through monotone alignment and are treated as weak labels.
>
> We compared Logistic Regression, Gaussian Naive Bayes, Decision Tree, Random Forest and Histogram Gradient Boosting. We sampled 200 observations per training trip, giving 128,000 candidate examples, and used three-fold validation grouped by trip to avoid correlated row overlap.
>
> Histogram Gradient Boosting had the highest baseline grouped CV Macro F1, 0.7369, narrowly ahead of the forest. We selected it using that measured criterion. Later Bayesian tuning improved CV F1 slightly to 0.7382. We do not claim untested alternatives are inferior or that the weak labels are perfect.

## 23. Final preparation checklist

- Run the two Review 1 commands before the session and confirm the files open.
- Know what one node, one arc, one GPS observation and one candidate-feature row represent.
- Explain one actual adjacency-list entry and why its direction matters.
- Understand projection distance, local metre coordinates and the eleven features.
- Distinguish weak label derivation from label-free prediction.
- Explain the five models' assumptions and the reason for trip grouping.
- Use the actual comparison table; distinguish binary candidate accuracy from road Top-1/Macro F1.
- Distinguish completed experiments from proposed improvements.
- Keep the offline PNG/CSV outputs available if internet is unreliable.
- Review the implementation and describe AI assistance honestly under the event rules.

Public GitHub publication, reserved evaluator testing and a physical two-laptop demonstration are separate external steps. None is needed to show the existing Review 1 evidence, and none should be claimed as completed by the local demonstration.

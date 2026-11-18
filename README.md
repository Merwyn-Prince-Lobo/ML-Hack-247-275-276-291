# PathSnap

An executed, end-to-end map-matching project: five trained classifiers, grouped cross-validation, ten Bayesian TPE trials, a directed HMM/Viterbi decoder, FastAPI, an offline geographical evaluator UI, Folium development maps, and a consolidated technical report.

For the complete Review 1 explanation, evidence files, demonstration commands and viva preparation, read [REVIEW1_README.md](REVIEW1_README.md).

For four-person file ownership, execution/presentation order and genuine contribution/commit workflows, read [TEAM_GUIDE.md](TEAM_GUIDE.md).

## Start the working system

This workspace already contains trained artifacts and extracted data. From this directory:

```powershell
python run.py serve --host 0.0.0.0 --port 8000
```

In a second terminal:

```powershell
python run.py ui --host 0.0.0.0 --port 8501
```

Open **http://localhost:8501**, connect to **http://localhost:8000**, select a trip and click **Reconstruct route**. API documentation: http://localhost:8000/docs. PowerShell launchers `start_backend.ps1` and `start_ui.ps1` provide the same commands.

The redesigned frontend is an app-style evaluation workspace with a searchable trip library, live server status, metric cards, map layer switches, zoom/pan/fit controls, start/end markers, route-break and gap diagnostics, and GeoJSON/JSON downloads. All predictions and scores come from the backend. The UI identifies development versus reserved-evaluator inputs and keeps the displayed trip labelled when the selection changes. Reference routes and point labels remain server-side. Browser checks covered all ten supplied student-test trips, connection-error recovery, downloads and responsive layouts; see `results/frontend_checks.json`.

Frontend source is split into `ui/index.html` (structure), `ui/styles.css` (appearance/responsive layout), and `ui/app.js` (API requests, interactions, geometry viewer and exports). Copy the complete `ui/` folder when setting up Laptop 2. No frontend build step or Docker is required. Refresh the browser after replacing files.

## Install on a fresh computer

Python 3.11 was used. Run from the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The current workspace also has optional downloaded libraries in `.deps/`; `run.py` appends this directory to the import path. It is excluded from the submission. A fresh installation uses normal pip dependencies.

Extract `Student folder.zip` into `data/`, retaining:

```text
data/Student folder/train/00000001/00000001.track  (.nodes, .arcs, .route)
data/Student folder/student_test/00000000/00000000.track  (.nodes, .arcs, .route)
```

Data is excluded from version control. Use the original event archive to reproduce it. Models, source, report and experiment evidence are included. Only load joblib artifacts from a trusted source.

## Two-laptop demonstration

1. Laptop 1 holds the backend, model artifacts and trip data. Run the backend on `0.0.0.0:8000`.
2. Laptop 2 holds `ui/` and `run.py`. Run the UI on port 8501, or serve `ui/` with any static web server. No ML libraries are needed for `python run.py ui`.
3. Put both laptops on the same trusted LAN. In Laptop 2's browser open `http://localhost:8501` and enter `http://LAPTOP1_LAN_IP:8000` in the API address field.
4. Keep Laptop 1's receiving terminal visible: each inference prints the trip ID, observation count, elapsed time and metric summary.
5. If the OS prompts, allow the intended private-network port. Do not deploy the unauthenticated evaluation API on the public internet.

The default UI lists the **ten supplied student-test trips**. Reserved evaluator trips were not in either supplied archive. When organisers supply them, on Laptop 1 set the directory before starting the backend:

```powershell
$env:PATHSNAP_EVAL_DIR = 'D:\reserved_evaluator_trips'
python run.py serve --host 0.0.0.0 --port 8000
```

That directory must contain eight-digit trip subfolders, each containing matching `.track`, `.nodes`, `.arcs`, and optionally server-side `.route` files. The UI discovers inputs through `/trips`; there is no hardcoded list or stored prediction. If references are absent, prediction still works and metrics display N/A. Reference files and labels never go to Laptop 2.

`PATHSNAP_UI_ORIGINS` can restrict CORS to comma-separated UI origins. The default allows any origin for the trusted LAN demo. Docker/Compose configuration is provided as an optional deployment path; Docker was not run in this environment.

## Reproduce the experiments

For a Review 1 demonstration of preprocessing and graph construction, run:

```powershell
python run.py explore
python run.py review1 --trip 00000003
```

The first command regenerates the complete inventory and EDA summary. The second independently processes training trip 00000003 and exports `results/review1/00000003/`: a road-graph PNG with directed arrows, an interactive Folium graph, node and arc CSVs, an adjacency-list sample, projected GPS points, all candidate feature rows, separate weak reference labels and a summary. It does not load or retrain a classifier. In `candidate_features.csv`, `used_for_training=1` identifies the 200 sampled observations; the exported table includes all observations for inspection. Labels are derived from the training reference route, not independent point ground truth. Folium JavaScript/tiles need internet; the PNG and CSVs work offline.

```powershell
python run.py explore
python run.py train --trials 10
python -c "import run; from pathsnap.visuals import main; main()"
python run.py verify
```

With the backend running, check every student-test trip over actual HTTP:

```powershell
python scripts/check_api.py
```

The script expects ten trips. It saves `results/api_checks.json` and a real response summary. In this workspace all ten passed. Four unit/integration tests also passed. Windows sandboxed execution may block local sockets; normal local execution needs socket access.

Generate the report after experiment outputs, API evidence and screenshots exist:

```powershell
python run.py report
```

Preprocessing caches are under `cache/`. **Remove that cache after changing input data, feature code or reference-alignment logic.** Bayesian search resumes its existing SQLite study; for an independent rerun use a fresh results directory or move the prior search database and results aside. The study must not be reused after changing the selected model, folds or search space.

## Actual results

All values below are means of trip-level metrics on the supplied development partitions.

| Model | Grouped CV Macro F1 | Student Top-1 | Student Macro F1 |
|---|---:|---:|---:|
| Logistic regression | 0.6938 | 0.8601 | 0.7108 |
| Gaussian NB | 0.6645 | 0.8383 | 0.6851 |
| Decision tree | 0.7083 | 0.8688 | 0.7398 |
| Random forest | 0.7342 | 0.8749 | 0.7567 |
| Histogram gradient boosting | 0.7369 | 0.8757 | 0.7616 |
| Tuned gradient boosting | 0.7382 | 0.8763 | 0.7625 |
| Tuned model + HMM | N/A (decoder tuned on student-test) | 0.8682 | 0.8191 |

HMM increases directed continuity from 97.38% to 99.51%, while reducing Top-1 accuracy. The report explains this tradeoff. Candidate miss rate is 0.392% averaged across test trips. API wall time includes candidate construction and geometry; it is greater than classifier scoring time in the model comparison.

**Weak-label qualification:** `.route` supplies traversed arc sequences, not a road label for each GPS point. Observation labels are derived by monotone alignment to the reference route. These metrics are therefore against derived labels; they are not organiser-certified ground truth. No evaluator data was used. Scores are development estimates, particularly because decoder beta was selected on student-test data.

## Method

- Validate raw data; project longitude/latitude to a local metric plane.
- Retrieve exact top-eight segments with a midpoint-tree radius bound and point-to-segment projection.
- Construct eleven geometric/movement features. Train binary candidate classifiers, preserving the local arc mapping.
- Fit on up to 200 observations per training trip. Evaluate every observation in each held-out trip using three trip-grouped folds.
- Select the family by grouped CV Macro F1; optimise with ten Optuna TPE trials on those folds.
- Normalise candidate scores into emissions; decode using directed shortest-path transition potentials and Viterbi backpointers.
- Reset across large gaps. Penalise disconnected transitions; record route breaks rather than inventing connections.

The method is offline: centred heading and next-observation distance use future observations. Transition potentials are unnormalised compatibility scores; decoded-chain log loss is not claimed. See the report for all limitations and exact metrics.

## Project layout

| Path | Contents |
|---|---|
| `pathsnap/core.py` | Input validation, candidates/features, reference alignment, graph search, decoder |
| `pathsnap/experiments.py` | Five models, grouped CV, TPE tuning and decoder comparison |
| `pathsnap/api.py` | FastAPI, label-separated inference and server-side metrics |
| `pathsnap/explore.py`, `visuals.py`, `report.py` | Audit, actual plots/Folium, report generation |
| `ui/` | App-style evaluator interface: HTML, CSS and JavaScript; no CDN or map tiles needed |
| `artifacts/` | All five baseline models, tuned model, selected final model, config |
| `results/` | Inventory, protocol, per-fold/per-trip metrics, SQLite search and CSV trial logs |
| `results/maps/` | Interactive Folium development map (uses external JS/tiles) |
| `results/figures/` | Actual plots and UI/Folium screenshots |
| `output/pdf/` | Consolidated technical report |
| `tests/`, `scripts/` | Algorithm, isolation and real HTTP verification |

## Submission and authorship

The local package is prepared for review and upload. Public GitHub publication needs the team's authenticated account and repository destination. No public URL, physical two-laptop test, receiving-laptop CMD screenshot or reserved-evaluator score is claimed. Capture the receiving terminal during the real two-laptop demonstration and add team details before final submission.

Codex assisted with implementation, actual experiment execution, tests, maps and report drafting. Review and disclose assistance according to event rules. Every team member should understand the code and be able to defend the weak-label assumptions and measured results. See `VIVA_GUIDE.md`.

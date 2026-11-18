# PathSnap: four-person roles, execution, presentation and Git guide

This guide assigns responsibility for the existing project to four people and explains how to run, demonstrate and commit each part. Replace Person 1-4 with your team members' names in your team notes.

The project already exists and contains AI-assisted implementation and executed experiments. Ownership below means responsibility for understanding, checking, maintaining and improving that area. It does not mean each person originally wrote the existing code unaided. Contributions and commit messages should accurately describe the work performed.

## 1. Current repository state and what commits can show

At preparation time, this local repository had one initial commit:

```text
fcce37c Build PathSnap with trained models, grouped experiments, decoder, API, UI and report
```

No GitHub remote was configured. The later Review 1 exporter, evidence outputs and documentation were working-tree changes. A local integration commit can preserve that existing work, but it cannot establish four separate people's historical contributions.

For each teammate to have meaningful commits, each person should check their assigned component, make and explain real changes, inspect the diff, and commit those changes using their own configured identity. Running unchanged code alone may produce no diff. Empty commits or rewriting an earlier commit's author do not demonstrate contribution. Preserve the existing history.

You can use one shared laptop, but separate clones on each person's laptop are preferable. Never have two people run Git operations concurrently in the same working directory.

## 2. Role assignment at a glance

| Person | Role | Review 1 presentation responsibility | Main deliverable |
|---|---|---|---|
| 1 | Dataset and EDA owner | Problem, file meanings, partition sizes, data quality, time gaps, graph-size/connectivity findings | Validated inventory, EDA evidence and explained preprocessing decisions |
| 2 | Geometry, graph and feature owner | Coordinate projection, directed graph, candidate generation, weak label alignment and eleven features | Inspectable graph and candidate-feature exports |
| 3 | ML experimentation owner | Five algorithms, alternatives, sampling, grouped validation, training and Bayesian tuning | Reproducible model comparison and model artifacts |
| 4 | Integration, evaluation and demonstration owner | Metrics, results interpretation, limitations and reproducibility; later API/UI demo | Working integrated system, plots, tests, report and submission package |

Execution and presentation order: **Person 1 -> Person 2 -> Person 3 -> Person 4**.

Every person should understand the overall pipeline. File ownership prevents conflicting edits; it does not prevent teammates from reviewing another component.

## 3. Shared setup on each laptop

### 3.1 Project and Python environment

The existing workspace root is:

```text
D:\sem 5\ML\Hackathon
```

On that laptop:

```powershell
Set-Location -LiteralPath 'D:\sem 5\ML\Hackathon'
```

For a fresh clone use your own chosen directory. Install Python 3.11 and the project requirements:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

In the commands below `python` means your environment's Python. If you do not activate the virtual environment, replace it with `.venv\Scripts\python.exe`. The existing workspace has additional libraries under `.deps/`, automatically appended by `run.py`; a fresh laptop should install requirements normally.

### 3.2 Dataset placement

Raw data is intentionally ignored by Git. Each teammate who runs data/model commands must extract the original `Student folder.zip` into `data/` so the layout is:

```text
data/
  Student folder/
    train/
      00000003/
        00000003.track
        00000003.nodes
        00000003.arcs
        00000003.route
      ...
    student_test/
      00000000/
        ...
```

The full local submission ZIP includes supplied data, while the Git repository excludes it. Do not force-add raw archives, data, caches, downloaded dependencies or credentials to Git.

### 3.3 Configure the actual person's Git identity

Each teammate runs this inside their own clone, using their own real name and an email recognised by their GitHub account (a verified GitHub no-reply email is also suitable):

```powershell
$memberName = Read-Host 'Your Git author name'
$memberEmail = Read-Host 'Your verified GitHub email or GitHub no-reply email'
git config --local user.name $memberName
git config --local user.email $memberEmail
git config --get user.name
git config --get user.email
```

Local configuration affects this repository, not every repository on the computer. Author identity and GitHub authentication are different: the identity labels commits; authentication grants permission to push. Do not put passwords or tokens into source files or remote URLs.

## 4. Person 1: dataset, EDA and data-quality decisions

### 4.1 What this person owns

| Path | Responsibility |
|---|---|
| `pathsnap/explore.py` | Dataset inventory, sampling statistics and connectivity audit |
| `results/inventory.csv` | One record per supplied trip |
| `results/eda.json` | Partition-level summary |
| `docs/person1_data_review.md` | Their own findings, commands run, observations and changes; create after doing the review |

`load_trip()` in `pathsnap/core.py` is a dependency owned by Person 2. Person 1 should understand the validation it performs and coordinate any modifications with Person 2.

### 4.2 What to understand

- The challenge: infer road segments from noisy GPS and reconstruct a coherent route.
- Track rows are observations, node rows are coordinates, arc rows are directed connections and route entries are ordered arc IDs.
- Arc IDs are local to each trip; observation and route rows are not paired by row number.
- There are 80 training trips and ten supplied student-test trips; reserved evaluator data is absent.
- Zero missing numeric values does not mean zero GPS error.
- Large time gaps, unequal trip sizes and disconnected graphs affect modelling assumptions.

### 4.3 Commands to run

```powershell
python run.py explore

Get-Content '.\results\eda.json'

Import-Csv '.\results\inventory.csv' |
    Select-Object -First 10 |
    Format-Table trip_id,observations,nodes,arcs,missing_values,max_gap_seconds,weak_components -AutoSize
```

### 4.4 Outputs and actual findings to show

| Finding | Training | Student-test |
|---|---:|---:|
| Trips | 80 | 10 |
| GPS observations | 208,417 | 19,160 |
| Missing numeric values | 0 | 0 |
| Duplicate timestamps | 0 | 0 |
| Intervals exactly one second | 96.50% | 98.62% |
| Largest gap | 153,064 s | 210 s |
| Trips with multiple weak components | 79 | 10 |
| Isolated nodes | 0 | 0 |

Training trip observation counts range from 361 to 19,313. Training network sizes range from 299 to 155,003 nodes and from 649 to 307,392 arcs. There are 22 training trips with a gap above 60 seconds.

Explain the consequences: no imputation required; fixed fitting budget per trip; timestamps retained; spatial candidate retrieval for large graphs; connectivity-aware reconstruction.

### 4.5 Meaningful work they can contribute

Review the actual audit, then implement and validate a concrete improvement if needed. Examples: export a dedicated large-gap table, add interval quantiles to the audit, or produce actual trip-size/time-gap charts. A documentation contribution can also be substantive: independently analyse the inventory and explain the findings with reproducible calculations. These are suggested tasks, not claims of completed teammate work.

Record what was actually changed and checked in `docs/person1_data_review.md`. Do not fabricate output or call a design assumption an EDA finding.

### 4.6 Suggested commit scope

After making real changes, inspect and stage only this person's paths:

```powershell
git diff -- pathsnap/explore.py results/inventory.csv results/eda.json
git add -- pathsnap/explore.py results/inventory.csv results/eda.json docs/person1_data_review.md
git diff --cached --stat
git diff --cached
git commit -m "Analyse dataset quality and document EDA decisions"
```

Only include paths that exist. Add any genuinely created chart/table paths explicitly. Edit the message to match the actual change.

### 4.7 Presentation handoff

> Our audit confirms the dataset structure and highlights irregular sampling, unequal trip sizes and disconnected road graphs. These findings explain why the next stage needs metric geometry, explicit graph construction and candidate-based features. Person 2 will show those transformations.

## 5. Person 2: geometry, graph construction and eleven features

### 5.1 What this person owns

| Path | Responsibility |
|---|---|
| `pathsnap/core.py` | Validation, projection, candidate generation, feature calculation, weak labels, directed graph and decoder primitives |
| `pathsnap/review1.py` | Human-inspectable graph and feature exports |
| `results/review1/00000003/` | Evidence for the chosen training demonstration trip |
| `docs/person2_features_review.md` | Their own geometry/feature review and actual changes |

Coordinate edits to decoder primitives with Person 3/4. Person 2 owns the common geometry file to reduce simultaneous edits.

### 5.2 Commands to run

```powershell
python run.py review1 --trip 00000003
Invoke-Item '.\results\review1\00000003\road_graph.png'
Get-Content '.\results\review1\00000003\adjacency_sample.txt'
Get-Content '.\results\review1\00000003\summary.json'

Import-Csv '.\results\review1\00000003\candidate_features.csv' |
    Select-Object -First 8 |
    Format-Table observation_id,candidate_arc_id,distance_m,heading_disagreement,weak_binary_label -AutoSize
```

Optional interactive geographical graph:

```powershell
Invoke-Item '.\results\review1\00000003\road_graph_map.html'
```

The HTML needs external libraries/tiles; use the PNG/CSVs as the offline demonstration.

### 5.3 What to explain in the code

| Function/location in `core.py` | Explanation |
|---|---|
| `load_trip()` | Validates structure and projects angular coordinates into a local metric plane |
| `project()` | Clipped projection onto a segment and point-to-segment distance |
| `candidates()` | Midpoint-tree radius bound, exact segment ranking and eleven features |
| `reference_labels()` | Monotone alignment to an ordered reference route; derives weak point labels |
| `Network.__init__()` | Directed weighted adjacency list preserving original arc IDs |

The graph stores `source -> (destination, length_m, arc_id)`. In the demonstration output:

```text
0 -> (7838, 153.193 m, arc 0), (3594, 12.439 m, arc 1), (154, 14.264 m, arc 2)
```

Node 0 has three outgoing connections. The graph does not invent their reverse directions.

### 5.4 Eleven features they must explain

1. GPS-to-segment distance: spatial compatibility.
2. Heading disagreement: `1-cosine`, approximately 0 aligned and 2 opposite.
3. Projection fraction: position along the candidate segment.
4. Segment length: local geometric context.
5. Observed speed: displacement divided by bounded time interval.
6. Time gap: sampling context.
7. Distance rank: relative proximity among candidates.
8. Distance above nearest: ambiguity/cost of choosing another segment.
9. Previous-observation distance to this candidate: local movement context.
10. Next-observation distance: future context, making this an offline method.
11. Heading-availability flag: heuristic low-movement context; it does not disable the heading value.

Raw longitude/latitude cannot be treated as metre coordinates. Numeric arc IDs are metadata, not one of the eleven inputs. Reference alignment produces weak labels, not independently verified observation truth. The reference route never becomes an inference feature.

### 5.5 Outputs to show

| Output | Demonstration |
|---|---|
| `nodes.csv`, `arcs.csv` | Original IDs, projected coordinates and directed edges |
| `gps_projected.csv` | Original and transformed coordinates/timestamps |
| `adjacency_sample.txt` | Actual outgoing graph neighbours |
| `road_graph.png` | Full graph and labelled directed candidates |
| `candidate_features.csv` | 6,568 rows = 821 observations x 8 candidates |
| `weak_reference_labels.csv` | Derived labels and alignment distances |
| `summary.json` | Counts and preprocessing notes |

`used_for_training=1` marks 200 observations / 1,600 candidate rows in this trip. The exported features are unscaled; scaling belongs inside the model-training pipeline.

### 5.6 Meaningful work they can contribute

Review candidate/arc correspondence and the projection calculations. Possible real changes include a clearer graph export legend, explicit handling/reporting of a discovered edge case, or a carefully justified improvement to heading treatment around gaps. If an algorithm/feature changes, coordinate cache invalidation and retraining with Person 3; old model results must not be presented as measuring changed features.

Independently explain and verify one observed feature row in their own review document. Do not claim every feature improved performance; no full ablation study has been performed.

### 5.7 Suggested commit scope

```powershell
git diff -- pathsnap/core.py pathsnap/review1.py
git add -- pathsnap/core.py pathsnap/review1.py results/review1/00000003 docs/person2_features_review.md
git diff --cached --stat
git diff --cached -- pathsnap/core.py pathsnap/review1.py docs/person2_features_review.md
git commit -m "Verify graph construction and improve feature evidence"
```

Include only real reviewed changes and an existing review document. Do not stage cache files or assign this commit to someone who did not do the work.

### 5.8 Presentation handoff

> These features convert every GPS observation into eight candidate examples while preserving the local arc mapping. We now have numerical inputs and weak binary targets. Person 3 will explain how we fit and compare classifiers without splitting trips across validation folds.

## 6. Person 3: five models, training and model selection

### 6.1 What this person owns

| Path | Responsibility |
|---|---|
| `pathsnap/experiments.py` | Sampling, five model factories, grouped CV, evaluation, tuning and decoder sweep |
| `artifacts/` | Trained baseline/tuned/final models and inference configuration |
| `results/models.json`, `results/protocol.json` | Model evidence and split/metric definitions |
| `results/bayesian_trials.csv`, `results/bayesian_search.sqlite3` | Real optimisation records |
| `results/final.json`, `results/hmm.json` | Final classifier/decoder comparisons |
| `docs/person3_models_review.md` | Their own experiment interpretation and actual changes |

### 6.2 Safe demonstration using saved experiments

```powershell
Get-Content '.\results\protocol.json'

python -c "import json; m=json.load(open('results/models.json')); [print(n, 'CV F1=',round(r['cv_macro_f1'],4),'Test F1=',round(r['student_test']['aggregate']['macro_f1'],4)) for n,r in m.items()]"

Get-Content '.\artifacts\config.json'
```

These commands inspect existing results and do not retrain. Person 4 owns the plot generator, but Person 3 may show the already generated comparison image.

### 6.3 When a full training run is intended

```powershell
python run.py train --trials 10
```

This refits baselines and rewrites model/evaluation outputs. It uses preprocessed caches and resumes the existing Bayesian SQLite study. If ten trials already exist, it does not necessarily create ten more. A genuinely new search requires an isolated fresh study/results setup. Do not rerun training live just to make a commit.

After changing feature/label code, invalidate stale preprocessing caches and rerun the relevant experiments before updating conclusions. Coordinate this with Person 2. Do not silently mix old feature caches with new source.

### 6.4 Training explanation

There are 80 training trips. We sample 200 observations from each, giving 16,000 observations and 128,000 candidate rows with eleven features. The sampled labels contain 15,546 positives and 112,454 negatives.

A trivial all-negative classifier would obtain approximately 87.85% binary candidate accuracy. We therefore compare observation-level Top-1, arc Macro F1 and probability loss, with CV Macro F1 as the selection criterion.

Three-fold GroupKFold keeps all rows from a trip together. Scaling is fitted inside the relevant model pipeline on the fitting fold only. All observations in held-out trips are evaluated, not merely the 200 sampled observations. Trip grouping does not guarantee unseen-geography generalisation.

### 6.5 Model choice explanation

| Model | Why included | Main limitation |
|---|---|---|
| Logistic Regression | Linear probability baseline; simple feature-weight combination | Limited nonlinear interactions |
| Gaussian Naive Bayes | Cheap generative probability baseline with different assumptions | Correlated distance features challenge conditional independence |
| Decision Tree | Tests nonlinear threshold rules | Single-tree instability and extreme leaf probabilities |
| Random Forest | Averages nonlinear trees to reduce reliance on one tree | Greater size/scoring cost |
| Histogram Gradient Boosting | Sequential loss corrections on numerical tabular features | Configuration sensitivity and risk of fitting weak-label noise |

Explain untested alternatives as prioritisation decisions, not proven inferior algorithms. KNN/SVM/MLP/sequence/GNN approaches can be valid but require different computational or representation choices. The full Review 1 README gives the configurations and objectives.

### 6.6 Actual evidence

| Model | CV Macro F1 | Student-test Top-1 | Student-test Macro F1 |
|---|---:|---:|---:|
| Logistic Regression | 0.6938 | 0.8601 | 0.7108 |
| Gaussian Naive Bayes | 0.6645 | 0.8383 | 0.6851 |
| Decision Tree | 0.7083 | 0.8688 | 0.7398 |
| Random Forest | 0.7342 | 0.8749 | 0.7567 |
| Histogram Gradient Boosting | 0.7369 | 0.8757 | 0.7616 |
| Tuned histogram boosting | 0.7382 | 0.8763 | 0.7625 |

Selection was by grouped CV Macro F1, not training accuracy. The baseline margin over Random Forest was small. Ten TPE trials yielded a small further improvement. These are measured development results against derived labels.

### 6.7 Meaningful work they can contribute

Independently review the training protocol and per-fold/per-trip failures. Possible real contributions include an actual nearest-road baseline experiment, a clearly separated ablation experiment, or improved structured recording of fitted configurations. Preserve prior results and document any new protocol. Proposed experiments must not be reported as completed.

### 6.8 Suggested commit scope

```powershell
git diff -- pathsnap/experiments.py results/protocol.json
git add -- pathsnap/experiments.py artifacts results/models.json results/protocol.json results/bayesian_trials.csv results/bayesian_search.sqlite3 results/final.json results/hmm.json docs/person3_models_review.md
git diff --cached --stat
git diff --cached -- pathsnap/experiments.py results/protocol.json docs/person3_models_review.md
git commit -m "Validate grouped model comparison and document selection evidence"
```

Stage only results actually produced by the code/protocol being committed. Joblib artifacts are binary and should come from the corresponding experiment, not from another team.

### 6.9 Presentation handoff

> Histogram boosting led our grouped CV comparison and tuning gave a small additional gain. The saved artifacts and logs make these claims reproducible. Person 4 will show the comparative plots, explain metric limitations and demonstrate the integrated checks.

## 7. Person 4: integration, evaluation, visualisation and final demonstration

### 7.1 What this person owns

| Path | Responsibility |
|---|---|
| `pathsnap/api.py`, `ui/` | API, model loading, UI and reference-isolated prediction |
| `pathsnap/visuals.py`, `pathsnap/report.py` | Actual plots, development Folium map and PDF generation |
| `tests/`, `scripts/check_api.py` | Verification and real HTTP checks |
| `run.py`, launchers, `requirements.txt`, Docker files | Shared entry point, installation and deployment integration |
| `scripts/package_submission.py`, `submission_manifest.json` | Delivery archive and integrity manifest |
| `results/figures/`, `results/maps/`, API evidence, `output/pdf/` | Integrated evidence and report |
| `README.md`, `REVIEW1_README.md`, `TEAM_GUIDE.md`, `VIVA_GUIDE.md` | Consistent team-facing documentation |
| `docs/person4_integration_review.md` | Their own verification record and actual changes |

This role owns shared entry-point/documentation edits; other people request changes rather than editing those files simultaneously.

### 7.2 Review 1: show existing results first

```powershell
Invoke-Item '.\results\figures\model_comparison.png'
Invoke-Item '.\results\figures\geography.png'
python run.py verify
```

Explain that higher F1/accuracy is better and lower log loss is better. Scores are means of trip-level results; point labels are derived. Binary candidate accuracy and road Top-1 are not interchangeable.

The existing four tests passed. They check directed path/decoder behaviour, candidate retrieval/alignment, input validation and inference isolation from reference labels. Running the tests requires local sockets for the FastAPI test client; a restricted sandbox can block that access.

### 7.3 Regenerate plots only when necessary

After Person 3 has completed any intended experiments:

```powershell
python -c "import run; from pathsnap.visuals import main; main()"
```

This consumes saved experiment results and model artifacts and regenerates actual comparison figures and the development Folium map. It does not train the five models. Regenerating Folium HTML can change generated IDs even when the underlying data is unchanged; inspect diffs rather than treating any changed file as a new scientific result.

### 7.4 Optional API/UI demonstration after Review 1 topics

On Laptop 1, terminal A:

```powershell
python run.py serve --host 0.0.0.0 --port 8000
```

Leave it running. On Laptop 2, in a separate terminal:

```powershell
python run.py ui --host 0.0.0.0 --port 8501
```

Open `http://localhost:8501` on Laptop 2 and enter `http://LAPTOP1_LAN_IP:8000` as the API address. Use `http://localhost:8000` when both processes run on the same laptop. The UI discovers trips from the API; the default inputs are the ten supplied student-test trips.

With the backend running, from another terminal:

```powershell
python scripts/check_api.py
```

For a real second laptop calling Laptop 1:

```powershell
python scripts/check_api.py http://LAPTOP1_LAN_IP:8000
```

The script checks all ten trips and saves `results/api_checks.json` plus a sample response summary. Keep receiving-server logs visible for the actual physical demonstration. Do not claim the previous local-port test was already a physical two-laptop test.

### 7.5 Final report and package, after evidence is ready

```powershell
python run.py report
python scripts/package_submission.py
```

Report generation expects recorded experiments, API evidence and screenshots. Updating source/data/results does not automatically update screenshots or the PDF. Refresh relevant evidence, render/inspect a revised report, then package the consistent final state. No report changes are required merely because a teammate wrote a review note.

The package script creates `PathSnap_Submission.zip` and a SHA-256 manifest. It includes supplied data locally; `.gitignore` keeps data and ZIPs out of the repository. Regenerate the package last, once teammates' changes are integrated. Do not manually update hash values to disguise differences.

### 7.6 Meaningful work they can contribute

Review UI error handling and label isolation, perform an actual two-laptop check when available, improve installation instructions from a fresh environment, or address a real integration defect found during testing. Record exact commands, observed results and any unverified deployment path. Do not manufacture terminal screenshots or claim a test that was not run.

### 7.7 Suggested commit scope

After making real changes and regenerating relevant outputs:

```powershell
git add -- pathsnap/api.py pathsnap/visuals.py pathsnap/report.py ui tests scripts/check_api.py run.py start_backend.ps1 start_ui.ps1 requirements.txt Dockerfile docker-compose.yml README.md REVIEW1_README.md TEAM_GUIDE.md VIVA_GUIDE.md docs/person4_integration_review.md
git add -- results/figures results/maps results/api_checks.json results/api_sample_summary.json output/pdf scripts/package_submission.py submission_manifest.json
git diff --cached --stat
git diff --cached -- pathsnap/api.py run.py docs/person4_integration_review.md
git commit -m "Verify integration and document reproducible demonstration"
```

Do not stage outputs that do not match the final source and artifacts. If a path does not exist, omit it from the command.

## 8. Execution order: preparation versus live review

### 8.1 Preparation on the working project

| Order | Person | Command / action | Dependency |
|---:|---|---|---|
| 1 | All | Install environment, extract data, configure own identity | Source and original data |
| 2 | 1 | `python run.py explore` | Raw files |
| 3 | 2 | `python run.py review1 --trip 00000003` | Raw training trip; no trained model required |
| 4 | 3 | Inspect saved comparison; retrain only for intended experiment changes | Core features/labels; train/test inputs |
| 5 | 4 | Run verification; regenerate plots if experiments changed | Corresponding model artifacts and results |
| 6 | 4 | Optional API, then UI, then real HTTP checks | Final model/config and evaluation trip inputs |
| 7 | 4 | Review report/evidence, regenerate package last | Integrated final source and evidence |

In the live Review 1, present in the same person order, but use already generated model results. Do not block the presentation on refitting five models or rebuilding large maps.

### 8.2 How the parts depend on each other

```text
Raw trip files
  -> validation / metric coordinates / graph
  -> candidate features + weak training labels
  -> grouped model experiments and saved model
  -> comparison plots and interpretation
  -> optional decoder/API/UI
  -> final evidence and package
```

The EDA command and Review 1 export can independently read the raw files. The full training script also constructs its preprocessing through the shared functions; it does not require the exported CSVs as inputs.

## 9. GitHub setup: repository owner does this once

The local repository already has Git history. Do not initialise it again. Choose one team member as repository owner/integrator. That person creates an empty GitHub repository in the team's chosen account and invites the other three people as collaborators using their actual GitHub usernames.

For this existing repository, create the remote repository without another initial README/license commit to avoid unnecessary divergent initial histories. Then run:

```powershell
git remote -v
$teamRepoUrl = Read-Host 'Paste the team GitHub repository HTTPS URL'
git remote add origin $teamRepoUrl
git push -u origin main
```

Run `remote add` only if no `origin` exists. If `origin` exists, inspect it and use the intended destination; do not blindly overwrite another remote. Authenticate through the normal GitHub/Git credential flow. The event requires a public repository; confirm the intended visibility on GitHub when publishing.

Push only after local changes have been reviewed and committed. A GitHub URL and authentication were not supplied in this chat, so local commits are not evidence of a successful push.

The other three teammates clone the same destination:

```powershell
$teamRepoUrl = Read-Host 'Paste the team GitHub repository HTTPS URL'
git clone $teamRepoUrl PathSnap
Set-Location -LiteralPath '.\PathSnap'
```

Then configure their own local author identity, create their Python environment and extract the dataset. Their clone folder does not have to match the original laptop's absolute path.

## 10. Recommended contribution workflow: separate clones and feature branches

### 10.1 Synchronise before starting a task

Each person starts from a clean, current main branch:

```powershell
git status --short
git switch main
git pull --ff-only origin main
```

If status shows unfinished changes, finish or preserve them deliberately before switching; do not discard files simply to make the command succeed.

### 10.2 Each person creates their own branch

Run only the line for the actual person:

```powershell
# Person 1
git switch -c person1-data-eda

# Person 2
git switch -c person2-graph-features

# Person 3
git switch -c person3-model-experiments

# Person 4
git switch -c person4-integration-demo
```

If that branch already exists, use `git switch BRANCH_NAME` rather than trying to create it again. These branch names are labels, not evidence of authorship by themselves.

### 10.3 Do the actual assigned work

Read the owned code, run the relevant commands, inspect the evidence, make a concrete improvement or a substantive review document, and record what was checked. Each person's review note should contain:

```text
Actual reviewer name
Scope reviewed and functions understood
Commands executed
Observed outputs with file references
Specific change made and why
Verification performed
Remaining limitations
Acknowledgement of inherited/AI-assisted work where relevant
```

Create the `docs` directory if needed, then write the person's note using their editor. The review-note paths in this guide are suggested new files, not existing signed attestations.

### 10.4 Inspect and commit only that person's change

Use the role-specific staging scope above. Before committing:

```powershell
git status --short
git diff --stat
git diff --cached --stat
git config --get user.name
git config --get user.email
```

Inspect source diffs, generated output consistency and binary-file changes. If there are no staged changes, there is nothing new to commit. Do not use `--allow-empty` merely to create a contribution count. If a teammate adopts an existing AI-assisted change after review, describe that adoption/review honestly rather than claiming its original independent authorship.

### 10.5 Push the person's branch

Run the matching branch command:

```powershell
git push -u origin person1-data-eda
# or person2-graph-features / person3-model-experiments / person4-integration-demo
```

Open a pull request to `main`. Describe the concrete change, commands used for verification and any limitations. Another teammate reviews it before merging. Preserve the individual commits with a regular merge when the goal is to retain each actual author's commits; avoid squashing all four people's commits into one integration-author commit.

### 10.6 Merge order

Prefer Person 1, then Person 2, then Person 3, then Person 4 for dependent changes. If Person 3's experiment depends on Person 2's modified features, merge those features first and update Person 3's branch before running the experiment.

To incorporate merged main changes into a clean feature branch:

```powershell
git fetch origin
git merge origin/main
```

Resolve any actual conflict by understanding both changes, rerun affected checks and commit the resolution. Do not blindly select one side. Avoid parallel edits to `core.py`, `run.py`, shared result files and the manifest by following ownership.

### 10.7 Verify final history

After the pull requests are merged:

```powershell
git switch main
git pull --ff-only origin main
git log --all --format="%h | %an <%ae> | %s"
git shortlog -sne --all
git status --short
```

Check that real authors and substantive commits appear. GitHub associates commits with accounts using recognised author emails and its own display rules. A repository's default-branch history, PRs, diffs and verification evidence are stronger contribution records than a simple count.

## 11. Alternative: all four people use one shared laptop

Use sequential sessions, not simultaneous work. The repository-local author identity persists until changed, so check it at every handoff.

1. Finish/review the existing integration snapshot under its current legitimate identity.
2. Person 1 configures their own identity, makes their real changes, stages only their paths, commits and pushes through an account with permission.
3. Confirm the working directory has no unintended changes before Person 2 takes over.
4. Person 2 changes the local identity to their own, does their work and commits.
5. Repeat for Persons 3 and 4.
6. Inspect the final history and remote state.

Do not use another person's logged-in account or configure someone else's author identity without their involvement. A shared keyboard does not require changing the author of old commits. Separate clones/branches remain preferable when feasible.

## 12. How the current pending work should be handled

Before teammates start, the integrator should inspect `git status`. Existing pending changes from this session include the Review 1 exporter/entry-point update, generated Review 1 evidence, consolidated README guides and packaging updates. Those are inherited work, not four unrecorded teammate contributions.

The safe approach is to preserve them in one truthful integration snapshot, then let each actual teammate build their own contribution on top. Do not cherry-pick copies of the same change under four different authors or rewrite the initial complete-project commit to simulate a historical split.

The live Git log is the source of truth; the initial-state description above is historical context. After the guide/snapshot commit is made, the exact status and commit count will differ.

## 13. Final division of presentation time

For a roughly 12-minute Review 1, adjust to the evaluator's actual time limit:

| Person | Approximate time | Presentation |
|---|---:|---|
| 1 | 3 minutes | Problem, four input file types, major EDA findings and decisions |
| 2 | 4 minutes | Graph/coordinates, candidates, weak labels and eleven features using actual rows |
| 3 | 3 minutes | Five model motivations, training sample, grouped CV and selection |
| 4 | 2 minutes | Comparison plot, metric interpretation, limitations and reproducibility; optional integration only if time permits |

Everyone should be able to answer: what one feature row means, why row-random validation is problematic, why labels are weak, why the nearest road can be wrong, and what the chosen model's measured improvement actually was.

## 14. Final checklist before submission

- All four members can independently explain their owned code and its interfaces.
- Each claimed personal contribution has a real diff and truthful commit author/message.
- Existing AI-assisted work and external steps are described accurately.
- Everyone uses the same integrated feature definitions, artifacts and metric protocol.
- Data/caches/dependencies/ZIPs/secrets remain out of Git.
- `main` contains the reviewed commits and intended artifacts/results.
- The public repository is reachable by evaluators after actual publication.
- Review 1 outputs open offline; Folium is optional when internet is unreliable.
- The final package is regenerated after integration, and its integrity check passes.
- Physical two-laptop and reserved evaluator tests are not claimed until actually performed.

Read `REVIEW1_README.md` for the full technical explanations and viva answers. Use this guide for team coordination, file ownership, run order and contribution workflow.

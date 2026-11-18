# Explain and demonstrate your project

This guide is a study aid. Review the actual source and report; do not present AI assistance as unaided student work.

1. **What is being classified?** Candidate suitability, not a global road ID. Arc 42 in one trip may be unrelated to arc 42 in another. Binary candidate scoring transfers across local networks.
2. **How are labels obtained?** A monotone dynamic program aligns GPS points to the ordered reference arcs by projection distance. This produces weak point labels. The source dataset does not supply independently verified observation labels.
3. **Why eight candidates?** It is a fixed computational budget. Exact segment retrieval avoids midpoint-only errors; a 0.392% average student-test miss rate remains. Increasing k needs a new experiment.
4. **What stops leakage?** All rows from one trip stay within a fold. Scaling fits within the fold. Inference only loads track/nodes/arcs. The API reads routes after prediction for scoring. A corruption test verifies prediction independence from labels.
5. **Why gradient boosting?** It had the highest measured baseline grouped CV Macro F1. The margin over the forest is small. The saved experiment table, not an assumption about algorithm popularity, supports selection.
6. **What makes tuning Bayesian?** Optuna TPE uses prior observed trial outcomes to propose new parameter values after three startup trials. Ten trials optimise the same three trip-grouped folds. See CSV and SQLite logs.
7. **What does Viterbi do?** At each candidate it stores the best prior score plus directed transition compatibility and current log emission. Backtracking finds the highest-scoring candidate sequence.
8. **What is a transition?** Remaining length on prior arc + bounded directed shortest path + partial length on next arc. Compare it to observed movement. Unreachable transitions receive a penalty; long time gaps reset the chain.
9. **Did HMM help?** It raised Macro F1 and continuity but reduced Top-1 accuracy. Read the per-trip decoder plot and explain why connectivity can help rare segments while changing frequent point labels.
10. **Is this a calibrated HMM?** Emissions are normalised learned scores; transitions are unnormalised potentials. We do not claim posterior calibration or decoded sequence log loss.
11. **What is still unverified?** Reserved evaluation, a physical two-laptop run, Docker execution and public GitHub publication. Local HTTP tests cover all supplied student-test trips, and browser testing covers real reconstruction.

## Demonstration order

Start the API on Laptop 1 and keep its terminal visible. Start the UI on Laptop 2. Enter Laptop 1's LAN IP, connect, choose any supplied evaluator trip, and reconstruct it. Point out API request logs, observation count, metrics, map layers, zoom/pan and visible route breaks. Show that the UI response has no reference route. Explain that metrics are derived from server-side weak labels when references are supplied.

Use `python scripts/check_api.py http://LAPTOP1_IP:8000` to exercise all ten trips. Save the actual output and capture the receiving terminal on Laptop 1. Add that screenshot and team details to the final report rather than claiming this workspace's local test was a physical two-laptop run.

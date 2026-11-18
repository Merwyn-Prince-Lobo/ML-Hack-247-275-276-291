\# Dataset Exploratory Data Analysis (EDA)



\## Overview

This module performs exploratory data analysis on the PathSnap GPS trajectory dataset. It analyses the training and student test datasets to understand GPS observations, road network structure, timestamps, and reference route statistics.



\## Files



| File | Description |

|---|---|

| `explore.py` | Python script for dataset exploration and statistical analysis. |

| `inventory.csv` | Per-trip statistics for the dataset. |

| `eda.json` | Aggregated EDA summary for training and student test splits. |



\## Analysis Performed



The EDA script examines:



\- Number of GPS observations per trip.

\- Number of road network nodes and arcs.

\- Missing-value count recorded by the analysis.

\- Duplicate timestamps.

\- Time gaps between consecutive GPS observations.

\- Maximum and median timestamp gaps.

\- Weakly connected components in road networks.

\- Isolated road network nodes.

\- Total GPS trajectory distance.

\- Geographic coordinate boundaries.

\- Reference route arc counts.

\- Dataset storage size per trip.



\## Dataset Summary



| Metric | Training | Student Test |

|---|---:|---:|

| Number of trips | 80 | 10 |

| GPS observations | 208,417 | 19,160 |

| Maximum time gap (seconds) | 153,064 | 210 |

| One-second sampling fraction | 96.50% | 98.62% |

| Trips with multiple weakly connected components | 79 | 10 |

| Total isolated nodes | 0 | 0 |



\*\*Note:\*\* The missing-value count is currently recorded as zero by the EDA script. This should be verified against the dataset loader's validation logic before treating it as an independently confirmed result.



\## Execution



The script depends on the project's shared `core.py` and `experiments.py` modules.



Run it from the project package context once those dependencies and the dataset paths are available.



\## Output



The analysis generates:

\- `inventory.csv` – detailed per-trip statistics.

\- `eda.json` – aggregated statistics for each dataset split.


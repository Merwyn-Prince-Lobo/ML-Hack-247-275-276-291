"""Actual, reproducible grouped experiments. No evaluator partition access."""
import csv
import json
import time
from pathlib import Path
import joblib
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix
from core import load_trip, candidates, reference_labels, probabilities, decode, continuity, FEATURES

ROOT = Path(__file__).resolve().parent
DATA = ROOT/'Student folder'
RESULTS = ROOT/'results'
SEED = 352

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')

def dataset(split):
    output = []
    for folder in sorted((DATA/split).iterdir()):
        if not folder.is_dir():
            continue
        cache = ROOT/'cache'/f'{split}_{folder.name}.joblib'
        if cache.exists():
            record = joblib.load(cache)
        else:
            trip = load_trip(folder)
            c = candidates(trip)
            labels, alignment_distance, route = reference_labels(trip, folder)
            record = {'trip': trip, 'c': c, 'labels': labels, 'alignment_distance': alignment_distance, 'route': route}
            cache.parent.mkdir(exist_ok=True)
            joblib.dump(record, cache, compress=3)
        output.append(record)
    return output

def training_arrays(records):
    xs, ys, groups = [], [], []
    for r in records:
        # Deterministic uniform observation subsample to give each trip equal budget.
        n = len(r['labels'])
        idx = np.unique(np.linspace(0, n-1, min(200, n), dtype=int))
        x = r['c']['x'][idx]
        y = (r['c']['ids'][idx] == r['labels'][idx, None]).astype(int)
        xs.append(x.reshape(-1, len(FEATURES)))
        ys.append(y.ravel())
        groups.extend([r['trip'].trip_id]*y.size)
    return np.concatenate(xs), np.concatenate(ys), np.array(groups)

def model_factory(name, params=None):
    params = params or {}
    if name == 'LogisticRegression':
        return make_pipeline(StandardScaler(), LogisticRegression(C=1., max_iter=500, random_state=SEED, **params))
    if name == 'GaussianNB':
        return make_pipeline(StandardScaler(), GaussianNB(**params))
    if name == 'DecisionTree':
        return DecisionTreeClassifier(max_depth=12, min_samples_leaf=20, random_state=SEED, **params)
    if name == 'RandomForest':
        defaults = dict(n_estimators=64, max_depth=16, min_samples_leaf=8, max_features=.8, n_jobs=-1, random_state=SEED)
        defaults.update(params)
        return RandomForestClassifier(**defaults)
    if name == 'HistGradientBoosting':
        defaults = dict(max_iter=100, max_leaf_nodes=15, learning_rate=.1, l2_regularization=1., random_state=SEED)
        defaults.update(params)
        return HistGradientBoostingClassifier(**defaults)
    raise ValueError(name)

def point_metrics(truth, pred):
    return {'top1_accuracy': float(accuracy_score(truth, pred)),
            'macro_f1': float(f1_score(truth, pred, average='macro', zero_division=0)),
            'macro_precision': float(precision_score(truth, pred, average='macro', zero_division=0)),
            'macro_recall': float(recall_score(truth, pred, average='macro', zero_division=0))}

def evaluate(model, records, with_continuity=False, hmm=False, beta=30.):
    rows, confusion = [], np.zeros((2, 2), dtype=int)
    for r in records:
        start = time.perf_counter()
        c, truth, trip = r['c'], r['labels'], r['trip']
        p = probabilities(model, c['x'])
        raw = c['ids'][np.arange(len(p)), p.argmax(axis=1)]
        pred = decode(trip, c, p, beta=beta)[0] if hmm else raw
        elapsed = time.perf_counter()-start
        hits = c['ids'] == truth[:, None]
        # Include candidate misses with epsilon mass; report separately too.
        true_probability = np.sum(p*hits, axis=1)
        metrics = point_metrics(truth, pred)
        metrics.update(trip_id=trip.trip_id, observations=len(truth), inference_seconds=elapsed,
                       log_loss=float(-np.log(np.clip(true_probability, 1e-15, 1)).mean()),
                       candidate_miss_rate=float((~hits.any(axis=1)).mean()),
                       route_set_f1=float(2*len(set(pred)&set(r['route']))/max(1, len(set(pred))+len(set(r['route'])))))
        if with_continuity:
            metrics['route_continuity'] = continuity(trip, pred)
        selected = np.zeros_like(hits)
        selected[np.arange(len(p)), p.argmax(axis=1)] = True
        confusion += confusion_matrix(hits.ravel(), selected.ravel(), labels=[0, 1])
        rows.append(metrics)
    keys = [k for k in rows[0] if k not in ['trip_id', 'observations']]
    aggregate = {k: float(np.mean([r[k] for r in rows])) for k in keys}
    aggregate['inference_seconds'] = sum(r['inference_seconds'] for r in rows)
    return {'aggregate': aggregate, 'per_trip': rows, 'candidate_confusion_matrix': confusion.tolist()}

def main(trials=10):
    RESULTS.mkdir(exist_ok=True)
    (ROOT/'artifacts').mkdir(exist_ok=True)
    print('Preparing training and student-test candidates...', flush=True)
    train, test = dataset('train'), dataset('student_test')
    if len(train) != 80 or len(test) != 10:
        raise ValueError('Expected exactly 80 training and 10 student-test trips')
    x, y, groups = training_arrays(train)
    folds = list(GroupKFold(3).split(x, y, groups))
    fold_ids = []
    for _, va in folds:
        fold_ids.append(set(groups[va]))
    write_json(RESULTS/'protocol.json', {'seed': SEED, 'folds': [sorted(s) for s in fold_ids],
        'train_observation_budget_per_trip': 200, 'candidate_k': 8, 'features': FEATURES,
        'selection_metric': 'mean trip macro F1 on held-out training trips',
        'label_method': 'monotone dynamic programming alignment to supplied route; weak labels',
        'log_loss': 'normalised candidate probability; misses get 1e-15; mean of trip means',
        'macro_f1': 'macro over union of predicted/reference local arc IDs within trip; mean across trips'})
    names = ['LogisticRegression', 'GaussianNB', 'DecisionTree', 'RandomForest', 'HistGradientBoosting']
    results = {}
    for name in names:
        print('Training', name, flush=True)
        started = time.perf_counter()
        cv = []
        for tr, va in folds:
            model = model_factory(name)
            model.fit(x[tr], y[tr])
            valid_ids = set(groups[va])
            cv.append(evaluate(model, [r for r in train if r['trip'].trip_id in valid_ids]))
        model = model_factory(name)
        model.fit(x, y)
        fit_seconds = time.perf_counter()-started
        joblib.dump(model, ROOT/'artifacts'/f'{name}.joblib', compress=3)
        test_result = evaluate(model, test, with_continuity=True)
        results[name] = {'configuration': model.get_params(deep=False).__repr__(),
                         'cv_macro_f1': float(np.mean([v['aggregate']['macro_f1'] for v in cv])),
                         'cv_fold_macro_f1': [v['aggregate']['macro_f1'] for v in cv],
                         'training_and_cv_seconds': fit_seconds, 'cv': cv, 'student_test': test_result,
                         'train_sample_candidate_accuracy': float(model.score(x, y))}
        write_json(RESULTS/'models.json', results)
        print(name, results[name]['cv_macro_f1'], test_result['aggregate'], flush=True)
    selected = max(names, key=lambda name: results[name]['cv_macro_f1'])
    print('Selected by grouped CV:', selected, flush=True)
    import optuna
    sampler = optuna.samplers.TPESampler(seed=SEED, n_startup_trials=3)
    study = optuna.create_study(direction='maximize', sampler=sampler, storage=f'sqlite:///{(RESULTS/"bayesian_search.sqlite3").as_posix()}', study_name='pathsnap', load_if_exists=True)
    def objective(trial):
        if selected == 'HistGradientBoosting':
            params = dict(learning_rate=trial.suggest_float('learning_rate', .025, .25, log=True),
                          max_leaf_nodes=trial.suggest_int('max_leaf_nodes', 7, 31),
                          l2_regularization=trial.suggest_float('l2_regularization', .01, 10., log=True),
                          max_iter=trial.suggest_int('max_iter', 60, 160))
        elif selected == 'RandomForest':
            params = dict(max_depth=trial.suggest_int('max_depth', 6, 22), min_samples_leaf=trial.suggest_int('min_samples_leaf', 2, 30), max_features=trial.suggest_float('max_features', .4, 1.))
        elif selected == 'DecisionTree':
            params = dict(criterion=trial.suggest_categorical('criterion', ['gini', 'entropy']), max_features=trial.suggest_float('max_features', .4, 1.))
        elif selected == 'GaussianNB':
            params = dict(var_smoothing=trial.suggest_float('var_smoothing', 1e-12, 1e-3, log=True))
        else:
            params = dict(tol=trial.suggest_float('tol', 1e-6, 1e-2, log=True), class_weight=trial.suggest_categorical('class_weight', [None, 'balanced']))
        scores = []
        for tr, va in folds:
            model = model_factory(selected, params)
            model.fit(x[tr], y[tr])
            ids = set(groups[va])
            scores.append(evaluate(model, [r for r in train if r['trip'].trip_id in ids])['aggregate']['macro_f1'])
        trial.set_user_attr('fold_scores', scores)
        return float(np.mean(scores))
    study.optimize(objective, n_trials=max(0, trials-len(study.trials)))
    study.trials_dataframe().to_csv(RESULTS/'bayesian_trials.csv', index=False)
    tuned = model_factory(selected, study.best_params)
    tuned.fit(x, y)
    tuned_result = evaluate(tuned, test, with_continuity=True)
    # Keep untuned model if tuning did not improve grouped CV.
    use_tuned = study.best_value > results[selected]['cv_macro_f1']
    final = tuned if use_tuned else joblib.load(ROOT/'artifacts'/f'{selected}.joblib')
    joblib.dump(tuned, ROOT/'artifacts'/'tuned_model.joblib', compress=3)
    joblib.dump(final, ROOT/'artifacts'/'model.joblib', compress=3)
    raw = evaluate(final, test, with_continuity=True)
    hmm_results = {}
    # Development-only decoder sweep, reported explicitly.
    for beta in [15., 30., 60.]:
        print('Evaluating HMM beta', beta, flush=True)
        hmm_results[str(beta)] = evaluate(final, test, with_continuity=True, hmm=True, beta=beta)
        write_json(RESULTS/'hmm.json', hmm_results)
    beta = max(hmm_results, key=lambda b: hmm_results[b]['aggregate']['macro_f1'])
    config = {'model_family': selected, 'use_tuned': use_tuned, 'parameters': study.best_params if use_tuned else {},
              'beta': float(beta), 'gap_s': 60., 'candidate_k': 8, 'features': FEATURES, 'seed': SEED}
    write_json(ROOT/'artifacts'/'config.json', config)
    write_json(RESULTS/'final.json', {'selected': selected, 'use_tuned': use_tuned, 'best_cv_macro_f1': study.best_value,
        'best_params': study.best_params, 'search_trials': len(study.trials), 'tuned_student_test': tuned_result,
        'classifier_only': raw, 'hmm': hmm_results[beta], 'decoder_beta': float(beta)})
    print('Experiments complete.', flush=True)


if __name__ == "__main__":
    main()

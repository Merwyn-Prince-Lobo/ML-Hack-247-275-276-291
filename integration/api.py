"""Inference has no access to reference labels; evaluation is a separate step."""
import json
import logging
import os
import time
from functools import lru_cache
from pathlib import Path
import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .core import load_trip, candidates, probabilities, decode, route_geometry, reference_labels
from .experiments import ROOT, DATA, point_metrics

log = logging.getLogger('uvicorn.error')
app = FastAPI(title='PathSnap', version='1.0.0')
origins = os.getenv('PATHSNAP_UI_ORIGINS', '*').split(',')
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

def data_root():
    return Path(os.environ.get('PATHSNAP_EVAL_DIR', str(DATA/'student_test'))).resolve()

@lru_cache(maxsize=1)
def assets():
    return joblib.load(ROOT/'artifacts'/'model.joblib'), json.loads((ROOT/'artifacts'/'config.json').read_text())

def trip_folder(trip_id):
    if len(trip_id) != 8 or not trip_id.isascii() or not trip_id.isdigit():
        raise HTTPException(400, 'Trip ID must contain exactly eight ASCII digits')
    folder = data_root()/trip_id
    if not folder.is_dir() or not all((folder/(trip_id+'.'+ext)).is_file() for ext in ['track', 'nodes', 'arcs']):
        raise HTTPException(404, 'Trip not found or inputs incomplete')
    return folder

class PredictRequest(BaseModel):
    trip_id: str = Field(min_length=8, max_length=8)
    evaluate: bool = True

@app.get('/health')
def health():
    try:
        _, config = assets()
    except (FileNotFoundError, ValueError):
        raise HTTPException(503, 'Train model first: python run.py train')
    return {'status': 'ok', 'model': config['model_family'], 'mode': 'reserved-evaluator' if os.getenv('PATHSNAP_EVAL_DIR') else 'student-test-development'}

@app.get('/trips')
def trips():
    root = data_root()
    if not root.is_dir():
        raise HTTPException(503, 'Configured evaluation directory does not exist')
    found = []
    for folder in sorted(root.iterdir()):
        if folder.is_dir() and len(folder.name) == 8 and folder.name.isascii() and folder.name.isdigit():
            if all((folder/(folder.name+'.'+ext)).is_file() for ext in ['track', 'nodes', 'arcs']):
                found.append({'trip_id': folder.name})
    return {'trips': found, 'count': len(found), 'mode': health()['mode']}

def infer(folder):
    start = time.perf_counter()
    model, config = assets()
    trip = load_trip(folder)
    c = candidates(trip, config['candidate_k'])
    p = probabilities(model, c['x'])
    predicted, choice, resets = decode(trip, c, p, beta=config['beta'], gap_s=config['gap_s'])
    route, lines, breaks = route_geometry(trip, predicted)
    snap = c['snap'][np.arange(len(choice)), choice]
    # Convert via interpolation on original lon/lat coordinates.
    fraction = c['frac'][np.arange(len(choice)), choice]
    endpoints = trip.nodes[trip.arcs[predicted]]
    snapped = endpoints[:, 0]+fraction[:, None]*(endpoints[:, 1]-endpoints[:, 0])
    result = {'trip_id': trip.trip_id, 'observations': len(trip.gps), 'model': config['model_family'],
              'gps': trip.gps[:, :2].tolist(), 'predicted_arc_ids': predicted.tolist(), 'route_arc_ids': route,
              'route_segments': lines, 'road_segments': trip.nodes[trip.arcs].tolist(), 'snapped': snapped.tolist(),
              'gap_reset_indices': resets, 'route_break_indices': breaks,
              'inference_seconds': time.perf_counter()-start}
    return trip, result

@app.post('/predict')
def predict(request: PredictRequest):
    folder = trip_folder(request.trip_id)
    try:
        trip, response = infer(folder)
        # Labels loaded only AFTER prediction has finished; never returned.
        if request.evaluate and (folder/(trip.trip_id+'.route')).is_file():
            labels, distances, _ = reference_labels(trip, folder)
            response['metrics'] = point_metrics(labels, np.array(response['predicted_arc_ids']))
            response['metrics']['reference_alignment_distance_median_m'] = float(np.median(distances))
            response['evaluation_note'] = 'Metrics use weak point labels derived from ordered reference route.'
        else:
            response['metrics'] = None
        log.info('trip=%s observations=%s latency=%.3fs metrics=%s', request.trip_id, response['observations'], response['inference_seconds'], response['metrics'])
        return response
    except (ValueError, OSError) as error:
        log.exception('Trip processing failed')
        raise HTTPException(422, f'Invalid trip data: {error}')

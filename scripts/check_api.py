"""Exercise every available trip over real HTTP; retain audit evidence."""
import sys
import json
import time
import urllib.request
from pathlib import Path

base = sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8000'
root = Path(__file__).resolve().parents[1]
def get(path, payload=None):
    request=urllib.request.Request(base+path, data=None if payload is None else json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=180) as response:
        assert response.status == 200
        return json.load(response)
health=get('/health'); trips=get('/trips');rows=[]
assert trips['count']==10, trips
for t in trips['trips']:
    value=get('/predict',{'trip_id':t['trip_id'],'evaluate':True})
    assert len(value['predicted_arc_ids'])==value['observations']==len(value['gps'])==len(value['snapped'])
    assert len(value['route_segments'])==len(value['route_arc_ids'])
    assert not any(key in value for key in ['reference_route','reference_labels','ground_truth','labels'])
    rows.append({key:value[key] for key in ['trip_id','observations','inference_seconds','metrics']})
    if len(rows)==1:
        (root/'results'/'api_sample_summary.json').write_text(json.dumps({k:v for k,v in value.items() if k not in ['gps','road_segments','route_segments','snapped','predicted_arc_ids','route_arc_ids']},indent=2))
    print(f"PASS {value['trip_id']} observations={value['observations']} time={value['inference_seconds']:.3f}s",flush=True)
(root/'results'/'api_checks.json').write_text(json.dumps({'health':health,'passed':len(rows),'trips':rows},indent=2))
print('All ten trips passed real HTTP checks.',flush=True)

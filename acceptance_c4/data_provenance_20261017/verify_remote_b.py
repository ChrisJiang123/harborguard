"""Read-only offline verification of fetched B code, without touching demo services."""
import os, sys, json, subprocess, hashlib
from pathlib import Path
checkout=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(checkout))
assert os.environ['CLOUD_PROVIDER']=='disabled'
import httpx
network_calls=[]
def forbidden(*args,**kwargs):
    network_calls.append('attempted_http')
    raise AssertionError('Network forbidden in offline B verification')
httpx.Client.send=forbidden
httpx.AsyncClient.send=forbidden
from backend.tools.model_acceptance import run
from backend.app import config
assert str(config.ROOT).startswith(str(checkout))
results=[]
for i in range(3):
    row=run('b')
    obstacles={d['zone'] for d in row['debris_zones']}
    false_clear=[e for e in row['events'] if e['event']=='zone_changed' and e['data']['zone_id'] in obstacles and e['data']['state']=='clear']
    assert not false_clear, false_clear
    assert len(row['debris_zones'])==4
    assert all(d['state'] in ('blocked','unsurveyed') for d in row['debris_zones'])
    assert row['calls'] and all(c['model']=='yolo26n' for c in row['calls'])
    assert not obstacles.intersection(row['reopen']['route_zone_ids']+row['reopen']['reopen_berth_zone_ids'])
    assert not network_calls
    row['no_obstacle_clear_throughout']=True
    results.append(row)
    print('B repeat',i+1,row['zone_counts'],row['reopen']['est_hours_saved'],flush=True)
assert len({r['semantic_sha256'] for r in results})==1
out={'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=checkout,text=True).strip(),'weights_sha256':hashlib.sha256(config.SONAR_WEIGHTS_PATH.read_bytes()).hexdigest(),'cloud_provider':'disabled','http_call_attempts':len(network_calls),'source_root_verified':str(config.ROOT),'runs':results,'scope':'Fetched remote B with tracked C renderer; does not update the live demo, does not include uncommitted C geometry helpers.'}
(Path(__file__).resolve().parents[2] / 'runs/codex-c4-handoff/b-offline-raw.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')

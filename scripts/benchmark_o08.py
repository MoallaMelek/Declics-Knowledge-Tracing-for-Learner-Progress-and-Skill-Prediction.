"""Measured local HTTP inference; no invented latency guarantees."""
import argparse
import json
from pathlib import Path
import time
import urllib.request
import numpy as np
ROOT=Path(__file__).resolve().parents[1]


def run(base,count,output):
    def request(path,payload=None):
        data=None if payload is None else json.dumps(payload).encode()
        req=urllib.request.Request(base+path,data=data,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
    results=[]
    for source in ('singpad','yousician'):
        history=request('/api/v6/o08/demo/history?source='+source)
        assert 'observed_target' not in history and not history['future_outcome_included']
        elapsed=[]
        for _ in range(count):
            start=time.perf_counter();prediction=request('/api/v6/o08/demo/predict',{'receipt':history['receipt']})
            elapsed.append(time.perf_counter()-start)
            assert prediction['forecast']['status']=='source_benchmark_only'
            assert 'observed_target' not in prediction
        reveal=request('/api/v6/o08/demo/reveal',{'receipt':prediction['reveal_receipt']})
        assert reveal['observed_target']
        results.append({'source':source,'requests':count,'first_measured_ms':elapsed[0]*1000,
            'warm_median_ms':float(np.median(elapsed[1:]))*1000,'warm_p95_ms':float(np.quantile(elapsed[1:],.95))*1000,
            'model_id':prediction['forecast']['model_id'],'real_three_step_workflow':True,
            'target_held_out_of_browser_until_reveal':True})
    report={'base_url':base,'measurements':results,'scope':'local machine HTTP requests; first measurement not necessarily cold, no concurrent-load benchmark',
            'configuration':'single uvicorn worker; actual runtime thread configuration recorded separately'}
    path=Path(output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--url',default='http://127.0.0.1:8773');p.add_argument('--count',type=int,default=15);p.add_argument('--output',required=True)
    args=p.parse_args()
    if args.count<3:raise ValueError('Need at least three requests')
    run(args.url,args.count,args.output)

"""Execute the actual v3 -> v4 frozen-model journey on explicitly synthetic assessments."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import argparse,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from axis7 import server

def replay():
    old_db=server.DB
    try:
        with tempfile.TemporaryDirectory(prefix='axis7-phase4-') as folder:
            server.DB=Path(folder)/'events.sqlite'
            with TestClient(server.app) as client:
                learner='phase4-explicit-simulation';start=datetime(2026,6,1,tzinfo=timezone.utc)
                def event(i,outcome):
                    return {'schema_version':'3.0','attempt_id':f'{learner}:{i}','student_id':learner,
                        'session_id':f's{i}','exercise_id':'demonstration-exercise','instrument':'piano-provisional',
                        'timestamp':(start+timedelta(days=i)).isoformat(),'provenance':'synthetic',
                        'rubric_version':'provisional-mock-v1','observations':[{'skill_id':'pitch','producer_axis':1,
                        'producer_version':'explicit-mock-assessment-v1','objective_id':'O01',
                        'assessment_kind':'direct','outcome':outcome,'source_confidence':1.,'reference_compared':True}]}
                for i,outcome in enumerate([0,0,1,0,1]):
                    response=client.post('/api/v3/evidence',json=event(i,outcome));response.raise_for_status()
                query={'student_id':learner,'instrument':'piano','exercise_id':None,
                    'model_id':'v2:music-mock:2026:enhanced_gru-7','as_of':(start+timedelta(days=5)).isoformat(),
                    'evidence_source':'team_v3','include_research_predictions':False}
                default=client.post('/api/v4/forecast',json=query);default.raise_for_status()
                query['include_research_predictions']=True
                before=client.post('/api/v4/forecast',json=query);before.raise_for_status();before=before.json()
                # Reveal a scripted synthetic outcome ONLY after the prediction has been produced.
                held_out=event(5,1);client.post('/api/v3/evidence',json=held_out).raise_for_status()
                repeat=client.post('/api/v4/forecast',json=query);repeat.raise_for_status();repeat=repeat.json()
                query_next={**query,'as_of':(start+timedelta(days=6)).isoformat()}
                after=client.post('/api/v4/forecast',json=query_next);after.raise_for_status();after=after.json()
                invariant=(before['probabilities']==repeat['probabilities'] and before['evidence_ids']==repeat['evidence_ids'])
                if not invariant:raise AssertionError('Future outcome changed a prior-cutoff forecast')
                if before['status']!='research_only' or default.json()['status']!='abstained':
                    raise AssertionError('Simulation/default policy incorrect')
                return {'provenance':'synthetic_demonstration_not_real_music','models_trained':0,
                    'default_response':default.json(),'forecast_before_reveal':before,
                    'revealed_synthetic_outcome':held_out,'same_cutoff_after_append':repeat,
                    'forecast_with_updated_history':after,'future_append_invariant':invariant,
                    'scope':'generic skill forecast; no validated exercise conditioning or real musical claim'}
    finally:server.DB=old_db

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'artifacts/phase4/synthetic-replay.json')
    output=parser.parse_args().output;result=replay();output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps({'future_append_invariant':result['future_append_invariant'],
        'prefix_before':result['forecast_before_reveal']['prefix_count'],
        'prefix_after':result['forecast_with_updated_history']['prefix_count'],
        'status':result['forecast_before_reveal']['status'],'output':str(output)}))

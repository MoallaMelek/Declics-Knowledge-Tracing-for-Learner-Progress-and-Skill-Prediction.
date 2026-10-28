"""Licensed piano practice inventory. MIDI descriptors are NOT performance assessments."""
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import hashlib, json, re

def checksum(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def rach_identity(path):
    match=re.fullmatch(r'(p[1-4])(\d{6})(\d)(\d{2})(.+)\.mid',Path(path).name)
    if not match:raise ValueError('Unsupported Rach3 rehearsal filename')
    learner,day,session,order,piece=match.groups()
    date=datetime.strptime('20'+day,'%Y%m%d').date().isoformat()
    return {'learner_id':'rach3-'+learner,'calendar_date':date,'daily_session':int(session),
            'piece_order':int(order),'exercise_id':piece,'time_precision':'calendar_day_and_source_order',
            'order_key':[date,int(session),int(order)]}

def midi_descriptors(path):
    import mido
    midi=mido.MidiFile(path)
    if midi.type==2:raise ValueError('Asynchronous type-2 MIDI is outside this descriptive loader')
    notes=sum(message.type=='note_on' and message.velocity>0 for track in midi.tracks for message in track)
    return {'duration_seconds':float(midi.length),'note_on_count':notes,'midi_tracks':len(midi.tracks),
            'ticks_per_beat':midi.ticks_per_beat,'meaning':'recording descriptors, not accuracy or skill'}

def duration_seconds(text):
    match=re.fullmatch(r'(\d+) days (\d{2}):(\d{2}):(\d{2})\.(\d{3})\.000000',text)
    if not match:raise ValueError('Unsupported PianoVAM duration')
    days,hours,minutes,seconds,milliseconds=map(int,match.groups())
    return days*86400+hours*3600+minutes*60+seconds+milliseconds/1000

def load_pianovam(metadata):
    names=sorted({row['P1_name'] for row in metadata.values() if row['performance_method']=='Solo'})
    ids={name:f'pianovam-p{i+1:02d}' for i,name in enumerate(names)}
    records=[]
    for key,row in metadata.items():
        if row['performance_method']!='Solo':continue
        timestamp=datetime.strptime(row['record_time'],'%Y-%m-%d_%H-%M-%S').isoformat()
        piece=f"{row['composer']} / {row['piece']}"
        records.append({'attempt_id':'pianovam-'+str(key),'learner_id':ids[row['P1_name']],
            'exercise_id':piece,'recorded_local_time':timestamp,'calendar_date':timestamp[:10],
            'time_precision':'source_wall_clock_timezone_unspecified','order_key':[timestamp],
            'duration_seconds':duration_seconds(row['duration']),
            'outcome':None,'source':'PianoVAM','instrument':'piano',
            'provenance':'licensed_public_practice_metadata','assessment_available':False})
    return sorted(records,key=lambda r:(r['learner_id'],r['order_key'],r['attempt_id']))

def descriptive_split(records):
    """Last distinct day per learner/piece withheld. No fabricated UTC or response labels."""
    groups=defaultdict(list)
    for row in records:groups[(row['learner_id'],row['exercise_id'])].append(row)
    partitions={'earlier':[],'future':[],'single_day_excluded':[]}
    for rows in groups.values():
        days={row['calendar_date'] for row in rows}
        if len(days)<2:
            partitions['single_day_excluded'].extend(row['attempt_id'] for row in rows);continue
        boundary=max(days)
        for row in rows:partitions['future' if row['calendar_date']==boundary else 'earlier'].append(row['attempt_id'])
    return {**partitions,'scope':'within-learner same-piece descriptive future-day holdout',
        'target_available':False,'usable_for_knowledge_tracing':False,
        'learner_disjoint':False,'warning':'No correctness labels; four Rach3 learners cannot support population-level neural validation.'}

def analyze(raw):
    raw=Path(raw);receipt=json.loads((raw/'acquisition.json').read_text(encoding='utf8'))
    for file in receipt['files']:
        path=(raw/file['path']).resolve()
        if not path.is_relative_to(raw.resolve()) or checksum(path)!=file['sha256']:
            raise ValueError('Acquired byte checksum or path invalid')
    rach=[]
    for file in receipt['files']:
        if file['path'].endswith('.mid'):
            identity=rach_identity(file['path'])
            rach.append({'attempt_id':Path(file['path']).stem,**identity,**midi_descriptors(raw/file['path']),
                'source':'Rach3','instrument':'piano','source_sha256':file['sha256'],
                'provenance':'licensed_public_practice_midi','outcome':None,'assessment_available':False})
    piano=load_pianovam(json.loads((raw/'PianoVAM/metadata.json').read_text(encoding='utf8')))
    records=sorted(rach,key=lambda r:(r['learner_id'],r['order_key']))+piano
    groups=defaultdict(list)
    for row in records:groups[(row['source'],row['learner_id'],row['exercise_id'])].append(row)
    repeats=[{'source':source,'learner_id':learner,'exercise_id':exercise,'recordings':len(rows),
        'distinct_days':len({r['calendar_date'] for r in rows}),
        'first_day':min(r['calendar_date'] for r in rows),'last_day':max(r['calendar_date'] for r in rows),
        'duration_min_seconds':min(r['duration_seconds'] for r in rows),
        'duration_max_seconds':max(r['duration_seconds'] for r in rows),
        'assessment_available':False} for (source,learner,exercise),rows in groups.items() if len(rows)>1]
    return {'schema_version':'music-case-study-1.0','acquisition':receipt,'records':records,
        'summary':{'rach3_recordings':len(rach),'rach3_learners':len({r['learner_id'] for r in rach}),
        'pianovam_solo_recordings':len(piano),'pianovam_learners':len({r['learner_id'] for r in piano}),
        'repeat_groups':len(repeats),'multi_day_repeat_groups':sum(r['distinct_days']>1 for r in repeats),
        'usable_assessment_targets':0,'models_trained':0,'real_music_predictive_validity_established':False},
        'repeated_groups':repeats,'partitions':descriptive_split(records),
        'limitations':['Duration and note count do not measure correctness, fluency, improvement or mastery.',
            'Source skill-level demographic fields are omitted; they are not longitudinal outcomes.',
            'No timezone invented. Holdouts separate whole calendar days.',
            'PianoVAM source train/test split is not treated as a learner-disjoint KT split.',
            'Rach3 sample selected for repeated coverage; no representative sampling claim.',
            'No assessment, recognition, alignment or other teammate model is implemented.']}

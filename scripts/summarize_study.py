"""Summarize real, paired manual-versus-assistant next-step study trials."""
import csv
import json
from pathlib import Path
from statistics import mean


def summarize(path):
    rows=list(csv.DictReader(Path(path).open(encoding="utf-8",newline="")))
    if not rows:
        return {"trials":0,"status":"Not run; no faster-resolution claim is supported."}
    pairs={}
    for row in rows:
        if row['condition'] not in {'manual','assistant'} or row['correct'] not in {'0','1'}:
            raise ValueError('condition must be manual/assistant; correct must be 0/1')
        row['seconds']=float(row['seconds'])
        if not 0 < row['seconds'] < float('inf'):
            raise ValueError('seconds must be finite and positive')
        key=(row['participant_id'],row['matched_pair_id'])
        if not all(key):
            raise ValueError('participant_id and matched_pair_id are required')
        pair=pairs.setdefault(key,{})
        if row['condition'] in pair:
            raise ValueError('Duplicate condition for participant and matched pair')
        pair[row['condition']]=row
    complete=[p for p in pairs.values() if set(p)=={'manual','assistant'}]
    comparable=[p for p in complete if all(r['correct']=='1' for r in p.values())]
    reductions=[1-p['assistant']['seconds']/p['manual']['seconds'] for p in comparable]
    return {'trials':len(rows),'complete_pairs':len(complete),'both_correct_pairs':len(comparable),
            'incomplete_pairs':len(pairs)-len(complete),
            'accuracy':{c:mean(int(r['correct']) for r in rows if r['condition']==c) if any(r['condition']==c for r in rows) else None for c in ['manual','assistant']},
            'mean_paired_time_reduction':mean(reductions) if reductions else None,
            'scope':'Time to identify the next step, not actual incident resolution time.'}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path',nargs='?',default='data/eval/timed_study.csv')
    print(json.dumps(summarize(parser.parse_args().path),indent=2))

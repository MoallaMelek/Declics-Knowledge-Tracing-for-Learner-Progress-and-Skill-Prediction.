"""An observation-only event is not a hidden neural clock tick.

Eligibility is resolved at ingestion. Legacy binary observations remain usable;
explicitly excluded, missing and low-confidence outcomes never update a model.
"""
from copy import copy
import numpy as np

def eligible(o):
    return o.get('k') is not None and o.get('y') in (0,1) and o.get('eligible',True)

def compact_history(rows):
    compact=[];positions=[0]
    for row in rows:
        obs=[o for o in row['obs'] if eligible(o)]
        if obs:
            record=copy(row);record['obs']=obs;compact.append(record)
        positions.append(len(compact))
    return compact,np.asarray(positions,dtype=int)

def expand_forecasts(predictions,positions,query=True):
    """Maps forecasts back to the original evidence timeline, including no-ops."""
    return predictions[positions if query else positions[:-1]]

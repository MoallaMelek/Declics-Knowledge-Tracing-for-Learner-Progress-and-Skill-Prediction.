"""Identities of effective serving inputs, never model features or claims of authenticity.

The source archive digest is retained separately. Hash the observations actually loaded,
including their schema/preparation configuration. Model generation includes full metadata
and the checksum verified against actual checkpoint bytes by the model registry.
"""
import hashlib
import json

CONTRACT = 'living-generation-v1'
MAX_HISTORY = 500


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


class FrozenDict(dict):
    """JSON-compatible immutable private generation; not a security boundary against Python code."""
    def _immutable(self, *args, **kwargs):
        raise TypeError('Serving generations are immutable; replace the prepared file to reload')
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _immutable

    def __deepcopy__(self, memo):
        return self


def freeze(value):
    if isinstance(value, dict):
        return FrozenDict({k: freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(v) for v in value)
    return value


def generation(data, meta, model_id):
    content = canonical_digest(data)
    identity = canonical_digest({'contract': CONTRACT, 'data_content': content,
                                 'model_id': model_id, 'metadata': meta,
                                 'checkpoint': meta['model_sha256'], 'history_limit': MAX_HISTORY})
    return content, identity


def request_identity(cohort, learner_index, rows, cutoff):
    # Re-hash effective history/target, rather than trusting a caller-supplied ID. This
    # also makes the audit's cloned/mutated in-memory inputs miss the old forecast cache.
    # Target outcomes are bound for receipt invalidation, NEVER passed to inference.
    return canonical_digest({'contract': CONTRACT, 'generation': cohort['generation'],
                             'learner_index': learner_index, 'cutoff': cutoff,
                             'history': rows[:cutoff],
                             'target': rows[cutoff] if cutoff < len(rows) else None})

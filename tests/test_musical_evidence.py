from axis7.musical_evidence import evidence


def group(t, values, exercise='1'):
    return {'time':t,'obs':[[0,v,1.] for v in values],'exercise':exercise}


def test_many_notes_in_one_recording_are_insufficient_for_recurring_weakness():
    result = evidence([group(0,[0]*100)], [0,1], 'singpad')['source_concepts']
    assert result[0]['status'] == 'insufficient_evidence'
    assert result[1]['status'] == 'not_evaluated'


def test_repeated_low_observations_and_coverage_are_explicit():
    rows = [group(t,[0,0,0,1],str(t)) for t in range(3)]
    result = evidence(rows,[0],'singpad')
    r = result['source_concepts'][0]
    assert r['status'] == 'recurring_low_observed_performance'
    assert r['exercise_coverage'] == 3 and r['observed_weight'] == 12
    assert r['observed_fraction'] == .25 and r['recent_fraction'] == .25
    assert result['taxonomy_mapping']['status'] == 'unvalidated'


def test_one_bad_group_after_good_history_is_not_called_recurring_low_performance():
    result = evidence([group(0,[1]*10),group(1,[1]*10),group(2,[0]*10)],[0],'singpad')
    assert result['source_concepts'][0]['status'] == 'observed_without_recurring_flag'


def test_continuous_scores_are_not_individual_note_skill_diagnoses():
    result = evidence([group(t,[.2]) for t in range(3)],[0],'yousician')
    assert 'score global' in result['scope']
    assert result['source_concepts'][0]['observed_weight'] == 3

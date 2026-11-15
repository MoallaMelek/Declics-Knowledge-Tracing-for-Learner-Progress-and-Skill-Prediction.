"""Write the numeric sections of the SYNTHETIC simulation report from the result files.

Every number in docs/PHASE11_SIMULATION_RESULTS.md comes from artifacts/simulation/<study>/:
nothing is typed by hand. The interpretation lives in docs/PHASE11_SIMULATION_REPORT.md.
Usage: python scripts/report_simulation.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from axis7 import sim_learners as sl  # noqa: E402

CFG = json.loads((ROOT / 'configs/simulation-study.json').read_text(encoding='utf-8'))
D = ROOT / 'artifacts/simulation' / CFG['study']
LABEL = {**{k: v['label'] for k, v in sl.FAMILIES_B.items()}, **{k: v['label'] for k, v in sl.FAMILIES_A.items()}}
M = [('elo', 'Elo (declic-elo-v1)'), ('gru', 'GRU DÉCLIC'), ('naive', 'Naïf')]


def read(name):
    p = D / name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


def f(v, d=4):
    return '—' if v is None else f'{v:.{d}f}'.replace('.', ',')


def pct(v):
    return '—' if v is None else f'{round(100 * v)} %'


def ci(v):
    return '—' if not v else f'[{f(v[0])} ; {f(v[1])}]'


def table(head, rows):
    out = ['| ' + ' | '.join(head) + ' |', '|' + '|'.join('---' for _ in head) + '|']
    out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return '\n'.join(out)


def final_table(res):
    m, b, own = res['common']['metrics'], res['common']['bootstrap'], res['own_coverage']
    return table(['Modèle', 'Brier', 'IC 95 % (élèves)', 'Log-loss', 'IC 95 % (élèves)', 'AUC', 'ECE', 'Élèves évalués', 'Couverture des prévisions'],
                 [[label, f(m[k]['brier']), ci(b[k]['brier']), f(m[k]['log_loss']), ci(b[k]['log_loss']), f(m[k].get('auc'), 3), f(m[k]['ece'], 3),
                   own[k]['learners'], pct(own[k]['coverage'])] for k, label in M])


def diffs(res):
    d = res['common']['bootstrap']['differences']
    names = {'elo-gru': 'Elo − GRU', 'elo-naive': 'Elo − naïf', 'gru-naive': 'GRU − naïf'}
    tt = all(k + ':to_truth' in d for k in names)
    return table(['Différence (négatif = le premier modèle a moins d’erreur)', 'Brier', 'IC 95 %', 'Log-loss', 'IC 95 %', *(['Écart à la vraie probabilité', 'IC 95 %'] if tt else [])],
                 [[n, f(d[k + ':brier']['point']), ci(d[k + ':brier']['ci95']), f(d[k + ':log_loss']['point']), ci(d[k + ':log_loss']['ci95']),
                   *([f(d[k + ':to_truth']['point']), ci(d[k + ':to_truth']['ci95'])] if tt else [])] for k, n in names.items()])


def truth(res):
    t, tr = res['truth_recovery'], res['trend']
    return table(['Mesure commune (probabilité de réussir la question)', *[l for _, l in M]], [
        ['Erreur quadratique à la vraie probabilité', *[f(t[k]['mse_to_truth']) for k, _ in M]],
        ['Corrélation avec la vraie probabilité', *[f(t[k]['corr_with_truth'], 3) for k, _ in M]],
        [f'Tendance : même sens que la vraie évolution ({tr["trajectories"]} trajectoires élève × compétence)', *[pct(tr.get(k, {}).get('same_direction')) for k, _ in M]],
        ['Tendance : corrélation avec la vraie évolution', *[f(tr.get(k, {}).get('corr_with_true_change'), 3) for k, _ in M]]]) + \
        f'\n\nBrier de la vraie probabilité cachée (le minimum atteignable en moyenne) : **{f(t["oracle"]["brier"])}**.'


def slice_table(res, name):
    sl_ = next(s for s in res['slices'] if s['slice'] == name)
    rows = []
    for r in sl_['rows']:
        best = min(r[k] for k, _ in M)
        d = r.get('elo_minus_gru', {}).get('brier')
        rows.append([LABEL.get(r['group'], r['group']), r['questions'], r['learners'], pct(r['observed']),
                     *[('**' + f(r[k]) + '**') if r[k] == best else f(r[k]) for k, _ in M],
                     f(d['point']) if d else '—', ci(d['ci95']) if d else '—', verdict(d)])
    return table([name, 'Questions', 'Élèves', 'Réussite', *[l for _, l in M], 'Elo − GRU', 'IC 95 %', 'Lecture'], rows)


def verdict(d):
    if not d:
        return 'trop peu d’élèves'
    lo, hi = d['ci95']
    return 'Elo meilleur' if hi < 0 else 'GRU meilleur' if lo > 0 else 'pas de différence nette'


def elo_better(res):
    found = []
    for sl_ in res['slices']:
        for r in sl_['rows']:
            d = r.get('elo_minus_gru', {}).get('brier')
            if d and d['ci95'][1] < 0:
                found.append([sl_['slice'], LABEL.get(r['group'], r['group']), r['questions'], r['learners'], f(r['elo']), f(r['gru']), f(r['naive']), f(d['point']), ci(d['ci95'])])
    return found


def main():
    insp, main_, rep, shift, size, fam, sens = (read(x) for x in ('inspection.json', 'results/main.json', 'results/replications.json',
                                                                   'results/shift.json', 'results/size.json', 'results/families.json', 'results/sensitivity.json'))
    out = ['# Phase 11 · Résultats chiffrés de l’étude de simulation (données SYNTHÉTIQUES)', '',
           '> Généré par `scripts/report_simulation.py` à partir de `artifacts/simulation/' + CFG['study'] + '/`. Aucun chiffre n’est saisi à la main. '
           'Les élèves sont simulés : ces résultats ne valident aucun modèle sur de vrais élèves.', '']
    if insp:
        out += ['## 1. Campagnes réellement exécutées', '',
                table(['Campagne', 'Simulateur', 'Élèves', 'Actifs ≥ 1 fois', 'Séances', 'Terminées', 'Questions', 'Justes', 'Abandons', 'Retours', 'Pauses', 'Actifs à la fin', 'Exports O08 acceptés', 'Durée (s)'],
                      [[n, c['variant'] + (f' ×{c["noise_scale"]}' if c['noise_scale'] != 1 else ''), c['n'], c['learners_with_answers'], c['counters']['sessions'],
                        c['counters']['sessions_finished'], c['questions'], pct(c['correct_rate']), c['dropouts'], c['returns'], c['breaks'], c['active_end'],
                        c['exports_accepted'], f(c['elapsed_seconds'], 0)] for n, c in insp.items()]), '']
        if 'A1' in insp:
            a1 = insp['A1']
            out += ['### Campagne principale A1 : courbes des familles (niveau caché moyen, 0 = débutant typique, 1 = expert typique)', '',
                    table(['Famille', 'Élèves', *[f'S{i+1}' for i in range(max(len(v['weekly_ability_mean']) for v in a1['families'].values()))], 'Gain moyen', 'Écart-type du gain'],
                          [[LABEL[k], v['learners'], *[f(x, 3) for x in v['weekly_ability_mean']], f(v['gain_mean'], 3), f(v['gain_sd'], 3)] for k, v in a1['families'].items()]), '',
                    f"Diversité : {a1['diversity']['distinct_weekly_curves']} courbes hebdomadaires distinctes sur {a1['diversity']['learners']} élèves ; "
                    f"gain individuel de {f(a1['diversity']['gain_min'], 3)} à {f(a1['diversity']['gain_max'], 3)} (écart-type {f(a1['diversity']['gain_sd_all'], 3)}).", '',
                    table(['Exercice', 'Questions', 'Réussite', 'Niveau moyen', 'Niveau max'],
                          [[e, v['questions'], pct(v['correct_rate']), f(v['mean_level'], 2), v['max_level']] for e, v in sorted(a1['exercises'].items(), key=lambda kv: -kv[1]['questions'])]), '']
    if main_:
        s0 = str(CFG['gru']['seeds'][0])
        t = main_['seeds'][s0]; cfg = t['gru_config']
        out += ['## 2. GRU DÉCLIC entraîné (A1)', '',
                f"EnhancedGRU, {cfg['parameters']} paramètres, mémoire {cfg['hidden']}, contexte {cfg['context']}, {cfg['K']} compétences, {len(cfg['items'])} exercices@niveau. "
                f"Élèves : {cfg['learners']['train']} entraînement / {cfg['learners']['validation']} validation / {cfg['learners']['test']} test. "
                f"{cfg['epochs_completed']} époques, meilleure : {cfg['best_epoch']}, {f(cfg['train_seconds'], 1)} s sur CPU. Empreinte `{cfg['model_sha256'][:16]}`.", '',
                '## 3. Elo vs GRU vs naïf', '', f'### 3.1 Test A1 ({t["common"]["learners"]} élèves jamais vus, {t["common"]["questions"]} questions communes, GRU graine {s0})', '',
                final_table(t), '', diffs(t), '', truth(t), '',
                f'### 3.2 Les 200 élèves de A1 en validation croisée (5 plis, {main_["crossfit"]["common"]["questions"]} questions communes)', '',
                final_table(main_['crossfit']), '', diffs(main_['crossfit']), '', truth(main_['crossfit']), '',
                '### 3.3 Graines du GRU (même partition)', '',
                table(['Graine', 'Brier Elo', 'Brier GRU', 'Brier naïf', 'Elo − GRU', 'IC 95 %'],
                      [[sd, f(r['common']['metrics']['elo']['brier']), f(r['common']['metrics']['gru']['brier']), f(r['common']['metrics']['naive']['brier']),
                        f(r['common']['bootstrap']['differences']['elo-gru:brier']['point']), ci(r['common']['bootstrap']['differences']['elo-gru:brier']['ci95'])]
                       for sd, r in main_['seeds'].items()]), '']
        if rep:
            out += ['### 3.4 Autres populations du même simulateur', '',
                    table(['Campagne', 'Élèves test', 'Questions', 'Brier Elo', 'Brier GRU', 'Brier naïf', 'Elo − GRU', 'IC 95 %'],
                          [[n, r['common']['learners'], r['common']['questions'], f(r['common']['metrics']['elo']['brier']), f(r['common']['metrics']['gru']['brier']),
                            f(r['common']['metrics']['naive']['brier']), f(r['common']['bootstrap']['differences']['elo-gru:brier']['point']),
                            ci(r['common']['bootstrap']['differences']['elo-gru:brier']['ci95'])] for n, r in rep.items()]), '']
        if sens:
            out += ['### 3.5 Sensibilité : entraînement plus long (A1, même partition, même test)', '',
                    'Le réglage O08 (12 époques) s’arrêtait parfois alors que la validation progressait encore. Même chose avec au plus 40 époques et une patience de 6 :', '',
                    table(['Graine', 'Meilleure époque (12 max)', 'Brier GRU (12 max)', 'Meilleure époque (40 max)', 'Brier GRU (40 max)', 'Brier Elo'],
                          [[sd, main_['seeds'][sd]['gru_config']['best_epoch'], f(main_['seeds'][sd]['common']['metrics']['gru']['brier']), r['best_epoch'],
                            f(r['common']['metrics']['gru']['brier']), f(r['common']['metrics']['elo']['brier'])] for sd, r in sens['seeds'].items()]), '']
        cf = main_['crossfit']
        ab = cf.get('elo_abstains')
        if ab:
            g = ab['bootstrap']['differences']['gru-naive:brier']
            out += ['### 3.6 Les questions où Elo s’abstient (moins de 5 réponses dans la compétence)', '',
                    table(['Modèle', 'Questions', 'Élèves', 'Brier', 'Log-loss', 'ECE'],
                          [[lab, ab['questions'], ab['learners'], f(ab['metrics'][k]['brier']), f(ab['metrics'][k]['log_loss']), f(ab['metrics'][k]['ece'], 3)]
                           for k, lab in (('gru', 'GRU DÉCLIC'), ('naive', 'Naïf'))]), '',
                    f"GRU − naïf : {f(g['point'])} {ci(g['ci95'])}. Elo ne prévoit pas ces questions : c’est sa règle d’abstention, pas une erreur.", '']
        eb = elo_better(cf)
        out += ['### 3.7 Où Elo fait mieux que le GRU (intervalle entièrement sous zéro)', '',
                table(['Découpage', 'Tranche', 'Questions', 'Élèves', 'Brier Elo', 'Brier GRU', 'Brier naïf', 'Elo − GRU', 'IC 95 %'], eb) if eb else 'Aucune tranche.', '']
        out += ['## 4. Par tranche (A1, validation croisée ; Brier, le plus bas en gras ; IC par tirage d’élèves)', '']
        for name in ('historique (réponses déjà données)', 'pause avant la question', 'compétence', 'famille', 'exercice'):
            out += [f'### {name[0].upper() + name[1:]}', '', slice_table(cf, name), '']
    if shift or size or fam:
        out += ['## 5. Expériences de robustesse', '']
    if size:
        out += ['### 5.1 Taille de la cohorte (L1 : test fixe de %d élèves)' % size['layout']['test'], '',
                table(['Cohorte', 'Élèves d’entraînement', 'Graine', 'Brier GRU', 'Brier Elo', 'Brier naïf', 'Elo − GRU', 'IC 95 %', 'Époques'],
                      [[c, r['train_learners'], sd, f(r['common']['metrics']['gru']['brier']), f(r['common']['metrics']['elo']['brier']), f(r['common']['metrics']['naive']['brier']),
                        f(r['common']['bootstrap']['differences']['elo-gru:brier']['point']), ci(r['common']['bootstrap']['differences']['elo-gru:brier']['ci95']), r['epochs_completed']]
                       for c, seeds in size['cohorts'].items() for sd, r in seeds.items()]), '']
    if shift:
        rows = []
        for n in ('B1', 'N1'):
            for k, lab in (('trained_on_A1', 'GRU entraîné sur A1 (transfert)'), ('trained_on_same_population', f'GRU entraîné sur {n}')):
                r = shift[n][k]
                rows.append([n, lab, r['common']['questions'], f(r['common']['metrics']['elo']['brier']), f(r['common']['metrics']['gru']['brier']), f(r['common']['metrics']['naive']['brier']),
                             f(r['common']['bootstrap']['differences']['elo-gru:brier']['point']), ci(r['common']['bootstrap']['differences']['elo-gru:brier']['ci95']),
                             f(r['truth_recovery']['gru']['mse_to_truth']), f(r['truth_recovery']['elo']['mse_to_truth'])])
        out += ['### 5.2 Autre simulateur (B1) et réponses plus bruyantes (N1)', '',
                table(['Population', 'GRU', 'Questions', 'Brier Elo', 'Brier GRU', 'Brier naïf', 'Elo − GRU', 'IC 95 %', 'GRU → vérité', 'Elo → vérité'], rows), '']
        at = shift['B1'].get('atypical_family')
        if at and at['trained_on_A1']['common']['questions']:
            out += ['### 5.3 Progression atypique (famille de B1 absente de A)', '',
                    table(['GRU', 'Élèves', 'Questions', 'Brier Elo', 'Brier GRU', 'Brier naïf', 'Tendance GRU (même sens)', 'Tendance Elo (même sens)'],
                          [[lab, r['common']['learners'], r['common']['questions'], f(r['common']['metrics']['elo']['brier']), f(r['common']['metrics']['gru']['brier']),
                            f(r['common']['metrics']['naive']['brier']), pct(tr.get('gru', {}).get('same_direction')), pct(tr.get('elo', {}).get('same_direction'))]
                           for lab, r, tr in (('entraîné sur A1', at['trained_on_A1'], at['trend_A1']), ('entraîné sur B1', at['trained_on_B1'], at['trend_B1']))]), '']
    if fam:
        out += ['### 5.4 Une famille absente de l’entraînement (L1)', '',
                table(['Famille testée', 'Élèves testés', 'Brier GRU sans la famille', 'Brier GRU avec (même taille)', 'Brier Elo', 'Brier naïf'],
                      [[LABEL[k], r['absente']['common']['learners'], f(r['absente']['common']['metrics']['gru']['brier']), f(r['presente_meme_taille']['common']['metrics']['gru']['brier']),
                        f(r['absente']['common']['metrics']['elo']['brier']), f(r['absente']['common']['metrics']['naive']['brier'])] for k, r in fam.items()]), '']
    (ROOT / 'docs/PHASE11_SIMULATION_RESULTS.md').write_text('\n'.join(out) + '\n', encoding='utf-8')
    print('docs/PHASE11_SIMULATION_RESULTS.md')


if __name__ == '__main__':
    main()

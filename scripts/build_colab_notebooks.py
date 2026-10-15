"""Build three executable Colab notebooks without a notebook-library dependency."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/MoallaMelek/Declics-Knowledge-Tracing-for-Learner-Progress-and-Skill-Prediction..git'
BRANCH = 'phase6/scientific-validation'
ARCHIVES = {'amme': '2gvty-osfstorage-archive.zip', 'singpad': 'singKT-dataset-main.zip',
            'yousician': 'yousician_ukulele.json.zip'}

MOUNT_CODE = '''if not Path('/content/drive/MyDrive').is_dir():
    try:
        drive.mount('/content/drive', timeout_ms=600000)
    except ValueError as error:
        if not str(error).startswith('mount failed'):
            raise
        print('Reprise du montage Drive après une erreur temporaire.')
        drive.mount('/content/drive', force_remount=True, timeout_ms=600000)
'''

REMAINING_CODE = '''# Reuse this GPU for the other sources: no additional Colab session required.
from axis7.cloud_training import train, atomic_json
import zipfile, json, shutil
REMAINING = {'amme': '2gvty-osfstorage-archive.zip',
             'yousician': 'yousician_ukulele.json.zip'}
for next_source, archive_name in REMAINING.items():
    local_archive = Path('/content') / archive_name
    shutil.copyfile(DATA_DIR / archive_name, local_archive)
    source_root = DRIVE_ROOT / 'phase6' / next_source / f'seed-{SEED}'
    model_folder = source_root / 'enhanced_gru'
    result = train(next_source, local_archive, model_folder, model_name='enhanced_gru',
                   epochs=EPOCHS, batch_size=BATCH_SIZE, seed=SEED)
    atomic_json(source_root / 'selection.json', {'selected': 'enhanced_gru', 'criterion': 'validation_mae'})
    export_path = source_root / f'{next_source}-benchmark-bundle.zip'
    with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in ('model.pt', 'metrics.json', 'metrics.csv', 'history.json'):
            z.write(model_folder / name, name)
    print(json.dumps({'source': next_source, 'test': result['test'],
                      'validation_gate': result['validation_gate']}, ensure_ascii=False))
    print('Export sauvegardé :', export_path)
drive.flush_and_unmount(timeout_ms=300000)
print('Les trois bases sont terminées ; les écritures Drive ont été transférées.')
'''


def cell(kind, text):
    result = {'cell_type': kind, 'metadata': {}, 'source': text.strip().splitlines(keepends=True)}
    if kind == 'code':
        result.update(execution_count=None, outputs=[])
    return result


def build(source):
    cells = [cell('markdown', f'''# DÉCLIC Phase 6 — {source.upper()}
Les anciens résultats SingPAD sont invalides : le tri de dates est corrigé et
les sorties sont séparées dans phase6. Ne pas reprendre les checkpoints Phase 5.
Entraînement PyTorch réel. Ouvrir ce notebook, choisir **Exécution → Modifier le type
d'exécution → GPU** si disponible, puis **Tout exécuter**. Le CPU fonctionne aussi.
Autoriser Google Drive quand Google le demande. Aucun abonnement payant nécessaire.

La sauvegarde est faite toutes les 25 minibatches ou deux minutes, ainsi qu'à chaque
époque. Après déconnexion, relancer les mêmes cellules : le dernier checkpoint intact
est retrouvé automatiquement. Le travail depuis la dernière sauvegarde est refait.
Les checkpoints contiennent le modèle, l'optimiseur et l'état aléatoire.

Déposer une fois `{ARCHIVES[source]}` dans `Mon Drive/DECLIC/datasets/`.
Si absent, un sélecteur d'importation est proposé. Les données ne sont pas publiées
sur GitHub. Les sorties restent dans votre Drive. Le benchmark conserve ses propres
concepts et son instrument ; il ne valide pas automatiquement les prévisions du piano
personnel de DÉCLIC. [Guide](https://github.com/MoallaMelek/Declics-Knowledge-Tracing-for-Learner-Progress-and-Skill-Prediction./blob/{BRANCH}/docs/PHASE5_COLAB.md)
'''), cell('code', f'''
from pathlib import Path
import subprocess, sys, os, json, shutil
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
SOURCE = {source!r}
EPOCHS = 12
SEED = 42
BATCH_SIZE = 16
# Changing architecture/seed uses a separate output folder. Resuming preserves the split.
MODELS = {(['dkt', 'enhanced_gru', 'item_attention'] if source == 'singpad' else ['enhanced_gru'])!r}
REPO_URL = {REPO!r}
REF = {BRANCH!r}
REPO_DIR = Path('/content/declic-axis7')
if not REPO_DIR.exists():
    subprocess.run(['git', 'clone', '--depth', '1', '--branch', REF, REPO_URL, str(REPO_DIR)], check=True)
else:
    print('Existing checkout retained for reproducible resume.')
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-e', str(REPO_DIR)], check=True)
os.chdir(REPO_DIR)
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))
import torch
print('PyTorch', torch.__version__, '| GPU:', torch.cuda.is_available())
if torch.cuda.is_available():
    print(torch.cuda.get_device_name(0))
else:
    print('CPU disponible. Le GPU gratuit est facultatif, selon disponibilité Colab.')
print('Code revision:', subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip())
'''), cell('code', f'''
from google.colab import drive, files
{MOUNT_CODE}
DRIVE_ROOT = Path('/content/drive/MyDrive/DECLIC')
DATA_DIR = DRIVE_ROOT / 'datasets'
DATA_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_NAME = {ARCHIVES[source]!r}
drive_archive = DATA_DIR / ARCHIVE_NAME
if not drive_archive.is_file():
    print('Importer uniquement', ARCHIVE_NAME, '(conservé dans Drive pour les prochains lancements).')
    uploaded = files.upload()
    if ARCHIVE_NAME not in uploaded:
        raise FileNotFoundError('Le nom du fichier doit être ' + ARCHIVE_NAME)
    shutil.copyfile(ARCHIVE_NAME, drive_archive)
    del uploaded
LOCAL_ARCHIVE = Path('/content') / ARCHIVE_NAME
shutil.copyfile(drive_archive, LOCAL_ARCHIVE)
RUN_ROOT = DRIVE_ROOT / 'phase6' / SOURCE / f'seed-{{SEED}}'
RUN_ROOT.mkdir(parents=True, exist_ok=True)
print('Données prêtes. Checkpoints et métriques :', RUN_ROOT)
'''), cell('markdown', '''## Entraîner et reprendre
Les apprenants d'entraînement, validation et test sont séparés. Chaque prévision
utilise seulement les groupes chronologiquement antérieurs. Pour SingPAD, toutes
les notes du même enregistrement et les enregistrements simultanés sont cachés
ensemble. AMME prédit le score du prochain bloc ; Yousician le prochain jour actif.
Les scores continus ne sont pas transformés artificiellement en « correct/incorrect ».
La référence est simplement la moyenne d'entraînement, sans modèle classique entraîné.
'''), cell('code', '''
from axis7.cloud_training import train, atomic_json
reports = {}
for name in MODELS:
    folder = RUN_ROOT / name
    reports[name] = train(SOURCE, LOCAL_ARCHIVE, folder, model_name=name,
                          epochs=EPOCHS, batch_size=BATCH_SIZE, seed=SEED)
    print(name, json.dumps(reports[name]['test'], ensure_ascii=False))
key = 'log_loss' if SOURCE == 'singpad' else 'mae'
# Select on validation only, never on test results.
selected = min(reports, key=lambda name: reports[name]['validation'][key])
atomic_json(RUN_ROOT / 'selection.json', {'selected': selected, 'criterion': 'validation_' + key})
print('Architecture sélectionnée sur validation :', selected)
print('Éligible au benchmark :', reports[selected]['validation_gate']['accepted'])
'''), cell('code', '''
# Small portable package: weights, exact config, actual metrics and history.
# No raw observations, prepared cache or optimizer checkpoints exported.
# Split provenance is counts/digests; learner IDs remain in private resume files.
import zipfile
EXPORT = RUN_ROOT / f'{SOURCE}-benchmark-bundle.zip'
folder = RUN_ROOT / selected
with zipfile.ZipFile(EXPORT, 'w', zipfile.ZIP_DEFLATED) as z:
    for name in ('model.pt', 'metrics.json', 'metrics.csv', 'history.json'):
        z.write(folder / name, name)
print('Export sauvegardé :', EXPORT)
print('Rapport :', folder / 'metrics.json')
# Optional download to this computer. Drive already holds the persistent copy.
# files.download(str(EXPORT))
'''), cell('markdown', '''## Retour dans DÉCLIC
Le fichier exporté peut être téléchargé puis importé avec
`python -m axis7.musical_registry import --bundle CHEMIN.zip`.
L'import vérifie le checksum, le découpage, les paramètres et le seuil de validation.
Un modèle refusé reste consultable en recherche, sans être utilisé pour des prévisions.
Les endpoints de recherche exposent uniquement le domaine et la cible réellement
évalués. Les auto-évaluations du carnet piano ne deviennent pas des labels de réussite.
''')]
    return {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {'colab': {'name': f'DECLIC_{source}.ipynb'},
            'accelerator': 'GPU', 'kernelspec': {'display_name': 'Python 3', 'name': 'python3'},
            'language_info': {'name': 'python'}}, 'cells': cells}


def build_all():
    notebook = build('singpad')
    notebook['metadata']['colab']['name'] = 'DECLIC_all.ipynb'
    notebook['cells'][0]['source'] = ('# DÉCLIC Phase 6 — les trois bases sur un seul GPU\n\n'
        'Ce notebook entraîne SingPAD, puis AMME et Yousician dans la même session.\n'
        'Les checkpoints restent séparés par base et architecture sur Drive.\n'
        'Déposer les trois archives dans `Mon Drive/DECLIC/datasets/`, puis tout exécuter.\n'
        'La reprise est automatique après une déconnexion. Aucun abonnement payant nécessaire.\n'
        'Les anciennes sorties SingPAD Phase 5 sont invalidées et ne sont pas réutilisées.\n').splitlines(keepends=True)
    notebook['cells'].insert(6, cell('markdown', '## AMME et Yousician, sur le même GPU\n'
        'Les sorties de chaque base restent séparées. Les écritures Drive sont transférées avant la fin.'))
    notebook['cells'].insert(7, cell('code', REMAINING_CODE))
    return notebook


if __name__ == '__main__':
    destination = ROOT / 'notebooks'; destination.mkdir(exist_ok=True)
    for source in [*ARCHIVES, 'all']:
        notebook = build_all() if source == 'all' else build(source)
        for i, c in enumerate(notebook['cells']):
            c['id'] = f'{source}-{i:02d}'
        (destination / f'DECLIC_{source}.ipynb').write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding='utf-8')

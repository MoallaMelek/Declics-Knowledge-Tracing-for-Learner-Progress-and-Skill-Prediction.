"""Identified, loopback-only Phase 8 supervisor; never kills an existing listener."""
import argparse
import json
import os
import socket
import signal
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from .data import ROOT
from .serving_identity import CONTRACT


def read_status(url):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            value = json.load(response)
            return value if isinstance(value, dict) else None
    except urllib.error.HTTPError as exc:
        try:
            value = json.load(exc)
            return value if isinstance(value, dict) else None
        except (ValueError, OSError): return None
    except (OSError, ValueError):
        return None


def occupied(host, port):
    with socket.socket() as probe:
        probe.settimeout(.3)
        return probe.connect_ex((host, port)) == 0


def matches_instance(report, revision, instance):
    return (report.get('identity_contract') == CONTRACT and report.get('revision') == revision
            and report.get('application') == 'declic-phase8' and report.get('instance_id') == instance)


def run(args):
    from .readiness import REVISION, BRANCH, VERSION
    if args.prepared_data:
        os.environ['DECLIC_PREPARED_DATA'] = str(args.prepared_data.resolve())
    url = f'http://{args.host}:{args.port}'
    if occupied(args.host, args.port):
        current = read_status(url+'/api/readiness')
        if (getattr(args, 'open', False) and current and current.get('application') == 'declic-phase8'
                and current.get('revision') == REVISION and current.get('identity_contract') == CONTRACT):
            # Same DÉCLIC revision already serving this port: show it rather than fail; nothing is stopped or started.
            print(f'DÉCLIC tourne déjà sur ce port (même révision). Ouvrir : {url}/', flush=True)
            import webbrowser
            webbrowser.open(url+'/')
            return 0
        print(json.dumps({'error': 'occupied_port', 'port': args.port,
                          'existing_application': current.get('application') if current else 'unknown_or_old',
                          'existing_revision': current.get('revision') if current else None,
                          'action': 'Choisir explicitement un port libre avec -Port ; aucun processus arrêté.'}, ensure_ascii=False), flush=True)
        return 2
    print(json.dumps({'repository': str(ROOT), 'revision': REVISION, 'branch': BRANCH,
                      'python': sys.executable, 'version': VERSION, 'host': args.host, 'port': args.port,
                      'prepared_data': os.environ.get('DECLIC_PREPARED_DATA', str(ROOT/'runtime/musical-demo')),
                      'state': 'starting_not_yet_ready'}, ensure_ascii=False), flush=True)
    env = os.environ.copy()
    instance = secrets.token_hex(16)  # public process identity, not an access credential
    env['DECLIC_INSTANCE_ID'] = instance
    env['PYTHONPATH'] = str(ROOT)+os.pathsep+env.get('PYTHONPATH', '')
    command = [sys.executable, '-X', 'utf8', '-B', '-m', 'uvicorn', 'axis7.server:app', '--host', args.host, '--port', str(args.port)]
    child = subprocess.Popen(command, cwd=ROOT, env=env)
    try:
        deadline = time.monotonic()+args.timeout
        while time.monotonic() < deadline and child.poll() is None:
            report = read_status(url+'/api/readiness')
            if report:
                if not matches_instance(report, REVISION, instance):
                    print('Échec : le service ne correspond pas à cette version de DÉCLIC.', flush=True)
                    return 3
                # 'url' keeps the Phase 8 journey address for existing tooling; 'home' is the Phase 9 entry point.
                print(json.dumps({'readiness': report, 'url': url+'/web/living.html', 'home': url+'/'}, ensure_ascii=False), flush=True)
                if not report.get('ready') and not args.allow_partial:
                    print('DÉCLIC non prêt : vérifiez les données/modèles indiqués. --allow-partial permet un diagnostic sans données.', flush=True)
                    return 3
                print('DÉCLIC prêt.' if report['ready'] else 'DÉCLIC partiellement disponible, démonstration non prête.', flush=True)
                print(f'Ouvrir : {url}/  (Parcours : {url}/web/living.html)', flush=True)
                if args.check: return 0
                if getattr(args, 'open', False):
                    import webbrowser
                    webbrowser.open(url+'/')
                return child.wait()
            time.sleep(.2)
        print('Échec du démarrage backend ou délai dépassé ; aucune disponibilité annoncée.', flush=True)
        return 3
    except KeyboardInterrupt:
        return 0
    finally:
        if child.poll() is None:
            child.terminate()
            try: child.wait(timeout=10)
            except subprocess.TimeoutExpired: child.kill(); child.wait()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host', choices=['127.0.0.1'], default='127.0.0.1')
    p.add_argument('--port', type=int, default=8781)
    p.add_argument('--prepared-data', type=__import__('pathlib').Path)
    p.add_argument('--timeout', type=float, default=45)
    p.add_argument('--allow-partial', action='store_true')
    p.add_argument('--check', action='store_true', help='Start, verify own readiness, then cleanly stop child')
    p.add_argument('--open', action='store_true', help='Open the home page in the default browser once ready')
    args = p.parse_args()
    def terminate(signum, frame): raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, terminate)
    if not 1 <= args.port <= 65535: p.error('Port entre 1 et 65535 requis')
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())

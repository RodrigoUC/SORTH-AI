"""Exercise two source revisions with synthetic data in isolated subprocesses.

This is storage compatibility evidence, NOT a Windows installer/binary test.
Outputs are private synthetic copies; never accepts a user's database as input.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

WORKER = r'''
import sys, json, hashlib, sqlite3, shutil
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.course import Course
from src.scheduling.classroom import Classroom
root, action = Path(sys.argv[2]), sys.argv[3]
p = root / ('rollback.db' if action == 'rollback' else 'active.db')
def summary(data):
    return {'seed': data['seed'], 'excel_path': data['excel_path'],
            'classrooms': {k: [v.capacity,v.room_type,v.description,v.campus] for k,v in data['classrooms'].items()},
            'courses': [[v.code,v.name,v.size,v.number_of_groups,v.duration_min] for v in data['courses']],
            'restrictions': {k:sorted(v) for k,v in data['restrictions'].items()},
            'assignments': data['assignments'], 'lab_overrides': sorted(data.get('lab_overrides',[]))}
if action == 'create':
    repo=SessionRepository(str(p))
    rooms={'Aula Á':Classroom('Aula Á',30,'REGULAR','Sintético','Campus Ñ')}
    courses=[Course('MAT',1,60,'REGULAR',size=24,name='Matemática')]
    repo.save_session('Café.xlsx',17,rooms,courses,{'Aula Á':{'MAT'}},{'MAT-G1':('Aula Á',0,420,480)})
    snapshot=SessionRepository._snapshot(p,root,'before-update-')
    (root/'backup-path.txt').write_text(str(snapshot))
    print(json.dumps({'schema':repo.SCHEMA_VERSION,'data':summary(repo.load_session())}))
elif action == 'upgrade':
    repo=SessionRepository(str(p)); before=summary(repo.load_session())
    data=repo.load_session()
    repo.save_session(data['excel_path'],99,data['classrooms'],data['courses'],data['restrictions'],data['assignments'])
    print(json.dumps({'schema':repo.SCHEMA_VERSION,'before':before,'after':summary(repo.load_session())}))
elif action == 'reject':
    before=p.read_bytes(); rejected=False
    try: SessionRepository(str(p)).load_session()
    except Exception: rejected=True
    assert p.read_bytes()==before, 'Old revision modified newer-schema data'
    print(json.dumps({'rejected':rejected,'unchanged':True}))
elif action == 'rollback':
    backup=Path((root/'backup-path.txt').read_text())
    shutil.copyfile(backup,p)
    repo=SessionRepository(str(p))
    print(json.dumps({'schema':repo.SCHEMA_VERSION,'data':summary(repo.load_session()),'backup_sha256':hashlib.sha256(backup.read_bytes()).hexdigest()}))
'''


def verify(previous, current, output):
    previous, current, output = map(lambda p: Path(p).resolve(), (previous, current, output))
    if output.exists():
        raise FileExistsError('Use a new output directory.')
    provenance = {}
    for label, root in [('previous', previous), ('current', current)]:
        code = root / 'src/infrastructure/session_repository.py'
        provenance[label] = {'repository_sha256': hashlib.sha256(code.read_bytes()).hexdigest()}
    if provenance['previous'] == provenance['current']:
        raise ValueError('Two distinct repository implementations are required, not same-build reinstall.')
    output.mkdir(parents=True)
    def run(root, action):
        result = subprocess.run([sys.executable, '-I', '-c', WORKER, str(root), str(output), action],
                                capture_output=True, text=True, check=True, timeout=60)
        return json.loads(result.stdout)
    old = run(previous, 'create')
    new = run(current, 'upgrade')
    assert old['schema'] < new['schema'], 'This test requires a genuine forward schema migration.'
    assert old['data'] == new['before'], 'Migration changed legacy data.'
    preserved_new = hashlib.sha256((output / 'active.db').read_bytes()).hexdigest()
    rejected = run(previous, 'reject')
    assert rejected['rejected'], 'Previous version did not reject future schema.'
    restored = run(previous, 'rollback')
    assert old['data'] == restored['data'], 'Rollback did not restore pre-upgrade contents.'
    assert restored['data']['seed'] == 17 and new['after']['seed'] == 99
    assert hashlib.sha256((output / 'active.db').read_bytes()).hexdigest() == preserved_new
    result = {'ok': True, 'scope': 'Two distinct source implementations, not packaged Windows binaries',
              'provenance': provenance, 'previous_schema': old['schema'], 'current_schema': new['schema'],
              'old_rejects_future_schema': rejected, 'restored_preupdate_contents': True,
              'post_update_changes_preserved_separately': True,
              'data_loss_boundary': 'Rollback snapshot has seed17; separately preserved current data has seed99',
              'clean_windows_no_python': 'NOT TESTED', 'installer_rollback': 'NOT TESTED'}
    (output / 'cross-version-recovery.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous-root', type=Path, required=True, help='Previous project_root')
    parser.add_argument('--current-root', type=Path, required=True, help='Current project_root')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.previous_root, args.current_root, args.output), indent=2))

"""nbnotes: the on-exit hook that was tw2nb's (1.4.x), now its own app (2026-11-05) so the phone
can keep task notes without tw2nb's archive and journal. It makes the note a bare `nb:` asks for,
and copies a linked task's status into its note, both through nb-plugins' tw.nb-plugin."""
import os
import subprocess
from pathlib import Path

HOOK = 'on-exit_nbnotes.py'
REPO = Path(__file__).resolve().parent.parent


def anns(env, uuid):
    return [a['description'] for a in env.export(uuid).get('annotations', [])]


def test_mirrors_status_into_the_tasknote(env):
    uuid = env.add_task('--', 'Mirror me')
    note = env.tw_note(uuid)
    env.task(uuid, 'done')
    env.hook(HOOK, env.export(uuid))
    assert 'tw_status: completed' in note.read_text()
    assert env.git_clean('tasknotes')


def test_skips_tasks_without_a_path_link(env):
    uuid = env.add_task('--', 'Archive link only')
    env.task(uuid, 'annotate', '--', 'nb: tasks:3')
    r = env.hook(HOOK, env.export(uuid), {'not': 'a task'})
    assert r.returncode == 0 and r.stdout == '' and r.stderr == ''


def test_without_the_plugin_changes_nothing_but_says_so(plain):
    uuid = plain.add_task('--', 'No plugin')
    plain.task(uuid, 'annotate', '--', 'nb: tasknotes:x.note.md')
    r = plain.hook(HOOK, plain.export(uuid))
    assert r.returncode == 0
    out = r.stdout + r.stderr
    assert 'nb-plugin tw is required' in out
    assert 'nb plugins install https://raw.githubusercontent.com/linuxcaffe/nb-plugins/main/tw.nb-plugin' in out
    assert out.count('nb-plugin tw') == 1


def test_without_the_plugin_is_quiet_when_nothing_needs_it(plain):
    uuid = plain.add_task('--', 'No note at all')
    r = plain.hook(HOOK, plain.export(uuid))
    assert r.returncode == 0 and 'nb-plugin' not in r.stdout + r.stderr


def test_fulfils_a_bare_request(env):
    uuid = env.add_task('--', 'Order the tiles')
    env.task(uuid, 'annotate', '--', 'nb:')
    r = env.hook(HOOK, env.export(uuid))
    assert r.returncode == 0, r.stderr
    notes = list((env.nb_dir / 'tasknotes').glob(f'*{uuid[:8]}.note.md'))
    assert len(notes) == 1
    assert anns(env, uuid) == [f'nb: tasknotes:{notes[0].name}']


def test_fulfils_a_request_for_another_notebook(env):
    env.run('nb', 'notebooks', 'add', 'acme')
    uuid = env.add_task('--', 'Call Jones')
    env.task(uuid, 'annotate', '--', 'nb: acme:')
    env.hook(HOOK, env.export(uuid))
    notes = list((env.nb_dir / 'acme').glob(f'*{uuid[:8]}.note.md'))
    assert len(notes) == 1
    assert anns(env, uuid) == [f'nb: acme:{notes[0].name}']


def test_a_request_for_a_missing_notebook_never_fails_the_command(env):
    uuid = env.add_task('--', 'Nowhere')
    env.task(uuid, 'annotate', '--', 'nb: nosuch:')
    r = env.hook(HOOK, env.export(uuid))
    assert r.returncode == 0
    assert 'nosuch' in r.stderr
    assert anns(env, uuid) == ['nb: nosuch:']


def test_needs_no_tw2nb(env):
    """The point of the split: no tw2nb.rc, no tasks notebook, no journal, and none made."""
    assert not (env.home / '.task' / 'config' / 'tw2nb.rc').exists()
    uuid = env.add_task('--', 'Phone task')
    env.task(uuid, 'annotate', '--', 'nb:')
    env.hook(HOOK, env.export(uuid))
    assert anns(env, uuid)[0].startswith('nb: tasknotes:')
    assert not (env.nb_dir / 'tasks').exists()
    assert not list((env.nb_dir / 'home').glob('*.md'))


def _install(home, action='install'):
    r = subprocess.run(['bash', str(REPO / 'nbnotes.install'), action], capture_output=True,
                       text=True, timeout=60, env={'PATH': os.environ['PATH'], 'HOME': str(home)})
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def test_install_takes_the_place_of_tw2nbs_old_on_exit(tmp_path):
    home = tmp_path / 'home'
    hooks = home / '.task' / 'hooks'
    hooks.mkdir(parents=True)
    (hooks / 'on-exit_tw2nb.py').write_text('# tw2nb 1.4\n')
    (hooks / 'on-modify_tw2nb.py').write_text('# tw2nb\n')
    out = _install(home)
    assert (hooks / 'on-exit_nbnotes.py').stat().st_mode & 0o111
    assert not (hooks / 'on-exit_tw2nb.py').exists()
    assert (hooks / 'on-modify_tw2nb.py').exists()                   # the rest of tw2nb stays
    assert 'nbnotes does its job now' in out
    manifest = (home / '.task' / 'config' / '.tw_manifest').read_text()
    assert manifest.count('nbnotes|1.0.0|') == 1
    _install(home)
    assert (home / '.task' / 'config' / '.tw_manifest').read_text().count('nbnotes|') == 1
    _install(home, 'remove')
    assert not (hooks / 'on-exit_nbnotes.py').exists()
    assert 'nbnotes|' not in (home / '.task' / 'config' / '.tw_manifest').read_text()

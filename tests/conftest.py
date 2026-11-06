"""Throwaway HOME (nb, Taskwarrior, optionally the nb-plugins tw.nb-plugin) for
driving nbnotes's hook the way Taskwarrior does: task JSON on stdin. Nothing touches the real
~/.nb or ~/.task. NB_PLUGIN may point at the plugin under test (default ~/dev/nb-plugins)."""
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PLUGIN = Path(os.environ.get('NB_PLUGIN', REPO.parent / 'nb-plugins' / 'tw.nb-plugin'))
ANSI = re.compile(r'\x1b\[[0-9;?]*[A-Za-z]|\x1b\([A-Za-z0-9]')


class Env:
    def __init__(self, root):
        self.home = root / 'home'
        self.nb_dir = self.home / '.nb'
        self.task_dir = root / 'task'
        self.env = {'PATH': os.environ['PATH'], 'HOME': str(self.home), 'NB_DIR': str(self.nb_dir),
                    'NBRC_PATH': str(self.home / '.nbrc'), 'TASKRC': str(self.home / '.taskrc'),
                    'EDITOR': 'true', 'LANG': os.environ.get('LANG', 'C.UTF-8'),
                    'NBNOTES_WAIT': '60', 'TW_TASK_DIR': str(root / 'task')}

    def run(self, *args, input='', check=True, timeout=90):
        r = subprocess.run(list(args), capture_output=True, text=True, env=self.env,
                           timeout=timeout, input=input)
        r.stdout, r.stderr = ANSI.sub('', r.stdout), ANSI.sub('', r.stderr)
        if check and r.returncode:
            raise AssertionError(f'{args} -> {r.returncode}\n{r.stdout}\n{r.stderr}')
        return r

    def task(self, *args, check=True):
        return self.run('task', 'rc.hooks=off', *args, check=check)

    def add_task(self, *words):
        out = self.task('rc.verbose=new-uuid', 'add', *words).stdout
        return re.search(r'Created task ([0-9a-f-]{36})', out).group(1)

    def export(self, uuid):
        return json.loads(self.task('rc.json.array=on', uuid, 'export').stdout)[0]

    def hook(self, name, *tasks):
        """Run the hook with these task dicts as JSON lines on stdin."""
        return self.run('python3', str(REPO / name),
                        input=''.join(json.dumps(t) + '\n' for t in tasks))

    def tw_note(self, uuid):
        out = self.run('nb', 'tw', 'note', uuid, '--porcelain').stdout
        return Path(re.search(r'^path: (.*)$', out, re.M).group(1))

    def git_clean(self, nb):
        return self.run('git', '-C', str(self.nb_dir / nb), 'status', '--porcelain').stdout == ''


def _base(tmp_path):
    e = Env(tmp_path)
    e.home.mkdir()
    e.task_dir.mkdir()
    (e.home / '.taskrc').write_text(f'data.location={e.task_dir}\nconfirmation=off\n')
    e.run('git', 'config', '--global', 'user.name', 'Pat Smith')
    e.run('git', 'config', '--global', 'user.email', 'pat@example.com')
    e.run('nb', 'notebooks', '--names')
    for nb in ('tasknotes',):
        e.run('nb', 'notebooks', 'add', nb)
    return e


@pytest.fixture
def env(tmp_path):
    e = _base(tmp_path)
    (e.nb_dir / '.plugins').mkdir(exist_ok=True)
    (e.nb_dir / '.plugins' / 'tw.nb-plugin').symlink_to(PLUGIN)
    return e


@pytest.fixture
def plain(tmp_path):
    return _base(tmp_path)

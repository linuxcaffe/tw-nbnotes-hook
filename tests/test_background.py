"""nbnotes 1.1.0: the nb work never holds up the task command (djp 2026-11-05, s5: deleting a task
with a bare `nb:` from tw-web "failed", and completing it then stalled). On the phone `nb tw note`
takes seconds; inside the hook it ran in the command's time, and tw-web gives a command 15 s.
Now the hook starts the work in a process of its own and waits for it at most NBNOTES_WAIT
seconds (3): a quick station still sees the link, and the errors, at once; a slow one gets its
command back and the note a moment later. What goes wrong after the wait goes to
~/.task/logs/nbnotes.log.

A fake nb that takes its time stands in; it records what it was asked."""
import json
import os
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TASK = {'uuid': '0badc0de-1234-4abc-8def-0123456789ab', 'description': 'Slow phone',
        'status': 'pending', 'annotations': [{'entry': '20261106T020613Z', 'description': 'nb:'}]}


def _station(tmp_path, delay, fail=False):
    home = tmp_path / 'home'
    (home / '.nb' / '.plugins').mkdir(parents=True)
    (home / '.nb' / '.plugins' / 'tw.nb-plugin').write_text('# tw\n')
    bin_ = tmp_path / 'bin'
    bin_.mkdir()
    log = tmp_path / 'nb-calls'
    (bin_ / 'nb').write_text(f'#!/bin/sh\nsleep {delay}\necho "$*" >> "{log}"\n'
                             + ('echo "no such notebook: nosuch" >&2; exit 1\n' if fail else ''))
    (bin_ / 'nb').chmod(0o755)
    task_dir = tmp_path / 'task'
    task_dir.mkdir()
    env = {'PATH': f"{bin_}:/usr/bin:/bin", 'HOME': str(home), 'TW_TASK_DIR': str(task_dir)}
    return env, log, task_dir


def _hook(env, wait=None):
    if wait is not None:
        env = dict(env, NBNOTES_WAIT=str(wait))
    t0 = time.monotonic()
    r = subprocess.run(['python3', str(REPO / 'on-exit_nbnotes.py')], input=json.dumps(TASK) + '\n',
                       capture_output=True, text=True, timeout=30, env=env)
    return r, time.monotonic() - t0


def _until(cond, secs=15):
    end = time.monotonic() + secs
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.2)
    return False


def test_a_slow_station_gets_its_command_back_and_the_note_after(tmp_path):
    env, log, _ = _station(tmp_path, delay=5)
    r, took = _hook(env, wait=1)
    assert r.returncode == 0 and took < 3, took
    assert not log.exists()                                    # not done yet...
    assert _until(log.exists)                                  # ...and done after
    assert log.read_text().split() == ['tw', 'note', TASK['uuid']]


def test_the_default_wait_is_three_seconds(tmp_path):
    env, log, _ = _station(tmp_path, delay=6)
    r, took = _hook(env)
    assert 2.5 < took < 5, took
    assert _until(log.exists)


def test_a_quick_station_still_sees_its_errors_at_once(tmp_path):
    env, log, _ = _station(tmp_path, delay=0, fail=True)
    r, took = _hook(env, wait=10)
    assert took < 5 and 'no such notebook' in r.stderr


def test_an_error_after_the_wait_goes_to_the_log(tmp_path):
    env, log, task_dir = _station(tmp_path, delay=3, fail=True)
    r, _ = _hook(env, wait=0.5)
    assert 'no such notebook' not in r.stderr
    nlog = task_dir / 'logs' / 'nbnotes.log'
    assert _until(lambda: nlog.exists() and 'no such notebook' in nlog.read_text())
    assert TASK['uuid'][:8] in nlog.read_text()

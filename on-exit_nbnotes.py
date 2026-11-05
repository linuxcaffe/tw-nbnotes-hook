#!/usr/bin/env python3
"""
on-exit_nbnotes.py - Task notes in nb: make the note an `nb:` asks for, keep its status
Version: 1.0.0

After Taskwarrior has written its changes:
- a task carrying an nb: request (a bare `nb:`, or `nb: <notebook>:`) gets its note:
  `nb tw note <uuid>` makes it and swaps the request for the link;
- a task that links a note by path (`nb: tasknotes:kitchen/x-1a2b3c4d.note.md`) has its status
  copied into that note: `nb tw status <uuid>`.
Both are nb-plugins' tw.nb-plugin; this hook only calls it. Numeric links (tw2nb's archive,
`nb: tasks:42`) and tasks with no `nb:` annotation cost nothing.

Was tw2nb's on-exit hook (tw2nb 1.4.x); its own app since 2026-11-05, so a station can keep
task notes without tw2nb's archive and journal (the phone).

on-exit, not on-modify: on-modify runs before the change is written, so the plugin's
`task export` would still see the old status.

Never blocks or fails a task command: problems go to stderr only.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

NUMERIC_LINK = re.compile(r'^nb: [\w.-]+:\d+$')
# An nb: request (tw-nb-interop M7 (b)): a bare `nb:` or `nb: <notebook>:` asks for a note.
# Same pattern as tw.nb-plugin's REQUEST.
REQUEST = re.compile(r'^nb:(?:\s+([A-Za-z0-9_.-]+):)?\s*$')

TW_NB_PLUGIN_URL = 'https://raw.githubusercontent.com/linuxcaffe/nb-plugins/main/tw.nb-plugin'


def has_request(task: dict) -> bool:
    return any(REQUEST.match(a.get('description', '')) for a in task.get('annotations', []))


def links_a_note(task: dict) -> bool:
    return any(a.get('description', '').startswith('nb: ') and
               not NUMERIC_LINK.match(a.get('description', '').strip()) and
               not REQUEST.match(a.get('description', ''))
               for a in task.get('annotations', []))


def main() -> int:
    lines = sys.stdin.read().splitlines()
    nb = shutil.which('nb')
    plugin = Path(os.environ.get('NB_DIR') or Path.home() / '.nb') / '.plugins' / 'tw.nb-plugin'
    if not nb:
        return 0        # no nb here: the notes live on another station, nothing to say
    have_plugin = plugin.exists()
    seen = set()
    for line in lines:
        try:
            task = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        uuid = task.get('uuid') if isinstance(task, dict) else None
        if not uuid or uuid in seen:
            continue
        # a request: make the note (it starts with the task's status, so no mirroring needed)
        cmd = 'note' if has_request(task) else 'status' if links_a_note(task) else None
        if not cmd:
            continue
        if not have_plugin:
            # never silently: a hook can't ask, so it names the install, once per run
            print(f'[nbnotes] nb-plugin tw is required for task notes, and is missing here. '
                  f'Install it: nb plugins install {TW_NB_PLUGIN_URL}', file=sys.stderr)
            return 0
        seen.add(uuid)
        try:
            r = subprocess.run([nb, 'tw', cmd, uuid], capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=60)
            if r.returncode != 0:
                print(f'[nbnotes] nb tw {cmd} {uuid[:8]}: {r.stderr.strip()}', file=sys.stderr)
        except Exception as e:                       # never fail the task command
            print(f'[nbnotes] nb tw {cmd} {uuid[:8]}: {e}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())

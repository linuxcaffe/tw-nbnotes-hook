# nbnotes — task notes in nb

A Taskwarrior on-exit hook that keeps a task's note in [nb](https://github.com/xwmx/nb):

- **Ask for a note:** annotate a task with a bare `nb:` (or `nb: <notebook>:`). The hook makes
  the task's note (in `tasknotes`, or the notebook you named) and swaps the request for the link,
  e.g. `nb: tasknotes:order-the-tiles-1a2b3c4d.note.md`. A notebook that doesn't exist leaves
  the request in place, and the hook says why. It works from any client (the CLI,
  tw-web, a phone) with nb on the same station, online or not.
- **Keep its status:** a task that links a note by path has its status (pending, completed, …)
  copied into the note's frontmatter whenever the task changes.

How it fits with syncing, nb-web, tw-web and a phone: [Task notes](https://github.com/linuxcaffe/tw-mobilize/blob/main/docs/task-notes.md).

The work is done by nb-plugins' `tw` plugin (`nb tw note`, `nb tw status`); this hook only calls
it. Tasks without an `nb:` annotation, and numeric links like tw2nb's `nb: tasks:42`, cost nothing.

## Install

```
tw -I nbnotes
```

With nb on the station, that also installs the nb plugin `tw` that does the work. Without nb the
hook does nothing, and the installer names the command to run once nb is there. If the plugin
goes missing later, the hook says so once, with the command. It never fails a task command; problems go to stderr.

## History

Until 2026-11-05 this was tw2nb's on-exit hook (tw2nb 1.4.x). It's its own app so a station can
keep task notes without tw2nb's archive and journal (on a phone, those would land in notebooks
that never sync). Installing nbnotes removes tw2nb 1.4's `on-exit_tw2nb.py`; tw2nb 1.5.0 no
longer ships it.

## Tests

`python3 -m pytest -q tests` (needs `task` 2.6, `nb`, and `~/dev/nb-plugins/tw.nb-plugin`, or
`NB_PLUGIN=<path>`). Everything runs in a throwaway HOME.

## License

MIT

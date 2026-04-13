---
phase: 05-add-ark-entry-e2e-arkmanager-wrapper
plan: 01
subsystem: ark-install-scaffolding
tags: [ark, arkmanager, install, templates, adapter]
requires: [phase-4-complete]
provides: [arkserver.service.template, logpose-ark.sudoers.template, _arkmanager_parse, _arkmanager_save, _install_ark]
affects: [logpose/main.py, logpose/templates/]
tech-stack:
  added: []
  patterns: [regex-line-editor, visudo-validate-before-install, idempotent-helpers]
key-files:
  created:
    - logpose/templates/arkserver.service.template
    - logpose/templates/logpose-ark.sudoers.template
  modified:
    - logpose/main.py
    - logpose/templates/CLAUDE.md
decisions:
  - "Adapter uses regex-based line editor (not ConfigParser) — main.cfg is sourced bash, not INI"
  - "_install_sudoers_fragment validates via `visudo -c -f` before atomic install (Pitfall 2 mitigation)"
  - "_arkmanager_install_validate runs arkmanager install TWICE (steamcmd self-update quirk from §4.9)"
  - "_install_ark does NOT render arkserver.service or start the server — those are Plan 05-02 / 05-04 concerns"
metrics:
  tasks_completed: 3
  tasks_total: 3
  commits: 3
  completed: "2026-04-13"
---

# Phase 5 Plan 1: ARK Install Scaffolding Summary

Adds two ARK templates + 11 underscore-prefixed install/adapter helpers to `logpose/main.py` without wiring anything into `GAMES` — Palworld render stays byte-identical.

## Commits

| Hash | Subject |
|------|---------|
| 1edb6f9 | feat(05-01): add arkserver.service + logpose-ark.sudoers templates |
| 999bdbb | feat(05-01): add _arkmanager_parse/_arkmanager_save adapter helpers |
| 7c956fe | feat(05-01): add _install_ark + sub-helpers wrapping install record §4.1-4.9 |

## What Was Built

### Templates (ARK-02, ARK-18)
- `arkserver.service.template` — static systemd unit (no placeholders) with `User=steam` and direct `ExecStart=/usr/local/bin/arkmanager start`. `Type=forking` + `RemainAfterExit=yes` to mirror arkmanager's background-exit semantics.
- `logpose-ark.sudoers.template` — single `{user}` placeholder; grants passwordless `sudo -u steam /usr/local/bin/arkmanager *`.
- `templates/CLAUDE.md` — added two inventory rows.

### Adapter (ARK-08, ARK-09, SET-02)
- `_ARKMANAGER_LINE_RE` — regex matching `key="value"` and `key=value` forms.
- `_arkmanager_parse(path)` — strips quotes, skips comments + blanks.
- `_arkmanager_save(path, settings)` — preserves comments, blank lines, unrelated keys byte-exactly; appends missing keys; preserves original quoting style of each line.
- `_ark_should_quote(value)` — mirrors Palworld `should_quote` semantics (True/False/numeric unquoted).

### Install scaffolding (ARK-11, ARK-14..ARK-18)
- `_ARK_INSTANCE_CFG`, `_ARK_GLOBAL_CFG`, `_ARK_APT_PACKAGES` (module constants).
- `_get_os_version_codename` → reads VERSION_CODENAME from /etc/os-release.
- `_enable_debian_contrib_nonfree(codename)` → sed on sources.list for main + -security + -updates; `dpkg --add-architecture i386`; apt-get update.
- `_accept_steam_eula` → 4 debconf-set-selections commands for steam/steamcmd.
- `_ensure_steam_user` → `getent passwd steam` gate + `useradd -m -s /bin/bash steam`.
- `_install_arkmanager_if_absent` → `/usr/local/bin/arkmanager` existence gate + curl-pipe netinstall.
- `_arkmanager_install_validate(branch)` → runs arkmanager install twice (first `check=False`).
- `_install_sudoers_fragment(user)` → renders template → tempfile → `sudo visudo -c -f <tmp>` → `sudo install -m 0440`.
- `_seed_ark_main_cfg(values)` → `_arkmanager_save` both cfgs + chmod 0640 + chgrp steam.
- `_install_ark(branch, main_cfg_values, invoking_user)` → composes all of §4.1-4.9.

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `pytest tests/test_palworld_golden.py -x` → 4 passed (all 3 commits) ✅
- `python -c "from logpose.main import _install_ark, ... ; print('OK')"` → OK ✅
- Inline round-trip for `_arkmanager_parse` + `_arkmanager_save` → OK (byte-exact preservation) ✅
- `test -f` for both templates → pass ✅
- `grep` for inventory rows in `templates/CLAUDE.md` → pass ✅
- New ARK helpers defined: 11 (parse, save, install_ark, _install_sudoers_fragment, _install_arkmanager_if_absent, _ensure_steam_user, _accept_steam_eula, _enable_debian_contrib_nonfree, _seed_ark_main_cfg, _arkmanager_install_validate, _get_os_version_codename) ✅

## Self-Check: PASSED

Artifacts verified:
- FOUND: logpose/templates/arkserver.service.template
- FOUND: logpose/templates/logpose-ark.sudoers.template
- FOUND: logpose/main.py contains `def _arkmanager_parse`, `def _arkmanager_save`, `def _install_ark`
- FOUND commits: 1edb6f9, 999bdbb, 7c956fe
- Byte-diff harness remained 4/4 green across all 3 commits.

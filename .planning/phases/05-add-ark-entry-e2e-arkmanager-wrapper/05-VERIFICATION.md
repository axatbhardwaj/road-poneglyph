---
status: human_needed
phase: 5
verified: 2026-04-13
score: 6/9 must-haves verified; 3 deferred to VM E2E (plans 05-04, 05-05)
re_verification:
  previous_status: none
  previous_score: n/a
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Plan 05-04 — fresh Debian 13 (trixie) VM ARK install E2E"
    expected: "`logpose ark install --map TheIsland --admin-password <pw> --start` completes; `/etc/arkmanager/instances/main.cfg` seeded with 10 keys; `/etc/sudoers.d/logpose-ark` mode 0440 root:root; `sudo -u steam arkmanager status` reports `Server running: Yes`; `/home/steam/ARK/ShooterGame/Binaries/Linux/ShooterGameServer` exists; merged `/etc/polkit-1/rules.d/40-logpose.rules` lists both palserver.service and arkserver.service; re-run is idempotent; `logpose ark stop` saves cleanly; `logpose ark edit-settings` round-trips preserving comments; RCON reachable on configured port. Record results in 05-04-E2E-RECORD.md."
    why_human: "Fresh VM provisioning is outside executor capability. ARK install pulls ~18 GB of game files, requires 16+ GB RAM, and installs/uses systemd units + sudoers fragments + steam service user — must not pollute the dev box. Install record at docs/ark-install-reference.md §4 is the reference oracle."
  - test: "Plan 05-05 — fresh Debian 12 (bookworm) VM Palworld regression + ARK compat + merged polkit E2E"
    expected: "`logpose palworld install --port 8211 --players 16 --start` on Debian 12 installs + starts with zero sudo prompts (E2E-03, POL-05 Palworld); rendered palserver.service on-VM is byte-equivalent to v0.1.19 golden (live confirmation of PAL-02/PAL-09); `logpose ark install ...` also completes on Debian 12 (validates 05-RESEARCH Assumption A3: `bookworm{suffix} main non-free-firmware` sed rewrites to working `main contrib non-free non-free-firmware`); after both installs, merged polkit rule covers both unit names (`pkcheck` allowed for both palserver.service and arkserver.service). Record results in 05-05-E2E-RECORD.md."
    why_human: "Fresh VM provisioning is outside executor capability. Debian 12's apt source structure (legacy /etc/apt/sources.list vs deb822 /etc/apt/sources.list.d/debian.sources) must be observed on a clean VM — this drives whether `_enable_debian_contrib_nonfree` needs a Debian-12-specific fallback. Cannot be determined statically."
---

# Phase 5: Add ARK Entry + E2E (arkmanager wrapper) — Verification Report

**Phase Goal:** ARK joins the registry via arkmanager wrapper. `logpose ark <verb>` dispatches to `sudo -u steam arkmanager <verb>`. Palworld native path byte-identical. E2E on fresh Debian 12 + 13.
**Verified:** 2026-04-13
**Status:** human_needed
**Re-verification:** No — initial verification
**Context:** Plans 05-01, 05-02, 05-03 are the autonomous portion and are complete on `main`. Plans 05-04 and 05-05 are `[HUMAN-NEEDED VM]` and are the blocking items for this phase's status.

## Goal Achievement

### Observable Truths (mapped to ROADMAP Success Criteria)

| # | ROADMAP Success Criterion | Status | Evidence |
|---|---|---|---|
| 1 | `logpose ark install ...` on fresh Debian 12/13 enables contrib+non-free, adds i386, pre-accepts EULA, installs apt deps (11 pkgs), creates `steam` user, installs arkmanager v1.6.68+ via netinstall.sh, runs `arkmanager install --beta=preaquatica --validate` twice, starts via `arkmanager start` | **DEFERRED_TO_VM** (code path VERIFIED; execution gated) | Static: `_install_ark` at `logpose/main.py:511` composes §4.1–4.9 in order; `_enable_debian_contrib_nonfree:382`, `_accept_steam_eula:406`, `_ensure_steam_user:421`, `_install_arkmanager_if_absent:436`, `_arkmanager_install_validate:450` (runs twice — `check=False` then default), `_install_sudoers_fragment:464`, `_seed_ark_main_cfg:495`. `_ARK_APT_PACKAGES` contains exactly the 11 packages. **Execution deferred to Plans 05-04 (Debian 13) + 05-05 (Debian 12).** |
| 2 | `logpose ark install` materializes `/etc/arkmanager/instances/main.cfg` from `GAMES["ark"]` with 10 install-flag keys; unrelated keys preserved in-place | **VERIFIED (static) / DEFERRED_TO_VM (live)** | Install closure at `main.py:848-859` constructs a dict of exactly the 10 required keys (`arkserverroot, serverMap, ark_SessionName, ark_Port, ark_QueryPort, ark_RCONEnabled="True", ark_RCONPort, ark_ServerPassword, ark_ServerAdminPassword, ark_MaxPlayers`). `_arkmanager_save:318` uses `splitlines(keepends=True)` + line-by-line regex gate to preserve comments, blank lines, and unrelated keys byte-exactly (ARK-09 invariant covered by Plan 05-01 SUMMARY round-trip assertion). |
| 3 | `logpose ark edit-settings` edits `main.cfg` via shared Rich-table editor; `SettingsAdapter` wired to arkmanager `ark_*` keys | **VERIFIED** | Shared `edit-settings` command at `main.py:1041` uses `spec.settings_adapter.parse`/`save` → `_arkmanager_parse`/`_arkmanager_save`. `logpose ark --help` lists `edit-settings`. `GAMES["ark"].settings_adapter = SettingsAdapter(parse=_arkmanager_parse, save=_arkmanager_save)` at `main.py:724`. `GameUserSettings.ini` path is NOT targeted by the adapter (arkmanager owns it — per spec). |
| 4 | `logpose ark start\|stop\|restart\|status\|saveworld\|backup\|update` delegate to `sudo -u steam arkmanager <verb>` | **VERIFIED** | Factory ARK branch at `main.py:765` defines all 7 verbs (+ `enable`, `disable`). Grep confirms `_run_command("sudo -u steam /usr/local/bin/arkmanager <verb>")` at lines 905, 910, 915, 921, 927, 932, 939–943 (update runs twice — self-update quirk). `logpose ark --help` surfaces 11 verbs (install + 7 dispatch + enable/disable + edit-settings). |
| 5 | Map validation (12-tuple), port probe (ss -tuln) before install, RCON triad alignment, `--admin-password` required (hidden prompt) or `--generate-password` via `secrets.token_urlsafe(16)` | **VERIFIED (static) / DEFERRED_TO_VM (live port probe behavior)** | `_ARK_SUPPORTED_MAPS` 12-tuple + `_validate_ark_map:564` (typer.BadParameter on unsupported). `_probe_port_collision:589` invoked at install-closure `main.py:826–831` BEFORE any apt action. RCON triad: closure hardcodes `ark_RCONEnabled="True"` alongside `ark_RCONPort` + `ark_ServerAdminPassword` at `main.py:854-857`. Admin-password precedence: explicit value → `--generate-password` (secrets.token_urlsafe(16), printed once) → hidden prompt (`main.py:834-846`). Live `ss -tuln` output parsing deferred to VM. |
| 6 | `palserver.service` output remains byte-identical to v0.1.19 under Phase 2 harness (Palworld path untouched) | **VERIFIED** | `pytest tests/ -v` → 6 passed including `test_palserver_service_byte_identical_to_v0_1_19`, `test_golden_matches_v0_1_19_tag`, `test_render_service_file_byte_identical_to_golden`, `test_polkit_rule_byte_identical_to_v0_2_0_golden`. Factory `else:` branch at `main.py:955` is a verbatim Phase-4 Palworld body (PAL-09 invariant preserved across commit boundary per Plan 05-02 atomic-commit strategy). |
| 7 | `logpose ark stop` completes clean save within arkmanager default timeout; RCON reachable on configured port | **DEFERRED_TO_VM** | Code dispatches `sudo -u steam /usr/local/bin/arkmanager stop` (arkmanager performs graceful save). Timeout/RCON behavior is arkmanager's, not logpose's — must be observed live. |
| 8 | Polkit/sudo posture: sudoers fragment `/etc/sudoers.d/logpose-ark` installed with visudo validation; `logpose ark install` drops it | **VERIFIED (static) / DEFERRED_TO_VM (live visudo run)** | `_install_sudoers_fragment:464` renders `logpose-ark.sudoers.template` → tempfile → `sudo visudo -c -f <tmppath>` → fails loudly if validation fails → atomic `sudo install -m 0440 -o root -g root <tmppath> /etc/sudoers.d/logpose-ark`. Template content verified (`{user} ALL=(steam) NOPASSWD: /usr/local/bin/arkmanager *`). |
| 9 | Auto-start at boot is opt-in: `arkserver.service` (`Type=forking`, `RemainAfterExit=yes`, `User=steam`, arkmanager ExecStart/Stop) NOT enabled by default; `--enable-autostart` opts in | **VERIFIED** | `logpose/templates/arkserver.service.template` matches spec exactly (296 bytes: `Type=forking`, `RemainAfterExit=yes`, `User=steam`, `ExecStart=/usr/local/bin/arkmanager start`, `ExecStop=/usr/local/bin/arkmanager stop`). Install closure at `main.py:871-886` renders + writes unit + runs `sudo systemctl enable arkserver` ONLY when `--enable-autostart` is passed. `--enable-autostart` flag is present in `logpose ark install --help`. |

**Score:** 6/9 truths fully VERIFIED statically; 3 truths (SC1, SC7, and the live halves of SC2/SC5/SC8) legitimately require VM execution and are covered by the pending human-needed plans 05-04 and 05-05.

### pytest Results

```
/root/personal/palworld-server-launcher/.venv/bin/pytest tests/ -v
============================= test session starts ==============================
platform linux -- Python 3.13.5, pytest-9.0.3, pluggy-1.6.0
collected 6 items

tests/test_ark_golden.py::test_arkserver_service_template_static PASSED  [ 16%]
tests/test_ark_golden.py::test_logpose_ark_sudoers_template_renders_correctly PASSED [ 33%]
tests/test_palworld_golden.py::test_palserver_service_byte_identical_to_v0_1_19 PASSED [ 50%]
tests/test_palworld_golden.py::test_golden_matches_v0_1_19_tag PASSED    [ 66%]
tests/test_palworld_golden.py::test_render_service_file_byte_identical_to_golden PASSED [ 83%]
tests/test_palworld_golden.py::test_polkit_rule_byte_identical_to_v0_2_0_golden PASSED [100%]

============================== 6 passed in 0.09s ===============================
```

**Harness stability:** 6/6 green (4 Palworld + 2 ARK). PAL-09 byte-diff invariant preserved across the 05-01/05-02/05-03 commit boundaries.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `logpose/main.py` → `GAMES["ark"]` entry | 14-field GameSpec; app_id=376030; settings_path=`/etc/arkmanager/instances/main.cfg`; service_name=`arkserver`; adapter wired to `_arkmanager_parse`/`_arkmanager_save`; install_options (port_default=7778, query_port=27015, rcon_port=27020, players=10, map_default=TheIsland, session_name=logpose-ark, branch=preaquatica, supported_maps 12-tuple) | VERIFIED | `main.py:713-743` — all 14 fields populated correctly. `post_install_hooks=[]` (ARK-12 — arkmanager owns SDK setup). `steam_sdk_paths=[]`. |
| `logpose/main.py` → factory ARK branch (`if spec.key == "ark":`) | 11 ARK verbs: install (12 flags) + start/stop/restart/status/saveworld/backup/update + enable/disable + shared edit-settings | VERIFIED | `main.py:765-953` — ARK branch. `else:` Palworld branch at `main.py:955` unchanged from Phase 4. Shared `edit-settings` at `main.py:1040-1064`. |
| `logpose/main.py` → adapter helpers | `_arkmanager_parse`, `_arkmanager_save`, `_ark_should_quote`, `_ARKMANAGER_LINE_RE` | VERIFIED | `main.py:294` (`_ark_should_quote`), `:305` (`_arkmanager_parse`), `:318` (`_arkmanager_save`). Regex at top of adapter block. |
| `logpose/main.py` → install scaffolding | `_install_ark` composes §4.1–4.9 via `_repair_package_manager`, `_enable_debian_contrib_nonfree`, `_accept_steam_eula`, 11-pkg apt install, `_ensure_steam_user`, `_install_arkmanager_if_absent`, `_seed_ark_main_cfg`, `_install_sudoers_fragment`, `_arkmanager_install_validate` (×2) | VERIFIED | All 9 sub-helpers present (lines 370, 382, 406, 421, 436, 450, 464, 495, 511). Line-by-line cross-referenceable against `docs/ark-install-reference.md` §4. |
| `logpose/main.py` → CLI-boundary validation | `_ARK_SUPPORTED_MAPS` 12-tuple; `_validate_ark_map`, `_validate_ark_session_name`, `_probe_port_collision` | VERIFIED | Constants + 3 validators present at lines 564, 573, 589. |
| `logpose/templates/arkserver.service.template` | Static (no placeholders): `Type=forking`, `RemainAfterExit=yes`, `User=steam`, `ExecStart=/usr/local/bin/arkmanager start`, `ExecStop=/usr/local/bin/arkmanager stop` | VERIFIED | 296 bytes, matches spec verbatim. |
| `logpose/templates/logpose-ark.sudoers.template` | Single `{user}` placeholder; `NOPASSWD: /usr/local/bin/arkmanager *` | VERIFIED | 57 bytes raw, 54 rendered with `user='foo'`. `{user} ALL=(steam) NOPASSWD: /usr/local/bin/arkmanager *`. |
| `logpose/templates/40-logpose.rules.template` | Merged rule driven by `GAMES.values()` — unchanged since Phase 4 | VERIFIED | Template structure unchanged; golden re-captured via `GAMES["ark"]` insertion. |
| `tests/test_ark_golden.py` | 2 byte-diff tests covering both ARK templates | VERIFIED | Both tests pass (see pytest block above). |
| `tests/golden/arkserver.service.v0_2_0` | 296 bytes, static template bytes | VERIFIED | 296 bytes. |
| `tests/golden/logpose-ark.sudoers.v0_2_0` | 54 bytes, rendered with `user='foo'` | VERIFIED | 54 bytes, content `foo ALL=(steam) NOPASSWD: /usr/local/bin/arkmanager *\n`. |
| `tests/golden/40-logpose.rules.v0_2_0` | 300 bytes with units list `["palserver.service", "arkserver.service"]` | VERIFIED | 300 bytes; grep confirms both `"palserver.service"` and `"arkserver.service"` present. |
| `logpose/templates/CLAUDE.md` | Lists `arkserver.service.template` + `logpose-ark.sudoers.template` with What/When-to-read rows | VERIFIED | Both rows present (see loaded CLAUDE.md content). |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `_install_sudoers_fragment` | `sudo visudo -c -f <tempfile>` | validate-before-install (Pitfall 2) | WIRED | `main.py:464-492` — subprocess.run with `["sudo", "visudo", "-c", "-f", tmppath]`, bails on non-zero return before calling `sudo install`. |
| `_install_ark` | `sudo -u steam /usr/local/bin/arkmanager install --beta=... --validate` ×2 | first call `check=False` (self-update quirk), second default `check=True` | WIRED | `_arkmanager_install_validate:450-462` — two `_run_command` invocations, first with `check=False`. |
| `_arkmanager_save` | preserve-order-and-comments invariant | `splitlines(keepends=True)` + regex gate | WIRED | `main.py:318-367` — line-by-line iteration, comment lines appended untouched, non-matching keys appended untouched, only matching key lines rewritten. Round-trip preservation asserted by Plan 05-01 verify block. |
| `GAMES["ark"]` | `_setup_polkit(user, GAMES.values())` | polkit rule auto-includes arkserver.service | WIRED | `_setup_polkit` call at install closure `main.py:869` after `_install_ark`. Units list in `40-logpose.rules` is driven by `GAMES.values()` iteration. |
| ARK verbs (start/stop/…) | `sudo -u steam /usr/local/bin/arkmanager <verb>` | `_run_command` per verb | WIRED | 7 dispatch lines confirmed via grep (lines 905, 910, 915, 921, 927, 932, 939). |
| `tests/test_palworld_golden.py::test_polkit_rule_…` | `tests/golden/40-logpose.rules.v0_2_0` | byte-equality check | WIRED | Test passes after 05-02 atomic golden recapture. |

### Data-Flow Trace (Level 4)

Not applicable — Phase 5 produces CLI dispatch wrappers, not data-rendering UI. Install/verb commands receive flag values from Typer and pass them into arkmanager subprocess calls. No hidden hardcoded-empty paths: `main_cfg_values` dict at `main.py:848` is built entirely from CLI flag values (no static `[]` or `{}` placeholders flowing to user-visible output).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| logpose CLI exposes both games | `.venv/bin/logpose --help` | Shows both `palworld` and `ark` sub-commands | PASS |
| ARK sub-app exposes 11 verbs | `.venv/bin/logpose ark --help` | install, start, stop, restart, status, saveworld, backup, update, enable, disable, edit-settings | PASS |
| ARK install flags (12) | `.venv/bin/logpose ark install --help` | --map, --port, --query-port, --rcon-port, --players, --session-name, --admin-password, --password, --beta, --generate-password, --enable-autostart, --start | PASS |
| Palworld sub-app unchanged | `.venv/bin/logpose palworld --help` | Shows 9 Phase-4 verbs (install, start, stop, restart, status, enable, disable, update, edit-settings) — no ARK leakage | PASS |
| Test suite green | `.venv/bin/pytest tests/ -v` | 6 passed | PASS |
| ARK adapter importable | (imported transitively via pytest) | No ImportError; `_arkmanager_parse`, `_arkmanager_save`, `_install_ark` all resolvable | PASS |

### Requirements Coverage

Requirements declared by the 3 autonomous plans (05-01, 05-02, 05-03):

| Requirement | Source Plan | Status | Evidence |
|---|---|---|---|
| ARK-01 (GAMES["ark"] exists) | 05-02 | SATISFIED | `main.py:713` |
| ARK-02 (arkserver.service template) | 05-01, 05-03 | SATISFIED (static) | Template + byte-diff test |
| ARK-03..ARK-07 (install flags, map validation, port probe, admin-password resolution) | 05-02 | SATISFIED (static) / NEEDS_VM (live port probe) | `main.py:765-900` + `_validate_ark_map`/`_probe_port_collision` |
| ARK-08, ARK-09 (adapter parse/save with in-place preservation) | 05-01 | SATISFIED | `main.py:305-367`; round-trip asserted in plan |
| ARK-10 (main.cfg seed via _arkmanager_save) | 05-01, 05-02 | SATISFIED (static) / NEEDS_VM (live path write) | `_seed_ark_main_cfg:495` |
| ARK-11 (apt deps) | 05-01 | SATISFIED (static) / NEEDS_VM (live apt install) | `_ARK_APT_PACKAGES` |
| ARK-12 (arkmanager owns SDK setup) | 05-02 | SATISFIED | `post_install_hooks=[]`, `steam_sdk_paths=[]` |
| ARK-13 (RCON triad alignment) | 05-01 | SATISFIED | `main.py:854-857` hardcodes `ark_RCONEnabled="True"` |
| ARK-14 (arkmanager netinstall idempotent) | 05-01 | SATISFIED (static) / NEEDS_VM (live netinstall) | `_install_arkmanager_if_absent:436` |
| ARK-15 (EULA debconf) | 05-01 | SATISFIED (static) / NEEDS_VM (live run) | `_accept_steam_eula:406` |
| ARK-16 (steam user idempotent) | 05-01 | SATISFIED (static) / NEEDS_VM | `_ensure_steam_user:421` |
| ARK-17 (arkmanager install ×2 quirk) | 05-01 | SATISFIED (static) / NEEDS_VM | `_arkmanager_install_validate:450` |
| ARK-18 (sudoers NOPASSWD fragment, visudo-validated) | 05-01, 05-03 | SATISFIED (static) / NEEDS_VM (live visudo) | `_install_sudoers_fragment:464` + sudoers template + byte-diff test |
| ARK-19 (verb delegation to arkmanager) | 05-02 | SATISFIED | 7 dispatch lines in factory branch |
| SET-02 (shared edit-settings via SettingsAdapter) | 05-02 | SATISFIED | `main.py:1040-1064` |
| SET-04 (install-time seed) | 05-01, 05-02 | SATISFIED | `default_settings_path=None` + `_seed_ark_main_cfg` |
| PAL-09 (byte-diff invariant preserved) | 05-02 | SATISFIED | 6/6 pytest green, including polkit golden |

Pending requirements (declared by 05-04 + 05-05, blocked by VM E2E): **POL-05 (Palworld + ARK), E2E-03 (Palworld on Debian 12), E2E-04 (ARK on Debian 12+13), PAL-01/PAL-02/PAL-06 live confirmation** — all explicitly rolled to the human-needed plans.

### Anti-Patterns Found

None. Static scan of ARK code path in `main.py` finds:
- No TODO/FIXME/PLACEHOLDER comments in the new 05-01..05-03 additions.
- No `return None`/`return []`/`return {}` stubs in verb dispatch.
- No `console.log`-only handlers.
- No hardcoded empty literals flowing to user output.
- `post_install_hooks=[]` and `steam_sdk_paths=[]` are intentionally empty (ARK-12 — arkmanager owns SDK); this is spec, not a stub.
- `ark_ServerPassword` defaulting to `""` is the documented "public server" semantics, not a stub.

### Human Verification Required

#### 1. Plan 05-04 — Debian 13 (trixie) ARK install E2E

**Test:** Provision a fresh Debian 13 trixie VM (16 GB RAM, 30 GB disk, 2 vCPU, sudo-enabled non-root user). Install `logpose-launcher` from the wheel/source. Run:
```
logpose ark install --map TheIsland --admin-password <test-pw> --start
```
Observe:
- `/etc/arkmanager/instances/main.cfg` contains all 10 seeded keys with correct values.
- `/etc/sudoers.d/logpose-ark` exists, mode 0440, owned root:root, contents match the template.
- `sudo visudo -c` exits 0 across all fragments.
- `sudo -u steam arkmanager status` shows `Server running: Yes`.
- `/home/steam/ARK/ShooterGame/Binaries/Linux/ShooterGameServer` exists (double-call install quirk worked correctly — ARK-17).
- `/etc/polkit-1/rules.d/40-logpose.rules` contains both `palserver.service` and `arkserver.service` in the units list.
- Re-running `logpose ark install ...` is idempotent (netinstall skipped, steam user skipped, apt already-installed, main.cfg re-seeded preserving unrelated keys).
- `logpose ark stop` performs a graceful save; `arkmanager status` then shows no running server.
- `logpose ark edit-settings` parses → Rich table → mutate `ark_MaxPlayers` to 20 → save → main.cfg has new value AND all unrelated keys intact.
- With `--enable-autostart`: `pkcheck --action-id=org.freedesktop.systemd1.manage-units --process $$ --detail unit arkserver.service` returns `allowed: 1`.

**Expected:** All must-have truths in plan 05-04's frontmatter pass; `05-04-E2E-RECORD.md` is written with command + output snippets.

**Why human:** Fresh VM provisioning requires cloud or hypervisor access the executor does not have. Running ARK E2E on the dev box would pollute `/home/steam`, `/etc/arkmanager`, `/etc/sudoers.d/logpose-ark`, and consume ~18 GB of disk for game files. Install record at `docs/ark-install-reference.md` is the reference oracle.

#### 2. Plan 05-05 — Debian 12 (bookworm) Palworld regression + ARK compat + merged-polkit cross-game E2E

**Test:** Provision a fresh Debian 12 bookworm VM (same resource floor as 05-04). Before any logpose run, snapshot `/etc/apt/sources.list` and `/etc/apt/sources.list.d/` — determines whether `_enable_debian_contrib_nonfree` needs a Debian-12-specific fallback. Then run:
```
logpose palworld install --port 8211 --players 16 --start
logpose ark install --map TheIsland --admin-password <test-pw> --start
```
Observe:
- Palworld install completes with zero sudo prompts (E2E-03, POL-05 Palworld).
- Rendered `/etc/systemd/system/palserver.service` on the VM is byte-equivalent to the v0.1.19 golden (closes Phase 2's deferred Criterion 4 — PAL-02 live).
- `systemctl stop palserver` → shutdown clean; savegame intact on next `systemctl start palserver`.
- `pkcheck --action-id=org.freedesktop.systemd1.manage-units --process $$ --detail unit palserver.service` → `allowed: 1`.
- ARK install completes on Debian 12 (validates 05-RESEARCH Assumption A3: `bookworm{suffix} main non-free-firmware` sed rewrite works).
- After both installs, merged polkit rule covers both units; `pkcheck` returns allowed for both `palserver.service` and `arkserver.service`.

**Expected:** All must-have truths in plan 05-05's frontmatter pass; `05-05-E2E-RECORD.md` written; Assumption A3 confirmed or a fallback-needed finding recorded.

**Why human:** Fresh VM provisioning requires cloud/hypervisor access. Debian 12's apt source structure (legacy vs deb822) cannot be determined statically and drives whether code fix is needed.

### Gaps Summary

No **gaps** in the autonomous portion of Phase 5. All 3 executed plans (05-01, 05-02, 05-03) landed exactly as written; 9 commits on `main` (1edb6f9, 999bdbb, 7c956fe, 9522b15, 8476d3a, 0d41957, 2ccecba, 65772a6, 951ca14). Phase-level summary at `22794ba`. Full test suite 6/6 green; Palworld byte-diff invariant preserved; ARK template byte-diff invariant introduced and green.

The phase status is **human_needed** (not `gaps_found` and not `passed`) because plans 05-04 and 05-05 — both explicitly scoped as `[HUMAN-NEEDED VM]` in the ROADMAP and written with `autonomous: false` + `checkpoint:human-action` gating — require fresh Debian 12 and Debian 13 VMs to exercise the install behavior end-to-end. These are not verification gaps in the autonomous work; they are the remaining, legitimately human-gated, plans of this phase. Until they run, ROADMAP Success Criteria 1 and 7 (and the live halves of SC 2, 5, 8) cannot be closed.

---

*Verified: 2026-04-13*
*Verifier: Claude (gsd-verifier)*

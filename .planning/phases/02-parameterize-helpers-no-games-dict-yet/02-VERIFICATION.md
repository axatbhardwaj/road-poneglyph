---
phase: "02-parameterize-helpers-no-games-dict-yet"
verified: 2026-04-12T00:00:00Z
status: human_needed
score: 3/4 must-haves verified (Criterion 4 requires manual VM E2E)
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: n/a
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  required: true
  items:
    - test: "Palworld E2E on fresh Debian 12 VM: `logpose install --port 8211 --players 32 --start` → server advertises → `logpose edit-settings` round-trip → `systemctl stop palserver` → saves intact → no sudo prompts"
      expected: "Observable behavior byte-identical to v0.1.19: service starts, edit-settings round-trips without corrupting the INI, stop saves cleanly, zero sudo prompts."
      why_human: "Success Criterion #4 is explicitly 'exercised manually' — requires fresh VM, real systemd/polkit, real Palworld download, real network. Out of scope for static byte-diff harness."
---

# Phase 2: Parameterize Helpers (no GAMES dict yet) — Verification Report

**Phase Goal:** Helper functions accept game-specific inputs as parameters (not module globals), and a byte-diff regression harness proves Palworld renders identically to v0.1.19 — the working oracle for every subsequent phase.

**Verified:** 2026-04-12
**Status:** human_needed (3 static criteria PASS; Criterion 4 is a documented manual E2E outside static scope)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| #   | Truth                                                                                                                                          | Status        | Evidence                                                                                                                                                                              |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `_palworld_parse(path) -> dict[str, str]` and `_palworld_save(path, values)` extracted as named functions, byte-equivalent to v0.1.19          | ✓ VERIFIED    | `logpose/main.py:200-211` (`_palworld_parse`) and `:214-237` (`_palworld_save`); regex + error string byte-verbatim per 02-REVIEW.md cross-check against v0.1.19 tag                  |
| 2   | `_create_service_file`, `_fix_steam_sdk`, install/settings helpers accept explicit paths/dicts as arguments (no module-global reads in bodies) | ✓ VERIFIED    | Grep for `STEAM_DIR\|PAL_SERVER_DIR\|PAL_SETTINGS_PATH\|DEFAULT_PAL_SETTINGS_PATH` inside helper bodies (lines 25–309): **0 hits**. All references live at module scope (19–22) or in Typer command bodies (324, 327, 333, 334, 397, 405, 408, 409, 416, 426) |
| 3   | Byte-diff test renders `palserver.service` against fixture and asserts zero-diff vs v0.1.19 golden; script exits 0                              | ✓ VERIFIED    | `.venv/bin/pytest tests/test_palworld_golden.py -x -v` → `3 passed in 0.05s`, exit 0. `.venv/bin/python tests/test_palworld_golden.py` → `OK: palserver.service matches v0.1.19 golden (template + real render path)`, exit 0. Negative-path mutation (`printf 'X' >> template`) → non-zero exit + diagnostic |
| 4   | Palworld E2E (install → start → edit-settings → stop) unchanged when exercised manually                                                        | ? NEEDS HUMAN | Static checks pass (`python -m logpose.main --help` exits 0; all 9 commands present; module imports cleanly). Manual VM E2E is explicitly out of static scope per criterion wording    |

**Score:** 3/4 static truths verified; 1 truth (#4) routed to manual verification by design.

### Required Artifacts

| Artifact                                                                   | Expected                                          | Status     | Details                                                                                                                                                     |
| -------------------------------------------------------------------------- | ------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `logpose/main.py`                                                          | Parameterized helpers; new `_palworld_parse/save` | ✓ VERIFIED | All 7 target helper signatures present (grep confirmed); `_create_service_file` deleted; module imports cleanly under `.venv`                               |
| `tests/test_palworld_golden.py`                                            | 3 tests, dual entrypoint, byte-diff oracle        | ✓ VERIFIED | 3 test functions: `test_palserver_service_byte_identical_to_v0_1_19`, `test_golden_matches_v0_1_19_tag`, `test_render_service_file_byte_identical_to_golden` |
| `tests/golden/palserver.service.v0_1_19`                                   | v0.1.19-faithful byte oracle                      | ✓ VERIFIED | 383 bytes (rendered), sha256 `b84d069a30552cff6960ace3dabc2dbab0142d2621de637d56147324ac77d02f`, ends with `et ` (no trailing newline)                      |
| `scripts/capture_golden.py`                                                | Idempotent golden capture                         | ✓ VERIFIED | Present at `scripts/capture_golden.py`; 1143 bytes; contains locked FIXTURE                                                                                  |
| `.gitattributes`                                                           | Preserves template EOF bytes                      | ✓ VERIFIED | Contains `logpose/templates/*.template -text` and `tests/golden/** -text`                                                                                   |
| `tests/__init__.py`                                                        | Package marker                                    | ✓ VERIFIED | Present, 1 byte                                                                                                                                              |

All 6 artifacts verified at Levels 1–3 (exists, substantive, wired) and Level 4 (data flowing — the harness actually reads `GOLDEN.read_bytes()` and compares to real render output).

### Key Link Verification

| From                                                          | To                                                                 | Via                                                                       | Status  | Details                                                                                     |
| ------------------------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------- |
| `tests/test_palworld_golden.py`                               | `tests/golden/palserver.service.v0_1_19`                           | `GOLDEN.read_bytes()` comparison                                          | ✓ WIRED | Lines 45, 97 — bytes loaded and asserted against render                                     |
| `tests/test_palworld_golden.py::test_render_service_file_...` | `logpose.main::_render_service_file`                               | deferred `from logpose.main import _render_service_file` inside test body | ✓ WIRED | Line 85; test passes under pytest + script mode                                             |
| `logpose/main.py::install`                                    | `_install_palworld`, `_fix_steam_sdk`, `_render_service_file`, `_write_service_file`, `_setup_polkit` | keyword/positional call with Palworld constants + literals                | ✓ WIRED | Lines 324–339; grep confirms exact call patterns from 02-04 plan                            |
| `logpose/main.py::update`                                     | `_run_steamcmd_update`                                             | `_run_steamcmd_update(PAL_SERVER_DIR, 2394010)`                           | ✓ WIRED | Line 397                                                                                    |
| `logpose/main.py::edit_settings`                              | `_palworld_parse`, `_palworld_save`, `_create_settings_from_default` | explicit PAL_SETTINGS_PATH + section-rename tuple threaded through        | ✓ WIRED | Lines 405–426; 0 stale zero-arg calls; section tuple matches v0.1.19 char-for-char          |

### Data-Flow Trace (Level 4)

| Artifact                          | Data Variable         | Source                                                                                                | Produces Real Data | Status      |
| --------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------- | ------------------ | ----------- |
| `test_render_service_file_...`    | `rendered_str`        | Real call into `logpose.main._render_service_file` with FIXTURE                                       | Yes                | ✓ FLOWING   |
| `test_palserver_service_...`      | `rendered`            | `TEMPLATE.read_bytes().decode("utf-8").format(**FIXTURE).encode("utf-8")` — reads real template bytes | Yes                | ✓ FLOWING   |
| Golden assertion                  | `expected`            | `GOLDEN.read_bytes()` — 383-byte on-disk byte oracle                                                  | Yes                | ✓ FLOWING   |

### Behavioral Spot-Checks

| Behavior                                                            | Command                                                        | Result                                                                                         | Status |
| ------------------------------------------------------------------- | -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ------ |
| Pytest harness green                                                | `.venv/bin/pytest tests/test_palworld_golden.py -x -v`         | `3 passed in 0.05s`                                                                            | ✓ PASS |
| Script-mode harness green                                           | `.venv/bin/python tests/test_palworld_golden.py; echo $?`      | `OK: palserver.service matches v0.1.19 golden (template + real render path)\nEXIT=0`           | ✓ PASS |
| Golden file is 383 bytes (rendered size per 02-01 deviation)        | `wc -c tests/golden/palserver.service.v0_1_19`                 | `383`                                                                                          | ✓ PASS |
| Negative-path oracle: single-byte mutation fires harness            | `printf 'X' >> logpose/templates/palserver.service.template && pytest -x` | `1 failed` with byte-count diagnostic; reverted cleanly                                         | ✓ PASS |
| All parameterized helpers callable + render matches golden          | `python -c "import logpose.main as m; ..."` (see below)        | `OK all callables + render == golden`                                                          | ✓ PASS |
| CLI introspects cleanly (no TypeError on module-level command lookup) | `python -m logpose.main --help`                                | Exit 0; 9 commands listed (install, start, stop, restart, status, enable, disable, update, edit-settings) | ✓ PASS |

### Requirements Coverage

All 6 Phase 2 requirement IDs declared across plans have implementation evidence:

| Requirement | Source Plans                         | Description                                                                              | Status       | Evidence                                                                                                                                                                           |
| ----------- | ------------------------------------ | ---------------------------------------------------------------------------------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ARCH-04     | 02-03, 02-04, 02-05                  | Helpers take game-specific values as args; no game-specific module-globals in helper bodies (Phase 2 partial) | ✓ SATISFIED  | Grep for `STEAM_DIR\|PAL_SERVER_DIR\|PAL_SETTINGS_PATH\|DEFAULT_PAL_SETTINGS_PATH` inside helper bodies: 0 hits. Typer commands still read them — intended (Phase 3 dissolves them). |
| PAL-03      | 02-02                                | `_palworld_parse` preserved verbatim from v0.1.19                                        | ✓ SATISFIED  | `logpose/main.py:200-211`; PAL-03 invariant comment; regex + error string byte-verbatim per 02-REVIEW.md                                                                           |
| PAL-04      | 02-02                                | `_palworld_save` with `should_quote` nested, preserved verbatim                           | ✓ SATISFIED  | `logpose/main.py:214-237`; PAL-04 invariant comment; `should_quote` nested at line 219; `console.print("Settings saved successfully.")` preserved at line 237                       |
| PAL-09      | 02-01, 02-05                         | Byte-diff harness (Palworld half; ARK half deferred to Phase 5)                           | ✓ SATISFIED  | 3 test functions green on both entrypoints; negative-path mutation confirms real oracle. ARK half explicitly deferred to Phase 5 in ROADMAP.                                        |
| SET-01      | 02-02, 02-04                         | `logpose palworld edit-settings` works (prep for Phase 2)                                 | ✓ SATISFIED (static) | `edit_settings` wired to `_palworld_parse(PAL_SETTINGS_PATH)` + `_palworld_save(PAL_SETTINGS_PATH, settings)` + `_create_settings_from_default(..., section_rename)`. Manual E2E is Criterion #4.  |
| E2E-01      | 02-01, 02-05                         | Byte-diff regression test — rendered Palworld service file matches v0.1.19                | ✓ SATISFIED  | Harness covers both template-format path AND real `_render_service_file` path; both assert against 383-byte v0.1.19-faithful golden                                                 |
| PAL-08      | 02-03, 02-04                         | `_fix_steam_sdk` Palworld-only sdk64 preserved via caller arg                             | ✓ SATISFIED  | `install()` at line 325-328 passes exactly `Path.home() / ".steam/sdk64"` + char-for-char steamclient.so source path                                                                 |
| SET-04      | 02-03, 02-04                         | `_create_settings_from_default` Palworld section-rename preserved via caller arg          | ✓ SATISFIED  | `edit_settings` at lines 407-414 passes tuple `("[/Script/Pal.PalWorldSettings]", "[/Script/Pal.PalGameWorldSettings]")` verbatim from v0.1.19                                      |

**Note on ARCH-04:** This requirement is mapped to Phase 2 AND Phase 3 in REQUIREMENTS.md. Phase 2 delivers the partial scope (helper bodies stop reading globals); Phase 3 completes it by dissolving the module-scope globals themselves into `GAMES["palworld"]`. The partial scope is fully met.

**Note on PAL-09:** Mapped to Phase 2 AND Phase 5. Phase 2 delivers the Palworld half of the byte-diff harness; ARK half lands in Phase 5. The Palworld half is fully met.

**No orphaned requirements:** All REQUIREMENTS.md entries mapping to Phase 2 (ARCH-04, PAL-03, PAL-04, PAL-09, SET-01, E2E-01) are claimed by at least one plan's frontmatter. Additional phase-scoped requirements (PAL-08, SET-04) were picked up by plans 02-03/02-04 — these are not orphaned; they're covered.

### Anti-Patterns Found

| File                                 | Line  | Pattern                                                                  | Severity | Impact                                                                                                                                                     |
| ------------------------------------ | ----- | ------------------------------------------------------------------------ | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `logpose/main.py`                    | 185   | `_run_command(f"echo '{content}' | sudo tee {service_file}")`            | ℹ️ Info   | Shell-injection posture byte-identical to v0.1.19. Phase 2's mandate is minimum-diff byte-compat; hardening is out of scope. Called out in 02-REVIEW.md. |
| `logpose/main.py`                    | 171   | `_ = service_name  # silence "unused parameter" linters`                  | ℹ️ Info   | Deliberate Phase-3 signature-symmetry affordance; documented in adjacent comment. Not dead code — reserved for GameSpec migration.                         |
| `logpose/main.py`                    | 321, 422, 429 | `sys.exit(1)` (not `typer.Exit`)                                         | ℹ️ Info   | v0.1.19-preserved behavior; `typer.Exit` migration is Phase 4 per CLI-05 and is out of Phase 2 scope.                                                        |

No blocker or warning anti-patterns. No TODO/FIXME/placeholder comments introduced. No hardcoded empty returns or stubs.

### Human Verification Required

#### 1. Palworld E2E on fresh Debian 12 VM

**Test:** On a fresh Debian 12 VM, run:
```bash
pip install -e .            # or logpose-launcher once published
logpose install --port 8211 --players 32 --start
# Wait for server to advertise; confirm no sudo prompts
logpose edit-settings       # round-trip an innocuous setting; save; reload
systemctl stop palserver    # confirm clean shutdown; save persists
```

**Expected:**
- Install completes with zero sudo prompts (polkit rule applied correctly).
- Server advertises on port 8211 with 32-player cap.
- `edit-settings` Rich-table editor works; saved INI parses back cleanly on next open (no regex drift from Phase 2 parse/save rename).
- `systemctl stop palserver` exits cleanly with saves intact.
- Observable behavior byte-identical to v0.1.19 user experience.

**Why human:** Requires fresh VM, real systemd, real polkit, real Palworld binary download, real network — out of scope for any static harness. Criterion #4 explicitly says "exercised manually". The static harness (3 green tests + negative-path proof) covers every byte-compat invariant that can be checked without a live server; the manual test confirms no observable regression introduced by parameterization.

### Gaps Summary

No gaps found for the three static success criteria. Criterion #4 is not a gap — it is a documented manual-verification item per ROADMAP wording. The code is ready for manual E2E; the byte-diff harness (Criterion #3) is the structural guarantee that the manual E2E should match v0.1.19 output byte-for-byte.

---

## Overall Assessment

**Phase 2 goal is achieved for every observable outcome that a static verifier can check:**

1. Parse/save extracted as named functions with verbatim bodies (PAL-03, PAL-04).
2. Every helper body takes game-specific inputs as arguments; zero module-global reads inside helper bodies.
3. Byte-diff regression harness is green on both entrypoints (pytest + script-mode), covers both the raw template-format path AND the real `_render_service_file` code path, and fires on a single-byte mutation — a real oracle, not a tautology.
4. Requirements ARCH-04 (partial), PAL-03, PAL-04, PAL-09 (Palworld half), SET-01 (prep), E2E-01, PAL-08, SET-04 all satisfied by evidence in `logpose/main.py` + `tests/test_palworld_golden.py`.

The remaining Criterion #4 is a manual VM E2E explicitly scoped as "exercised manually" in ROADMAP. The static foundation is solid — the byte-diff harness guarantees that any future drift in Palworld render output fires immediately, so the manual E2E is verifying the wiring (systemd + polkit + real binary), not the byte-compat invariants.

**Recommendation:** Mark Phase 2 passed pending one-time manual E2E on a fresh Debian 12 VM. The harness is ready to anchor Phase 3's `GameSpec` migration.

---

_Verified: 2026-04-12_
_Verifier: Claude (gsd-verifier)_

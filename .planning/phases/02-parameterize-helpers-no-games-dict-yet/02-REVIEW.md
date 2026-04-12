---
status: clean
phase: "02"
reviewed_at: 2026-04-12
depth: deep
files_reviewed:
  - logpose/main.py
  - tests/__init__.py
  - tests/test_palworld_golden.py
  - tests/golden/palserver.service.v0_1_19
  - scripts/capture_golden.py
  - .gitattributes
findings_count:
  blocker: 0
  high: 0
  medium: 0
  low: 0
---

# Phase 02: Code Review Report

**Reviewed:** 2026-04-12
**Depth:** deep (cross-file + byte-level v0.1.19 oracle comparison)
**Files Reviewed:** 6
**Status:** clean

## Summary

Phase 2 lands the byte-diff regression harness and the parameterization refactor cleanly. Every requested invariant was verified by source inspection against the `v0.1.19` tag:

- `_palworld_parse` and `_palworld_save` bodies are **byte-verbatim** with the v0.1.19 `_parse_settings`/`_save_settings` bodies — only the `PAL_SETTINGS_PATH` module-global read/write is swapped for the `path` parameter, and a single comment plus a one-word docstring tweak are added. Regex literals (`r"OptionSettings=\((.*)\)"`, `r'(\w+)=(".*?"|[^,]+)'`, `r"OptionSettings=\(.*?\)"`), the error string `"Could not find OptionSettings in PalWorldSettings.ini"`, the nested `should_quote` closure, the `("true", "false", "none")` tuple, the ternary f-strings, the `console.print("Settings saved successfully.")` side effect — all preserved character-for-character (PAL-03 / PAL-04 ✓).
- Python 3.8 compatibility holds: `from __future__ import annotations` is present at `logpose/main.py:5`, so PEP-585 generics (`dict[str, str]`) and `Optional[tuple[str, str]]` in annotations are deferred-evaluated and safe. No runtime-evaluated PEP-604 unions or subscripted builtins anywhere in the module.
- No helper body reads the Palworld-specific module globals. A full grep for `PAL_SERVER_DIR|PAL_SETTINGS_PATH|DEFAULT_PAL_SETTINGS_PATH|STEAM_DIR` inside helper bodies (lines 25–309) returns zero hits. All remaining references are in the Typer command functions (`install`, `update`, `edit_settings`) at lines 324, 327, 333, 334, 397, 405, 408, 409, 416, 426, exactly as the plan prescribes. Phase 3 will dissolve the module globals themselves — this phase's partial ARCH-04 scope is met (ARCH-04 ✓).
- Typer wiring is type-correct and argument-correct: `_install_palworld(PAL_SERVER_DIR, 2394010)`, `_run_steamcmd_update(PAL_SERVER_DIR, 2394010)`, `_fix_steam_sdk(Path.home() / ".steam/sdk64", STEAM_DIR / "steamapps/common/Steamworks SDK Redist/linux64/steamclient.so")`, `_render_service_file(service_name="palserver", template_name="palserver.service.template", user=Path.home().name, working_directory=PAL_SERVER_DIR, exec_start_path=PAL_SERVER_DIR / "PalServer.sh", port=port, players=players)`, `_write_service_file(Path("/etc/systemd/system/palserver.service"), service_content)`, `_setup_polkit("40-palserver.rules", "palserver.rules.template", Path.home().name)`, and `_create_settings_from_default(DEFAULT_PAL_SETTINGS_PATH, PAL_SETTINGS_PATH, ("[/Script/Pal.PalWorldSettings]", "[/Script/Pal.PalGameWorldSettings]"))`. No zero-arg stale calls. The SDK source path reproduces v0.1.19 char-for-char, including the two embedded spaces in "Steamworks SDK Redist" (PAL-08 ✓, SET-04 ✓).
- Harness integrity verified: `tests/test_palworld_golden.py` reads both template and golden as bytes (`TEMPLATE.read_bytes()`, `GOLDEN.read_bytes()`), `.gitattributes` disables text-mode transforms on `logpose/templates/*.template` and `tests/golden/**`, and the trailing `et ` (space, no newline) EOF state is preserved on both template and golden. The `sys.path.insert(0, str(ROOT))` guard at module top correctly makes the `python tests/test_palworld_golden.py` entrypoint work in script mode. Three test functions present: `test_palserver_service_byte_identical_to_v0_1_19`, `test_golden_matches_v0_1_19_tag`, `test_render_service_file_byte_identical_to_golden` (3rd exercises the real `_render_service_file` path with a deferred import — Pitfall 4 closed; PAL-09 half ✓, E2E-01 ✓).
- Shell-injection posture is **unchanged from v0.1.19** (byte-identical `_run_command(f"echo '{content}' | sudo tee {service_file}")` in `_write_service_file`). Phase 2's mandate is minimum-diff byte-compat; hardening this is out of scope and will be reconsidered in Phase 4 (CLI restructure) or later.
- Commit hygiene is textbook: 19 atomic commits between `6a57d03..HEAD`, each touching one logical concern (one plan's one task per commit, with task-number prefixes like `refactor(02-03):`, `test(02-01):`, `chore(02-01):`), summaries separated from code commits (`docs(02-01):`, `docs(02-04):` etc.), and a final merge marker per plan. No bundled concerns, no drive-by reformatting.
- No speculative abstractions introduced. The one cosmetic hedge is the `_ = service_name` lint-silencer in `_render_service_file` (line 171); the adjacent comment explicitly documents it as a deliberate Phase-3 signature-symmetry affordance, not dead code. No unused imports (verified: `subprocess`, `sys`, `Path`, `Optional`, `re`, `rich`, `typer`, `rich.console.Console` all used).

### Byte-level verification performed

- Compared `_palworld_parse` body against `git show v0.1.19:palworld_server_launcher/main.py` lines 189–201 — IDENTICAL modulo the `PAL_SETTINGS_PATH` → `path` swap and the added `# verbatim from v0.1.19 — PAL-03 invariant` comment.
- Compared `_palworld_save` body against v0.1.19 lines 202–226 — IDENTICAL modulo the `PAL_SETTINGS_PATH` → `path` swap (twice), the added PAL-04 comment, and the added `path: Path` parameter.
- Compared `_create_settings_from_default` body against v0.1.19 lines 228–251 — IDENTICAL modulo the parameterization of `default_path`/`dst_path`/`section_rename` and gating the `.replace(...)` call on `section_rename is not None`. The v0.1.19 `PAL_SETTINGS_PATH.parent.mkdir(...)` call is preserved as `dst_path.parent.mkdir(...)`; the section-rename strings (`"[/Script/Pal.PalWorldSettings]"` → `"[/Script/Pal.PalGameWorldSettings]"`) are char-identical.
- Compared `_render_service_file`+`_write_service_file` against v0.1.19 `_create_service_file` — same five placeholders, same order, same `sudo tee` + `sudo systemctl daemon-reload` sequence; `console.print("Creating Pal Server service...")` moved from old `_create_service_file` preamble to new `_write_service_file` preamble (expected split boundary).
- Template byte count: `logpose/templates/palserver.service.template` = 323 bytes, ends with `et ` (no trailing newline). Golden render: `tests/golden/palserver.service.v0_1_19` = 383 bytes, ends with `et ` (expected — template placeholders expand to longer strings when substituted). The plan's nominal 323-byte claim conflated template and render sizes; the `02-01-SUMMARY.md` already captured this as a plan deviation, fixed in implementation. The golden is faithful to a v0.1.19-tag render under the locked FIXTURE — not a phase regression.

### Test execution note

Running the harness in the review sandbox failed with `ModuleNotFoundError: No module named 'typer'` — the sandbox Python has no `typer` installed. This is an environment artefact, not a code finding. The authoritative run under the project's `.venv` (documented in `02-05-SUMMARY.md`) passes `3 passed in 0.05s` for pytest and `OK: palserver.service matches v0.1.19 golden (template + real render path)` for the script entrypoint, and the negative-path mutation fires the Plan 05 test with a clean byte-count+index diagnostic — confirming the harness is a real oracle, not a tautology (success criterion #3 ✓).

### No findings

No blocker, high, medium, or low findings. The phase cleanly meets every success criterion documented in ROADMAP phase 2 and the five plans (02-01 through 02-05). The harness is load-bearing and ready to anchor Phase 3's `GameSpec` migration.

---

_Reviewed: 2026-04-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_

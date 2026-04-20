# Phase 8: Settings Adapter + HTTPS API Client - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

`road-poneglyph satisfactory edit-settings` works via INI-based adapter for Engine.ini/Game.ini/GameUserSettings.ini; pre-shutdown save calls HTTPS API `SaveGame` before SIGINT; `road-poneglyph satisfactory save` verb available.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, research at `.planning/research/satisfactory-hosting.md`, and codebase conventions to guide decisions.

</decisions>

<code_context>
## Existing Code Insights

- INI adapter pattern: Palworld uses custom regex parser (`_palworld_parse`/`_palworld_save`). ARK uses regex line editor (`_arkmanager_parse`/`_arkmanager_save`). Satisfactory uses standard Unreal Engine INI → stdlib `configparser` is appropriate.
- HTTPS API: No RCON. REST API on port 7777 with Bearer token auth. Key endpoints: HealthCheck (no auth), PasswordLogin (returns token), SaveGame, Shutdown.
- Pre-shutdown save: ExecStop script or pre-stop hook calls SaveGame API before main process receives SIGINT.
- Token storage: `~/.config/road-poneglyph/satisfactory-api-token` with mode 0600.
- First-run quirk: Config files don't exist until first graceful stop. edit-settings must handle FileNotFoundError gracefully.

</code_context>

<specifics>
## Specific Ideas

- configparser with: `RawConfigParser(strict=False, interpolation=None, comment_prefixes=(';',))`, `cp.optionxform = str` (preserve case)
- Settings path: `{server_dir}/FactoryGame/Saved/Config/LinuxServer/GameUserSettings.ini`
- API client: minimal — just save, health check, password login. No full SDK.
- ExecStop in service template: bash one-liner calling curl to API SaveGame, then sleep 2 to let save complete
- Token flow: on first `save` or `stop`, prompt for admin password → PasswordLogin → cache token

</specifics>

<deferred>
## Deferred Ideas

- Full API SDK (LoadGame, CreateNewGame, DownloadSaveGame, etc.) → future milestone
- Custom HTTPS certs → out of scope per PROJECT.md
- Multi-instance support → out of scope

</deferred>

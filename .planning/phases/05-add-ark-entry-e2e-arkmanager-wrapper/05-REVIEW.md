---
phase: 05-add-ark-entry-e2e-arkmanager-wrapper
reviewed: 2026-04-13T00:00:00Z
depth: deep
files_reviewed: 8
files_reviewed_list:
  - logpose/main.py
  - logpose/templates/arkserver.service.template
  - logpose/templates/logpose-ark.sudoers.template
  - logpose/templates/40-logpose.rules.template
  - tests/test_ark_golden.py
  - tests/golden/arkserver.service.v0_2_0
  - tests/golden/logpose-ark.sudoers.v0_2_0
  - tests/golden/40-logpose.rules.v0_2_0
findings:
  critical: 0
  warning: 0
  info: 6
  total: 6
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-04-13
**Depth:** deep
**Files Reviewed:** 8
**Status:** issues_found (all findings Info-level; no Critical, no Warning)

## Summary

Deep review of the Phase 5 autonomous deliverables (plans 05-01, 05-02, 05-03) covering the ARK entry: arkmanager adapter, install scaffolding, `GAMES["ark"]` + factory branch, templates, and byte-diff harness. Scope: commits `1edb6f9..181e7b1` against base `3ef4f10`, filtered to source files only (planning artifacts excluded; golden fixtures reviewed but treated as locked shape oracles, not subjects).

Overall assessment: the phase code is well-structured and defensively coded in the areas that matter most. The high-risk touch points were audited carefully:

- **Shell injection surface.** `_run_command` uses `shell=True`, but every interpolated value in the new ARK paths (`_ARK_APT_PACKAGES`, service name, tempfile path from `tempfile.NamedTemporaryFile`, constants like `_ARK_INSTANCE_CFG`, the hardcoded `pkg` literal in `_accept_steam_eula`) is either a static constant or a safe Python-generated token. No CLI flag value is ever concatenated into a shell-interpreted command string.
- **sudoers fragment (`_install_sudoers_fragment`)** follows the correct pattern: render → tempfile → `sudo visudo -c -f <tmp>` check → bail on non-zero → atomic `sudo install -m 0440 -o root -g root` → cleanup in `finally`. Pitfall 2 (bad sudoers locks everyone out) is mitigated.
- **Atomic file writes via `_write_via_sudo_tee`** correctly avoid shell interpolation by piping content via `stdin`.
- **Input validation at the Typer boundary** is thorough: `_validate_ark_map` (12-tuple whitelist), `_validate_ark_session_name` (forbids the four bash-double-quote-breaking characters `"`, `$`, `` ` ``, `\`), `_probe_port_collision` (`ss -tuln` scan before apt action). `--admin-password` is prompted hidden when not supplied.
- **`_arkmanager_parse`/`_arkmanager_save`** use a line-by-line regex-gated editor and correctly preserve comments, blank lines, and unrelated keys in place (ARK-09 invariant). Round-trip harness green (6/6 including the two new ARK byte-diff tests).
- **Double-call install quirk** (`_arkmanager_install_validate`) is documented and implemented per spec: first call `check=False` (self-update exits 0 with no payload), second call default check.
- **Polkit golden recapture** byte-equals the expected merged units list (`["palserver.service", "arkserver.service"]`).
- **Palworld byte-diff invariant (PAL-09)** preserved — 4/4 Palworld tests still green on `main`.

No Critical or Warning-level findings. Six Info-level items are recorded below, mostly around edge-case robustness and documented design trade-offs. None block phase closure.

## Info

### IN-01: `_arkmanager_save` drops inline trailing comments on rewritten key lines

**File:** `logpose/main.py:331-343`
**Issue:** For a main.cfg line that carries a trailing in-line bash comment on a key we mutate (e.g., `ark_MaxPlayers=10  # raised from default`), the rewrite path at `:339-342` re-emits only `ark_MaxPlayers="10"\n`, discarding the `  # raised from default` tail. The ARK-09 invariant is preserved for comment-only lines and non-matching key lines (both hit the `out.append(line)` branch untouched); the loss is limited to in-line comments on lines where the key is present in the `settings` dict passed by the caller. In the install-time seed case (`_seed_ark_main_cfg`) the file is freshly written by arkmanager's default scaffolding, so no user in-line comments exist yet. For `edit-settings`, a user who added an inline comment to a key they later edit via the Rich-table editor will lose that comment.
**Fix:** If this becomes a user-visible pain point, capture the trailing comment from the original line and re-append it on rewrite. Sketch:
```python
# After matching m, split off any unquoted trailing "# ..." tail
rhs = line.split("=", 1)[1] if "=" in line else ""
# Detect bash-style trailing comment outside quotes — naive version:
m_comment = re.search(r'\s+(#.*)$', rhs.rstrip("\n"))
trailing_comment = f"  {m_comment.group(1)}" if m_comment else ""
out.append(f'{key}="{value}"{trailing_comment}{trailing_newline}')
```
Not urgent — arkmanager main.cfg is typically machine-managed, and the loss is confined to user-added in-line commentary on edited keys.

### IN-02: `_arkmanager_parse` absorbs trailing inline comments into the value for unquoted lines

**File:** `logpose/main.py:291, 305-315`
**Issue:** `_ARKMANAGER_LINE_RE` anchors to `\s*$`, not to an unquoted `#`. For a line like `key=value  # comment`, the value capture group becomes `value  # comment` (with whitespace absorbed as part of the lazy `.*?`). Downstream, `_arkmanager_save` would then write back `key="value  # comment"`, converting the comment into part of the quoted value — a silent semantic change for that key on round-trip. For quoted inputs (`key="value"  # comment`) the lazy `.*?"` match terminates at the closing quote, and the `#` comment tail is then matched by the trailing `\s*$`... actually the regex requires `"?\s*$`, which does not permit a `#` tail. So quoted lines with trailing comments wouldn't match at all and would be preserved verbatim (good), but unquoted lines would silently be mis-parsed.
**Fix:** Either (a) strip unquoted trailing `# ...` before regex-matching (`line.split('#', 1)[0]` on non-quoted lines), or (b) tighten the value class to exclude `#` for unquoted captures. Current arkmanager main.cfg shipped by upstream has no inline comments on key lines (only full-line `#` comments), so this is a latent issue, not an active bug.
Example defensive parse:
```python
# Drop bash-style trailing inline comments outside of quotes
stripped = re.sub(r'(?<!["\w])\s+#.*$', '', line)
m = _ARKMANAGER_LINE_RE.match(stripped)
```

### IN-03: `invoking_user = Path.home().name` is `$HOME`-dependent; prefer `pwd`/`getpass`

**File:** `logpose/main.py:860` (ARK install closure); same pattern at `:977` (Palworld — pre-existing)
**Issue:** `Path.home()` consults `$HOME` first; if a user (or an invoking systemd unit, or a misconfigured shell) has `HOME` pointing somewhere whose basename is not their POSIX login name, this propagates into:
1. The `{user}` placeholder in `/etc/sudoers.d/logpose-ark` (wrong username → fragment grants NOPASSWD to the wrong or nonexistent user, and the intended user still prompts).
2. The `{user}` placeholder in `/etc/polkit-1/rules.d/40-logpose.rules` (same class of failure for pkcheck).
3. The `User=` directive in the ARK systemd unit via `_render_service_file(user=invoking_user, ...)` — note: the rendered `arkserver.service` template itself hardcodes `User=steam` and does NOT consume this value, so that arm is safe; but the `user` kwarg is still passed.
POSIX login names cannot contain shell metacharacters, so this is not a shell-injection concern — it's a correctness/robustness concern for edge environments (containers, su-with-preserved-env, chrooted shells).
**Fix:** Derive the invoking user from the process UID, which is the ground truth:
```python
import getpass
invoking_user = getpass.getuser()
# or:
import pwd, os
invoking_user = pwd.getpwuid(os.getuid()).pw_name
```
Note: this is a pre-existing convention in the Palworld install path; Phase 5 reuses it for ARK. If the team decides to harden it, both call sites should be updated together to keep the two games symmetric.

### IN-04: `_install_ark` treats unknown `ID=` as Ubuntu-compatible

**File:** `logpose/main.py:524-533`
**Issue:** `_get_os_id()` can return `""` (when `/etc/os-release` is missing — logged via `rich.print` then swallowed). Inside `_install_ark`, the `else:` branch (`os_id != "debian"`) unconditionally runs `sudo add-apt-repository multiverse -y` (Ubuntu-specific) and `sudo dpkg --add-architecture i386`. On a non-Debian, non-Ubuntu apt-family system — or when `/etc/os-release` is unreadable — this silently falls into the Ubuntu path rather than failing fast. On Ubuntu the behavior is correct. On Debian the behavior is correct (the `if` branch runs). On anything else, the install will spend a while before failing noisily on the arkmanager netinstall step.
**Fix:** Make the unknown-OS case explicit:
```python
if os_id == "debian":
    _enable_debian_contrib_nonfree(_get_os_version_codename())
elif os_id == "ubuntu":
    _run_command("sudo add-apt-repository multiverse -y", check=False)
    _run_command("sudo dpkg --add-architecture i386")
    _run_command("sudo apt-get update")
else:
    rich.print(
        f"Unsupported OS_ID={os_id!r}; ARK install is tested on debian/ubuntu only.",
        file=sys.stderr,
    )
    raise typer.Exit(code=1)
```
Phase 5 explicitly scopes live E2E to Debian 12/13 (plans 05-04, 05-05); tightening this is optional until broader distro coverage is planned.

### IN-05: `curl | sudo bash -s steam` installs arkmanager without integrity verification

**File:** `logpose/main.py:436-447`
**Issue:** `_install_arkmanager_if_absent` downloads `netinstall.sh` from `raw.githubusercontent.com/arkmanager/ark-server-tools/master/netinstall.sh` over HTTPS and pipes it to `sudo bash -s steam`. HTTPS gives transport integrity, but a compromise of the upstream GitHub repo or CDN would deliver arbitrary root-executed code. This is the documented install path in `docs/ark-install-reference.md` §4.5 and matches what arkmanager's own project README recommends; the review raises it as an acknowledgement rather than an action item. Mitigations if ever desired: pin to a commit SHA instead of `master`, verify a published release signature, or vendor the script and run it from the package.
**Fix:** None required. If hardening is pursued, pin the script URL:
```python
_ARKMANAGER_NETINSTALL_URL = (
    "https://raw.githubusercontent.com/arkmanager/ark-server-tools/"
    "<pinned-commit-sha>/netinstall.sh"
)
# Optionally: download → sha256sum compare against a vendored digest → then bash.
```

### IN-06: sudoers `NOPASSWD` wildcard matches any arkmanager invocation

**File:** `logpose/templates/logpose-ark.sudoers.template`, `logpose/main.py:464-492`
**Issue:** The installed fragment is `{user} ALL=(steam) NOPASSWD: /usr/local/bin/arkmanager *`. Sudo's `*` glob matches any argv (it does not match newlines but does match whitespace), so the user can invoke `sudo -u steam arkmanager <anything>`. Because the invoking user already has full sudo (they invoked `logpose ark install` which ran multiple unrestricted `sudo` commands), this NOPASSWD grant does not enlarge their privilege set — it only removes the password prompt for this narrow target-user command. By design per ARK-18 and consistent with the intent of letting `logpose ark start|stop|...` run non-interactively. The finding is recorded for traceability: reviewers who skim the template in isolation should know the wildcard is intentional and privilege-neutral relative to the installing user's existing sudo rights.
**Fix:** None. If a more restrictive posture is ever desired (e.g., invoker is intended to be a lesser-privileged operator rather than the installer), enumerate the verbs:
```
{user} ALL=(steam) NOPASSWD: /usr/local/bin/arkmanager start, \
                              /usr/local/bin/arkmanager stop, \
                              /usr/local/bin/arkmanager restart, \
                              /usr/local/bin/arkmanager status, \
                              /usr/local/bin/arkmanager saveworld, \
                              /usr/local/bin/arkmanager backup, \
                              /usr/local/bin/arkmanager update --validate --beta=*, \
                              /usr/local/bin/arkmanager install --beta=* --validate
```
Then update `_install_ark` and the ARK verb dispatch accordingly. Not recommended for v1 — would rathole on argv matching (sudoers `*` vs `""` quoting, `--beta=` value wildcards, etc.).

---

_Reviewed: 2026-04-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_

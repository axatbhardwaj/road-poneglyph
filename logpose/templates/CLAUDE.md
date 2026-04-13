# templates/

Configuration templates for systemd and polkit integration.

## Files

| File                         | What                               | When to read                                                              |
| ---------------------------- | ---------------------------------- | ------------------------------------------------------------------------- |
| `palserver.service.template` | systemd unit file with placeholders | Modifying service behavior, changing restart policy, debugging startup    |
| `40-logpose.rules.template`  | Merged polkit rule template — authorizes every registered game's systemd unit | Modifying permission rules, debugging sudo-less service control          |
| `arkserver.service.template`      | Opt-in systemd wrapper running `arkmanager start`/`stop` as the `steam` user (ARK-02) | Tuning ARK systemd semantics; debugging `--enable-autostart` |
| `logpose-ark.sudoers.template`    | NOPASSWD sudoers fragment granting the installing user `sudo -u steam arkmanager *` (ARK-18) | Adjusting sudo posture, debugging `logpose ark <verb>` auth failures |

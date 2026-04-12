# templates/

Configuration templates for systemd and polkit integration.

## Files

| File                         | What                               | When to read                                                              |
| ---------------------------- | ---------------------------------- | ------------------------------------------------------------------------- |
| `palserver.service.template` | systemd unit file with placeholders | Modifying service behavior, changing restart policy, debugging startup    |
| `40-logpose.rules.template`  | Merged polkit rule template — authorizes every registered game's systemd unit | Modifying permission rules, debugging sudo-less service control          |

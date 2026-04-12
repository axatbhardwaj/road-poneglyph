# templates/

Configuration templates for systemd and polkit integration.

## Files

| File                         | What                               | When to read                                                              |
| ---------------------------- | ---------------------------------- | ------------------------------------------------------------------------- |
| `palserver.service.template` | systemd unit file with placeholders | Modifying service behavior, changing restart policy, debugging startup    |
| `palserver.rules.template`   | polkit rules for passwordless control | Modifying permission rules, debugging sudo-less service control          |

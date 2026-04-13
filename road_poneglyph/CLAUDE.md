# palworld_server_launcher/

Main Python package implementing the CLI application.

## Files

| File          | What                                        | When to read                                                                   |
| ------------- | ------------------------------------------- | ------------------------------------------------------------------------------ |
| `__init__.py` | Package marker                              | -                                                                              |
| `main.py`     | CLI commands, systemd/polkit setup, steamcmd | Implementing commands, debugging installation, modifying service configuration |

## Subdirectories

| Directory    | What                             | When to read                                                             |
| ------------ | -------------------------------- | ------------------------------------------------------------------------ |
| `templates/` | systemd service, polkit templates | Modifying service behavior, changing polkit rules, debugging permissions |

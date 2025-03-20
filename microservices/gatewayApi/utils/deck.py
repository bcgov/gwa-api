
def deck_cmd_sync_diff(deck_cli, cmd):
    if deck_cli.startswith("deck_kong2_"):
        return [ deck_cli, cmd ]
    else:
        return [ deck_cli, "gateway", cmd ]

def deck_cmd_validate(deck_cli):
    if deck_cli.startswith("deck_kong2_"):
        return [ deck_cli, "validate" ]
    else:
        return [ deck_cli, "gateway", "validate" ]

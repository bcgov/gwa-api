
def deck_cmd_sync_diff(deck_cli, cmd, select_tag, state):
    if deck_cli.startswith("deck_kong2_"):
        return [ deck_cli, cmd, "--config", "/tmp/deck.yaml", "--skip-consumers", "--select-tag", select_tag, "--state", state]
    else:
        return [ deck_cli, "gateway", cmd, "--config", "/tmp/deck.yaml", "--skip-consumers", "--select-tag", select_tag, state]

def deck_cmd_validate(deck_cli, state):
    if deck_cli.startswith("deck_kong2_"):
        return [ deck_cli, "validate", "--config", "/tmp/deck.yaml", "--state", state ]
    else:
        return [ deck_cli, "gateway", "validate", "--config", "/tmp/deck.yaml", state ]

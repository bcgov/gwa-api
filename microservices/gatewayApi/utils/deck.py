
def deck_cmd_sync_diff(deck_cli, cmd, select_tag, state, kong_addr = None):
    if deck_cli == "deck" or deck_cli.startswith("deck_kong3_"):
        args = [ deck_cli, "gateway", cmd, "--config", "/tmp/deck.yaml", "--skip-consumers", "--select-tag", select_tag]
        if kong_addr:
            args.extend(["--kong-addr", kong_addr])
        args.append(state)
        return args
    else:
        return [ deck_cli, cmd, "--config", "/tmp/deck.yaml", "--skip-consumers", "--select-tag", select_tag, "--state", state]

def deck_cmd_validate(deck_cli, state, kong_addr = None):
    if deck_cli == "deck" or deck_cli.startswith("deck_kong3_"):
        args = [ deck_cli, "gateway", "validate", "--config", "/tmp/deck.yaml" ]
        if kong_addr:
            args.extend(["--kong-addr", kong_addr])
        args.append(state)
        return args
    else:
        return [ deck_cli, "validate", "--config", "/tmp/deck.yaml", "--state", state ]

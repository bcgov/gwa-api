import config
import logging
from flask import current_app as app

conf = config.Config().data

# Some plugins will need to be automatically transformed, such as the
# rate-limiting plugin
def plugins_transformations (namespace, yaml):
    traverse_plugins (yaml)

def rate_limiting (plugin):
    log = app.logger
    override_config = conf['plugins']['rate_limiting']

    if 'config' not in plugin:
        plugin['config'] = {}

    plugin_config = plugin['config']

    policy = "redis"
    if 'policy' in plugin_config and plugin_config['policy'] == 'local':
        policy = 'local'
    else:
        for k, v in override_config.items():
            plugin_config[k] = v
    plugin_config['policy'] = policy
    
    # Add null values to the following if they are not specified
    for nval in ['second', 'minute', 'hour', 'day', 'month', 'year', 'header_name']:
        if nval not in plugin_config:
            plugin_config[nval] = None

    # Add these defaults if not defined
    defaults = {
        "enabled": True,
        "protocols": [
            "http",
            "https"
        ]
    }
    for k, v in defaults.items():
        if k not in plugin:
            plugin[k] = v

def traverse_plugins (yaml):
    traversables = ['services', 'routes', 'plugins', 'upstreams', 'consumers', 'certificates']
    for k in yaml:
        if k in traversables:
            for item in yaml[k]:
                if k == 'plugins':
                    if item['name'] == 'rate-limiting':
                        rate_limiting(item)
                traverse_plugins (item)


import config
import logging
from flask import current_app as app

conf = config.Config().data

# Some plugins will need to be automatically transformed, such as the
# rate-limiting plugin
def plugins_transformations (namespace, yaml):
    traverse_plugins (yaml)

def proxy_cache (plugin, plugin_configs=None):
    override_config = conf['plugins']['proxy_cache']

    if 'config' in plugin:
        plugin_config = plugin['config']
    else:
        plugin['config'] = {}
        plugin_config = plugin['config']

    for k, v in override_config.items():
        plugin_config[k] = v

def upstream_jwt (plugin, plugin_configs=None):
    override_config = conf['plugins']['upstream_jwt']

    if 'config' in plugin:
        plugin_config = plugin['config']
    else:
        plugin['config'] = {}
        plugin_config = plugin['config']

    for k, v in override_config.items():
        plugin_config[k] = v


def rate_limiting (plugin, plugin_configs=None):
    override_config = conf['plugins']['rate_limiting']

    if '_config' in plugin:
        if not plugin_configs == None:
            if plugin['_config'] not in plugin_configs:
                plugin_configs[plugin['_config']] = {}
            plugin_config = plugin_configs[plugin['_config']]
        else:
            plugin_configs = {plugin['_config']: {}}
            plugin_config = plugin_configs[plugin['_config']]

    elif 'config' in plugin:
        plugin_config = plugin['config']
    else:
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

def traverse_plugins (yaml, plugin_configs = None):
    if plugin_configs == None:
        if '_plugin_configs' in yaml:
            plugin_configs = yaml['_plugin_configs']
    traversables = ['services', 'routes', 'plugins', 'upstreams', 'consumers', 'certificates']
    for k in yaml:
        if k in traversables:
            for item in yaml[k]:
                if k == 'plugins':
                    if item['name'] == 'rate-limiting':
                        rate_limiting(item, plugin_configs)
                    elif item['name'] == 'proxy-cache':
                        proxy_cache(item, plugin_configs)
                    elif item['name'] == 'kong-upstream-jwt':
                        upstream_jwt(item, plugin_configs)
                traverse_plugins (item, plugin_configs)
    
def add_version_if_missing(yaml):
    for k in yaml:
        if k not in ["_format_version"] or yaml["_format_version"] != 3.0:
            yaml["_format_version"] = 3.0

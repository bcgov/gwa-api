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

    for k, v in override_config.items():
        log.debug("[%s] Override %s" % (plugin['name'], k))
        plugin_config[k] = v

    # Add null values to the following if they are not specified
    for nval in ['second', 'minute', 'hour', 'day', 'month', 'year', 'header_name']:
        if nval not in plugin_config:
            plugin_config[nval] = None

def traverse_plugins (yaml):
    traversables = ['services', 'routes', 'plugins', 'upstreams', 'consumers', 'certificates']
    for k in yaml:
        if k in traversables:
            for item in yaml[k]:
                if k == 'plugins':
                    if item['name'] == 'rate-limiting':
                        rate_limiting(item)
                traverse_plugins (item)
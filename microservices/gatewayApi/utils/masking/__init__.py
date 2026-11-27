"""Mask secrets in Kong gateway configuration and deck output.

What counts as a secret is data in rules.json, shared with the Portal Kong
feeder. mask_plugin walks a plugin config. mask_document walks a whole gateway
document. mask() scrubs deck stdout and then the platform rate-limiting Redis
password and host.
"""

import json
import re
from pathlib import Path

import config

conf = config.Config().data

with Path(__file__).with_name("rules.json").open(encoding="utf-8") as rules_file:
    rules = json.load(rules_file)

MASK = rules["mask"]

vault_reference = re.compile(rules["vaultReference"], re.ASCII)
secret_field_patterns = [
    re.compile(pattern, re.ASCII) for pattern in rules["secretFields"]["patterns"]
]


def _compile_text_rule(rule):
    flags = re.ASCII
    if rule.get("ignoreCase"):
        flags |= re.IGNORECASE
    compiled = dict(rule)
    compiled["regex"] = re.compile(rule["pattern"], flags)
    return compiled


text_rules = [_compile_text_rule(rule) for rule in rules["textRules"]]


def is_secret_field(key, parent_key):
    name = key.lower()
    by_parent = rules["secretFields"]["byParent"].get(parent_key) or []
    return (
        name in by_parent
        or name in rules["secretFields"]["names"]
        or any(pattern.search(name) for pattern in secret_field_patterns)
    )


def is_secret_name(name):
    compact = re.sub(r"[-_.\s]", "", name.lower(), flags=re.ASCII)
    secret_names = rules["secretNames"]
    return (
        compact in secret_names["names"]
        or any(part in compact for part in secret_names["contains"])
        or any(compact.startswith(prefix) for prefix in secret_names["prefixes"])
        or any(compact.endswith(suffix) for suffix in secret_names["suffixes"])
    )


def is_vault_reference(value):
    return isinstance(value, str) and vault_reference.search(value.strip()) is not None


def mask_if_secret(name, value):
    if is_secret_name(name) and value != "" and not is_vault_reference(value):
        return MASK
    return value


def apply_text_rule(text, rule):
    def replace(match):
        if rule["mask"] == "match":
            return MASK
        parts = ["" if part is None else part for part in match.groups()]
        group_index = rule["group"] - 1
        if rule["mask"] == "group":
            parts[group_index] = MASK
        else:
            parts[group_index] = mask_if_secret(
                parts[rule["nameGroup"] - 1], parts[group_index]
            )
        return "".join(parts)

    return rule["regex"].sub(replace, text)


def scrub_text(text):
    for rule in text_rules:
        text = apply_text_rule(text, rule)
    return text


def mask_name_value_entry(entry):
    separator = entry.find(":")
    if separator <= 0:
        return entry
    name = entry[:separator]
    value = entry[separator + 1 :]
    if mask_if_secret(name.strip(), value.strip()) == MASK:
        return "%s:%s" % (name, MASK)
    return entry


def is_maskable(value):
    if value is None or isinstance(value, (bool, int, float)):
        return False
    return not is_vault_reference(value)


def is_plain_object(value):
    return isinstance(value, dict)


def mask_config(node, path=None):
    """Walk a config tree. path is the keys from the root down to node."""
    if path is None:
        path = ["config"]
    parent_key = path[-1]
    if isinstance(node, list):
        is_name_value_list = parent_key in rules["nameValueLists"]["fields"] and not any(
            key in path for key in rules["nameValueLists"]["except"]
        )
        for index, element in enumerate(node):
            if isinstance(element, str):
                entry = mask_name_value_entry(element) if is_name_value_list else element
                node[index] = scrub_text(entry)
            else:
                mask_config(element, path)
    elif is_plain_object(node):
        for key in list(node.keys()):
            value = node[key]
            if is_secret_field(key, parent_key) and is_maskable(value):
                node[key] = MASK
            elif key in rules["headerMaps"] and is_plain_object(value):
                for name in list(value.keys()):
                    if is_secret_name(name) and is_maskable(value[name]):
                        value[name] = MASK
                mask_config(value, path + [key])
            elif isinstance(value, str):
                node[key] = scrub_text(value)
            else:
                mask_config(value, path + [key])
    return node


def mask_plugin(plugin):
    """Mask plugin.config in place and return the plugin."""
    if is_plain_object(plugin) and is_plain_object(plugin.get("config")):
        mask_config(plugin["config"])
    return plugin


def mask_document(document):
    """Mask a gateway document in place, starting at the document root."""
    return mask_config(document, ["document"])


def mask(payload):
    """Scrub deck stdout, then the platform Redis password and host."""
    returned = scrub_text(payload)
    redis = conf["plugins"]["rate_limiting"]
    for val in (redis["redis_password"], redis["redis_host"]):
        if isinstance(val, str) and val != "":
            returned = returned.replace(val, MASK)
    return returned

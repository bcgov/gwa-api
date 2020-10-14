import os
import shutil
from subprocess import Popen, PIPE, STDOUT
import uuid
import logging
import json
import yaml
from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app
from io import TextIOWrapper

from v1.auth.auth import admin_jwt, enforce_authorization

gw = Blueprint('gwa', 'gateway')

@gw.route('',
           methods=['PUT'], strict_slashes=False)
@admin_jwt(None)
def write_config(namespace: str) -> object:
    """
    (Over)write
    :return: JSON of success message or error message
    """
    log = app.logger
    enforce_authorization(namespace)

    selectTag = outFolder = namespace

    log.debug(g.principal)

    if 'configFile' in request.files:
        log.debug(request.files['configFile'])
        dfile = request.files['configFile']

        tempFolder = "%s/%s/%s" % ('/tmp', uuid.uuid4(), outFolder)
        os.makedirs (tempFolder, exist_ok=False)

        dfile.save("%s/%s" % (tempFolder, 'config.yaml'))
        
        log.debug("Saved to %s" % tempFolder)

        with open("%s/%s" % (tempFolder, 'config.yaml')) as file:
            gw_config = yaml.load(file, Loader=yaml.FullLoader)

        # Validation #1
        # Validate that the every object is tagged with the namespace
        try:
            validate_tags (gw_config, "ns.%s" % namespace)
        except Exception as ex:
            abort(make_response(jsonify(error="Validation Errors - %s" % ex), 400))

        # Validation #3
        # Validate that certain plugins are configured (such as the gwa_gov_endpoint) at the right level

        # Enrichment #1
        # Enrich the rate-limiting plugin with the appropriate Redis details

        # Call the 'deck' command
        cmd = "sync"
        print(request.values)
        if request.values['dryRun'] == 'true':
            cmd = "diff"

        log.info("%s for %s" % (cmd, namespace))
        args = [
            "deck", cmd, "--config", "/tmp/deck.yaml", "--skip-consumers", "--select-tag", "ns.%s" % selectTag, "--state", tempFolder
        ]
        deck_run = Popen(args, stdout=PIPE, stderr=STDOUT)
        out, err = deck_run.communicate()
        if deck_run.returncode != 0:
            cleanup (tempFolder)
            log.warn("%s - %s" % (team, out.decode('utf-8')))
            abort(make_response(jsonify(error="Sync Failed.", results=out.decode('utf-8')), 400))

        cleanup (tempFolder)

        log.debug("The exit code was: %d" % deck_run.returncode)

        message = "Sync successful."
        if cmd == 'diff':
            message = "Dry-run.  No changes applied."

        return make_response(jsonify(message=message, results=out.decode('utf-8')))
    else:
        log.error("Missing input")
        log.error(request.get_data())
        log.error(request.form)
        log.error(request.headers)
        abort(make_response(jsonify(error="Missing input"), 400))

def cleanup (dir_path):
    log = app.logger
    try:
        shutil.rmtree(dir_path)
        log.debug("Deleted folder %s" % dir_path)
    except OSError as e:
        log.error("Error: %s : %s" % (dir_path, e.strerror))

def validate_tags (yaml, required_tag):
    # throw an exception if there are invalid tags
    errors = []
    traverse ("", errors, yaml, required_tag)
    if len(errors) != 0:
        raise Exception(','.join(errors))

def traverse (source, errors, yaml, required_tag):
    traversables = ['services', 'routes', 'plugins', 'upstreams', 'consumers', 'certificates']
    for k in yaml:
        if k in traversables:
            for item in yaml[k]:
                if 'tags' in item:
                    if required_tag not in item['tags']:
                        errors.append("%s.%s.%s missing required tag %s" % (source, k, item['name'], required_tag))
                    for tag in item['tags']:
                        if tag.startswith("ns.") and tag != required_tag:
                            errors.append("%s.%s.%s invalid ns tag %s" % (source, k, item['name'], tag))
                else:
                    errors.append("%s.%s.%s no tags found" % (source, k, item['name']))
                traverse ("%s.%s.%s" % (source, k, item['name']), errors, item, required_tag)

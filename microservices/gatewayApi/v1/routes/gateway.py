import os
import shutil
from subprocess import Popen, PIPE
import uuid
import logging
from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app
from io import TextIOWrapper

from v1.auth.auth import admin_jwt

gw = Blueprint('gwa', 'gateway')

from authlib.integrations.flask_oauth2 import ResourceProtector
from auth.token import RemoteToken, OIDCTokenValidator
require_oauth = ResourceProtector()
require_oauth.register_token_validator(OIDCTokenValidator(RemoteToken))

@gw.route('/<string:namespace>',
           methods=['PUT'], strict_slashes=False)
@require_oauth(None)
def write_config(namespace: str) -> object:
    """
    (Over)write
    :return: JSON of success message or error message
    """
    log = app.logger

    if 'team' not in g.principal:
        abort(make_response(jsonify(error="Missing Claims."), 500))

    team = g.principal['team']

    selectTag = outFolder = team

    log.debug(g.principal)

    if 'configFile' in request.files:
        log.debug(request.files['configFile'])
        dfile = request.files['configFile']

        tempFolder = "%s/%s/%s" % ('/tmp', uuid.uuid4(), outFolder)
        os.makedirs (tempFolder, exist_ok=False)

        dfile.save("%s/%s" % (tempFolder, 'config.yaml'))
        
        log.debug("Saved to %s" % tempFolder)

        # Validation #1
        # Validate that the principal has a claim for 'team' and ensure that the 'team'
        # is part of all the tags

        # Validation #2
        # Validate that there are no reserved words in the tags
        
        # Validation #3
        # Validate that certain plugins are configured (such as the gwa_gov_endpoint) at the right level

        # Call the 'deck' command
        cmd = "sync"
        print(request.values)
        if request.values['dryRun'] == 'true':
            cmd = "diff"

        log.info("%s for %s" % (cmd, team))
        args = [
            "deck", cmd, "--config", "/tmp/deck.yaml", "--skip-consumers", "--select-tag", selectTag, "--state", tempFolder
        ]
        deck_run = Popen(args, stdout=PIPE)
        out, err = deck_run.communicate()
        if deck_run.returncode != 0:
            print(out, err)
            cleanup (tempFolder)
            abort(make_response(jsonify(error="Sync Failed."), 500))

        cleanup (tempFolder)

        print(deck_run.returncode)
        log.debug("The exit code was: %d" % deck_run.returncode)

        message = "Config Updated."
        if cmd == 'diff':
            message = "Dry-run.  No changes applied."

        return make_response(jsonify(message=message, results=out.decode('utf-8')))
    else:
        abort(make_response(jsonify(error="Missing Input."), 500))


def cleanup (dir_path):
    log = app.logger
    try:
        shutil.rmtree(dir_path)
        log.debug("Deleted folder %s" % dir_path)
    except OSError as e:
        log.error("Error: %s : %s" % (dir_path, e.strerror))

def validate_tags (yaml, required_tag):
    # throw an exception if there are invalid tags
    abort(make_response(jsonify(error="Validation failed"), 500))

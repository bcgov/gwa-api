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

from clients.openshift import prepare_apply_routes, prepare_delete_routes, apply_routes, delete_routes

from utils.validators import host_valid

gw = Blueprint('gwa', 'gateway')

@gw.route('',
           methods=['PUT'], strict_slashes=False)
@admin_jwt(None)
def write_config(namespace: str) -> object:
    """
    (Over)write
    :return: JSON of success message or error message
    """
    enforce_authorization(namespace)
    log = app.logger

    selectTag = outFolder = namespace

    if 'configFile' in request.files:
        log.debug(request.files['configFile'])
        dfile = request.files['configFile']

        tempFolder = "%s/%s/%s" % ('/tmp', uuid.uuid4(), outFolder)
        os.makedirs (tempFolder, exist_ok=False)

        # dfile.save("%s/%s" % (tempFolder, 'config.yaml'))
        
        # log.debug("Saved to %s" % tempFolder)
        yaml_documents = yaml.load_all(dfile, Loader=yaml.FullLoader)

        for index, gw_config in enumerate(yaml_documents):
            log.debug("Parsing file %s %s" % (namespace, index))

            # Transformations before saving
            host_transformation (namespace, gw_config)

            with open("%s/%s" % (tempFolder, 'config-%02d.yaml' % index), 'w') as file:
                yaml.dump(gw_config, file)

            # Validation #1
            # Validate that the every object is tagged with the namespace
            try:
                validate_tags (gw_config, "ns.%s" % namespace)
            except Exception as ex:
                abort(make_response(jsonify(error="Validation Errors:\n%s" % ex), 400))

            # Validate that hosts are valid
            # try:
            #     validate_hosts (gw_config)
            # except Exception as ex:
            #     abort(make_response(jsonify(error="Validation Errors:\n%s" % ex), 400))

            # Validation #3
            # Validate that certain plugins are configured (such as the gwa_gov_endpoint) at the right level

            # Enrichment #1
            # Enrich the rate-limiting plugin with the appropriate Redis details

            # Validate based on DNS 952
        
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
            log.warn("%s - %s" % (namespace, out.decode('utf-8')))
            abort(make_response(jsonify(error="Sync Failed.", results=out.decode('utf-8')), 400))

        elif cmd == "sync":
            route_count = prepare_apply_routes (namespace, tempFolder)
            if route_count > 0:
                apply_routes (tempFolder)
            route_count = prepare_delete_routes (namespace, tempFolder)
            if route_count > 0:
                delete_routes (tempFolder)

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
        raise Exception('\n'.join(errors))

def traverse (source, errors, yaml, required_tag):
    traversables = ['services', 'routes', 'plugins', 'upstreams', 'consumers', 'certificates']
    for k in yaml:
        if k in traversables:
            for item in yaml[k]:
                if 'tags' in item:
                    if required_tag not in item['tags']:
                        errors.append("%s.%s.%s missing required tag %s" % (source, k, item['name'], required_tag))
                    for tag in item['tags']:
                        # if the required_tag is "abc" and the tag starts with "ns."
                        # then ns.abc and ns.abc.dev are valid, but anything else is an error
                        if tag.startswith("ns.") and tag != required_tag and not tag.startswith("%s." % required_tag):
                            errors.append("%s.%s.%s invalid ns tag %s" % (source, k, item['name'], tag))
                else:
                    errors.append("%s.%s.%s no tags found" % (source, k, item['name']))
                traverse ("%s.%s.%s" % (source, k, item['name']), errors, item, required_tag)

def host_transformation (namespace, yaml):
    log = app.logger

    transforms = 0
    conf = app.config['hostTransformation']
    if conf['enabled'] is True:
        for service in yaml['services']:
            for route in service['routes']:
                if 'hosts' in route:
                    new_hosts = []
                    for host in route['hosts']:
                        new_hosts.append("%s.%s" % (host.replace('.', '-'), conf['baseUrl']))
                        transforms = transforms + 1
                    route['hosts'] = new_hosts
    log.debug("[%s] Host transformations %d" % (namespace, transforms))

def validate_hosts (yaml):
    log = app.logger
    errors = []

    for service in yaml['services']:
        for route in service['routes']:
            if 'hosts' in route:
                for host in route['hosts']:
                    if host_valid(host) is False:
                        errors.append("Host not passing DNS-952 validation '%s'" % host)
    if len(errors) != 0:
        raise Exception('\n'.join(errors))

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

    outFolder = namespace

    if 'configFile' in request.files:
        log.debug(request.files['configFile'])
        dfile = request.files['configFile']

        tempFolder = "%s/%s/%s" % ('/tmp', uuid.uuid4(), outFolder)
        os.makedirs (tempFolder, exist_ok=False)

        # dfile.save("%s/%s" % (tempFolder, 'config.yaml'))
        
        # log.debug("Saved to %s" % tempFolder)
        yaml_documents = yaml.load_all(dfile, Loader=yaml.FullLoader)

        selectTag = "ns.%s" % namespace
        ns_qualifier = None

        for index, gw_config in enumerate(yaml_documents):
            log.debug("Parsing file %s %s" % (namespace, index))

            #######################
            # Enrichments
            #######################

            # Transformation route hosts if in non-prod environment (HOST_TRANSFORM_ENABLED)
            host_transformation (namespace, gw_config)

            # If there is a tag with a pipeline qualifier (i.e./ ns.<namespace>.dev)
            # then add to tags automatically the tag: ns.<namespace>
            tags_transformation (namespace, gw_config)

            #
            # Enrich the rate-limiting plugin with the appropriate Redis details

            with open("%s/%s" % (tempFolder, 'config-%02d.yaml' % index), 'w') as file:
                yaml.dump(gw_config, file)

            #######################
            # Validations
            #######################

            # Validate that the every object is tagged with the namespace
            try:
                validate_tags (gw_config, selectTag)
            except Exception as ex:
                abort(make_response(jsonify(error="Validation Errors:\n%s" % ex), 400))

            # Validate that hosts are valid
            try:
                validate_hosts (gw_config)
            except Exception as ex:
                abort(make_response(jsonify(error="Validation Errors:\n%s" % ex), 400))

            # Validation #3
            # Validate that certain plugins are configured (such as the gwa_gov_endpoint) at the right level

            # Validate based on DNS 952
        
            nsq = traverse_get_ns_qualifier (gw_config, selectTag)
            if nsq is not None:
                if ns_qualifier is not None and nsq != ns_qualifier:
                    abort(make_response(jsonify(error="Validation Errors:\n%s" % ("Conflicting ns qualifiers (%s != %s)" % (ns_qualifier, nsq))), 400))
                ns_qualifier = nsq

        if ns_qualifier is not None:
            selectTag = ns_qualifier

        # Call the 'deck' command
        cmd = "sync"
        print(request.values)
        if request.values['dryRun'] == 'true':
            cmd = "diff"

        log.info("%s for %s using %s" % (cmd, namespace, selectTag))
        args = [
            "deck", cmd, "--config", "/tmp/deck.yaml", "--skip-consumers", "--select-tag", selectTag, "--state", tempFolder
        ]
        deck_run = Popen(args, stdout=PIPE, stderr=STDOUT)
        out, err = deck_run.communicate()
        if deck_run.returncode != 0:
            cleanup (tempFolder)
            log.warn("%s - %s" % (namespace, out.decode('utf-8')))
            abort(make_response(jsonify(error="Sync Failed.", results=out.decode('utf-8')), 400))

        elif cmd == "sync":
            route_count = prepare_apply_routes (namespace, selectTag, tempFolder)
            if route_count > 0:
                apply_routes (tempFolder)
            route_count = prepare_delete_routes (namespace, selectTag, tempFolder)
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
    qualifiers = []

    if traverse_has_ns_qualifier(yaml, required_tag) and traverse_has_ns_tag_only(yaml, required_tag):
        errors.append("Tags for the namespace can not have a mix of 'ns.<namespace>' and 'ns.<namespace>.<qualifier>'.  Rejecting request.")

    traverse ("", errors, yaml, required_tag, qualifiers)
    if len(qualifiers) > 1:
        errors.append("Too many different qualified namespaces (%s).  Rejecting request." % qualifiers)

    if len(errors) != 0:
        raise Exception('\n'.join(errors))

def traverse (source, errors, yaml, required_tag, qualifiers):
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
                        if tag.startswith("%s." % required_tag) and tag not in qualifiers:
                            qualifiers.append(tag)
                else:
                    errors.append("%s.%s.%s no tags found" % (source, k, item['name']))
                traverse ("%s.%s.%s" % (source, k, item['name']), errors, item, required_tag, qualifiers)

def host_transformation (namespace, yaml):
    log = app.logger

    transforms = 0
    conf = app.config['hostTransformation']
    if conf['enabled'] is True:
        for service in yaml['services']:
            if 'routes' in service:
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
        if 'routes' in service:
            for route in service['routes']:
                if 'hosts' in route:
                    for host in route['hosts']:
                        if host_valid(host) is False:
                            errors.append("Host not passing DNS-952 validation '%s'" % host)
                else:
                    errors.append("service.%s.route.%s A host must be specified for routes." % (service['name'], route['name']))

    if len(errors) != 0:
        raise Exception('\n'.join(errors))

def tags_transformation (namespace, yaml):
    traverse_tags_transform (yaml, namespace, "ns.%s" % namespace)

def traverse_tags_transform (yaml, namespace, required_tag):
    log = app.logger
    traversables = ['services', 'routes', 'plugins', 'upstreams', 'consumers', 'certificates']
    for k in yaml:
        if k in traversables:
            for item in yaml[k]:
                if 'tags' in item:
                    new_tags = []
                    for tag in item['tags']:
                        new_tags.append(tag)
                        # add the base required tag automatically if there is already a qualifying namespace
                        if tag.startswith("ns.") and tag.startswith("%s." % required_tag) and required_tag not in item['tags']:
                            log.debug("[%s] Adding base tag %s to %s" % (namespace, required_tag, k))
                            new_tags.append(required_tag)
                    item['tags'] = new_tags
                traverse_tags_transform (item, namespace, required_tag)

def traverse_has_ns_qualifier (yaml, required_tag):
    log = app.logger
    traversables = ['services', 'routes', 'plugins', 'upstreams', 'consumers', 'certificates']
    for k in yaml:
        if k in traversables:
            for item in yaml[k]:
                if 'tags' in item:
                    for tag in item['tags']:
                        if tag.startswith("%s." % required_tag):
                            return True
                if traverse_has_ns_qualifier (item, required_tag) == True:
                    return True
    return False

def traverse_has_ns_tag_only (yaml, required_tag):
    log = app.logger
    traversables = ['services', 'routes', 'plugins', 'upstreams', 'consumers', 'certificates']
    for k in yaml:
        if k in traversables:
            for item in yaml[k]:
                if 'tags' in item:
                    if required_tag in item['tags'] and has_ns_qualifier(item['tags'], required_tag) is False:
                        return True
                if traverse_has_ns_tag_only (item, required_tag) == True:
                    return True
    return False

def has_ns_qualifier (tags, required_tag):
    for tag in tags:
        if tag.startswith("%s." % required_tag):
            return True
    return False

def traverse_get_ns_qualifier (yaml, required_tag):
    log = app.logger
    traversables = ['services', 'routes', 'plugins', 'upstreams', 'consumers', 'certificates']
    for k in yaml:
        if k in traversables:
            for item in yaml[k]:
                if 'tags' in item:
                    for tag in item['tags']:
                        if tag.startswith("%s." % required_tag):
                            return tag
                qualifier = traverse_get_ns_qualifier (item, required_tag)
                if qualifier is not None:
                    return qualifier
    return None

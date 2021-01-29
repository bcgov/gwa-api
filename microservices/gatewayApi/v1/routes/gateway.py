import os
import shutil
import sys
import http
import traceback
from subprocess import Popen, PIPE, STDOUT
import uuid
import logging
import json
import yaml
from werkzeug.exceptions import HTTPException, NotFound
from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app
from io import TextIOWrapper

from v1.auth.auth import admin_jwt, enforce_authorization

from v1.services.namespaces import NamespaceService

from clients.kong import get_routes
from clients.ocp_networksecuritypolicy import get_ocp_service_namespaces, check_nsp, apply_nsp, delete_nsp
from clients.ocp_routes import prepare_apply_routes, prepare_delete_routes, apply_routes, delete_routes
from clients.ocp_gateway_secret import prep_submitted_config, prep_and_apply_secret, write_submitted_config

from utils.validators import host_valid
from utils.transforms import plugins_transformations
from utils.masking import mask

gw = Blueprint('gwa', 'gateway')

@gw.route('/',
           methods=['DELETE'], strict_slashes=False)
@gw.route('/<string:qualifier>',
           methods=['DELETE'], strict_slashes=False)
@admin_jwt(None)
def delete_config(namespace: str, qualifier = "") -> object:
    log = app.logger

    outFolder = namespace

    tempFolder = "%s/%s/%s" % ('/tmp', uuid.uuid4(), outFolder)
    os.makedirs (tempFolder, exist_ok=False)

    with open("%s/%s" % (tempFolder, 'empty.yaml'), 'w') as file:
        file.write("")

    selectTag = "ns.%s" % namespace
    log.debug("ST = %s" % selectTag)
    if qualifier is not None and qualifier != "":
        log.debug("What is qual? %s" % qualifier)
        selectTag = "ns.%s.%s" % (namespace, qualifier)
    
    # Call the 'deck' command
    cmd = "sync"

    log.info("[%s] %s action using %s" % (namespace, cmd, selectTag))
    args = [
        "deck", cmd, "--config", "/tmp/deck.yaml", "--skip-consumers", "--select-tag", selectTag, "--state", tempFolder
    ]
    log.debug("[%s] Running %s" % (namespace, args))
    deck_run = Popen(args, stdout=PIPE, stderr=STDOUT)
    out, err = deck_run.communicate()
    if deck_run.returncode != 0:
        cleanup (tempFolder)
        log.warn("%s - %s" % (namespace, out.decode('utf-8')))
        abort(make_response(jsonify(error="Sync Failed.", results=mask(out.decode('utf-8'))), 400))

    elif cmd == "sync":
        try:
            route_count = prepare_apply_routes (namespace, selectTag, is_host_transform_enabled(), tempFolder)
            log.debug("%s - Prepared %d routes" % (namespace, route_count))
            if route_count > 0:
                apply_routes (tempFolder)
                log.debug("%s - Applied %d routes" % (namespace, route_count))
            route_count = prepare_delete_routes (namespace, selectTag, tempFolder)
            log.debug("%s - Prepared %d deletions" % (namespace, route_count))
            if route_count > 0:
                delete_routes (tempFolder)
        
            # create Network Security Policies (nsp) for any upstream that
            # has the format: <name>.<ocp_ns>.svc
            log.debug("%s - Update NSPs" % (namespace))
            ocp_ns_list = get_ocp_service_namespaces (tempFolder)
            for ocp_ns in ocp_ns_list:
                if check_nsp (namespace, ocp_ns) is False:
                    apply_nsp (namespace, ocp_ns, tempFolder)

            # ok all looks good, so update a secret containing the original submitted request
            log.debug("%s - Update Original Config" % (namespace))
            write_submitted_config ("", tempFolder)
            prep_and_apply_secret (namespace, selectTag, tempFolder)
            log.debug("%s - Updated Original Config" % (namespace))
        except HTTPException as ex:
            traceback.print_exc()
            log.error("Error updating custom routes, nsps and secrets. %s" % ex)
            abort(make_response(jsonify(error="Partially failed."), 400))
        except:
            traceback.print_exc()
            log.error("Error updating custom routes, nsps and secrets. %s" % sys.exc_info()[0])
            abort(make_response(jsonify(error="Partially failed."), 400))

    cleanup (tempFolder)

    log.debug("[%s] The exit code was: %d" % (namespace, deck_run.returncode))

    message = "Sync successful."
    if cmd == 'diff':
        message = "Dry-run.  No changes applied."

    return make_response('', http.HTTPStatus.NO_CONTENT)


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

    # Build a list of existing hosts that are outside this namespace
    # They become reserved and any conflict will return an error
    reserved_hosts = []
    all_routes = get_routes()
    tag_match = "ns.%s" % namespace
    for route in all_routes:
        if tag_match not in route['tags'] and 'hosts' in route:
            for host in route['hosts']:
                reserved_hosts.append(transform_host(host))
    reserved_hosts = list(set(reserved_hosts))


    ns_svc = NamespaceService()
    ns_attributes = ns_svc.get_namespace_attributes (namespace)

    dfile = None

    if 'configFile' in request.files:
        log.debug("[%s] %s" % (namespace, request.files['configFile']))
        dfile = request.files['configFile']
        dry_run = request.values['dryRun']
    elif request.content_type.startswith("application/json"):
        dfile = request.json['configFile']
        dry_run = request.json['dryRun']
    else:
        log.error("Missing input")
        log.error(request.get_data())
        log.error(request.form)
        log.error(request.content_type)
        log.error(request.headers)
        abort(make_response(jsonify(error="Missing input"), 400))

    tempFolder = "%s/%s/%s" % ('/tmp', uuid.uuid4(), outFolder)
    os.makedirs (tempFolder, exist_ok=False)

    # dfile.save("%s/%s" % (tempFolder, 'config.yaml'))
    
    # log.debug("Saved to %s" % tempFolder)
    yaml_documents_iter = yaml.load_all(dfile, Loader=yaml.FullLoader)

    yaml_documents = []
    for doc in yaml_documents_iter:
        yaml_documents.append(doc)

    selectTag = "ns.%s" % namespace
    ns_qualifier = None

    orig_config = prep_submitted_config (yaml_documents)

    for index, gw_config in enumerate(yaml_documents):
        log.info("[%s] Parsing file %s" % (namespace, index))

        if gw_config is None:
            continue

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
        plugins_transformations (namespace, gw_config)

        with open("%s/%s" % (tempFolder, 'config-%02d.yaml' % index), 'w') as file:
            yaml.dump(gw_config, file)

        #######################
        # Validations
        #######################

        # Validate that the every object is tagged with the namespace
        try:
            validate_tags (gw_config, selectTag)
        except Exception as ex:
            traceback.print_exc()
            log.error("%s - %s" % (namespace, " Tag Validation Errors: %s" % ex))
            abort(make_response(jsonify(error="Validation Errors:\n%s" % ex), 400))

        # Validate that hosts are valid
        try:
            validate_hosts (gw_config, reserved_hosts, ns_attributes)
        except Exception as ex:
            traceback.print_exc()
            log.error("%s - %s" % (namespace, " Host Validation Errors: %s" % ex))
            abort(make_response(jsonify(error="Validation Errors:\n%s" % ex), 400))

        # Validation #3
        # Validate that certain plugins are configured (such as the gwa_gov_endpoint) at the right level

        # Validate based on DNS 952
    
        nsq = traverse_get_ns_qualifier (gw_config, selectTag)
        if nsq is not None:
            if ns_qualifier is not None and nsq != ns_qualifier:
                abort(make_response(jsonify(error="Validation Errors:\n%s" % ("Conflicting ns qualifiers (%s != %s)" % (ns_qualifier, nsq))), 400))
            ns_qualifier = nsq
            log.info("[%s] CHANGING ns_qualifier %s" % (namespace, ns_qualifier))

    if ns_qualifier is not None:
        selectTag = ns_qualifier

    # Call the 'deck' command
    cmd = "sync"
    if dry_run == 'true' or dry_run is True:
        cmd = "diff"

    log.info("[%s] %s action using %s" % (namespace, cmd, selectTag))
    args = [
        "deck", cmd, "--config", "/tmp/deck.yaml", "--skip-consumers", "--select-tag", selectTag, "--state", tempFolder
    ]
    log.debug("[%s] Running %s" % (namespace, args))
    deck_run = Popen(args, stdout=PIPE, stderr=STDOUT)
    out, err = deck_run.communicate()
    if deck_run.returncode != 0:
        cleanup (tempFolder)
        log.warn("%s - %s" % (namespace, out.decode('utf-8')))
        abort(make_response(jsonify(error="Sync Failed.", results=mask(out.decode('utf-8'))), 400))

    elif cmd == "sync":
        try:
            route_count = prepare_apply_routes (namespace, selectTag, is_host_transform_enabled(), tempFolder)
            log.debug("%s - Prepared %d routes" % (namespace, route_count))
            if route_count > 0:
                apply_routes (tempFolder)
                log.debug("%s - Applied %d routes" % (namespace, route_count))
            route_count = prepare_delete_routes (namespace, selectTag, tempFolder)
            log.debug("%s - Prepared %d deletions" % (namespace, route_count))
            if route_count > 0:
                delete_routes (tempFolder)
        
            # create Network Security Policies (nsp) for any upstream that
            # has the format: <name>.<ocp_ns>.svc
            log.debug("%s - Update NSPs" % (namespace))
            ocp_ns_list = get_ocp_service_namespaces (tempFolder)
            for ocp_ns in ocp_ns_list:
                if check_nsp (namespace, ocp_ns) is False:
                    apply_nsp (namespace, ocp_ns, tempFolder)

            # ok all looks good, so update a secret containing the original submitted request
            log.debug("%s - Update Original Config" % (namespace))
            write_submitted_config (orig_config, tempFolder)
            prep_and_apply_secret (namespace, selectTag, tempFolder)
            log.debug("%s - Updated Original Config" % (namespace))
        except HTTPException as ex:
            traceback.print_exc()
            log.error("Error updating custom routes, nsps and secrets. %s" % ex)
            abort(make_response(jsonify(error="Partially failed."), 400))
        except:
            traceback.print_exc()
            log.error("Error updating custom routes, nsps and secrets. %s" % sys.exc_info()[0])
            abort(make_response(jsonify(error="Partially failed."), 400))

    cleanup (tempFolder)

    log.debug("[%s] The exit code was: %d" % (namespace, deck_run.returncode))

    message = "Sync successful."
    if cmd == 'diff':
        message = "Dry-run.  No changes applied."

    return make_response(jsonify(message=message, results=mask(out.decode('utf-8'))))

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
    if is_host_transform_enabled():
        if 'services' in yaml:
            for service in yaml['services']:
                if 'routes' in service:
                    for route in service['routes']:
                        if 'hosts' in route:
                            new_hosts = []
                            for host in route['hosts']:
                                new_hosts.append(transform_host(host))
                                transforms = transforms + 1
                            route['hosts'] = new_hosts
    log.debug("[%s] Host transformations %d" % (namespace, transforms))

def transform_host (host):
    if is_host_transform_enabled():
        conf = app.config['hostTransformation']
        return "%s.%s" % (host.replace('.', '-'), conf['baseUrl'])
    else:
        return host

def validate_hosts (yaml, reserved_hosts, ns_attributes):
    errors = []

    allowed_domains = []
    for domain in ns_attributes.get('perm-domains', ['.api.gov.bc.ca'] ):
        allowed_domains.append("%s" % domain)

    ## A host must not exist outside of namespace (reserved_hosts)
    if 'services' in yaml:
        for service in yaml['services']:
            if 'routes' in service:
                for route in service['routes']:
                    if 'hosts' in route:
                        for host in route['hosts']:
                            if host in reserved_hosts:
                                errors.append("service.%s.route.%s The host is already used in another namespace '%s'" % (service['name'], route['name'], host))
                            if host_valid(host) is False:
                                errors.append("Host not passing DNS-952 validation '%s'" % host)
                            if host_ends_with_one_of_list (host, allowed_domains) is False:
                                errors.append("Host invalid: %s.  Route hosts must end with one of [%s] for this namespace." % (route['name'], ','.join(allowed_domains)))
                    else:
                        errors.append("service.%s.route.%s A host must be specified for routes." % (service['name'], route['name']))

    if len(errors) != 0:
        raise Exception('\n'.join(errors))

def host_ends_with_one_of_list (a_str, a_list):
    for item in a_list:
        if a_str.endswith(transform_host(item)):
            return True
    return False

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

def is_host_transform_enabled ():
    conf = app.config['hostTransformation']
    return conf['enabled'] is True

import os
import shutil
import sys
import http
import traceback
from urllib.parse import urlparse
from subprocess import Popen, PIPE, STDOUT
import uuid
import logging
import json
import requests
import yaml
from werkzeug.exceptions import HTTPException, NotFound
from flask import Blueprint, config, jsonify, request, Response, make_response, abort, g, current_app as app
from io import TextIOWrapper
from clients.ocp_routes import get_host_list, get_route_overrides

from v2.auth.auth import admin_jwt, uma_enforce

from v2.services.namespaces import NamespaceService

from clients.portal import record_gateway_event
from clients.kong import get_routes, get_public_certs_by_ns, register_kong_certs
from clients.ocp_gateway_secret import prep_submitted_config, prep_and_apply_secret, write_submitted_config

from utils.validators import host_valid
from utils.transforms import plugins_transformations
from utils.masking import mask

gw = Blueprint('gwa_v2', 'gateway')
local_environment = os.environ.get("LOCAL_ENVIRONMENT", default=False)


def abort_early(event_id, action, namespace, response):
    record_gateway_event(event_id, action, 'failed', namespace, json.dumps(response.get_json()))
    abort(make_response(response, 400))


@gw.route('/',
          methods=['DELETE'], strict_slashes=False)
@gw.route('/<string:qualifier>',
          methods=['DELETE'], strict_slashes=False)
@admin_jwt(None)
@uma_enforce('namespace', 'GatewayConfig.Publish')
def delete_config(namespace: str, qualifier="") -> object:

    event_id = str(uuid.uuid4())
    record_gateway_event(event_id, 'delete', 'received', namespace)
    ns_svc = NamespaceService()
    ns_attributes = ns_svc.get_namespace_attributes(namespace)

    log = app.logger

    outFolder = namespace

    tempFolder = "%s/%s/%s" % ('/tmp', uuid.uuid4(), outFolder)
    os.makedirs(tempFolder, exist_ok=False)

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
        cleanup(tempFolder)
        log.warn("%s - %s" % (namespace, out.decode('utf-8')))
        abort_early(event_id, 'delete', namespace, jsonify(error="Sync Failed.", results=mask(out.decode('utf-8'))))

    elif cmd == "sync" and not local_environment:
        try:
            session = requests.Session()
            session.headers.update({"Content-Type": "application/json"})
            route_payload = {
                "hosts": get_host_list(tempFolder),
                "select_tag": selectTag,
                "ns_attributes": ns_attributes.getAttrs()
            }
            dp = get_data_plane(ns_attributes)
            rqst_url = app.config['data_planes'][dp]["kube-api"]
            log.debug("[%s] - Initiating request to kube API" % (dp))
            res = session.put(rqst_url + "/namespaces/%s/routes" % namespace, json=route_payload, auth=(
                app.config['kubeApiCreds']['kubeApiUser'], app.config['kubeApiCreds']['kubeApiPass']))
            log.debug("[%s] - The kube API responded with %s" % (dp, res.status_code))
            if res.status_code != 201:
                log.debug("[%s] - The kube API could not process the request" % (dp))
                raise Exception("[%s] - Failed to apply routes: %s" % (dp, str(res.text)))
            # route_count = prepare_apply_routes(namespace, selectTag, is_host_transform_enabled(), tempFolder)
            # log.debug("%s - Prepared %d routes" % (namespace, route_count))
            # if route_count > 0:
            #     apply_routes(tempFolder)
            #     log.debug("%s - Applied %d routes" % (namespace, route_count))
            # route_count = prepare_delete_routes(namespace, selectTag, tempFolder)
            # log.debug("%s - Prepared %d deletions" % (namespace, route_count))
            # if route_count > 0:
            #     delete_routes(tempFolder)

            # # create Network Security Policies (nsp) for any upstream that
            # # has the format: <name>.<ocp_ns>.svc
            # log.debug("%s - Update NSPs" % (namespace))
            # ocp_ns_list = get_ocp_service_namespaces(tempFolder)
            # for ocp_ns in ocp_ns_list:
            #     if check_nsp(namespace, ocp_ns) is False:
            #         apply_nsp(namespace, ocp_ns, tempFolder)

            # ok all looks good, so update a secret containing the original submitted request
            # log.debug("%s - Update Original Config" % (namespace))
            # write_submitted_config("", tempFolder)
            # prep_and_apply_secret(namespace, selectTag, tempFolder)
            # log.debug("%s - Updated Original Config" % (namespace))
            session.close()
        except HTTPException as ex:
            traceback.print_exc()
            log.error("Error updating custom routes. %s" % ex)
            abort_early(event_id, 'delete', namespace, jsonify(error="Partially failed."))
        except:
            traceback.print_exc()
            log.error("Error updating custom routes. %s" % sys.exc_info()[0])
            abort_early(event_id, 'delete', namespace, jsonify(error="Partially failed."))

    cleanup(tempFolder)

    log.debug("[%s] The exit code was: %d" % (namespace, deck_run.returncode))

    record_gateway_event(event_id, 'delete', 'completed', namespace)
    return make_response('', http.HTTPStatus.NO_CONTENT)

@gw.route('',
          methods=['PUT'], strict_slashes=False)
@admin_jwt(None)
@uma_enforce('namespace', 'GatewayConfig.Publish')
def write_config(namespace: str) -> object:
    """
    (Over)write
    :return: JSON of success message or error message
    """

    event_id = str(uuid.uuid4())

    log = app.logger

    outFolder = namespace

    ns_svc = NamespaceService()
    ns_attributes = ns_svc.get_namespace_attributes(namespace)

    dp = get_data_plane(ns_attributes)

    # Build a list of existing hosts that are outside this namespace
    # They become reserved and any conflict will return an error
    reserved_hosts = []
    all_routes = get_routes()
    tag_match = "ns.%s" % namespace
    for route in all_routes:
        if tag_match not in route['tags'] and 'hosts' in route:
            for host in route['hosts']:
                reserved_hosts.append(host)
    reserved_hosts = list(set(reserved_hosts))


    dfile = None
    select_tag_qualifier = None

    if 'configFile' in request.files and not request.files['configFile'].filename == '':
        log.debug("[%s] %s", namespace, request.files['configFile'])
        dfile = request.files['configFile']
        dry_run = request.values['dryRun']
        if "qualifier" in request.values:
            select_tag_qualifier = request.values['qualifier']
    elif request.content_type.startswith("application/json") \
        and 'configFile' in request.json \
        and not request.json['configFile'] in [None, '']:
        dfile = request.json['configFile']
        dry_run = request.json['dryRun']
        if "qualifier" in request.json:
            select_tag_qualifier = request.json['qualifier']
    else:
        log.error("Missing input")
        log.error("%s", request.get_data())
        log.error(request.form)
        log.error(request.content_type)
        log.error(request.headers)
        abort_early(event_id, 'publish', namespace, jsonify(error="Missing input"))

    cmd = "sync"
    if dry_run == 'true' or dry_run is True:
        cmd = "diff"

    if cmd == 'sync':
        record_gateway_event(event_id, 'publish', 'received', namespace)

    tempFolder = "%s/%s/%s" % ('/tmp', uuid.uuid4(), outFolder)
    os.makedirs(tempFolder, exist_ok=False)

    # dfile.save("%s/%s" % (tempFolder, 'config.yaml'))

    # log.debug("Saved to %s" % tempFolder)
    yaml_documents = load_yaml_files(dfile)

    if len(yaml_documents) == 0:
        log.error("%s - %s" % (namespace, "Empty Configuration Passed"))
        abort_early(event_id, 'publish', namespace, jsonify(error="Empty Configuration Passed"))

    selectTag = "ns.%s" % namespace
    ns_qualifier = None
    if select_tag_qualifier is not None and select_tag_qualifier != "" and "." not in select_tag_qualifier:
        ns_qualifier = "%s.%s" % (selectTag, select_tag_qualifier)

    orig_config = prep_submitted_config(clone_yaml_files(yaml_documents))

    update_routes_flag = False

    for index, gw_config in enumerate(yaml_documents):
        log.info("[%s] Parsing file %s" % (namespace, index))

        if gw_config is None:
            continue

        #######################
        # Enrichments
        #######################

        # Transformation route hosts if in non-prod environment (HOST_TRANSFORM_ENABLED)
        host_transformation(namespace, dp, gw_config)

        # If there is a tag with a pipeline qualifier (i.e./ ns.<namespace>.dev)
        # then add to tags automatically the tag: ns.<namespace>
        object_count = tags_transformation(namespace, gw_config)

        #
        # Enrich the rate-limiting plugin with the appropriate Redis details
        plugins_transformations(namespace, gw_config)

        with open("%s/%s" % (tempFolder, 'config-%02d.yaml' % index), 'w') as file:
            yaml.dump(gw_config, file)

        #######################
        # Validations
        #######################

        # Validate that the every object is tagged with the namespace
        try:
            validate_base_entities(gw_config, ns_attributes)
            validate_tags(gw_config, selectTag)
        except Exception as ex:
            traceback.print_exc()
            log.error("%s - %s" % (namespace, " Tag Validation Errors: %s" % ex))
            abort_early(event_id, 'publish', namespace, jsonify(error="Validation Errors:\n%s" % ex))

        # Validate that hosts are valid
        try:
            validate_hosts(gw_config, reserved_hosts, ns_attributes)
        except Exception as ex:
            traceback.print_exc()
            log.error("%s - %s" % (namespace, " Host Validation Errors: %s" % ex))
            abort_early(event_id, 'publish', namespace, jsonify(error="Validation Errors:\n%s" % ex))

        # Validate upstream URLs are valid
        try:
            protected_kube_namespaces = json.loads(app.config['protectedKubeNamespaces'])
            validate_upstream(gw_config, ns_attributes, protected_kube_namespaces)
        except Exception as ex:
            traceback.print_exc()
            log.error("%s - %s" % (namespace, " Upstream Validation Errors: %s" % ex))
            abort_early(event_id, 'publish', namespace, jsonify(error="Validation Errors:\n%s" % ex))

        # Validation #3
        # Validate that certain plugins are configured (such as the gwa_gov_endpoint) at the right level

        # Validate based on DNS 952

        nsq = traverse_get_ns_qualifier(gw_config, selectTag)
        if nsq is not None:
            if ns_qualifier is not None and nsq != ns_qualifier:
                abort_early(event_id, 'publish', namespace, jsonify(error="Validation Errors:\n%s" %
                            ("Conflicting ns qualifiers (%s != %s)" % (ns_qualifier, nsq))))
            ns_qualifier = nsq
            log.info("[%s] CHANGING ns_qualifier %s" % (namespace, ns_qualifier))
        elif ns_qualifier is not None and object_count > 0:
            abort_early(event_id, 'publish', namespace, jsonify(error="Validation Errors:\n%s" %
                ("Specified qualifier (%s) does not match tags in configuration (%s)" % (ns_qualifier, selectTag))))

        if update_routes_check(gw_config):
            update_routes_flag = True

    if ns_qualifier is not None:
        selectTag = ns_qualifier

    # Call the 'deck' command

    log.info("[%s] %s action using %s" % (namespace, cmd, selectTag))

    args = [
        "deck", "validate", "--config", "/tmp/deck.yaml", "--state", tempFolder
    ]
    log.debug("[%s] Running %s" % (namespace, args))
    deck_validate = Popen(args, stdout=PIPE, stderr=STDOUT)
    out, err = deck_validate.communicate()

    if deck_validate.returncode != 0:
        log.warning("[%s] - %s" % (namespace, out.decode('utf-8')))
        abort_early(event_id, 'validate', namespace, jsonify(
            error="Validation Failed.", results=mask(out.decode('utf-8'))))

    args = [
        "deck", cmd, "--config", "/tmp/deck.yaml", "--skip-consumers", "--select-tag", selectTag, "--state", tempFolder
    ]
    log.debug("[%s] Running %s" % (namespace, args))
    deck_run = Popen(args, stdout=PIPE, stderr=STDOUT)
    out, err = deck_run.communicate()
    if deck_run.returncode != 0:
        cleanup(tempFolder)
        log.warn("[%s] - %s" % (namespace, out.decode('utf-8')))
        abort_early(event_id, 'publish', namespace, jsonify(error="Sync Failed.", results=mask(out.decode('utf-8'))))
    # skip creation of routes in local development environment
    elif cmd == "sync" and not local_environment:
        try:
            if update_routes_flag:
                host_list = get_host_list(tempFolder)
                certs = get_public_certs_by_ns(namespace)
                session = requests.Session()
                session.headers.update({"Content-Type": "application/json"})
                route_payload = {
                    "hosts": host_list,
                    "select_tag": selectTag,
                    "ns_attributes": ns_attributes.getAttrs(),
                    "overrides": {
                        "aps.route.session.cookie.enabled": get_route_overrides(tempFolder, "aps.route.session.cookie.enabled"),
                        "aps.route.dataclass.low": get_route_overrides(tempFolder, "aps.route.dataclass.low"),
                        "aps.route.dataclass.medium": get_route_overrides(tempFolder, "aps.route.dataclass.medium"),
                        "aps.route.dataclass.high": get_route_overrides(tempFolder, "aps.route.dataclass.high"),
                        "aps.route.dataclass.public": get_route_overrides(tempFolder, "aps.route.dataclass.public"),
                    },
                    "certificates": certs
                }
                log.debug("[%s] - Initiating request to kube API %s" % (dp, route_payload))
                rqst_url = app.config['data_planes'][dp]["kube-api"]
                res = session.put(rqst_url + "/namespaces/%s/routes" % namespace, json=route_payload, auth=(
                    app.config['kubeApiCreds']['kubeApiUser'], app.config['kubeApiCreds']['kubeApiPass']))
                log.debug("[%s] - The kube API responded with %s" % (dp, res.status_code))
                if res.status_code != 201:
                    log.debug("[%s] - The kube API could not process the request" % (dp))
                    raise Exception("[%s] - Failed to apply routes: %s" % (dp, str(res.text)))
                session.close()
                
                if has_namespace_local_host_permission(ns_attributes):
                    session = requests.Session()
                    session.headers.update({"Content-Type": "application/json"})
                    rqst_url = app.config['data_planes'][dp]["kube-api"]
                    log.debug("[%s] - Initiating request to kube API for Certs" % (dp))
                    res = session.get(rqst_url + "/namespaces/%s/local_tls" % namespace, auth=(
                        app.config['kubeApiCreds']['kubeApiUser'], app.config['kubeApiCreds']['kubeApiPass']))
                    log.debug("[%s] - The kube API responded with %s" % (dp, res.status_code))
                    if res.status_code != 200:
                        log.debug("[%s] - The kube API could not process the request" % (dp))
                        raise Exception("[%s] - Failed to get certs: %s" % (dp, str(res.text)))
                    cert_data = res.json()
                    session.close()

                    register_kong_certs(namespace, cert_data)
                
        except HTTPException as ex:
            traceback.print_exc()
            log.error("[%s] Error updating custom routes. %s" % (namespace, ex))
            abort_early(event_id, 'publish', namespace, jsonify(error="Partially failed."))
        except:
            traceback.print_exc()
            log.error("[%s] Error updating custom routes. %s" % (namespace, sys.exc_info()[0]))
            abort_early(event_id, 'publish', namespace, jsonify(error="Partially failed."))

    cleanup(tempFolder)

    log.debug("[%s] The exit code was: %d" % (namespace, deck_run.returncode))

    message = "Sync successful."
    if cmd == 'diff':
        message = "Dry-run.  No changes applied."

    if cmd == 'sync':
        record_gateway_event(event_id, 'published', 'completed', namespace, blob=orig_config)
    return make_response(jsonify(message=message, results=mask(out.decode('utf-8'))))


def cleanup(dir_path):
    log = app.logger
    try:
        shutil.rmtree(dir_path)
        log.debug("Deleted folder %s" % dir_path)
    except OSError as e:
        log.error("Error: %s : %s" % (dir_path, e.strerror))

def validate_base_entities(yaml, ns_attributes):
    traversables = ['_format_version', '_plugin_configs', 'services', 'upstreams', 'certificates']

    allow_protected_ns = ns_attributes.get('perm-protected-ns', ['deny'])[0] == 'allow'
    if allow_protected_ns:
        traversables.append('plugins')
        traversables.append('ca_certificates')

    for k in yaml:
        if k not in traversables:
            raise Exception("Invalid base entity %s" % k)

def validate_tags(yaml, required_tag):
    # throw an exception if there are invalid tags
    errors = []
    qualifiers = []

    if traverse_has_ns_qualifier(yaml, required_tag) and traverse_has_ns_tag_only(yaml, required_tag):
        errors.append(
            "Tags for the gateway can not have a mix of 'ns.<gateway>' and 'ns.<gateway>.<qualifier>'.  Rejecting request.")

    traverse("", errors, yaml, required_tag, qualifiers)
    if len(qualifiers) > 1:
        errors.append("Too many different qualified gateways (%s).  Rejecting request." % qualifiers)

    if len(errors) != 0:
        raise Exception('\n'.join(errors))

def traverse(source, errors, yaml, required_tag, qualifiers):
    # If at root level, allow different resources than if its traversed down a level
    if source == "":
        traversables = ['services', 'upstreams', 'consumers', 'certificates', 'ca_certificates']
    else:
        traversables = ['routes', 'plugins']

    for k in yaml:
        if k in traversables:
            for index, item in enumerate(yaml[k]):
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
                nm = "[%d]" % index
                if 'name' in item:
                    nm = item['name']
                traverse("%s.%s.%s" % (source, k, nm), errors, item, required_tag, qualifiers)


def host_transformation(namespace, data_plane, yaml):
    log = app.logger

    transforms = 0
    if 'services' in yaml:
        for service in yaml['services']:
            if 'routes' in service:
                for route in service['routes']:
                    if 'hosts' in route:
                        new_hosts = []
                        for host in route['hosts']:
                            if is_host_local(host):
                                new_hosts.append(transform_local_host(data_plane, host))
                            if is_host_custom_domain(host):
                                new_hosts.append(host)
                            elif is_host_transform_enabled():
                                new_hosts.append(transform_host(host))
                                transforms = transforms + 1
                            else:
                                new_hosts.append(host)
                        route['hosts'] = new_hosts
    log.debug("[%s] Host transformations %d" % (namespace, transforms))

def is_host_local(host):
    return host.endswith(".cluster.local")

def is_host_custom_domain(host):
    non_custom_suffixes = [
        '.cluster.local', 
        '.api.gov.bc.ca', 
        '.data.gov.bc.ca', 
        '.webapps.gov.bc.ca', 
        '.maps.gov.bc.ca', 
        '.openmaps.gov.bc.ca'
    ]
    
    # Check if the host ends with any of the non-custom suffixes
    for suffix in non_custom_suffixes:
        if host.endswith(suffix):
            return False
    
    return True

def has_namespace_local_host_permission(ns_attributes):
    for domain in ns_attributes.get('perm-domains', ['.api.gov.bc.ca']):
        if is_host_local(domain):
            return True
    return False

# Validate transformed host: <service>.<namespace>.svc.cluster.local
def validate_local_host(host):
    if is_host_local(host) and len(host.split('.')) != 5:
        return False
    return True
  
def transform_local_host(data_plane, host):
    suffix_len = len(".cluster.local")
    kube_ns = app.config['data_planes'][data_plane]["kube-ns"]
    name_part = host[:-suffix_len]
    return "gw-%s.%s.svc.cluster.local" % (name_part, kube_ns)

def transform_host(host):
    if is_host_local(host):
        return host
    elif is_host_transform_enabled():
        conf = app.config['hostTransformation']
        return "%s%s" % (host.replace('.', '-'), conf['baseUrl'])
    else:
        return host

def validate_upstream(yaml, ns_attributes, protected_kube_namespaces):
    errors = []

    allow_protected_ns = ns_attributes.get('perm-protected-ns', ['deny'])[0] == 'allow'

    # A host must not contain a list of protected
    if 'services' in yaml:
        for service in yaml['services']:
            if 'url' in service:
                try:
                    u = urlparse(service["url"])
                    if u.hostname is None:
                        errors.append("service upstream has invalid url specified (e1)")
                    else:
                        validate_upstream_host(u.hostname, errors, allow_protected_ns, protected_kube_namespaces)
                except Exception as e:
                    errors.append("service upstream has invalid url specified (e2)")

            if 'host' in service:
                host = service["host"]
                validate_upstream_host(host, errors, allow_protected_ns, protected_kube_namespaces)

    if len(errors) != 0:
        raise Exception('\n'.join(errors))


def validate_upstream_host(_host, errors, allow_protected_ns, protected_kube_namespaces):
    host = _host.lower()

    restricted = ['localhost', '127.0.0.1', '0.0.0.0']

    if host in restricted:
        errors.append("service upstream is invalid (e1)")
    if host.endswith('svc'):
        partials = host.split('.')
        # get the namespace, and make sure it is not in the protected_kube_namespaces list
        if len(partials) != 3:
            errors.append("service upstream is invalid (e2)")
        elif partials[1] in protected_kube_namespaces and allow_protected_ns is False:
            errors.append("service upstream is invalid (e3)")
    if host.endswith('svc.cluster.local'):
        partials = host.split('.')
        # get the namespace, and make sure it is not in the protected_kube_namespaces list
        if len(partials) != 5:
            errors.append("service upstream is invalid (e4)")
        elif partials[1] in protected_kube_namespaces and allow_protected_ns is False:
            errors.append("service upstream is invalid (e5)")

def update_routes_check(yaml):
    if 'services' in yaml or 'upstreams' not in yaml:
        return True
    else:
        return False

def validate_hosts(yaml, reserved_hosts, ns_attributes):
    errors = []

    allowed_domains = []
    for domain in ns_attributes.get('perm-domains', ['.api.gov.bc.ca']):
        allowed_domains.append("%s" % domain)

    # A host must not exist outside of namespace (reserved_hosts)
    if 'services' in yaml:
        for service in yaml['services']:
            if 'routes' in service:
                for route in service['routes']:
                    if 'hosts' in route:
                        for host in route['hosts']:
                            if host in reserved_hosts:
                                errors.append("service.%s.route.%s The host is already used in another gateway '%s'" % (
                                    service['name'], route['name'], host))
                            if host_valid(host) is False:
                                errors.append("Host not passing DNS-952 validation '%s'" % host)
                            if validate_local_host(host) is False:
                                errors.append("Host failed validation for data plane '%s'" % host)
                            if host_ends_with_one_of_list(host, allowed_domains) is False:
                                errors.append("Host invalid: %s %s.  Route hosts must end with one of [%s] for this gateway." % (
                                    route['name'], host, ','.join(allowed_domains)))
                    else:
                        errors.append("service.%s.route.%s A host must be specified for routes." %
                                      (service['name'], route['name']))

    if len(errors) != 0:
        raise Exception('\n'.join(errors))


def host_ends_with_one_of_list(a_str, a_list):
    for item in a_list:
        if a_str.endswith(transform_host(item)):
            return True
    return False


def tags_transformation(namespace, yaml):
    return traverse_tags_transform(yaml, namespace, "ns.%s" % namespace)


def traverse_tags_transform(yaml, namespace, required_tag):
    object_count = 0
    log = app.logger
    traversables = ['services', 'routes', 'plugins', 'upstreams', 'consumers', 'certificates', 'ca_certificates']
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
                object_count = object_count + 1
                object_count = object_count + traverse_tags_transform(item, namespace, required_tag)
    return object_count


def traverse_has_ns_qualifier(yaml, required_tag):
    log = app.logger
    traversables = ['services', 'routes', 'plugins', 'upstreams', 'consumers', 'certificates', 'ca_certificates']
    for k in yaml:
        if k in traversables:
            for item in yaml[k]:
                if 'tags' in item:
                    for tag in item['tags']:
                        if tag.startswith("%s." % required_tag):
                            return True
                if traverse_has_ns_qualifier(item, required_tag) == True:
                    return True
    return False


def traverse_has_ns_tag_only(yaml, required_tag):
    log = app.logger
    traversables = ['services', 'routes', 'plugins', 'upstreams', 'consumers', 'certificates', 'ca_certificates']
    for k in yaml:
        if k in traversables:
            for item in yaml[k]:
                if 'tags' in item:
                    if required_tag in item['tags'] and has_ns_qualifier(item['tags'], required_tag) is False:
                        return True
                if traverse_has_ns_tag_only(item, required_tag) == True:
                    return True
    return False


def has_ns_qualifier(tags, required_tag):
    for tag in tags:
        if tag.startswith("%s." % required_tag):
            return True
    return False


def traverse_get_ns_qualifier(yaml, required_tag):
    log = app.logger
    traversables = ['services', 'routes', 'plugins', 'upstreams', 'consumers', 'certificates', 'ca_certificates']
    for k in yaml:
        if k in traversables:
            for item in yaml[k]:
                if 'tags' in item:
                    for tag in item['tags']:
                        if tag.startswith("%s." % required_tag):
                            return tag
                qualifier = traverse_get_ns_qualifier(item, required_tag)
                if qualifier is not None:
                    return qualifier
    return None


def get_data_plane(ns_attributes):
    default_data_plane = app.config['defaultDataPlane']
    return ns_attributes.get('perm-data-plane', [default_data_plane])[0]


def is_host_transform_enabled():
    conf = app.config['hostTransformation']
    return conf['enabled'] is True


def should_we_apply_nsp_policies():
    conf = app.config['applyAporetoNSP']
    return conf is True

def load_yaml_files (dfile):
    yaml_documents_iter = yaml.load_all(dfile, Loader=yaml.FullLoader)
    yaml_documents = []
    for doc in yaml_documents_iter:
        yaml_documents.append(doc)
    return yaml_documents

def clone_yaml_files (yaml_documents):
    cloned_yaml = []
    for doc in yaml_documents:
        cloned_yaml.append(yaml.load(yaml.dump(doc), Loader=yaml.FullLoader))
    return cloned_yaml
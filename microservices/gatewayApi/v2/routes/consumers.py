from v2.routes.gateway import abort_early
from utils.transforms import rate_limiting
import sys
import traceback
import uuid
from flask import Blueprint, abort, jsonify, request, make_response, current_app as app
from werkzeug.exceptions import HTTPException
from clients.portal import record_custom_event
from v2.services.gateway_consumers import GatewayConsumerService
from v2.auth.auth import admin_jwt, uma_enforce

consumers = Blueprint('consumers.v2', 'consumers')


@admin_jwt(None)
@uma_enforce('namespace', 'Access.Manage')
@consumers.route('/<string:consumer_id>/plugins',
                 methods=['POST'], strict_slashes=False)
def create_consumer_plugin(namespace: str, consumer_id: str) -> object:
    event_id = str(uuid.uuid4())
    log = app.logger
    plugin_data = request.get_json()
    cnsr = GatewayConsumerService()
    selectTag = "ns.%s" % namespace
    ns_qualifier = None

    if plugin_data == None:
        log.error("Missing input")
        record_custom_event(event_id, 'GatewayConsumerPlugin', 'add', 'failed', namespace, "Missing input.")
        abort(make_response(jsonify(error="Missing input."), 400))

    transform_tags(plugin_data, namespace, "ns.%s" % namespace)

    if plugin_data['name'] == 'rate-limiting':
        rate_limiting(plugin_data)

    validate_tags(plugin_data, selectTag)

    nsq = traverse_get_ns_qualifier(plugin_data, selectTag)
    if nsq is not None:
        if ns_qualifier is not None and nsq != ns_qualifier:
            abort_early(event_id, 'GatewayConsumerPlugin', namespace, jsonify(error="Validation Errors:\n%s" %
                        ("Conflicting ns qualifiers (%s != %s)" % (ns_qualifier, nsq))))
        ns_qualifier = nsq
        log.info("[%s] CHANGING ns_qualifier %s" % (namespace, ns_qualifier))

    if ns_qualifier is not None:
        selectTag = ns_qualifier

    try:
        response = cnsr.add_consumer_plugin(consumer_id, plugin_data)
    except Exception as ex:
        handle_exceptions(exception=ex, event_id=event_id, type='GatewayConsumerPlugin',
                          action='add', namespace=namespace, message='failed to create plugin.')

    record_custom_event(event_id, 'GatewayConsumerPlugin', 'add', 'completed', namespace)
    return response


@admin_jwt(None)
@uma_enforce('namespace', 'Access.Manage')
@consumers.route('/<string:consumer_id>/plugins/<string:plugin_id>',
                 methods=['PUT'], strict_slashes=False)
def update_consumer_plugin(namespace: str, consumer_id: str, plugin_id: str) -> object:
    event_id = str(uuid.uuid4())
    log = app.logger
    plugin_data = request.get_json()
    cnsr = GatewayConsumerService()
    selectTag = "ns.%s" % namespace
    ns_qualifier = None

    if plugin_data == None:
        log.error("Missing input")
        record_custom_event(event_id, 'GatewayConsumerPlugin', 'update', 'failed', namespace, "Missing input.")
        abort(make_response(jsonify(error="Missing input."), 400))

    transform_tags(plugin_data, namespace, "ns.%s" % namespace)

    if plugin_data['name'] == 'rate-limiting':
        rate_limiting(plugin_data)

    validate_tags(plugin_data, selectTag)

    nsq = traverse_get_ns_qualifier(plugin_data, selectTag)
    if nsq is not None:
        if ns_qualifier is not None and nsq != ns_qualifier:
            abort_early(event_id, 'GatewayConsumerPlugin', namespace, jsonify(error="Validation Errors:\n%s" %
                        ("Conflicting ns qualifiers (%s != %s)" % (ns_qualifier, nsq))))
        ns_qualifier = nsq
        log.info("[%s] CHANGING ns_qualifier %s" % (namespace, ns_qualifier))

    if ns_qualifier is not None:
        selectTag = ns_qualifier

    try:
        response = cnsr.update_consumer_plugin(consumer_id, plugin_id, plugin_data)
    except Exception as ex:
        handle_exceptions(exception=ex, event_id=event_id, type='GatewayConsumerPlugin',
                          action='update', namespace=namespace, message='failed to update plugin.')

    record_custom_event(event_id, 'GatewayConsumerPlugin', 'update', 'completed', namespace)
    return response


@admin_jwt(None)
@uma_enforce('namespace', 'Access.Manage')
@consumers.route('/<string:consumer_id>/plugins/<string:plugin_id>',
                 methods=['DELETE'], strict_slashes=False)
def delete_consumer_plugin(namespace: str, consumer_id: str, plugin_id: str) -> object:
    event_id = str(uuid.uuid4())
    cnsr = GatewayConsumerService()

    try:
        response = cnsr.delete_consumer_plugin(consumer_id, plugin_id)
    except Exception as ex:
        handle_exceptions(exception=ex, event_id=event_id, type='GatewayConsumerPlugin',
                          action='delete', namespace=namespace, message='failed to delete plugin.')

    record_custom_event(event_id, 'GatewayConsumerPlugin', 'delete', 'completed', namespace)
    return response


def handle_exceptions(**kwargs):
    log = app.logger
    if not kwargs['exception'] == None:
        if isinstance(kwargs['exception'], HTTPException):
            log.error("%s. %s" % (kwargs['message'], kwargs['exception']))
        else:
            log.error("%s. %s" % (kwargs['message'], sys.exc_info()[0]))

        traceback.print_exc()
        record_custom_event(kwargs['event_id'], kwargs['type'], kwargs['action'],
                            'failed', kwargs['namespace'], kwargs['message'])
        abort(make_response(jsonify(error=kwargs['message']), 400))


def transform_tags(data, namespace, required_tag):
    log = app.logger
    if 'tags' in data:
        new_tags = []
        for tag in data['tags']:
            new_tags.append(tag)
            # add the base required tag automatically if there is already a qualifying namespace
            if tag.startswith("ns.") and tag.startswith("%s." % required_tag) and required_tag not in data['tags']:
                log.debug("[%s] Adding base tag %s" % (namespace, required_tag))
                new_tags.append(required_tag)
        data['tags'] = new_tags


def validate_tags(data, required_tag):
    # throw an exception if there are invalid tags
    errors = []
    qualifiers = []

    if traverse_has_ns_qualifier(data, required_tag) and traverse_has_ns_tag_only(data, required_tag):
        errors.append(
            "Tags for the namespace can not have a mix of 'ns.<namespace>' and 'ns.<namespace>.<qualifier>'.  Rejecting request.")

    traverse("", errors, data, required_tag, qualifiers)
    if len(qualifiers) > 1:
        errors.append("Too many different qualified namespaces (%s).  Rejecting request." % qualifiers)

    if len(errors) != 0:
        #raise Exception('\n'.join(errors))
        abort(make_response(jsonify(error=errors), 400))


def traverse(source, errors, data, required_tag, qualifiers):

    if 'tags' in data:
        if required_tag not in data['tags']:
            errors.append("missing required tag %s" % (required_tag))
        for tag in data['tags']:
            # if the required_tag is "abc" and the tag starts with "ns."
            # then ns.abc and ns.abc.dev are valid, but anything else is an error
            if tag.startswith("ns.") and tag != required_tag and not tag.startswith("%s." % required_tag):
                errors.append("invalid ns tag %s" % (tag))
            if tag.startswith("%s." % required_tag) and tag not in qualifiers:
                qualifiers.append(tag)
    else:
        errors.append("no tags found")


def traverse_has_ns_qualifier(data, required_tag):
    log = app.logger
    if 'tags' in data:
        for tag in data['tags']:
            if tag.startswith("%s." % required_tag):
                return True
    return False


def traverse_has_ns_tag_only(data, required_tag):
    log = app.logger
    if 'tags' in data:
        if required_tag in data['tags'] and has_ns_qualifier(data['tags'], required_tag) is False:
            return True
    if traverse_has_ns_tag_only(data, required_tag) == True:
        return True
    return False


def has_ns_qualifier(tags, required_tag):
    for tag in tags:
        if tag.startswith("%s." % required_tag):
            return True
    return False


def traverse_get_ns_qualifier(data, required_tag):
    if 'tags' in data:
        for tag in data['tags']:
            if tag.startswith("%s." % required_tag):
                return tag
    return None

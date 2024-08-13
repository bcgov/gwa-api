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

consumers = Blueprint('consumers_v2', 'consumers')


@consumers.route('/<string:consumer_id>/plugins',
                 methods=['POST'], strict_slashes=False)
@admin_jwt(None)
@uma_enforce('namespace', 'Access.Manage')
def create_consumer_plugin(namespace: str, consumer_id: str) -> object:
    event_id = str(uuid.uuid4())
    log = app.logger
    plugin_data = request.get_json()
    cnsr = GatewayConsumerService()
    selectTag = "ns.%s" % namespace

    if plugin_data == None:
        log.error("Missing input")
        record_custom_event(event_id, 'GatewayConsumerPlugin', 'add', 'failed', namespace, "Missing input.")
        abort(make_response(jsonify(error="Missing input."), 400))

    if plugin_data['name'] == 'rate-limiting':
        rate_limiting(plugin_data)

    validate_tags(plugin_data, selectTag)

    try:
        log.debug("[add_consumer_plugin] %s" % consumer_id)
        response = cnsr.add_consumer_plugin(consumer_id, plugin_data)
    except Exception as ex:
        handle_exceptions(exception=ex, event_id=event_id, type='GatewayConsumerPlugin',
                          action='add', namespace=namespace, message='failed to create plugin')

    record_custom_event(event_id, 'GatewayConsumerPlugin', 'add', 'completed', namespace)
    return response


@consumers.route('/<string:consumer_id>/plugins/<string:plugin_id>',
                 methods=['PUT'], strict_slashes=False)
@admin_jwt(None)
@uma_enforce('namespace', 'Access.Manage')
def update_consumer_plugin(namespace: str, consumer_id: str, plugin_id: str) -> object:
    event_id = str(uuid.uuid4())
    log = app.logger
    plugin_data = request.get_json()
    cnsr = GatewayConsumerService()
    selectTag = "ns.%s" % namespace

    if plugin_data == None:
        log.error("Missing input")
        record_custom_event(event_id, 'GatewayConsumerPlugin', 'update', 'failed', namespace, "Missing input.")
        abort(make_response(jsonify(error="Missing input."), 400))

    if plugin_data['name'] == 'rate-limiting':
        rate_limiting(plugin_data)

    validate_tags(plugin_data, selectTag)

    try:
        log.debug("[update_consumer_plugin] %s" % consumer_id)
        verify_tags(consumer_id, plugin_id, selectTag)
        response = cnsr.update_consumer_plugin(consumer_id, plugin_id, plugin_data)
    except Exception as ex:
        handle_exceptions(exception=ex, event_id=event_id, type='GatewayConsumerPlugin',
                          action='update', namespace=namespace, message='failed to update plugin')

    record_custom_event(event_id, 'GatewayConsumerPlugin', 'update', 'completed', namespace)
    return response


@consumers.route('/<string:consumer_id>/plugins/<string:plugin_id>',
                 methods=['DELETE'], strict_slashes=False)
@admin_jwt(None)
@uma_enforce('namespace', 'Access.Manage')
def delete_consumer_plugin(namespace: str, consumer_id: str, plugin_id: str) -> object:
    log = app.logger
    event_id = str(uuid.uuid4())
    selectTag = "ns.%s" % namespace
    cnsr = GatewayConsumerService()
  
    try:
        log.debug("[delete_consumer_plugin] %s %s" % (consumer_id, plugin_id))
        plugin = cnsr.get_consumer_plugin(consumer_id, plugin_id)
        if plugin is None:
          response = {}
        else:
          verify_tags(consumer_id, plugin_id, selectTag)
          response = cnsr.delete_consumer_plugin(consumer_id, plugin_id)
    except Exception as ex:
        handle_exceptions(exception=ex, event_id=event_id, type='GatewayConsumerPlugin',
                          action='delete', namespace=namespace, message='failed to delete plugin')

    record_custom_event(event_id, 'GatewayConsumerPlugin', 'delete', 'completed', namespace)
    return response


def handle_exceptions(**kwargs):
    log = app.logger
    if not kwargs['exception'] == None:
        log.error("handle_exception of %s" % kwargs['exception'])
        if isinstance(kwargs['exception'], HTTPException):
            log.error("%s. (HTTP)" % (kwargs['message']))
        else:
            log.error("%s. %s" % (kwargs['message'], sys.exc_info()[0]))

        # traceback.print_exc()
        record_custom_event(kwargs['event_id'], kwargs['type'], kwargs['action'],
                            'failed', kwargs['namespace'], kwargs['message'])
        abort(make_response(jsonify(error=kwargs['message']), 400))
    else:
        abort(make_response(jsonify(error="unknown"), 400))

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

    if 'tags' in data:
        if required_tag not in data['tags']:
            errors.append("missing required tag %s" % (required_tag))

        if traverse_has_ns_qualifier(data, required_tag):
            errors.append(
                "Tags for the gateway can not have a mix of 'ns.<gateway>' and 'ns.<gateway>.<qualifier>'.  Rejecting request.")
    else:
        errors.append("no tags found")

    if len(errors) != 0:
        abort(make_response(jsonify(error=errors), 400))


def traverse_has_ns_qualifier(data, required_tag):
    log = app.logger
    if 'tags' in data:
        for tag in data['tags']:
            if tag.startswith("%s." % required_tag):
                return True
    return False


def verify_tags(consumer_id: str, plugin_id: str, select_tag):
    cnsr = GatewayConsumerService()
    plugin_tags = cnsr.get_consumer_plugin(consumer_id, plugin_id)['tags']
    if select_tag not in plugin_tags:
        abort(make_response(jsonify(error="The request tag does not match with the plugin tag."), 400))

import sys
import traceback
import uuid
from flask import Blueprint, abort, jsonify, request, make_response, current_app as app
from werkzeug.exceptions import HTTPException
from clients.portal import record_custom_event
from v2.services.gateway_consumers import GatewayConsumerService

consumers = Blueprint('consumers.v2', 'consumers')


@consumers.route('/<string:consumer_id>/plugins',
                 methods=['POST'], strict_slashes=False)
def create_consumer_plugin(namespace: str, consumer_id: str) -> object:
    event_id = str(uuid.uuid4())
    record_custom_event(event_id, 'GatewayConsumerPlugin', 'add', 'received', namespace)
    log = app.logger
    pluginData = request.get_json()
    cnsr = GatewayConsumerService()

    if pluginData == None:
        log.error("Missing input")
        record_custom_event(event_id, 'GatewayConsumerPlugin', 'add', 'failed', namespace, "Missing input.")
        abort(make_response(jsonify(error="Missing input."), 400))
    else:
        try:
            response = cnsr.add_consumer_plugin(consumer_id, pluginData)
        except Exception as ex:
            handle_exceptions(exception=ex, event_id=event_id, type='GatewayConsumerPlugin',
                              action='add', namespace=namespace, message='failed to create plugin.')

    record_custom_event(event_id, 'GatewayConsumerPlugin', 'add', 'completed', namespace)
    return response


@consumers.route('/<string:consumer_id>/plugins/<string:plugin_id>',
                 methods=['PUT'], strict_slashes=False)
def update_consumer_plugin(namespace: str, consumer_id: str, plugin_id: str) -> object:
    event_id = str(uuid.uuid4())
    record_custom_event(event_id, 'GatewayConsumerPlugin', 'update', 'received', namespace)
    log = app.logger
    pluginData = request.get_json()
    cnsr = GatewayConsumerService()

    if pluginData == None:
        log.error("Missing input")
        record_custom_event(event_id, 'GatewayConsumerPlugin', 'update', 'failed', namespace, "Missing input.")
        abort(make_response(jsonify(error="Missing input."), 400))
    else:
        try:
            response = cnsr.update_consumer_plugin(consumer_id, plugin_id, pluginData)
        except Exception as ex:
            handle_exceptions(exception=ex, event_id=event_id, type='GatewayConsumerPlugin',
                              action='update', namespace=namespace, message='failed to update plugin.')

    record_custom_event(event_id, 'GatewayConsumerPlugin', 'update', 'completed', namespace)
    return response


@consumers.route('/<string:consumer_id>/plugins/<string:plugin_id>',
                 methods=['DELETE'], strict_slashes=False)
def delete_consumer_plugin(namespace: str, consumer_id: str, plugin_id: str) -> object:
    event_id = str(uuid.uuid4())
    record_custom_event(event_id, 'GatewayConsumerPlugin', 'delete', 'received', namespace)
    cnsr = GatewayConsumerService()

    try:
        response = cnsr.delete_consumer_plugin(consumer_id, plugin_id)
    except Exception as ex:
        handle_exceptions(exception=ex, event_id=event_id, type='GatewayConsumerPlugin',
                          action='delete', namespace=namespace, message='failed to delete plugin.')

    record_custom_event(event_id, 'GatewayConsumerPlugin', 'delete', 'completed', namespace)
    return response


@consumers.route('/<string:username>',
                 methods=['GET'], strict_slashes=False)
def get_consumer_by_username(namespace: str, username: str) -> object:
    log = app.logger
    cnsr = GatewayConsumerService()

    try:
        response = cnsr.get_consumer(username)
    except:
        traceback.print_exc()
        log.error("failed to fetch consumer. %s" % sys.exc_info()[0])

    return response


@consumers.route('',
                 methods=['POST'], strict_slashes=False)
def create_consumer(namespace: str):
    event_id = str(uuid.uuid4())
    record_custom_event(event_id, 'GatewayConsumer', 'create', 'received', namespace)
    log = app.logger
    consumerData = request.get_json()
    cnsr = GatewayConsumerService()

    if consumerData == None:
        log.error("Missing input")
        record_custom_event(event_id, 'GatewayConsumer', 'create', 'failed', namespace, "Missing input.")
        abort(make_response(jsonify(error="Missing input."), 400))
    else:
        try:
            response = cnsr.create_consumer(consumerData)
        except Exception as ex:
            handle_exceptions(exception=ex, event_id=event_id, type='GatewayConsumer',
                              action='create', namespace=namespace, message='failed to create consumer.')

        record_custom_event(event_id, 'GatewayConsumer', 'create', 'completed', namespace)
        return response


@consumers.route('/<string:username>',
                 methods=['PUT'], strict_slashes=False)
def update_consumer(namespace: str, username: str):
    event_id = str(uuid.uuid4())
    record_custom_event(event_id, 'GatewayConsumer', 'update', 'received', namespace)
    log = app.logger
    consumerData = request.get_json()
    cnsr = GatewayConsumerService()

    if consumerData == None:
        log.error("Missing input")
        record_custom_event(event_id, 'GatewayConsumer', 'update', 'failed', namespace, "Missing input.")
        abort(make_response(jsonify(error="Missing input."), 400))
    else:
        try:
            response = cnsr.update_consumer(username, consumerData)
        except Exception as ex:
            handle_exceptions(exception=ex, event_id=event_id, type='GatewayConsumer',
                              action='update', namespace=namespace, message='failed to update consumer.')

    record_custom_event(event_id, 'GatewayConsumer', 'update', 'completed', namespace)
    return response


@consumers.route('/<string:username>',
                 methods=['DELETE'], strict_slashes=False)
def delete_consumer(namespace: str, username: str) -> object:
    event_id = str(uuid.uuid4())
    record_custom_event(event_id, 'GatewayConsumer', 'delete', 'received', namespace)
    cnsr = GatewayConsumerService()

    try:
        response = cnsr.delete_consumer(username)
    except Exception as ex:
        handle_exceptions(exception=ex, event_id=event_id, type='GatewayConsumer', action='delete',
                          namespace=namespace, message='failed to delete consumer.')

    record_custom_event(event_id, 'GatewayConsumer', 'delete', 'completed', namespace)
    return response


@consumers.route('/<string:consumer_id>/key-auth',
                 methods=['POST'], strict_slashes=False)
def add_consumer_keyauth(namespace: str, consumer_id: str) -> object:
    event_id = str(uuid.uuid4())
    record_custom_event(event_id, 'GatewayConsumerKeyAuth', 'add', 'received', namespace)
    log = app.logger
    keyauth_data = request.get_json()
    cnsr = GatewayConsumerService()

    if keyauth_data == None:
        log.error("Missing input")
        record_custom_event(event_id, 'GatewayConsumerKeyAuth', 'add', 'failed', namespace, "Missing input.")
        abort(make_response(jsonify(error="Missing input."), 400))
    else:
        try:
            response = cnsr.add_keyauth_to_consumer(consumer_id, keyauth_data)
        except Exception as ex:
            handle_exceptions(exception=ex, event_id=event_id, type='GatewayConsumerKeyAuth',
                              action='add', namespace=namespace, message='failed to add keyauth to consumer.')

    record_custom_event(event_id, 'GatewayConsumerKeyAuth', 'add', 'completed', namespace)
    return response


@consumers.route('/<string:consumer_id>/key-auth/<string:keyauth_id>',
                 methods=['PUT'], strict_slashes=False)
def generate_consumer_keyauth_key(namespace: str, consumer_id: str, keyauth_id: str):
    event_id = str(uuid.uuid4())
    record_custom_event(event_id, 'GatewayConsumerKeyAuth', 'create', 'received', namespace)
    log = app.logger
    key_data = request.get_json()
    cnsr = GatewayConsumerService()

    if key_data == None:
        log.error("Missing input")
        record_custom_event(event_id, 'GatewayConsumerKeyAuth', 'update', 'failed', namespace, "Missing input.")
        abort(make_response(jsonify(error="Missing input."), 400))
    else:
        try:
            response = cnsr.gen_key_for_consumer_keyauth(consumer_id, keyauth_id, key_data)
        except Exception as ex:
            handle_exceptions(exception=ex, event_id=event_id, type='GatewayConsumerKeyAuth', action='update',
                              namespace=namespace, message='failed to generate key for consumer keyauth.')

    record_custom_event(event_id, 'GatewayConsumerKeyAuth', 'update', 'completed', namespace)
    return response


@consumers.route('',
                 methods=['GET'], strict_slashes=False)
def get_consumers_by_namespace(namespace: str) -> object:
    log = app.logger

    cnsr = GatewayConsumerService()
    try:
        response = cnsr.get_consumers_by_ns(namespace)
    except:
        traceback.print_exc()
        log.error("failed to fetch consumers. %s" % sys.exc_info()[0])

    return response


@consumers.route('/<string:consumer_id>/acls',
                 methods=['GET'], strict_slashes=False)
def get_consumer_acl_by_namespace(namespace: str, consumer_id: str) -> object:
    log = app.logger

    cnsr = GatewayConsumerService()
    try:
        response = cnsr.get_consumer_acl_by_ns(consumer_id, namespace)
    except:
        traceback.print_exc()
        log.error("failed to fetch consumer ACL. %s" % sys.exc_info()[0])

    return response


@consumers.route('/<string:consumer_id>/acls',
                 methods=['POST'], strict_slashes=False)
def assign_consumer_acl(namespace: str, consumer_id: str) -> object:
    event_id = str(uuid.uuid4())
    record_custom_event(event_id, 'GatewayConsumerACL', 'add', 'received', namespace)
    log = app.logger
    acl_data = request.get_json()
    cnsr = GatewayConsumerService()

    if acl_data == None:
        log.error("Missing input")
        record_custom_event(event_id, 'GatewayConsumerACL', 'add', 'failed', namespace, "Missing input.")
        abort(make_response(jsonify(error="Missing input."), 400))
    else:
        try:
            response = cnsr.add_consumer_acl(consumer_id, acl_data)
        except Exception as ex:
            handle_exceptions(exception=ex, event_id=event_id, type='GatewayConsumerACL',
                              action='add', namespace=namespace, message='failed to add consumer ACL.')

    record_custom_event(event_id, 'GatewayConsumerACL', 'add', 'completed', namespace)
    return response


@consumers.route('/<string:consumer_id>/acls/<string:acl_id>',
                 methods=['DELETE'], strict_slashes=False)
def remove_consumer_acl(namespace: str, consumer_id: str, acl_id: str) -> object:
    event_id = str(uuid.uuid4())
    record_custom_event(event_id, 'GatewayConsumerACL', 'delete', 'received', namespace)
    cnsr = GatewayConsumerService()

    try:
        response = cnsr.delete_consumer_acl(consumer_id, acl_id)
    except Exception as ex:
        handle_exceptions(exception=ex, event_id=event_id, type='GatewayConsumerACL', action='delete',
                          namespace=namespace, message='failed to delete consumer ACL.')

    record_custom_event(event_id, 'GatewayConsumerACL', 'delete', 'completed', namespace)
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

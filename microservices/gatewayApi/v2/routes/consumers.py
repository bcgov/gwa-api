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
def create_gateway_consumer_plugin(namespace: str, consumer_id: str) -> object:
    event_id = str(uuid.uuid4())
    record_custom_event(event_id, 'GatewayConsumerPlugin', 'add','received', namespace)
    response = None
    log = app.logger

    pluginData = request.get_json()

    cnsr = GatewayConsumerService()

    if pluginData == None:
        log.error("Missing input")
        record_custom_event(event_id, 'GatewayConsumerPlugin', 'add', 'failed', namespace, "Missing input.")
        abort(make_response(jsonify(error="Missing input."), 400))
    else:
        try:
            response = cnsr.add_plugin_to_consumer(consumer_id, pluginData)
        except HTTPException as ex:
            traceback.print_exc()
            log.error("Error adding consumer plugin. %s" % ex)
            record_custom_event(event_id, 'GatewayConsumerPlugin', 'add', 'failed', namespace, "failed to add plugin.")
            abort(make_response(jsonify(error="failed to add plugin"), 400))
        except:
            traceback.print_exc()
            log.error("Error adding plugin to customer. %s" % sys.exc_info()[0])
            record_custom_event(event_id, 'GatewayConsumerPlugin', 'add', 'failed', namespace, "failed to add plugin.")
            abort(make_response(jsonify(error="failed to add plugin"), 400))
        
        if "http_error" in response:
            record_custom_event(event_id, 'GatewayConsumerPlugin', 'add', 'failed', namespace, response['message'])
            abort(make_response(response, response["http_error"]))
        record_custom_event(event_id, 'GatewayConsumerPlugin', 'add', 'completed', namespace)
        return response

@consumers.route('/<string:consumer_id>/plugins/<string:plugin_id>',
           methods=['PUT'], strict_slashes=False)
def update_gateway_consumer_plugin(namespace: str, consumer_id: str, plugin_id: str) -> object:
    event_id = str(uuid.uuid4())
    record_custom_event(event_id, 'GatewayConsumerPlugin', 'update', 'received', namespace)
    response = None
    log = app.logger

    pluginData = request.get_json()

    cnsr = GatewayConsumerService()

    if pluginData == None:
        log.error("Missing input")
        record_custom_event(event_id, 'GatewayConsumerPlugin', 'update', 'failed', namespace, "Missing input.")
        abort(make_response(jsonify(error="Missing input."), 400))
    else:
        try:
            response = cnsr.update_plugin_to_consumer(consumer_id, plugin_id, pluginData)
        except HTTPException as ex:
            traceback.print_exc()
            log.error("Error updating consumer plugin. %s" % ex)
            record_custom_event(event_id, 'GatewayConsumerPlugin', 'update', 'failed', namespace, "failed to update plugin.")
            abort(make_response(jsonify(error="failed to update plugin"), 400))
        except:
            traceback.print_exc()
            log.error("Error updating plugin to customer. %s" % sys.exc_info()[0])
            record_custom_event(event_id, 'GatewayConsumerPlugin', 'update', 'failed', namespace, "failed to update plugin.")
            abort(make_response(jsonify(error="failed to update plugin"), 400))

        record_custom_event(event_id, 'GatewayConsumerPlugin', 'update', 'completed', namespace)
        return response

@consumers.route('/<string:consumer_id>/plugins/<string:plugin_id>',
           methods=['DELETE'], strict_slashes=False)
def delete_gateway_consumer_plugin(namespace: str, consumer_id: str, plugin_id: str) -> object:
    event_id = str(uuid.uuid4())
    record_custom_event(event_id, 'GatewayConsumerPlugin', 'delete', 'received', namespace)
    response = None
    log = app.logger

    cnsr = GatewayConsumerService()

    try:
        response = cnsr.delete_plugin_to_consumer(consumer_id, plugin_id)
    except HTTPException as ex:
        traceback.print_exc()
        log.error("Error deleting consumer plugin. %s" % ex)
        record_custom_event(event_id, 'GatewayConsumerPlugin', 'delete', 'failed', namespace, "failed to delete plugin.")
        abort(make_response(jsonify(error="failed to delete plugin"), 400))
    except:
        traceback.print_exc()
        log.error("failed to delete plugin. %s" % sys.exc_info()[0])
        record_custom_event(event_id, 'GatewayConsumerPlugin', 'delete', 'failed', namespace, "failed to delete plugin.")
        abort(make_response(jsonify(error="failed to delete plugin"), 400))

    record_custom_event(event_id, 'GatewayConsumerPlugin', 'delete', 'completed', namespace)
    return response

@consumers.route('/<string:username>',
           methods=['GET'], strict_slashes=False)
def get_consumer_by_username(username: str) -> object:
    log = app.logger


    cnsr = GatewayConsumerService()
    try:
        response = cnsr.get_gateway_consumer(username)
    except:
        traceback.print_exc()
        log.error("Error retrieving customer. %s" % sys.exc_info()[0])
    
    return response

import os
import logging
import traceback
from clients.namespace import NamespaceService
import traceback

logger = logging.getLogger(__name__)

def transform_data_by_ns(data):
    ns_svc = NamespaceService()
    try:
        ns_dict = {}
        ns_attr_dict = {}
        for route_obj in data:
            select_tag = get_select_tag(route_obj['tags'])
            namespace = select_tag.split(".")[1]

            if namespace not in ns_dict:
                ns_dict[namespace] = []
                ns_attr_dict[namespace] = ns_svc.get_namespace_attributes(namespace)

            logger.debug("%s - %s" % (namespace, ns_attr_dict[namespace].get('perm-data-plane', [''])))

            # check if namespace has data plane attribute
            if ns_attr_dict[namespace].get('perm-data-plane', [''])[0] == os.getenv('DATA_PLANE'):
                session_cookie_enabled = False
                if 'aps.route.session.cookie.enabled' in route_obj['tags']:
                    session_cookie_enabled = True
                for host in route_obj['hosts']:
                    name = 'wild-%s-%s' % (select_tag.replace(".", "-"), host)
                    ns_dict[namespace].append({"name": name, "selectTag": select_tag, "host": host,
                                               "sessionCookieEnabled": session_cookie_enabled,
                                               "dataPlane": os.getenv('DATA_PLANE')})
        return ns_dict
    except Exception as err:
        traceback.print_exc()
        logger.error("Error transforming data. %s" % str(err))

def get_select_tag(tags):
    required_tag = None
    for tag in tags:
        if tag.startswith("ns."):
            required_tag = tag
            if len(tag.split(".")) > 2:
                required_tag = tag
                break
    return required_tag

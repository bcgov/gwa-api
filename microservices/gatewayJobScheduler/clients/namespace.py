from clients.keycloak import admin_api
from keycloak.exceptions import KeycloakGetError

class NamespaceService:

    def __init__(self):
        self.keycloak_admin = admin_api()

    def get_namespace_attributes(self, namespace):
        try:
            ns_group_summary = self.keycloak_admin.get_group_by_path(
                path="/%s/%s" % ('ns', namespace))
        except KeycloakGetError:
            return {}
        if ns_group_summary is not None:
            try:
                ns_group = self.keycloak_admin.get_group(ns_group_summary['id'])
            except KeycloakGetError:
                return {}
            attrs = ns_group.get('attributes', {})
            return attrs
        return {}

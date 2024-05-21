from clients.keycloak import admin_api

class NamespaceService:

    def __init__(self):
        self.keycloak_admin = admin_api()

    def get_namespace_attributes(self, namespace):
        ns_group_summary = self.keycloak_admin.get_group_by_path(
            path="/%s/%s" % ('ns', namespace), search_in_subgroups=True)
        if ns_group_summary is not None:
            ns_group = self.keycloak_admin.get_group(ns_group_summary['id'])
            attrs = ns_group['attributes']
            return attrs
        # returning empty dict when namespace or group not found in keycloak
        return {}

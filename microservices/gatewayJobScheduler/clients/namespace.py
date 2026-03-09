class NamespaceService:

    def __init__(self, keycloak_admin):
        self.keycloak_admin = keycloak_admin

    def get_namespace_attributes(self, namespace):
        ns_group_summary = self.keycloak_admin.get_group_by_path(
            path="/%s/%s" % ('ns', namespace))
        if ns_group_summary is not None:
            ns_group = self.keycloak_admin.get_group(ns_group_summary['id'])
            attrs = ns_group.get('attributes', {})
            return attrs
        return {}

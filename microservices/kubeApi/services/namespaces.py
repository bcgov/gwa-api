
from auth.authz import users_group_root, admins_group_root

from clients.keycloak import admin_api


class NamespaceService:

    def __init__(self):
        self.keycloak_admin = admin_api()
    std_attrs = []
    priv_attrs = ['perm-domains', 'perm-protected-ns']

    def get_namespace(self, namespace):
        group_base_path = get_base_group_path('viewer')
        ns_group_summary = self.keycloak_admin.get_group_by_path(
            path="%s/%s" % (group_base_path, namespace), search_in_subgroups=True)
        ns_group = self.keycloak_admin.get_group(ns_group_summary['id'])
        return ns_group

    def get_namespace_attributes(self, namespace):
        ns_group = self.get_namespace(namespace)
        attrs = ns_group['attributes']

        # Convert booleans
        for booly in self.std_attrs + self.priv_attrs:
            if booly in attrs and attrs[booly] == 'true':
                attrs[booly] = True
            if booly in attrs and attrs[booly] == 'false':
                attrs[booly] = False
        return NamespaceAttributes(attrs)


def get_base_group_name(role_name):
    if role_name == "viewer":
        return users_group_root()
    elif role_name == "admin":
        return admins_group_root()
    else:
        raise Exception("Illegal Argument - Role %s" % role_name)


def get_base_group_path(role_name):
    return "/%s" % get_base_group_name(role_name)


class NamespaceAttributes:
    def __init__(self, attrs):
        self.attrs = attrs

    def get(self, name, default):
        if name in self.attrs:
            return self.attrs[name]
        else:
            return default

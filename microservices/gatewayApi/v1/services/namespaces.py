from v1.auth.auth import users_group_root, admins_group_root
from flask import current_app as app
from v1.auth.auth import admin_jwt
from clients.keycloak import admin_api


class NamespaceService:
    std_attrs = []
    priv_attrs = ['perm-domains', 'perm-protected-ns']

    def __init__(self):
        self.keycloak_admin = admin_api()

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

    def create_or_get_ns(self, namespace, initial_username):
        log = app.logger
        payload = {
            "name": namespace
        }

        for role_name in ['viewer', 'admin']:

            group_base_path = get_base_group_path(role_name)
            parent_group = self.keycloak_admin.get_group_by_path(group_base_path)
            if parent_group is None:
                self.keycloak_admin.create_group({"name": get_base_group_name(role_name)})
                parent_group = self.keycloak_admin.get_group_by_path(group_base_path)

            response = self.keycloak_admin.create_group(payload, parent=parent_group['id'])
            log.debug("[%s] Group %s/%s created!" % (namespace, group_base_path, namespace))

            new_users_group_id = response['id']

            if initial_username is not None:
                user_id = self.keycloak_admin.get_user_id(initial_username)
                log.debug("[%s] ADDING user %s TO %s" % (namespace, initial_username, group_base_path))
                self.keycloak_admin.group_user_add(user_id, new_users_group_id)

    ## Example: { 'id': '00516e2c-ade3-47c3-aad9-703deef00524', 'name': 'platform', 'path': '/ns/platform', 'attributes': {'perm-domains': ['apps.ca']}, 'realmRoles': [], 'clientRoles':{}, 'subGroups': [], 'access': {'view': True, 'manage': True, 'manageMembership': True}}
    def update_ns_attributes(self, ns_group, params):
        self.update_attributes(self.std_attrs, ns_group, params)

        if len(set(self.priv_attrs) & set(params.keys())) > 0:
            self.update_ns_priv_attributes(ns_group, params)

        self.keycloak_admin.update_group(ns_group['id'], ns_group)

    @admin_jwt('Namespace.Admin')
    def update_ns_priv_attributes(self, ns_group, params):
        self.update_attributes(self.priv_attrs, ns_group, params)

        self.keycloak_admin.update_group(ns_group['id'], ns_group)

    def update_attributes(self, attrs, ns_group, params):
        log = app.logger
        ns_attributes = ns_group['attributes']

        for attr in attrs:
            if attr in params:
                log.debug("[%s] Updating attribute  %s -> %s" % (ns_group['name'], attr, params[attr]))
                if type(params[attr]) == list:
                    ns_attributes[attr] = params[attr]
                else:
                    ns_attributes[attr] = [params[attr]]


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

    def getAttrs(self):
        return self.attrs

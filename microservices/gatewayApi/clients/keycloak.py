
from flask import current_app as app
from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
from keycloak.exceptions import KeycloakGetError

#     conf = app.config['keycloak']

def admin_api(conf):

    keycloak_connection = KeycloakOpenIDConnection(server_url=conf['serverUrl'],
        username=conf['username'],
        password=conf['password'],
        realm_name=conf['realm'],
        client_id=conf['clientId'],
        user_realm_name=conf['userRealm'],
        verify=True)


    keycloak_admin = KeycloakAdmin(connection=keycloak_connection)
    return keycloak_admin


def safe_get_group_by_path(keycloak_admin, path, **kwargs):
    """Returns None when a group path doesn't exist, regardless of
    python-keycloak version or Keycloak server version."""
    try:
        result = keycloak_admin.get_group_by_path(path, **kwargs)
        if isinstance(result, dict) and "error" in result:
            return None
        return result
    except KeycloakGetError as e:
        if e.response_code == 404:
            return None
        raise
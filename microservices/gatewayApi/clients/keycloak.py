
from flask import current_app as app
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakGetError

def admin_api():
    conf = app.config['keycloak']

    keycloak_admin = KeycloakAdmin(server_url=conf['serverUrl'],
        username=conf['username'],
        password=conf['password'],
        realm_name=conf['realm'],
        client_id=conf['clientId'],
        user_realm_name=conf['userRealm'],
        verify=True)
    return keycloak_admin

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
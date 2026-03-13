from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
import os

def admin_api():

    keycloak_connection = KeycloakOpenIDConnection(
        server_url=os.getenv('KC_SERVER_URL'),
        username=os.getenv('KC_USERNAME'),
        password=os.getenv('KC_PASSWORD'),
        realm_name=os.getenv('KC_REALM'),
        client_id=os.getenv('KC_CLIENT_ID'),
        user_realm_name=os.getenv('KC_USER_REALM'),
        verify=True)

    keycloak_admin = KeycloakAdmin(connection=keycloak_connection)
    return keycloak_admin

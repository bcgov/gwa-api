from keycloak import KeycloakAdmin
import os

def admin_api():

    keycloak_admin = KeycloakAdmin(server_url=os.getenv('KC_SERVER_URL'),
                                   username=os.getenv('KC_USERNAME'),
                                   password=os.getenv('KC_PASSWORD'),
                                   realm_name=os.getenv('KC_REALM'),
                                   client_id=os.getenv('KC_CLIENT_ID'),
                                   user_realm_name=os.getenv('KC_USER_REALM'),
                                   verify=True)
    return keycloak_admin

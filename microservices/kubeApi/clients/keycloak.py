from keycloak import KeycloakAdmin
from config import settings


def admin_api():
    print(str(settings))
    return KeycloakAdmin(server_url=settings.keycloak["serverUrl"],
                         username=settings.keycloak["username"],
                         password=settings.keycloak["password"],
                         realm_name=settings.keycloak["realm"],
                         client_id=settings.keycloak["clientId"],
                         user_realm_name=settings.keycloak["userRealm"],
                         verify=True)

import logging

from clients.keycloak import admin_api
from keycloak.exceptions import KeycloakGetError

logger = logging.getLogger(__name__)


class NamespaceService:

    def __init__(self):
        self.keycloak_admin = admin_api()

    def get_namespace_attributes(self, namespace):
        try:
            ns_group_summary = self.keycloak_admin.get_group_by_path(
                path="/%s/%s" % ('ns', namespace))
        except KeycloakGetError as e:
            logger.warning(
                "NamespaceService: Keycloak error fetching group path for namespace %s: %s",
                namespace, e, exc_info=True
            )
            return {}
        except Exception as e:
            logger.error(
                "NamespaceService: Unexpected error fetching group path for namespace %s: %s",
                namespace, e, exc_info=True
            )
            raise
        if ns_group_summary is not None:
            try:
                ns_group = self.keycloak_admin.get_group(ns_group_summary['id'])
            except KeycloakGetError as e:
                logger.warning(
                    "NamespaceService: Keycloak error fetching group %s for namespace %s: %s",
                    ns_group_summary['id'], namespace, e, exc_info=True
                )
                return {}
            except Exception as e:
                logger.error(
                    "NamespaceService: Unexpected error fetching group for namespace %s: %s",
                    namespace, e, exc_info=True
                )
                raise
            attrs = ns_group.get('attributes', {})
            return attrs
        return {}

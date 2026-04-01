
import re
from urllib.parse import urlparse

namespace_validation_rule='^[a-z][a-z0-9-]{4,14}$'

host_validation_rule='[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*'

def namespace_valid(input_string):
    regex = re.compile(namespace_validation_rule)
    match = regex.match(str(input_string))
    return bool(match is not None)

def host_valid(input_string):
    return True
    # regex = re.compile(host_validation_rule)
    # match = regex.match(str(input_string))
    # return bool(match is not None)

def validate_upstream(yaml, ns_attributes, protected_kube_namespaces, do_validate_upstreams: bool = False):
    errors = []

    perm_upstreams = ns_attributes.get('perm-upstreams', [])

    allow_protected_ns = ns_attributes.get('perm-protected-ns', ['deny'])[0] == 'allow'

    # A service host must not contain a list of protected
    if 'services' in yaml:
        for service in yaml['services']:
            if 'url' in service:
                try:
                    u = urlparse(service["url"])
                    if u.hostname is None:
                        errors.append("service upstream has invalid url specified (e1)")
                    else:
                        validate_upstream_host(u.hostname, errors, allow_protected_ns, protected_kube_namespaces, do_validate_upstreams, perm_upstreams)
                except Exception as e:
                    errors.append("service upstream has invalid url specified (e2)")

            if 'host' in service:
                host = service["host"]
                validate_upstream_host(host, errors, allow_protected_ns, protected_kube_namespaces, do_validate_upstreams, perm_upstreams)

    if len(errors) != 0:
        raise Exception('\n'.join(errors))


def validate_upstream_host(_host, errors, allow_protected_ns, protected_kube_namespaces, do_validate_upstreams, perm_upstreams):
    host = _host.lower()

    restricted = ['localhost', '127.0.0.1', '0.0.0.0']

    if host in restricted:
        errors.append("service upstream is invalid (e1)")
    elif host.endswith('.svc'):
        partials = host.split('.')
        # get the namespace, and make sure it is not in the protected_kube_namespaces list
        if len(partials) != 3:
            errors.append("service upstream is invalid (e2)")
        elif partials[1] in protected_kube_namespaces and allow_protected_ns is False:
            errors.append("service upstream is invalid (e3)")
        elif do_validate_upstreams and (partials[1] in perm_upstreams) is False:
            errors.append("service upstream is invalid (e6)")
    elif host.endswith('.svc.cluster.local'):
        partials = host.split('.')
        # get the namespace, and make sure it is not in the protected_kube_namespaces list
        if len(partials) != 5:
            errors.append("service upstream is invalid (e4)")
        elif partials[1] in protected_kube_namespaces and allow_protected_ns is False:
            errors.append("service upstream is invalid (e5)")
        elif do_validate_upstreams and (partials[1] in perm_upstreams) is False:
            errors.append("service upstream is invalid (e6)")
    elif do_validate_upstreams and (host in perm_upstreams) is False:
        errors.append("service upstream is invalid (e6)")

def validate_route_paths(yaml, ns_attributes, do_validate_route_paths: bool = False):
    if not do_validate_route_paths:
        return

    errors = []
    perm_route_paths = ns_attributes.get('perm-route-paths', [])

    for service in yaml.get('services', []):
        for route in service.get('routes', []):
            for path in route.get('paths', []):
                validate_route_path(path, errors, perm_route_paths)

    if len(errors) != 0:
        raise Exception('\n'.join(errors))


def validate_route_paths(yaml, ns_attributes, do_validate_route_paths: bool = False):
    if not do_validate_route_paths:
        return

    errors = []
    perm_route_paths = ns_attributes.get('perm-route-paths', [])

    for service in yaml.get('services', []):
        service_name = service.get('name', '<unknown-service>')

        for route in service.get('routes', []):
            route_name = route.get('name', '<unknown-route>')

            for path in route.get('paths', []):
                validate_route_path(
                    path,
                    service_name,
                    route_name,
                    errors,
                    perm_route_paths
                )

    if errors:
        raise Exception('\n'.join(errors))


def validate_route_path(_path, service_name, route_name, errors, perm_route_paths):
    display_path = _path if _path else "<empty>"

    if not _path:
        errors.append(
            f"service.{service_name}.route.{route_name} "
            f"path '{display_path}' does not match any allowed paths (e7)"
        )
        return

    if not perm_route_paths:
        errors.append(
            f"service.{service_name}.route.{route_name} "
            f"path '{display_path}' does not match any allowed paths (e7)"
        )
        return

    path = _path if _path.startswith("/") else f"/{_path}"

    for allowed in perm_route_paths:
        if not allowed:
            continue

        allowed_path = allowed if allowed.startswith("/") else f"/{allowed}"

        if path == allowed_path or path.startswith(f"{allowed_path}/"):
            return

    errors.append(
        f"service.{service_name}.route.{route_name} "
        f"path '{path}' does not match any allowed paths (e7)"
    )

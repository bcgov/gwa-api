from patterns.eval import evaluate_pattern

class GatewayConfigPattern:
    def __init__(self, pattern: str, gateway: str, service_name: str, upstream_uri: str,
                 host: str, provider_resource_locator: str):
        self.pattern = pattern
        self.gateway = gateway
        self.service_name = service_name
        self.upstream_uri = upstream_uri
        self.host = host
        self.provider_resource_locator = provider_resource_locator

    def get_config_file(self):
        context = {
            'host': self.host,
            'gateway': self.gateway,
            'service_name': self.service_name,
            'upstream_uri': self.upstream_uri,
            'provider_resource_locator': self.provider_resource_locator
        }
        
        return evaluate_pattern(self.pattern, context)

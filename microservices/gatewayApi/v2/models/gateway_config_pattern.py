from patterns.eval import evaluate_pattern
# Example: Initializing GatewayConfigPattern from a JSON object
# import json
# json_data = '''
# {
#     "pattern": "some-pattern",
#     "gateway": "main-gateway",
#     "service_name": "my-service",
#     "upstream_uri": "http://upstream.example.com",
#     "route_host": "api.example.com",
#     "route_path": "/v1/resource",
#     "mtls_allow_list": ["CN=abc"]
# }
# '''
# data = json.loads(json_data)
# obj = GatewayConfigPattern(**data)
class GatewayConfigPattern:
    def __init__(self, pattern: str, service_name: str, upstream_uri: str,
           route_host: str, route_path: str, mtls_allow_list: str, gateway: str = None):
      self.pattern = pattern
      self.gateway = gateway
      self.service_name = service_name
      self.upstream_uri = upstream_uri
      self.route_host = route_host
      self.route_path = route_path
      self.mtls_allow_list = mtls_allow_list

    def get_config_file(self):
        context = {
            'gateway': self.gateway,
            'service_name': self.service_name,
            'upstream_uri': self.upstream_uri,
            'route_host': self.route_host,
            'route_path': self.route_path,
            'mtls_allow_list': self.mtls_allow_list,
        }
        
        return evaluate_pattern(self.pattern, context)

    def set_gateway(self, gateway: str):
        self.gateway = gateway
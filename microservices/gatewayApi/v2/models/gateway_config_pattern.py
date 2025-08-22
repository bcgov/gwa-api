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
    def __init__(self, pattern: str, service_name: str, upstream_uri: str, consumer_client_id: str,
           route_host: str, route_path: str, mtls_allow_list: str, ns_qualifer: str, openid_issuer, openid_audience, openid_scope, gateway: str = None):
      self.pattern = pattern
      self.gateway = gateway
      self.ns_qualifier = ns_qualifer
      self.consumer_client_id = consumer_client_id
      self.service_name = service_name
      self.upstream_uri = upstream_uri
      self.route_host = route_host
      self.route_path = route_path
      self.mtls_allow_list = mtls_allow_list
      self.openid_audience = openid_audience
      self.openid_issuer = openid_issuer
      self.openid_scope = openid_scope

    def get_config_file(self):
        context = {
            'gateway': self.gateway,
            'ns_qualifier': self.ns_qualifier,
            'consumer_client_id': self.consumer_client_id,
            'service_name': self.service_name,
            'upstream_uri': self.upstream_uri,
            'route_host': self.route_host,
            'route_path': self.route_path,
            'mtls_allow_list': self.mtls_allow_list,
            'openid_issuer': self.openid_issuer,
            'openid_audience': self.openid_audience,
            'openid_scope': self.openid_scope,
        }
        
        return evaluate_pattern(self.pattern, context)

    def set_gateway(self, gateway: str):
        self.gateway = gateway
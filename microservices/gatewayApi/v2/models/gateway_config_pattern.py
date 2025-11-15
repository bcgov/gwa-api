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
    def __init__(self, document: dict):
      self.document = document
      self.gateway = None

    def get_config_file(self):
        context = self.document.copy()
        pattern = context["pattern"]
        if self.gateway:
            context["gateway"] = self.gateway
        return evaluate_pattern(pattern, context)

    def set_gateway(self, gateway: str):
        self.gateway = gateway
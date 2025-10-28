from patterns.sdx.access_point_r1 import eval_access_point_pattern
from patterns.sdx.service_r1 import eval_service_pattern
from patterns.sdx.service_pub_r1 import eval_service_pub_pattern
from patterns.sdx.service_mtls_r1 import eval_service_mtls_pattern
from patterns.sdx.p2p_provider_r1 import eval_p2p_provider_pattern

from patterns.sdx.p2p_provider_pub_r1 import eval_p2p_provider_pub_pattern
from patterns.sdx.p2p_consumer_r1 import eval_p2p_consumer_pattern
from patterns.sdx.p2p_consumer_pub_r1 import eval_p2p_consumer_pub_pattern

def evaluate_pattern(pattern, context):
    """
    Evaluates a pattern against the provided context.
    """
    if pattern == 'sdx-access-point-r1':
        return eval_access_point_pattern(context)
    elif pattern == 'sdx-service-r1':
        return eval_service_pattern(context)
    elif pattern == 'sdx-service-mtls-r1':
        return eval_service_mtls_pattern(context)
    elif pattern == 'sdx-service-pub-r1':
        return eval_service_pub_pattern(context)
    elif pattern == 'sdx-p2p-provider-r1':
        return eval_p2p_provider_pattern(context)
    elif pattern == 'sdx-p2p-provider-pub-r1':
        return eval_p2p_provider_pub_pattern(context)
    elif pattern == 'sdx-p2p-consumer-r1':
        return eval_p2p_consumer_pattern(context)
    elif pattern == 'sdx-p2p-consumer-pub-r1':
        return eval_p2p_consumer_pub_pattern(context)
    else:
        raise ValueError(f"Unknown pattern: {pattern}")
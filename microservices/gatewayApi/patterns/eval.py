from patterns.sdx.service_r1 import  eval_service_pattern;
from patterns.sdx.service_pub_r1 import  eval_service_pub_pattern;
from patterns.sdx.p2p_service_r1 import  eval_p2p_service_pattern;
from patterns.sdx.application_r1 import eval_application_pattern
from patterns.sdx.access_point_r1 import eval_access_point_pattern

def evaluate_pattern(pattern, context):
    """
    Evaluates a pattern against the provided context.
    
    """
    if pattern == 'sdx-service-r1':
        return eval_service_pattern(context)
    elif pattern == 'sdx-service-pub-r1':
        return eval_service_pub_pattern(context)
    elif pattern == 'sdx-p2p-service-r1':
        return eval_p2p_service_pattern(context)
    elif pattern == 'sdx-application-r1':
        return eval_application_pattern(context)
    elif pattern == 'sdx-access-point-r1':
        return eval_access_point_pattern(context)
    else:
        raise ValueError(f"Unknown pattern: {pattern}")
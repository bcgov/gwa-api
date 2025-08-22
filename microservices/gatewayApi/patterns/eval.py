from patterns.sdx.service_r1 import  eval_service_pattern;
from patterns.sdx.application_r1 import eval_application_pattern

def evaluate_pattern(pattern, context):
    """
    Evaluates a pattern against the provided context.
    
    """
    if pattern == 'sdx-service-r1':
        return eval_service_pattern(context)
    elif pattern == 'sdx-application-r1':
        return eval_application_pattern(context)
    else:
        raise ValueError(f"Unknown pattern: {pattern}")
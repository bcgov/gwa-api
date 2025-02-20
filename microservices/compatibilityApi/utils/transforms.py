import copy
import re

def convert_to_kong2(kong3_config: dict) -> dict | None:
    """Convert Kong 3.x config back to Kong 2.x format"""
    if not kong3_config:
        return None
        
    # Deep copy to avoid modifying original
    kong2_config = copy.deepcopy(kong3_config)
    
    # Set format version to 2.1
    kong2_config["_format_version"] = "2.1"
    
    # Remove tildes from paths
    if "services" in kong2_config:
        for service in kong2_config["services"]:
            if "routes" in service:
                for route in service["routes"]:
                    if "paths" in route:
                        route["paths"] = [
                            path[1:] if path.startswith("~") else path 
                            for path in route["paths"]
                        ]
    
    return kong2_config

# Compile the regex pattern
path_regex_pattern = re.compile(r'[^a-zA-Z0-9._~/%-]')

def is_path_regex_like(path):
    """
    Checks if a path string contains a regex pattern.
    
    Args:
    path (str): The path string to check.
    
    Returns:
    bool: True if the path contains a regex pattern, False otherwise.
    """
    return bool(path_regex_pattern.search(path))

def tag_routes(config: dict) -> tuple[dict, list[str]]:
    """
    Tags routes based on Kong 3.x compatibility of their paths
    
    Args:
        config: Kong configuration dictionary
        
    Returns:
        tuple containing:
        - tagged config dict
        - list of route names that failed Kong 3 compatibility
    
    Adds:
    - 'kong3=pass' tag if path contains regex and starts with ~
    - 'kong3=fail' tag if path contains regex but doesn't start with ~
    """
    if not config or "services" not in config:
        return config, []
        
    # Deep copy to avoid modifying original
    tagged_config = copy.deepcopy(config)
    failed_routes = []
    
    for service in tagged_config["services"]:
        if "routes" in service:
            for route in service["routes"]:
                # Initialize or clean existing tags
                if "tags" not in route:
                    route["tags"] = []
                else:
                    # Remove any existing kong3 tags
                    route["tags"] = [
                        tag for tag in route["tags"] 
                        if not tag.startswith("kong3=")
                    ]
                
                if "paths" in route:
                    has_regex = any(is_path_regex_like(path) for path in route["paths"])
                    if has_regex:
                        # Check if all regex paths start with tilde
                        all_tildes = all(
                            not is_path_regex_like(path) or path.startswith("~") 
                            for path in route["paths"]
                        )
                        
                        # Add appropriate tag
                        new_tag = "kong3=pass" if all_tildes else "kong3=fail"
                        route["tags"].append(new_tag)
                        
                        # Track failed routes
                        if not all_tildes and "name" in route:
                            failed_routes.append(route["name"])
    
    return tagged_config, failed_routes


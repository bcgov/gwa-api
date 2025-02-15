import tempfile
import os
from subprocess import Popen, PIPE, STDOUT
import yaml
from fastapi.logger import logger

def validate_config(config: dict) -> tuple[bool, str]:
    """
    Validates Kong configuration using deck
    Returns (is_valid, message)
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = os.path.join(temp_dir, "config.yaml")
        
        # Write config to temporary file
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Run deck validate
        args = [
            "deck", "file", "validate", 
            config_file
        ]
        logger.debug("Running %s", args)
        
        process = Popen(args, stdout=PIPE, stderr=STDOUT)
        out, _ = process.communicate()
        
        output = out.decode('utf-8') if out else ""
        is_valid = process.returncode == 0
        
        return is_valid, output 

def convert_to_kong3(config: dict) -> tuple[bool, str, dict | None]:
    """
    Converts Kong configuration from Kong 2.x to Kong 3.x format
    Returns (success, message, converted_config)
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        input_file = os.path.join(temp_dir, "input.yaml")
        output_file = os.path.join(temp_dir, "output.yaml")
        
        # Write input config to temporary file
        with open(input_file, 'w') as f:
            yaml.dump(config, f)
        
        # Run deck convert
        args = [
            "deck", "file", "convert",
            "--to", "kong-gateway-3.x",
            "--from", "kong-gateway-2.x",
            "--input-file", input_file,
            "--output-file", output_file
        ]
        logger.debug("Running %s", args)
        
        process = Popen(args, stdout=PIPE, stderr=STDOUT)
        out, _ = process.communicate()
        
        output_message = out.decode('utf-8') if out else ""
        success = process.returncode == 0
        
        # Check if there are unsupported routes paths
        has_unsupported_paths = "unsupported routes' paths format with Kong version 3.0" in output_message
        
        converted_config = None
        if success and os.path.exists(output_file):
            with open(output_file, 'r') as f:
                converted_config = yaml.safe_load(f)
                
        return (not has_unsupported_paths), output_message, converted_config 
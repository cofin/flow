#!/usr/bin/env python3
"""
Validate Codex marketplace and plugin manifest files for compatibility with Codex CLI 0.125.0+.
"""

import json
import os
import sys
import re

def validate_marketplace(file_path):
    print(f"Validating marketplace: {file_path}")
    with open(file_path, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  ERROR: Invalid JSON: {e}")
            return False

    errors = 0
    plugins = data.get('plugins', [])
    for plugin in plugins:
        name = plugin.get('name', 'unknown')
        source_field = plugin.get('source', {})
        
        path = ""
        is_local = False
        
        if isinstance(source_field, str):
            path = source_field
            is_local = True
        elif isinstance(source_field, dict):
            if source_field.get('source') == 'local':
                path = source_field.get('path', '')
                is_local = True
        
        if is_local:
            # 1. Must start with ./
            if not path.startswith('./'):
                print(f"  ERROR [plugin {name}]: path '{path}' must start with './'")
                errors += 1
            
            # 2. Must not be empty (after stripping ./)
            normalized = path[2:] if path.startswith('./') else path
            if not normalized or normalized.strip('/') == '':
                print(f"  ERROR [plugin {name}]: path '{path}' must not be empty or just './'")
                errors += 1
            
            # 3. No traversal (..)
            if '..' in path:
                print(f"  ERROR [plugin {name}]: path '{path}' must not contain '..'")
                errors += 1
                
    return errors == 0

def validate_plugin_manifest(file_path):
    print(f"Validating plugin manifest: {file_path}")
    with open(file_path, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  ERROR: Invalid JSON: {e}")
            return False

    errors = 0
    user_config = data.get('userConfig', {})
    for key in user_config.keys():
        # Check for camelCase (no hyphens or underscores)
        if not re.match(r'^[a-z][a-zA-Z0-9]*$', key):
            print(f"  ERROR [userConfig]: key '{key}' must be camelCase (no hyphens or underscores)")
            errors += 1
            
    return errors == 0

def main():
    success = True
    
    # Find all marketplace.json files
    for root, _, files in os.walk('.'):
        if 'marketplace.json' in files:
            path = os.path.join(root, 'marketplace.json')
            if not validate_marketplace(path):
                success = False
                
        if 'plugin.json' in files:
            path = os.path.join(root, 'plugin.json')
            if not validate_plugin_manifest(path):
                success = False

    if not success:
        print("\nValidation failed!")
        sys.exit(1)
    else:
        print("\nAll manifests are valid.")

if __name__ == "__main__":
    main()

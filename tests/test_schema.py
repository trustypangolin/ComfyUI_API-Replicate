import json
import os
import sys
import traceback

# Get this package's directory (the parent of the tests folder)
package_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, package_dir)

try:
    from schema_to_node import schema_to_comfyui_input_types, get_return_type
except Exception as e:
    print(f"Error importing schema_to_node: {e}")
    traceback.print_exc()
    sys.exit(1)

# Get the directory where this script is located (tests folder)
script_dir = os.path.dirname(os.path.abspath(__file__))

# Get the schemas directory relative to the tests folder
schemas_dir = os.path.join(script_dir, "..", "schemas")
schemas_dir = os.path.normpath(schemas_dir)

schema_files = [f for f in os.listdir(schemas_dir) if f.endswith(".json")]

# Print table header
print(f"{'Schema Name':<50} {'Inputs':<25} {'Parameters':<25} {'Outputs':<15}")
print("=" * 120)

errors = []
for schema_file in sorted(schema_files):
    try:
        schema_path = os.path.join(schemas_dir, schema_file)
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        # Get input types
        result = schema_to_comfyui_input_types(schema)
        
        # Get return types - can be dict or string
        return_types = get_return_type(schema)
        
        # Get schema name - try different formats
        # Replicate format: owner/name (e.g., black-forest-labs/flux-1.1-pro)
        # Fal AI format: x-fal-metadata.endpointId or info.title
        if "owner" in schema and "name" in schema:
            # Replicate format
            endpoint_id = f"{schema['owner']}/{schema['name']}"
        else:
            # Fal AI format or fallback to filename
            endpoint_id = schema.get("info", {}).get("x-fal-metadata", {}).get("endpointId")
            if not endpoint_id:
                endpoint_id = schema.get("info", {}).get("title", schema_file.replace(".json", ""))
    except Exception as e:
        errors.append((schema_file, str(e), traceback.format_exc()))
        continue
    
    # Separate inputs (IMAGE type) from parameters (all other types)
    # Inputs are what users connect from other nodes (IMAGE type)
    # Parameters are dialog box settings (STRING, INT, FLOAT, BOOLEAN, enums)
    
    all_required = result.get("required", {})
    all_optional = result.get("optional", {})
    
    # Combine required and optional inputs
    all_inputs = {}
    all_inputs.update(all_required)
    all_inputs.update(all_optional)
    
    # Separate into Inputs (IMAGE) and Parameters (everything else)
    inputs_list = [(name, inp) for name, inp in all_inputs.items() if inp[0] == "IMAGE"]
    parameters_list = [(name, inp) for name, inp in all_inputs.items() if inp[0] != "IMAGE"]
    
    # Format outputs - handle both dict and string return types
    if isinstance(return_types, dict):
        output_str = ", ".join([v for v in return_types.values()])
    elif isinstance(return_types, str):
        output_str = return_types
    else:
        output_str = "None"
    
    # Determine max rows needed
    max_rows = max(len(inputs_list), len(parameters_list), 1)
    
    for i in range(max_rows):
        input_name = ""
        input_type = ""
        param_name = ""
        param_type = ""
        
        if i < len(inputs_list):
            input_name = inputs_list[i][0]
            input_type = inputs_list[i][1][0]
        
        if i < len(parameters_list):
            param_name = parameters_list[i][0]
            param_type = parameters_list[i][1][0]
            # Handle enum case where param_type is a list
            if isinstance(param_type, list):
                param_type = str(param_type)
        
        if i == 0:
            print(f"{endpoint_id:<50} {input_name:<25} {param_name:<25} {output_str:<15}")
        else:
            print(f"{'':<50} {input_name:<25} {param_name:<25} {'':<15}")

# Print any errors that occurred
if errors:
    print("\n" + "=" * 80)
    print("ERRORS ENCOUNTERED:")
    print("=" * 80)
    for schema_file, error_msg, tb in errors:
        print(f"\nSchema: {schema_file}")
        print(f"Error: {error_msg}")
        print(tb)

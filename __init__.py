from .node import NODE_CLASS_MAPPINGS
__all__ = ['NODE_CLASS_MAPPINGS']

import os
if os.environ.get("REPLICATE_API_TOKEN"):
  ascii_art = "\033[94m[ComfyUI_API-REPLICATE] Loaded API, \033[93mfound\033[0m\033[94m REPLICATE_API_TOKEN Environment variable\033[0m"
else:
  ascii_art = "\033[94m[ComfyUI_API-REPLICATE] Loaded API, REPLICATE_API_TOKEN Environment \033[91mmissing\033[0m\033[94m (did you export/set the variable?)\033[0m"


print(ascii_art)

# Run tests only if DEBUG_API_TRUSTYPANGOLIN environment variable is set

if os.environ.get("DEBUG_API_TRUSTYPANGOLIN", "false").lower() == "true":
    # Import and run tests from the tests folder
    import importlib.util
    import sys

    # Get the tests directory path
    tests_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests')

    # Import test_schema module
    spec = importlib.util.spec_from_file_location("test_schema", os.path.join(tests_dir, "test_schema.py"))
    test_schema = importlib.util.module_from_spec(spec)
    sys.modules["test_schema"] = test_schema
    spec.loader.exec_module(test_schema)

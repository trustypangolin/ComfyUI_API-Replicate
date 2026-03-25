import os
import json
from PIL import Image
from io import BytesIO
import io
from torchvision import transforms
import torch
import base64
import time
import torchaudio
import soundfile as sf
from replicate.client import Client
from .schema_to_node import (
    schema_to_comfyui_input_types,
    get_return_type,
    name_and_version,
    inputs_that_need_arrays,
    get_max_images,
    get_array_input_mapping,
)

replicate = Client(headers={"User-Agent": "comfyui-replicate/1.0.1"})


def convert_to_json_serializable(obj):
    """Convert objects to JSON serializable format (e.g., tensors to lists)."""
    if isinstance(obj, torch.Tensor):
        # Return tensor shape info instead of full data for debugging
        return f"<Tensor shape={list(obj.shape)}, dtype={obj.dtype}>"
    elif isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    else:
        return obj


def create_comfyui_node(schema):
    replicate_model, node_name = name_and_version(schema)
    return_type = get_return_type(schema)

    class ReplicateToComfyUI:
        @classmethod
        def IS_CHANGED(cls, **kwargs):
            return time.time() if kwargs["force_rerun"] else ""

        @classmethod
        def INPUT_TYPES(cls):
            return schema_to_comfyui_input_types(schema)

        RETURN_TYPES = (
            tuple(return_type.values())
            if isinstance(return_type, dict)
            else (return_type,)
        ) + ("STRING",)  # Add STRING output for the JSON payload
        RETURN_NAMES = (
            tuple(return_type.values())
            if isinstance(return_type, dict)
            else (return_type,)
        ) + ("INPUT_JSON",)  # Name for the JSON output
        FUNCTION = "run_replicate_model"
        CATEGORY = "🎨 API Replicate"

        def convert_input_images_to_base64(self, kwargs):
            for key, value in kwargs.items():
                if value is not None:
                    # Check if value is a tensor - convert regardless of input type mapping
                    if isinstance(value, torch.Tensor):
                        kwargs[key] = self.image_to_base64(value)
                        continue
                    
                    # Check if value is a list that may contain tensors
                    if isinstance(value, list):
                        # Check if any item is a tensor - if so, convert all items
                        has_tensor = any(isinstance(item, torch.Tensor) for item in value)
                        if has_tensor:
                            kwargs[key] = [self.image_to_base64(item) for item in value]
                            continue
                    
                    input_type = (
                        self.INPUT_TYPES()["required"].get(key, (None,))[0]
                        or self.INPUT_TYPES().get("optional", {}).get(key, (None,))[0]
                    )
                    if input_type == "IMAGE":
                        # Handle array inputs (from handle_array_inputs) - convert each to base64
                        if isinstance(value, list):
                            kwargs[key] = [self.image_to_base64(item) for item in value]
                        else:
                            kwargs[key] = self.image_to_base64(value)
                    elif input_type == "AUDIO":
                        # Handle array inputs (from handle_array_inputs) - convert each to base64
                        if isinstance(value, list):
                            kwargs[key] = [self.audio_to_base64(item) for item in value]
                        else:
                            kwargs[key] = self.audio_to_base64(value)

        def image_to_base64(self, image):
            if isinstance(image, torch.Tensor):
                image = image.permute(0, 3, 1, 2).squeeze(0)
                to_pil = transforms.ToPILImage()
                pil_image = to_pil(image)
            else:
                pil_image = image

            buffer = io.BytesIO()
            pil_image.save(buffer, format="PNG")
            buffer.seek(0)
            img_str = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_str}"

        def audio_to_base64(self, audio):
            if (
                isinstance(audio, dict)
                and "waveform" in audio
                and "sample_rate" in audio
            ):
                waveform = audio["waveform"]
                sample_rate = audio["sample_rate"]
            else:
                waveform, sample_rate = audio

            # Ensure waveform is 2D
            if waveform.dim() == 1:
                waveform = waveform.unsqueeze(0)
            elif waveform.dim() > 2:
                waveform = waveform.squeeze()
                if waveform.dim() > 2:
                    raise ValueError("Waveform must be 1D or 2D")

            buffer = io.BytesIO()
            sf.write(buffer, waveform.numpy().T, sample_rate, format="wav")
            buffer.seek(0)
            audio_str = base64.b64encode(buffer.getvalue()).decode()
            return f"data:audio/wav;base64,{audio_str}"

        def handle_array_inputs(self, kwargs):
            array_inputs = inputs_that_need_arrays(schema)
            for input_name in array_inputs:
                if input_name in kwargs:
                    if isinstance(kwargs[input_name], str):
                        if kwargs[input_name] == "":
                            kwargs[input_name] = []
                        else:
                            kwargs[input_name] = kwargs[input_name].split("\n")
                    else:
                        kwargs[input_name] = [kwargs[input_name]]

        def log_input(self, kwargs):
            def format_value(v):
                if isinstance(v, torch.Tensor):
                    return f"<Tensor {list(v.shape)} {v.dtype}>"
                elif isinstance(v, str) and (v.startswith("data:image") or v.startswith("data:audio")):
                    return v[:20] + "..."
                return v
            
            truncated_kwargs = {k: format_value(v) for k, v in kwargs.items()}
            print(f"Running {replicate_model} with {truncated_kwargs}")

        def _base64_to_tensor(self, base64_str):
            """Convert a base64 image string to a tensor."""
            if not base64_str or not isinstance(base64_str, str):
                print(f"DEBUG: _base64_to_tensor received invalid input: {type(base64_str)}")
                return None
            try:
                # Extract base64 content from data URL
                if "," in base64_str:
                    base64_data = base64_str.split(",", 1)[1]
                else:
                    base64_data = base64_str
                
                image_data = base64.b64decode(base64_data, validate=True)
                image = Image.open(BytesIO(image_data))
                if image.mode != "RGB":
                    image = image.convert("RGB")
                
                transform = transforms.ToTensor()
                tensor_image = transform(image)
                tensor_image = tensor_image.unsqueeze(0)
                tensor_image = tensor_image.permute(0, 2, 3, 1).cpu().float()
                print(f"DEBUG: _base64_to_tensor success: shape={tensor_image.shape}")
                return tensor_image
            except Exception as e:
                print(f"Error converting base64 to tensor: {e}")
                import traceback
                traceback.print_exc()
                return None

        def handle_image_output(self, output):
            if output is None:
                print("No image output received")
                return None

            output_list = [output] if not isinstance(output, list) else output
            if output_list:
                output_tensors = []
                transform = transforms.ToTensor()
                for file_obj in output_list:
                    image_data = file_obj.read()
                    image = Image.open(BytesIO(image_data))
                    if image.mode != "RGB":
                        image = image.convert("RGB")

                    tensor_image = transform(image)
                    tensor_image = tensor_image.unsqueeze(0)
                    tensor_image = tensor_image.permute(0, 2, 3, 1).cpu().float()
                    output_tensors.append(tensor_image)

                # Combine all tensors into a single batch if multiple images
                return (
                    torch.cat(output_tensors, dim=0)
                    if len(output_tensors) > 1
                    else output_tensors[0]
                )
            else:
                print("No output received from the model")
                return None

        def handle_audio_output(self, output):
            if output is None:
                print("No audio output received from the model")
                return None

            output_list = [output] if not isinstance(output, list) else output

            audio_data = []
            for audio_file in output_list:
                if audio_file:
                    audio_content = BytesIO(audio_file.read())
                    waveform, sample_rate = torchaudio.load(audio_content)
                    audio_data.append({
                        "waveform": waveform.unsqueeze(0),
                        "sample_rate": sample_rate
                    })
                else:
                    print("Empty audio file received")

            if len(audio_data) == 1:
                return audio_data[0]
            elif len(audio_data) > 0:
                return audio_data
            else:
                print("No valid audio files processed")
                return None

        def remove_falsey_optional_inputs(self, kwargs):
            optional_inputs = self.INPUT_TYPES().get("optional", {})
            for key in list(kwargs.keys()):
                if key in optional_inputs:
                    if isinstance(kwargs[key], torch.Tensor):
                        # Keep tensors with elements, delete empty tensors
                        if kwargs[key].numel() == 0:
                            del kwargs[key]
                    elif not kwargs[key]:
                        del kwargs[key]

        def combine_split_image_inputs(self, kwargs, replicate_model):
            """
            Combine split image inputs (image_1, image_2, etc.) back into arrays.
            
            This is needed because schema_to_node.py splits image arrays into
            individual inputs for ComfyUI, but the Replicate API expects arrays.
            """
            # Get model base name (without version hash)
            model_base = replicate_model.split(":")[0] if ":" in replicate_model else replicate_model
            
            # Get max_images for this model
            max_images = get_max_images(replicate_model)
            
            if max_images == 0:
                return  # No split inputs to combine
            
            # Get the original array input name for this model
            array_input_name = get_array_input_mapping(replicate_model)
            if not array_input_name:
                return
            
            # Find all split image inputs (e.g., image_1, image_2, etc.)
            # or input_image_1, input_image_2, etc.
            base_name = array_input_name.replace("images", "image").replace("_url", "")
            
            split_inputs = []
            for i in range(1, max_images + 1):
                input_name = f"{base_name}_{i}"
                if input_name in kwargs and kwargs[input_name] is not None:
                    split_inputs.append(kwargs[input_name])
                    # Remove the individual input
                    del kwargs[input_name]
            
            # If we found any split inputs, combine them into an array
            if split_inputs:
                kwargs[array_input_name] = split_inputs

        def run_replicate_model(self, **kwargs):
            # Extract debug flag before processing
            debug_mode = kwargs.pop("debug", False)
            
            self.handle_array_inputs(kwargs)
            self.remove_falsey_optional_inputs(kwargs)
            self.combine_split_image_inputs(kwargs, replicate_model)
            self.convert_input_images_to_base64(kwargs)
            self.log_input(kwargs)
            
            # Remove force_rerun from the API call but keep for debug output
            kwargs_without_special = {
                k: v for k, v in kwargs.items() if k not in ["force_rerun", "debug"]
            }
            
            # Convert kwargs to JSON string for output
            kwargs_for_json = convert_to_json_serializable(kwargs_without_special)
            input_json = json.dumps(kwargs_for_json, indent=2)
            
            if debug_mode:
                # In debug mode, return the first input image and the JSON payload
                print(f"DEBUG MODE: Skipping API call, returning input data")
                print(f"Input JSON: {input_json}")
                print(f"DEBUG: kwargs_without_special keys: {list(kwargs_without_special.keys())}")
                
                # Find the first image input to return and convert to tensor
                debug_tensor = None
                for key, value in kwargs_without_special.items():
                    print(f"DEBUG: checking key={key}, type={type(value)}, value={str(value)[:50] if value else None}")
                    if isinstance(value, str) and value.startswith("data:image"):
                        print(f"DEBUG: Found direct image string, converting")
                        debug_tensor = self._base64_to_tensor(value)
                        break
                    elif key in ["image", "images", "input_image", "input_images", "media"]:
                        print(f"DEBUG: Found image key={key}, processing")
                        if isinstance(value, list) and value:
                            print(f"DEBUG: value is list, first element type={type(value[0])}")
                            debug_tensor = self._base64_to_tensor(value[0])
                        elif isinstance(value, str) and value:
                            print(f"DEBUG: value is string, converting")
                            debug_tensor = self._base64_to_tensor(value)
                        else:
                            print(f"DEBUG: value type not handled: {type(value)}")
                        break
                
                print(f"DEBUG: Final debug_tensor: {debug_tensor}")
                
                processed_outputs = []
                if isinstance(return_type, dict):
                    for prop_name, prop_type in return_type.items():
                        if prop_type == "IMAGE":
                            processed_outputs.append(debug_tensor)
                        elif prop_type == "AUDIO":
                            processed_outputs.append(None)
                        else:
                            processed_outputs.append("")
                else:
                    if return_type == "IMAGE":
                        processed_outputs.append(debug_tensor)
                    elif return_type == "AUDIO":
                        processed_outputs.append(None)
                    else:
                        processed_outputs.append("")
                
                processed_outputs.append(input_json)
                return tuple(processed_outputs)
            
            output = replicate.run(replicate_model, input=kwargs_without_special)
            print(f"Output: {output}")

            processed_outputs = []
            if isinstance(return_type, dict):
                for prop_name, prop_type in return_type.items():
                    if prop_type == "IMAGE":
                        processed_outputs.append(
                            self.handle_image_output(output.get(prop_name))
                        )
                    elif prop_type == "AUDIO":
                        processed_outputs.append(
                            self.handle_audio_output(output.get(prop_name))
                        )
                    elif prop_type == "STRING":
                        processed_outputs.append(
                            "".join(list(output.get(prop_name, ""))).strip()
                        )
            else:
                if return_type == "IMAGE":
                    processed_outputs.append(self.handle_image_output(output))
                elif return_type == "AUDIO":
                    processed_outputs.append(self.handle_audio_output(output))
                else:
                    processed_outputs.append("".join(list(output)).strip())

            processed_outputs.append(input_json)
            return tuple(processed_outputs)

    return node_name, ReplicateToComfyUI


def create_comfyui_nodes_from_schemas(schemas_dir):
    nodes = {}
    current_path = os.path.dirname(os.path.abspath(__file__))
    schemas_dir_path = os.path.join(current_path, schemas_dir)
    for schema_file in os.listdir(schemas_dir_path):
        if schema_file.endswith(".json"):
            with open(
                os.path.join(schemas_dir_path, schema_file), "r", encoding="utf-8"
            ) as f:
                schema = json.load(f)
                node_name, node_class = create_comfyui_node(schema)
                nodes[node_name] = node_class
    return nodes


_cached_node_class_mappings = None


def get_node_class_mappings():
    global _cached_node_class_mappings
    if _cached_node_class_mappings is None:
        _cached_node_class_mappings = create_comfyui_nodes_from_schemas("schemas")
    return _cached_node_class_mappings


NODE_CLASS_MAPPINGS = get_node_class_mappings()

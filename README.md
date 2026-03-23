# ComfyUI_API-Replicate

Custom nodes for running [Replicate models](https://replicate.com/explore) in ComfyUI.

Forked from [replicate/comfyui-replicate](https://github.com/replicate/comfyui-replicate) with modifications and additional features.

Take a look at the [example workflows](https://github.com/trustypangolin/ComfyUI_API-Replicate/tree/main/example_workflows) and the [supported Replicate models](https://github.com/trustypangolin/ComfyUI_API-Replicate/blob/main/supported_models.json) to get started.

![example-screenshot](https://github.com/replicate/comfyui-replicate/assets/319055/0eedb026-de3e-402a-b8fc-0a14c2fd209e)

## Features

- Run Replicate models directly in ComfyUI
- Auto-generated nodes from Replicate model schemas
- Support for image generation, upscaling, face restoration, and more
- Easily add new models by updating the supported models list

## Set your Replicate API token before running

Make sure you set your REPLICATE_API_TOKEN in your environment. Get your API tokens here, we recommend creating a new one:

https://replicate.com/account/api-tokens

To pass in your API token when running ComfyUI you could do:

On MacOS or Linux:

```sh
export REPLICATE_API_TOKEN="r8_************"; python main.py
```

On Windows:

```sh
set REPLICATE_API_TOKEN="r8_************"; python main.py
```

## Installation

### Manual Installation

```sh
cd ComfyUI/custom_nodes
git clone https://github.com/trustypangolin/ComfyUI_API-Replicate
cd ComfyUI_API-Replicate
pip install -r requirements.txt
```

### Via ComfyUI Manager

Search for "ComfyUI_API-Replicate" in ComfyUI Manager and install.

## Supported Replicate models

This repository includes pre-configured support for the following model families:

### Image Generation
- **Flux** (Black Forest Labs) - flux-pro, flux-dev, flux-schnell, flux-1.1-pro, flux-2-pro, flux-2-max, flux-2-klein-9b

### Image Processing
- **CodeFormer** - Face restoration and image enhancement
- **GFPGAN** - Face restoration
- **SeedVR2** - Image/Video restoration
- **Crystal Upscaler** - Image upscaling
- **Topaz Labs Image Upscale** - AI-powered image upscaling

### Audio
- **Realistic Voice Cloning** - Voice synthesis from text

View the `supported_models.json` to see the full list of supported models.

## Update Replicate models

Simply run `python import_schemas.py` to update all model nodes. The latest version of a model is used by default.

## Add more models

Only models that return simple text or image outputs are currently supported. If a model returns audio, video, JSON objects or a combination of outputs, the node will not work as expected.

If you want to add more models, you can:

- Add the model to `supported_models.json` (for example, `fofr/consistent-character`)
- Run `python import_schemas.py`, this will update all schemas and import your new model
- Restart ComfyUI
- Use the model in workflow, it'll have the title 'Replicate [model author/model name]'

## Project Structure

```
ComfyUI_API-Replicate/
├── __init__.py              # Package initialization
├── node.py                  # Main ComfyUI node implementation
├── import_schemas.py        # Script to import/update model schemas
├── schema_to_node.py        # Schema conversion utilities
├── pyproject.toml           # Project configuration
├── requirements.txt         # Python dependencies
├── supported_models.json    # List of supported models
├── schemas/                 # Replicate model schemas
├── example_workflows/       # Example ComfyUI workflows
└── LICENSE                 # MIT License
```

## Roadmap

Things to investigate and add to this custom node package:

- support for more types of Replicate model (audio and video first)
- showing logs, prediction status and progress (via tqdm)

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Contributing

If you add models that others would find useful, feel free to raise PRs.

## Links

- [Repository](https://github.com/trustypangolin/ComfyUI_API-Replicate)
- [Documentation Wiki](https://github.com/trustypangolin/ComfyUI_API-Replicate/wiki)
- [Issue Tracker](https://github.com/trustypangolin/ComfyUI_API-Replicate/issues)
- [Original Replicate Repository](https://github.com/replicate/comfyui-replicate)

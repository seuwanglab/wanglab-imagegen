# Wanglab Imagegen

Wanglab Imagegen is a Codex skill for image generation and image editing through custom API endpoints.

## Install

```bash
git clone https://github.com/seuwanglab/wanglab-imagegen.git
cd wanglab-imagegen
python3 scripts/install_local.py --mode symlink
```

If you prefer a copied install:

```bash
python3 scripts/install_local.py --mode copy
```

Restart Codex after installation.

## Configure

Edit `skills/wanglab-imagegen/scripts/wanglab_image.py` and set:

```python
IMAGEGEN_BASE_URL = "https://XXX/v1"
IMAGEGEN_API_KEY = "sk-XXX"
```

## Usage

In Codex, call the skill with:

```text
$wanglab-imagegen
```

Example:

```text
Use $wanglab-imagegen to generate a cute cat
```

![Wanglab Imagegen example](gen-images.png)

## More

You can also follow our work here:

https://seuwanglab.github.io/

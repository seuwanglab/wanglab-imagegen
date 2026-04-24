import argparse
import base64
import json
import mimetypes
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional


DEFAULT_MODEL = "gpt-image-2-vip"
DEFAULT_SIZE = "1536x1024"
DEFAULT_OUTPUT_FORMAT = "png"
IMAGEGEN_BASE_URL = "https://XXX/v1"
IMAGEGEN_API_KEY = "sk-XXX"
DATA_URL_RE = re.compile(r"^data:(?P<mime>[^;]+);base64,(?P<data>.+)$", re.IGNORECASE)


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def build_api_url(base_url: str, endpoint: str) -> str:
    clean_base = normalize_base_url(base_url)
    if clean_base.endswith("/v1") and endpoint.startswith("/v1/"):
        return f"{clean_base}{endpoint[3:]}"
    return f"{clean_base}{endpoint}"


def require_runtime_config() -> tuple[str, str]:
    if not IMAGEGEN_BASE_URL:
        raise RuntimeError("请先在脚本中设置 IMAGEGEN_BASE_URL。")
    if not IMAGEGEN_API_KEY:
        raise RuntimeError("请先在脚本中设置 IMAGEGEN_API_KEY。")
    return normalize_base_url(IMAGEGEN_BASE_URL), IMAGEGEN_API_KEY


def resolve_mode(mode: str, input_images: list[str]) -> str:
    if mode == "auto":
        return "edit" if input_images else "generate"
    if mode == "edit" and not input_images:
        raise RuntimeError("Edit mode requires at least one --image.")
    return mode


def endpoint_for_mode(mode: str) -> str:
    if mode == "edit":
        return "/v1/images/edits"
    return "/v1/images/generations"


def add_form_field(command: list[str], field: str, value: Optional[object]) -> None:
    if value is None:
        return
    command.extend(["-F", f"{field}={value}"])


def add_json_field(payload: dict[str, Any], field: str, value: Optional[object]) -> None:
    if value is None:
        return
    payload[field] = value


def data_url_to_bytes(data_url: str) -> tuple[bytes, str]:
    match = DATA_URL_RE.match(data_url)
    if not match:
        raise RuntimeError("Invalid data URL image source.")
    try:
        return base64.b64decode(match.group("data")), match.group("mime")
    except Exception as exc:
        raise RuntimeError("Failed to decode data URL image source.") from exc


def extension_for_source(mime: Optional[str], source: Optional[str] = None) -> str:
    if mime:
        guessed = mimetypes.guess_extension(mime)
        if guessed:
            return guessed.replace(".jpe", ".jpg")
    if source:
        parsed_path = urllib.parse.urlparse(source).path or source
        suffix = Path(parsed_path).suffix
        if suffix:
            return suffix
    return ".bin"


def source_to_generation_image(source: str) -> str:
    if source.startswith("data:"):
        return source
    if source.startswith("http://") or source.startswith("https://"):
        return source

    path = Path(source).expanduser()
    if not path.is_file():
        raise RuntimeError(f"Input image does not exist: {path}")

    binary = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(binary).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def materialize_input_source(source: str, temp_dir: Path, prefix: str) -> Path:
    if source.startswith("data:"):
        binary, mime = data_url_to_bytes(source)
        destination = temp_dir / f"{prefix}{extension_for_source(mime)}"
        destination.write_bytes(binary)
        return destination

    if source.startswith("http://") or source.startswith("https://"):
        with urllib.request.urlopen(source) as response:  # nosec B310
            binary = response.read()
            mime = response.headers.get_content_type()
        destination = temp_dir / f"{prefix}{extension_for_source(mime, source)}"
        destination.write_bytes(binary)
        return destination

    path = Path(source).expanduser()
    if not path.is_file():
        raise RuntimeError(f"Input image does not exist: {path}")
    return path


def build_generate_payload(args: argparse.Namespace, reference_images: list[str]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    add_json_field(payload, "model", args.model)
    add_json_field(payload, "prompt", args.prompt)
    add_json_field(payload, "n", args.n)
    add_json_field(payload, "size", args.size)
    add_json_field(payload, "output_format", args.output_format)
    add_json_field(payload, "quality", args.quality)
    add_json_field(payload, "background", args.background)
    add_json_field(payload, "output_compression", args.output_compression)
    add_json_field(payload, "partial_images", args.partial_images)
    add_json_field(payload, "moderation", args.moderation)
    if reference_images:
        payload["image"] = reference_images
    return payload


def build_generate_command(
    args: argparse.Namespace,
    base_url: str,
    api_key: str,
    response_path: Path,
    reference_images: list[str],
) -> list[str]:
    payload = build_generate_payload(args, reference_images)
    return [
        "curl",
        "-sS",
        "-L",
        "-X",
        "POST",
        build_api_url(base_url, endpoint_for_mode("generate")),
        "-H",
        f"Authorization: Bearer {api_key}",
        "-H",
        "Content-Type: application/json",
        "-d",
        json.dumps(payload, ensure_ascii=False),
        "-o",
        str(response_path),
    ]


def build_edit_command(
    args: argparse.Namespace,
    base_url: str,
    api_key: str,
    response_path: Path,
    input_images: list[Path],
    mask_image: Optional[Path],
) -> list[str]:
    command = [
        "curl",
        "-sS",
        "-L",
        "-X",
        "POST",
        build_api_url(base_url, endpoint_for_mode("edit")),
        "-H",
        f"Authorization: Bearer {api_key}",
    ]
    add_form_field(command, "model", args.model)
    add_form_field(command, "prompt", args.prompt)
    add_form_field(command, "n", args.n)
    add_form_field(command, "size", args.size)
    add_form_field(command, "output_format", args.output_format)
    add_form_field(command, "quality", args.quality)
    add_form_field(command, "background", args.background)
    add_form_field(command, "output_compression", args.output_compression)
    add_form_field(command, "partial_images", args.partial_images)
    add_form_field(command, "moderation", args.moderation)
    add_form_field(command, "input_fidelity", args.input_fidelity)
    for input_image in input_images:
        command.extend(["-F", f"image[]=@{input_image}"])
    if mask_image is not None:
        command.extend(["-F", f"mask=@{mask_image}"])
    command.extend(["-o", str(response_path)])
    return command


def output_dir() -> Path:
    directory = Path.cwd() / "gen-images"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def normalize_output_path(output_path: Optional[Path], output_format: str) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    if output_path is None:
        return output_dir() / f"{stamp}.{output_format}"
    expanded = output_path.expanduser()
    if expanded.exists() and expanded.is_dir():
        return expanded / f"{stamp}.{output_format}"
    if expanded.suffix:
        return expanded
    return expanded.with_suffix(f".{output_format}")


def next_available_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(1, 10_000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find an available output path near: {path}")


def output_paths(base_path: Path, count: int) -> list[Path]:
    if count <= 1:
        return [next_available_path(base_path)]
    return [
        next_available_path(base_path.with_name(f"{base_path.stem}-{index}{base_path.suffix}"))
        for index in range(1, count + 1)
    ]


def read_json_file(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse JSON file: {path}") from exc


def parse_response_payload(path: Path) -> dict[str, Any]:
    payload = read_json_file(path)
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message") or error
        raise RuntimeError(f"Image API returned an error: {message}")
    if "data" not in payload:
        raise RuntimeError("Image API response does not contain data.")
    return payload


def write_image_record(record: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    b64_json = record.get("b64_json")
    if isinstance(b64_json, str) and b64_json:
        destination.write_bytes(base64.b64decode(b64_json))
        return

    url = record.get("url")
    if isinstance(url, str) and url:
        with urllib.request.urlopen(url) as response:  # nosec B310
            destination.write_bytes(response.read())
        return

    raise RuntimeError("Image response did not contain b64_json or url data.")


def materialize_images(payload: dict[str, Any], output_path: Path) -> list[Path]:
    records = payload.get("data")
    if not isinstance(records, list) or not records:
        raise RuntimeError("Image response did not contain any image records.")

    destinations = output_paths(output_path, len(records))
    for record, destination in zip(records, destinations):
        if not isinstance(record, dict):
            raise RuntimeError("Image response record had an invalid shape.")
        write_image_record(record, destination)
    return destinations


def build_used_params(args: argparse.Namespace, mode: str) -> dict[str, Any]:
    params: dict[str, Any] = {
        "mode": mode,
        "model": args.model,
        "size": args.size,
        "output_format": args.output_format,
        "n": args.n,
    }
    for field in ("quality", "background", "output_compression", "partial_images", "moderation"):
        value = getattr(args, field)
        if value is not None:
            params[field] = value
    if mode == "edit":
        if args.input_fidelity is not None:
            params["input_fidelity"] = args.input_fidelity
        if args.mask is not None:
            params["mask"] = True
    if args.image:
        params["image_count"] = len(args.image)
    return params


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("auto", "generate", "edit"),
        default="auto",
        help="auto: infer from whether --image is present; generate: new image or reference-image generation; edit: modify existing image.",
    )
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--image",
        action="append",
        default=[],
        help="Image source. May be repeated. Supports local path, URL, or data URL.",
    )
    parser.add_argument("--mask")
    parser.add_argument("--size", default=DEFAULT_SIZE)
    parser.add_argument("--quality")
    parser.add_argument("--background")
    parser.add_argument("--output-format", dest="output_format", default=DEFAULT_OUTPUT_FORMAT)
    parser.add_argument("--output-compression", dest="output_compression", type=int)
    parser.add_argument("--partial-images", dest="partial_images", type=int)
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--moderation")
    parser.add_argument("--input-fidelity", dest="input_fidelity")
    parser.add_argument(
        "--out",
        type=Path,
        help="Output file path or existing directory. Missing parent directories are created automatically.",
    )
    return parser.parse_args(argv)


def run(argv: Optional[list[str]] = None) -> dict[str, Any]:
    if shutil.which("curl") is None:
        raise RuntimeError("curl is required but was not found in PATH.")

    args = parse_args(argv)
    mode = resolve_mode(args.mode, args.image)
    if mode != "edit" and args.mask:
        raise RuntimeError("--mask is only supported in edit mode.")
    if mode != "edit" and args.input_fidelity:
        raise RuntimeError("--input-fidelity is only supported in edit mode.")

    base_url, api_key = require_runtime_config()
    output_path = normalize_output_path(args.out, args.output_format)

    with tempfile.TemporaryDirectory(prefix="wanglab-imagegen-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        response_path = temp_dir / "response.json"
        effective_inputs = (
            [
                materialize_input_source(source, temp_dir, f"image-{index}")
                for index, source in enumerate(args.image, start=1)
            ]
            if mode == "edit"
            else []
        )
        reference_images = [source_to_generation_image(source) for source in args.image] if mode == "generate" else []
        effective_mask = materialize_input_source(args.mask, temp_dir, "mask") if args.mask else None

        if mode == "edit":
            command = build_edit_command(args, base_url, api_key, response_path, effective_inputs, effective_mask)
        else:
            command = build_generate_command(args, base_url, api_key, response_path, reference_images)
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "curl request failed.")
        payload = parse_response_payload(response_path)

    paths = materialize_images(payload, output_path)
    return {
        "ok": True,
        "paths": [str(path) for path in paths],
        "used_params": build_used_params(args, mode),
    }


def main() -> int:
    try:
        print(json.dumps(run(), ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

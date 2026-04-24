# Runtime Notes

## 固定配置

运行时只使用 `scripts/wanglab_image.py` 里的这两个常量：

- `IMAGEGEN_BASE_URL`
- `IMAGEGEN_API_KEY`

## 模式

- 没有 `--image`：文生图
- 有 `--image` 且目标是修改原图：改图
- 有 `--image` 但目标是参考图生成：文生图，并把图片作为参考输入传给 `/v1/images/generations`

## 改图输入

改图模式支持：

- 本地文件路径
- `http://` 或 `https://` 图片 URL
- `data:` URL

`--mask` 也支持同样的输入类型。

`--image` 可以重复传入；脚本会根据 `--mode` 决定它们是参考图还是待编辑图片。

## 可选字段

脚本会按需透传这些字段：

- `quality`
- `background`
- `output_compression`
- `partial_images`
- `moderation`
- `input_fidelity`
- `mask`

默认模型是 `gpt-image-2-vip`。`quality`、2K/4K `size`、参考图生成、`background=transparent` 和 `input_fidelity` 会按用户意图透传；如果远端返回不支持，去掉对应字段后重试。

## 输出

- 成功时输出 JSON：`ok`、`paths`、`used_params`
- 失败时输出 JSON：`ok`、`error`
- 如果未指定输出路径，默认写到 `./gen-images/`
- 如果 `--out` 指向已存在目录，脚本会在该目录里自动生成文件名
- 如果指定的父目录不存在，脚本会自动创建
- 如果输出文件已存在，脚本会自动追加数字后缀避免覆盖

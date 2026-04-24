---
name: wanglab-imagegen
description: 生成或编辑位图图片，包括照片、插画、纹理、海报、透明背景素材、参考图生成、改图和多图变体；不用于 SVG、HTML/CSS、canvas 或代码原生视觉输出。
---

# wanglab-imagegen

使用这个 skill 处理通过 Wanglab AI 图片接口完成的位图生成、参考图生成与改图任务。

## 目标

- 判断用户是要文生图还是改图
- 从自然语言中提取可用字段
- 缺少必填字段时先追问，不要盲目执行
- 字段足够时调用 `scripts/wanglab_image.py`
- 完成后返回图片路径和实际使用参数

## 资源

- `references/fields.md`
- `references/runtime.md`
- `scripts/wanglab_image.py`

## 任务类型

优先根据用户意图自适应选择：没有图片来源时文生图；有图片来源但目标是重新生成时仍可文生图并带参考图；需要保留、替换、修复或局部修改原图时走改图。

### 文生图

以下情况按文生图处理：

- `生成图片`
- `文生图`
- `画一张图`
- `做一张海报`

### 改图

以下情况按改图处理：

- `修改图片`
- `编辑图片`
- `改图`
- `把这张图改成...`

如果同时出现图片来源和修改意图，优先按改图处理。

如果用户给的是参考图，但目标是“按这个风格再生成一张”“参考这张做新图”，优先按文生图处理，并把图片作为参考输入传给脚本。

## 必填字段

### 文生图

- `prompt`

### 改图

- `prompt`
- `image`

图片来源支持：

- 本地路径
- URL
- data URL
- 多次传入 `--image`

字段规则与自然语言映射见 `references/fields.md`。

## 执行步骤

1. 先判断是文生图还是改图。
2. 提取 `prompt`、图片来源和可选字段。
3. 如果缺少必填字段，先简短追问。
4. 字段齐全后调用 `scripts/wanglab_image.py`。
5. 执行完成后返回图片路径和实际使用参数。

## 调用示例

文生图：

```bash
python3 skills/wanglab-imagegen/scripts/wanglab_image.py \
  --mode generate \
  --prompt "A cinematic science-fiction city street at dusk, rain reflections, dense detail." \
  --size "1536x1024"
```

改图：

```bash
python3 skills/wanglab-imagegen/scripts/wanglab_image.py \
  --mode edit \
  --prompt "Keep the main subject and change the background into a warm sunset sky." \
  --image ./references/source.png \
  --quality high
```

## 注意事项

- 这个 skill 处理的是位图图片任务，不适合 SVG、HTML/CSS、canvas 或其他代码原生输出。
- 不要另外发明新的接口调用方式，直接使用 `scripts/wanglab_image.py`。
- 改图时，把用户要求保持不变的部分明确写进 prompt。
- 2K/4K `size`、`quality`、透明背景、参考图生成和 `input_fidelity` 按当前接口能力处理。
- 有参考图时，先判断它是“参考图”还是“待修改原图”，再决定走文生图还是改图；prompt 里要写清保留点和变化点。
- 如果用户要多张图，显式传 `--n`。

# Wanglab Imagegen 字段规则

## 任务类型

- 文生图：调用 `/v1/images/generations`
- 改图：调用 `/v1/images/edits`

如果用户同时给出图片来源和修改意图，优先识别为改图。
如果只是给参考图并要求生成相似风格、新构图或新画面，仍按文生图处理，并把图片作为参考输入传给 `/v1/images/generations`。

## 必填字段

### 文生图

- `prompt`

缺少时追问：

`请补充图片提示词，例如你想生成什么画面。`

### 改图

- `prompt`
- `image`

图片来源支持：

- 本地路径
- 图片 URL
- data URL
- 多次传入 `--image`

缺少图片来源时追问：

`请提供要编辑的图片来源：1）本地路径 2）图片 URL / data URL`

缺少修改要求时追问：

`请补充修改要求，例如你想把图片改成什么效果。`

## 可选字段

- `size`
- `quality`
- `background`
- `output_format`
- `n`
- `moderation`
- `output_compression`
- `partial_images`
- `input_fidelity`
- `mask`
- 输出路径

如果用户没有提供，不要为了这些字段反复追问。

## 模型与 provider 边界

- 默认模型是 `gpt-image-2-vip`。
- 当前 GPT Image 路径支持 `quality` 与更灵活的 2K/4K `size`。
- 当前接口支持参考图生成、`background=transparent` 与 `input_fidelity` 透传；如果远端返回不支持，移除对应字段后重试。
- 不要把透明背景只写成字段；prompt 里也要明确说明需要透明背景、无底色、适合抠图素材。
- 有参考图时，先判断它是参考图还是待修改原图；prompt 要写清保留主体、改变内容和风格约束。

## 自然语言映射

### size

- `1024x1024`、`1:1` -> `size=1024x1024`
- `1024x1536`、`3:4` -> `size=1024x1536`
- `1536x1024`、`4:3` -> `size=1536x1024`
- `2048x2048` -> `size=2048x2048`
- `3840x2160`、`16:9`、`4k横向` -> `size=3840x2160`
- `2160x3840`、`9:16`、`4k竖向` -> `size=2160x3840`

### quality

- `高清`、`高质量`、`高品质` -> `quality=high`
- `中等质量` -> `quality=medium`
- `低质量` -> `quality=low`
- `自动质量` -> `quality=auto`

### background

- `透明背景` -> `background=transparent`
- `白色背景` -> `background=white`
- `黑色背景` -> `background=black`

### output_format

- `png` -> `output_format=png`
- `jpg` -> `output_format=jpg`
- `jpeg` -> `output_format=jpeg`
- `webp` -> `output_format=webp`

### n

- `生成3张`、`来3张`、`输出3张` -> `n=3`

## 结果返回

成功后返回：

- 图片路径
- 实际使用的关键参数

失败后返回：

- 简短错误原因

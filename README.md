# OCR CLI Scaffolding

命令行工具用于对比调用阿里云 OCR 与百炼 DashScope Qwen-OCR 的识别结果，并将统一结构的结果输出到终端与 JSON 文件。

## 环境准备

1. `python -m venv .venv && source .venv/bin/activate`（Windows 请执行 `..\.venv\Scripts\activate`）
2. `pip install -r requirements.txt`
3. 复制 `.env.example` 为 `.env`，填入真实的云服务密钥
4. 准备测试图片并放置于 `samples/` 或任意可访问路径

## 使用示例

```bash
python main.py --backend aliyun --image samples/receipt.jpg
python main.py --backend qwen --image samples/page1.jpg --task table
```

常用参数说明：

- `--backend`: `aliyun` 或 `qwen`
- `--image`: 本地图片路径
- `--task`: Qwen OCR 任务类型（document/table/general）
- `--min_conf`: 置信度阈值，低于该值的文本行会被过滤
- `--outdir`: 输出 JSON 保存目录，默认为 `outputs`
- `--alltext_type`: 当使用阿里云 `RecognizeAllText` 时的 type 字符串

执行后会在控制台打印格式化 JSON，并在输出目录生成 `backend_task_时间戳.json`。

## 测试

```bash
pytest
```

## Run/Debug Config（PyCharm）

- Script path: `<项目根目录>/main.py`
- Parameters 示例：`--backend qwen --image samples/page1.jpg --task document`
- Working directory: `<项目根目录>`
- Environment variables: 通过 `.env` 或 IDE 的环境变量配置注入密钥

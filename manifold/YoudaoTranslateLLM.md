# YouDao Translate LLM Pipeline

一个调用有道云 LLM 翻译 API 的管道，支持流式翻译和自动文本领域/风格检测。

## 功能特点

- 支持流式翻译，实时返回翻译结果
- 自动检测文本领域（文学、计算机、医学、生物、机械、金融、法律等）
- 自动检测文本风格（文学、正式、随意、简洁、丰富、技术等）
- 根据检测结果自动选择最佳翻译选项和提示词
- 支持多种语言翻译（中文、英文、日文、韩文、法文等）
- 与OpenWebUI兼容的SSE格式输出

## 安装要求

- Python 3.6+
- requests库

## 安装方法

```bash
pip install requests
```

## 配置

在使用前，需要设置以下环境变量或通过阀门配置：

- `YOUDAO_APP_KEY`: 有道API的应用密钥
- `YOUDAO_APP_SECRET`: 有道API的应用密钥
- `YOUDAO_TARGET_LANG`: 目标语言代码（默认为"zh"，即中文）

## 使用方法

### 基本用法

```python
from manifold.YoudaoTranslateLLM import Pipeline

# 初始化管道
pipeline = Pipeline()

# 设置API密钥（如果未通过环境变量设置）
pipeline.valves.APP_KEY = "your_app_key"
pipeline.valves.APP_SECRET = "your_app_secret"

# 调用翻译
result = pipeline.pipe("Hello, world!", "youdao-translate", [], {})

# 处理流式结果
for chunk in result:
    print(chunk.decode('utf-8'), end='')
```

### 本地测试

```bash
python -m manifold.YoudaoTranslateLLM
```

## 支持的领域和风格

### 领域检测

- 文学：包含情感、自然、艺术等关键词
- 计算机：包含程序、代码、软件等关键词
- 医学：包含病人、疾病、治疗等关键词
- 生物：包含细胞、基因、蛋白质等关键词
- 机械：包含机器、引擎、设备等关键词
- 金融：包含股票、债券、投资等关键词
- 法律：包含法律、合同、协议等关键词

### 风格检测

- 文学：包含隐喻、比喻、意象等关键词
- 正式：包含因此、从而、据此等关键词
- 随意：包含嘿、酷、棒等关键词
- 简洁：包含简短、简单、直接等关键词
- 丰富：包含详细、全面、深入等关键词
- 技术：包含参数、变量、函数等关键词

## 语言代码映射

- 'zh': 'zh-CHS' (中文)
- 'en': 'en' (英文)
- 'ja': 'ja' (日文)
- 'ko': 'ko' (韩文)
- 'fr': 'fr' (法文)

## 错误处理

管道会处理以下错误情况：

- API调用失败（HTTP错误）
- JSON解析错误
- 网络连接异常
- 其他未预期的异常

所有错误都会以OpenWebUI兼容的SSE格式返回，包含适当的错误信息。
# TXT2EPUB Pro (Modular Edition)

**TXT2EPUB Pro** 是一个专业级的小说转换工具，旨在将 `.txt` 文本文件高质量地转换为 `.epub` 电子书格式。

本项目采用了模块化架构设计（MVC 变体），不仅具备极高的稳定性与扩展性，还针对中文网络小说的排版、编码和元数据进行了深度优化。

## 核心特性

*   **智能章节识别**：基于预编译正则引擎，精准识别“第X章/节/回”等中文目录格式，自动生成 EPUB 目录（TOC）。
*   **工程级健壮性**：内置 `get_app_root` 路径锚定技术，无论是在 IDE 中运行还是打包成 EXE，均能准确读写文件，彻底解决路径报错问题。
*   **智能编码探测**：自动处理 UTF-8 与 GB18030/GBK 编码，告别乱码困扰。
*   **进度无损重制**：基于“书名+作者”生成确定性 UUID，重新生成书籍后，阅读器（如 iBooks, Kindle, 多看）仍能保留高亮与阅读进度。
*   **资源自动嵌入**：
    *   **封面**：自动探测同名图片或 `cover.jpg`。
    *   **字体**：支持嵌入自定义 `.ttf/.otf` 字体，并在 CSS 中自动引用。
*   **批量处理**：支持单本转换与目录下所有文件的一键批量转换。

## 项目结构

本项目采用了分离关注点（Separation of Concerns）的模块化设计：

```text
txt2epub_pro/
│
├── main.py           # [入口] 程序控制器，负责用户交互与流程调度
├── converter.py      # [核心] 业务逻辑层，封装了 EPUB 生成与文本解析逻辑
├── utils.py          # [工具] 底层工具库，处理路径锚定、文件名清洗等
│
├── input/            # [自动生成] 存放待转换的 .txt 小说
├── output/           # [自动生成] 存放转换完成的 .epub 电子书
├── fonts/            # [自动生成] 存放自定义字体文件 (.ttf)
│
└── requirements.txt  # 依赖说明
```

## 快速开始

### 1. 环境准备

确保你的电脑已安装 Python 3.6 或以上版本。

安装核心依赖库 `EbookLib`：

```bash
pip install EbookLib
```

### 2. 运行程序

在终端或命令行中进入项目目录，运行：

```bash
python main.py
```

程序启动后，会自动创建 `input`, `output`, `fonts` 三个文件夹。

### 3. 开始转换

1.  将你的小说文件（`.txt`）放入 `input` 文件夹。
2.  (可选) 将封面图片放入同目录。
3.  在终端按提示操作即可。

## 进阶功能指南

### 自动封面 (Cover)
程序按以下优先级查找封面：
1.  **同名图片**：如果小说叫 `凡人修仙传.txt`，程序会优先寻找 `凡人修仙传.jpg` (或 .png)。
2.  **通用封面**：如果没有同名图片，程序会寻找 `cover.jpg`。

### 自定义字体 (Fonts)
1.  将字体文件（例如 `KaiTi.ttf`）放入 `fonts` 文件夹。
2.  运行程序时，选择对应的字体序号。
3.  生成的 EPUB 会自动嵌入该字体，并设置为全文默认字体。

### 打包为 EXE (推荐)
得益于 `utils.py` 中的路径处理逻辑，你可以轻松将其打包为独立可执行文件分享给他人：

```bash
pip install pyinstaller
pyinstaller -F main.py -n "TXT2EPUB_Converter"
```
打包后的 EXE 文件可以直接在任何 Windows 电脑上运行，无需安装 Python。

## 架构设计说明 (For Developers)

本重构版本解决了旧版单文件脚本的以下痛点：

1.  **解耦 (Decoupling)**：
    *   `converter.py` 不包含任何 `input()` 或 `print()` 交互逻辑，使其可以轻松被移植到 Web 后端或 GUI 界面（如 PyQt/Tkinter）中。
    *   `utils.py` 隔离了操作系统层面的差异。

2.  **安全性 (Safety)**：
    *   引入 `sanitize_filename`，防止恶意文件名（如包含 `../../` 或 `|`）导致的文件系统错误。
    *   显式的异常捕获机制，防止单本书籍的错误中断整个批量任务。

## 依赖库

*   [EbookLib](https://github.com/aerkalov/ebooklib): 用于生成 EPUB 容器的核心库。

## License

MIT License. 欢迎用于个人学习或二次开发。

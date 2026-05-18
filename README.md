# HUST-Template-of-Thesis

这是一个基于 LaTeX 的华中科技大学本科毕业论文模板。模板包含封面、原创性声明、中文摘要、英文摘要、目录、正文、参考文献、致谢和附录等常见部分，并提供一套从 LaTeX 导出 Word（DOCX）的辅助流程。

本文档按日常使用顺序组织：先说明如何使用 LaTeX 模板完成论文写作和 PDF 编译，再说明如何把同一份论文内容转换为 Word。

**注意：本项目纯 ai 生成，仅供参考。请务必根据最新的学校和学院要求进行调整，并在提交前仔细检查论文格式和内容是否符合规范。**

## 目录结构

```text
.
├── main.tex                         # LaTeX 主入口：封面信息、章节顺序、PDF 编译入口
├── macros.sty                       # 自定义宏与常用命令
├── ref.bib                          # 参考文献数据库
├── body/                            # 正文、摘要、致谢、附录等章节文件
├── images/                          # 图片资源
├── template/                        # 学位论文模板类与封面样式
├── word.tex                         # DOCX 转换入口
├── hust-template.docx               # DOCX 参考模板
├── scripts/                         # DOCX 转换与后处理脚本
├── pandoc-word-macros.tex           # Pandoc 转 Word 专用宏
├── pandoc-image-fallback.lua        # DOCX 图片回退过滤器
└── numeric-superscript-brackets.csl # DOCX 参考文献引用样式
```

## LaTeX 模板使用方法

### 环境要求

建议使用 Windows + VS Code 编写，也可以在其他支持 XeLaTeX 的环境中编译。

必需环境：

1. TeX Live 或 MiKTeX。
2. XeLaTeX，用于编译中文论文。
3. Biber，用于处理 `biblatex` 参考文献。
4. 常见中文字体。Windows 通常已经包含宋体、黑体、楷体等字体；非 Windows 环境需要自行安装并确认 LaTeX 能找到这些字体。

推荐工具：

1. VS Code。
2. LaTeX Workshop 插件。
3. Git，用于版本管理。

### 快速开始

1. 克隆或下载本仓库。
2. 用 VS Code 打开仓库根目录。
3. 安装 LaTeX Workshop 插件。
4. 确认 `xelatex` 和 `biber` 已加入系统 `PATH`。
5. 修改 `main.tex` 中的论文信息。
6. 修改 `body/` 下的正文文件。
7. 使用 LaTeX Workshop 的 `XeLaTeX -> Biber -> XeLaTeX*2` recipe 编译。

也可以在终端中手动编译：

```powershell
xelatex -synctex=1 -interaction=nonstopmode -file-line-error -shell-escape main.tex
biber main
xelatex -synctex=1 -interaction=nonstopmode -file-line-error -shell-escape main.tex
xelatex -synctex=1 -interaction=nonstopmode -file-line-error -shell-escape main.tex
```

编译成功后会生成 `main.pdf`。本仓库的 `.gitignore` 默认忽略 PDF、LaTeX 中间文件和 DOCX 输出文件。

### VS Code 配置示例

如果你的 LaTeX Workshop 没有自动识别编译流程，可以在本地 `.vscode/settings.json` 中配置：

```json
{
  "latex-workshop.latex.tools": [
    {
      "name": "xelatex",
      "command": "xelatex",
      "args": [
        "-synctex=1",
        "-interaction=nonstopmode",
        "-file-line-error",
        "-shell-escape",
        "main.tex"
      ]
    },
    {
      "name": "biber",
      "command": "biber",
      "args": ["main"]
    }
  ],
  "latex-workshop.latex.recipes": [
    {
      "name": "XeLaTeX -> Biber -> XeLaTeX*2",
      "tools": ["xelatex", "biber", "xelatex", "xelatex"]
    },
    {
      "name": "XeLaTeX",
      "tools": ["xelatex"]
    }
  ],
  "latex-workshop.latex.recipe.default": "first"
}
```

### 修改论文基本信息

论文题目、作者、学院、班级、学号、指导教师和日期都在 `main.tex` 中维护：

```tex
\title{这是标题这是标题这是标题}
\author{小岳岳}
\school{计算机科学与技术}
\classnum{计科 2201}
\stunum{U202215102}
\instructor{郭德纲}
\date{2026年5月7日}
```

封面和原创性声明由模板命令生成：

```tex
\maketitle
\authorization
```

如果论文需要保密声明，可以使用：

```tex
\authorization[x]
```

其中 `x` 表示保密年限。

### 编写正文

正文内容主要放在 `body/` 目录中。默认文件包括：

1. `body/abstract-ch.tex`：中文摘要。
2. `body/abstract-en.tex`：英文摘要。
3. `body/introduction.tex`：绪论。
4. `body/related_works.tex`：相关工作。
5. `body/method.tex`：方法。
6. `body/experiments.tex`：实验。
7. `body/conclusion.tex`：结论。
8. `body/references.tex`：参考文献标题与打印入口。
9. `body/acknowledgement.tex`：致谢。
10. `body/appendices.tex`：附录。

章节顺序在 `main.tex` 中通过 `\include{...}` 控制：

```tex
\include{body/introduction}
\include{body/related_works}
\include{body/method}
\include{body/experiments}
\include{body/conclusion}
```

新增章节时，建议先在 `body/` 下新建一个独立 `.tex` 文件，再把它加入 `main.tex`。如果后续还要导出 Word，也需要同步加入 `word.tex`。

### 图片、表格、公式和引用

图片建议放在 `images/` 目录中，再通过 LaTeX 正常引用。图片文件名尽量使用英文、数字、下划线或连字符，避免空格和特殊符号。

参考文献统一写在 `ref.bib` 中，正文中使用 `\cite{...}` 引用。模板默认使用 `biblatex + gb7714-2015`，并已按学校常见要求调整为：

1. 作者姓名按“姓在前，名在后”显示。
2. 作者超过 3 人时显示前 3 人并自动追加“等”或 `et al`。
3. 默认关闭 `[J]`、`[M]` 等文献类型标识。

常见 BibTeX 条目示例：

```bibtex
@article{example-article,
  author       = {张三 and 李四 and 王五 and 赵六},
  title        = {文章名称},
  journaltitle = {期刊名称},
  year         = {2024},
  volume       = {10},
  number       = {2},
  pages        = {100-120}
}
```

```bibtex
@book{example-book,
  author    = {张三 and 李四 and 王五 and 赵六},
  title     = {书名},
  edition   = {2},
  translator= {某某},
  location  = {北京},
  publisher = {某出版社},
  year      = {2024},
  pages     = {1-20}
}
```

```bibtex
@thesis{example-thesis,
  author      = {作者},
  title       = {题名},
  type        = {硕士学位论文},
  institution = {华中科技大学},
  location    = {武汉},
  year        = {2024}
}
```

### LaTeX 模板边界

本模板面向华中科技大学本科毕业论文的常规写作场景，重点覆盖版式和常用结构，但仍有以下边界：

1. 学校或学院格式要求如果发生变化，需要以最新正式要求为准。
2. 不同操作系统、TeX 发行版和字体环境可能导致 PDF 细节略有差异。
3. 模板不自动判断论文内容是否符合学院审查要求。
4. 复杂浮动体、超宽表格、大量子图或特殊宏包可能需要手动微调。
5. 如果直接修改 `template/` 下的模板核心文件，需要自行验证封面、页眉页脚、目录、参考文献和页码是否仍然正确。

## LaTeX 转 Word（DOCX）

### 适用场景

仓库内置的 DOCX 流程用于把当前 LaTeX 论文转换成可编辑的 Word 文档。它不是简单调用 Pandoc，而是在 Pandoc 转换后继续做一系列 Word 格式后处理，以尽量贴近本模板的论文版式。

适合使用 DOCX 导出的情况：

1. 学院或导师要求提交 Word 文件。
2. 需要在 Word 中继续审阅、批注或做少量格式修订。
3. 希望复用同一份 LaTeX 正文生成 PDF 和 DOCX。

不适合完全依赖 DOCX 自动导出的情况：

1. 论文使用了大量自定义 LaTeX 宏，且这些宏没有在 `pandoc-word-macros.tex` 中提供 Pandoc 兼容写法。
2. 版面强依赖 LaTeX 浮动机制，例如非常复杂的跨页图表、特殊子图布局或手工排版。
3. Word 文件必须做到和 PDF 每一页完全一致。当前目标是“结构和主要格式可用”，不是像素级复刻 PDF。

### 环境要求

DOCX 转换建议在 Windows 上运行。必需环境：

1. PowerShell。
2. Python 3，并确保 `python` 可以在终端中直接调用。
3. Pandoc，并确保 `pandoc` 可以在终端中直接调用。
4. Microsoft Word 桌面版，用于通过 COM 更新目录、域代码并填充封面信息。
5. `hust-template.docx`，作为 Word 输出的参考模板。

可选环境：

1. Poppler 的 `pdftoppm`，用于把 `images/*.pdf` 渲染成 DOCX 更稳定的 PNG 回退图。
2. 如果没有 `pdftoppm`，转换流程会继续运行，但 PDF 图片可能依赖 Pandoc 自身处理能力；建议为 PDF 图片准备同名 PNG 或 SVG。

运行前请关闭目标 DOCX 文件。如果 `main.docx` 正在 Word 中打开，脚本可能无法覆盖它。

### 一键导出

在仓库根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\convert_to_docx.ps1
```

默认行为：

1. 读取 `main.tex` 中的封面信息。
2. 读取 `word.tex` 作为 Pandoc 转换入口。
3. 使用 `hust-template.docx` 作为参考 Word 模板。
4. 生成 `.docx-build/` 中间文件。
5. 输出 `main.docx`。
6. 使用 Word 更新目录和域代码。
7. 运行最终格式修复脚本。

指定输出文件：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\convert_to_docx.ps1 -Output thesis.docx
```

常用参数：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\convert_to_docx.ps1 `
  -Output thesis.docx `
  -MainTex main.tex `
  -WordTex word.tex `
  -ReferenceDoc hust-template.docx
```

如果当前机器没有 Word，或只想生成未经 Word 更新目录和域代码的中间结果，可以使用：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\convert_to_docx.ps1 -SkipWordUpdate
```

注意：`-SkipWordUpdate` 会降低最终 DOCX 的完整度，目录、域代码和封面填充可能不完整。

### `word.tex` 的维护方式

`word.tex` 是 DOCX 转换专用入口，不是 PDF 编译入口。它不包含 `\documentclass`，也不生成封面和目录，而是把正文内容交给 Pandoc 转换：

```tex
\input{pandoc-word-macros.tex}

\section*{摘  要}
\input{body/abstract-ch}

\section*{Abstract}
\input{body/abstract-en}

\input{body/introduction}
\input{body/related_works}
\input{body/method}
\input{body/experiments}
\input{body/conclusion}
\input{body/references}
\input{body/acknowledgement}
```

维护原则：

1. `main.tex` 负责 PDF 的完整论文结构。
2. `word.tex` 负责 DOCX 的正文转换顺序。
3. 新增、删除或重排章节时，同时检查 `main.tex` 和 `word.tex`。
4. 只在 `word.tex` 中放 Pandoc 能理解的内容入口；不要把 LaTeX 封面、目录和页码命令搬进去。
5. DOCX 专用宏优先放在 `pandoc-word-macros.tex`，避免影响 PDF 编译。

### DOCX 流程会处理的格式

当前脚本会尽量处理这些常见问题：

1. 复用 `hust-template.docx` 中的封面、原创性声明、页眉页脚和正文样式。
2. 从 `main.tex` 读取标题、作者、学院、班级、学号、指导教师和日期，并填入 Word 封面。
3. 中文摘要、英文摘要和目录使用罗马页码，正文从阿拉伯数字第 1 页重新编号。
4. 目录只收录一级和二级标题。
5. 参考文献引用显示为黑色上标方括号编号。
6. 图、表、公式、算法交叉引用尽量转换为论文中的可读编号。
7. 独立公式居中显示，并在右侧显示章内编号。
8. 表格转换为 Word 三线表，顶线和底线较粗，中间线较细。
9. 表格中文使用宋体，英文和数字使用 Times New Roman。
10. 图片段落居中，并尽量保留 LaTeX 中 `\includegraphics[width=...]` 的宽度比例。
11. PDF 图片会优先使用 `.docx-build/pdf-images/` 中生成的 PNG 回退图。
12. 超链接样式会尽量去除蓝色和下划线，但保留内部跳转目标。

### DOCX 转换边界

DOCX 流程的目标是生成可提交、可继续编辑的 Word 文档，但它不是完整的 LaTeX 排版引擎。需要注意：

1. Word 和 LaTeX 的分页、浮动体、公式布局机制不同，页数和换页位置可能不同。
2. Pandoc 不能理解所有 LaTeX 宏；复杂自定义命令需要在 `pandoc-word-macros.tex` 或转换脚本中补兼容逻辑。
3. 很宽的表格可能需要人工检查。必要时可在仓库根目录新增 `docx-table-widths.json` 覆盖列宽比例。
4. 复杂图片布局、子图、跨页算法和超长表格需要人工打开 Word 检查。
5. 如果 Word 自动更新域后改写了某些样式，脚本会做最终修复，但仍建议人工抽查目录、页码、图表题注、公式编号和参考文献。
6. 非 Windows 环境通常无法使用 Word COM，因此不能完整执行封面填充和目录更新。

复杂表格列宽覆盖示例：

```json
{
  "chart:example": [1600, 2400, 2900, 1412]
}
```

键名使用 LaTeX 表格的 `\label{...}`，数组表示列宽比例。脚本会把这些数值缩放到正文宽度内，避免表格超出页面。

### 导出后检查清单

生成 `main.docx` 后，建议至少检查：

1. Word 能正常打开文件。
2. 封面信息是否正确。
3. 原创性声明页是否保留。
4. 中文摘要、英文摘要、目录和正文页码是否正确。
5. 目录是否只包含需要的标题层级。
6. 图题、表题、公式编号、算法编号是否符合预期。
7. 参考文献引用是否为上标方括号编号。
8. 表格是否超出页面，数字和英文是否异常换行。
9. 图片是否清晰，PDF 图片是否成功回退为 PNG。
10. 致谢、参考文献和附录顺序是否正确。

如果发现 DOCX 中某一类格式反复不理想，优先修复 `scripts/` 中的转换脚本或 `pandoc-word-macros.tex`，再重新运行一键导出流程。

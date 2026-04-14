# HUST-Template-of-Thesis
这是一个基于 LaTeX 的华中科技大学毕业论文模板，适用于本科生。模板包含了封面、原创页、目录、摘要、正文、参考文献等常见部分，并且提供了示例内容和格式设置，方便同学们快速撰写毕业论文。

此仓库 fork 自 [template-of-thesis](https://github.com/SukunaShinmyoumaru-hust/template-of-thesis)，并在此基础上进行了修改和完善，以更好地适应华中科技大学的毕业论文要求。

## 使用方法

### VS Code

#### 即开即用版
1. 克隆或下载此仓库到本地。
2. 使用 VS Code 打开项目文件夹。
3. 安装 LaTeX Workshop 插件（如果尚未安装）。
4. 配置 .vscode/settings.json 文件，设置 LaTeX 编译器路径（如 TeX Live 或 MiKTeX）。
参考配置实例：
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
      "args": [
        "main"
      ]
    }
  ],
  "latex-workshop.latex.recipes": [
    {
      "name": "XeLaTeX -> Biber -> XeLaTeX*2",
      "tools": [
        "xelatex",
        "biber",
        "xelatex",
        "xelatex"
      ]
    },
    {
      "name": "XeLaTeX",
      "tools": [
        "xelatex"
      ]
    }
  ],
  "latex-workshop.latex.recipe.default": "first",
}
```
#### 进阶配置版（开发者用）

面向长期维护此仓库并持续同步上游模板的用户。目标是：在保留个人论文内容与格式定制的同时，尽量降低 merge 冲突。

##### 一、推荐分支模型

建议长期维护两个分支：

1. `template-sync`：只用于同步上游模板，不写个人论文内容。
2. `thesis`：个人写作分支，放置论文正文与个人定制。

建议关系如下：

- `upstream/main` -> 同步到 `template-sync` -> 再合并到 `thesis`

##### 二、目录与文件约定（核心）

为减少与上游示例文本冲突，建议采用“模板文件不动，个人文件新增”的策略。

1. 尽量不直接改模板示例正文文件（如 `body/abstract-ch.tex`、`body/introduction.tex`）。
2. 新建个人正文文件（建议使用统一前缀，例如 `body/my-abstract-ch.tex`、`body/my-introduction.tex`）。
3. 在 `main.tex` 中只引用个人文件。
4. 模板文件保留为参考，便于后续手动吸收上游改进。

> 说明：
> 不建议把现有模板文件“整体重命名”为 template 前缀版本再继续修改。
> 这会让 Git 更难识别上游后续改动与本地历史的对应关系，反而增加冲突处理成本。

##### 三、首次迁移步骤（把正文与模板解耦）

1. 在 `body/` 下复制出个人文件（内容先与模板一致）。
2. 修改 `main.tex`，将 `\\input` 或 `\\include` 指向个人文件。
3. 之后仅在个人文件中写作。
4. 模板示例文件只在需要时查看，不作为日常写作入口。

##### 四、日常同步上游流程（低冲突）

```bash
# 0) 仅首次：添加上游仓库
git remote add upstream <上游仓库地址>

# 1) 拉取上游最新
git fetch upstream

# 2) 切到模板同步分支并合并上游
git checkout template-sync
git merge upstream/main

# 3) 切回个人写作分支，吸收模板更新
git checkout thesis
git merge template-sync
```

若你的主开发分支不是 `thesis`，将命令中的分支名替换为你实际使用的分支即可。

##### 五、冲突处理原则

1. 个人正文文件（如 `body/my-*.tex`）优先保留个人版本。
2. 模板类文件（如 `template/hust.cls`）优先吸收上游，再做最小化本地补丁。
3. 若冲突发生在 `main.tex`，保持“引用个人正文文件”的入口不变。
4. 解决冲突后先完整编译一次，再提交。

##### 六、推荐 Git 配置

启用 rerere，Git 会记录你过去的冲突解决方式，在后续类似冲突中自动复用：

```bash
git config --global rerere.enabled true
```

可选：在仓库内设置默认拉取策略（避免无意 rebase 或不一致行为）：

```bash
git config pull.rebase false
```

##### 七、提交规范建议

建议把提交拆成三类，便于追踪和回滚：

1. `chore(sync): merge upstream/main into template-sync`
2. `chore(merge): merge template-sync into thesis`
3. `feat(thesis): update chapter content` / `style(format): adjust local thesis style`

##### 八、适合放本地覆盖层的改动

以下改动优先放在你自己的宏包或样式文件中，而不是直接改模板核心文件：

1. 行距、段间距、标题间距微调。
2. 自定义命令与术语宏。
3. 图表标题格式与编号显示细节。
4. 个人写作辅助命令（如 TODO 标记、术语高亮等）。

这样做能显著降低上游模板更新时的冲突概率。


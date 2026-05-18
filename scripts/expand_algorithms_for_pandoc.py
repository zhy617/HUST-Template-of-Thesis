from __future__ import annotations

import re
import sys
from pathlib import Path


INPUT_RE = re.compile(r"\\(?:input|include)\{([^}]+)\}")
EVENT_RE = re.compile(r"\\section\*?\{|\\begin\{algorithm\}")


def read_tex(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def resolve_tex_path(root: Path, current_dir: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.suffix == "":
        candidate = candidate.with_suffix(".tex")
    if not candidate.is_absolute():
        local = current_dir / candidate
        candidate = local if local.exists() else root / candidate
    return candidate.resolve()


def flatten_inputs(path: Path, root: Path, seen: set[Path] | None = None) -> str:
    seen = seen or set()
    path = path.resolve()
    if path in seen:
        return ""
    seen.add(path)
    text = read_tex(path)

    def repl(match: re.Match[str]) -> str:
        child = resolve_tex_path(root, path.parent, match.group(1))
        if not child.exists():
            return match.group(0)
        return "\n" + flatten_inputs(child, root, seen) + "\n"

    return INPUT_RE.sub(repl, text)


def strip_latex_comment_lines(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("%"))


def find_balanced_brace(text: str, open_brace: int) -> int:
    depth = 0
    escaped = False
    for index in range(open_brace, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("Unbalanced TeX braces")


def command_argument(text: str, command: str) -> str | None:
    pos = text.find(command)
    if pos < 0:
        return None
    brace = text.find("{", pos + len(command))
    if brace < 0:
        return None
    end = find_balanced_brace(text, brace)
    return text[brace + 1 : end]


def strip_latex_caption(caption: str) -> str:
    caption = caption.replace(r"\%", "%").replace(r"\to", "→")
    caption = re.sub(r"\\[a-zA-Z]+", "", caption)
    return caption.replace("{", "").replace("}", "").strip()


def expand_algorithm_block(block: str, number: str) -> str:
    caption = command_argument(block, r"\caption") or "算法"
    label = command_argument(block, r"\label")
    caption_text = strip_latex_caption(caption)
    alg_match = re.search(r"\\begin\{algorithmic\}(?:\[[^\]]+\])?(.*?)\\end\{algorithmic\}", block, re.S)
    if not alg_match:
        return block

    states: list[str] = []
    pending: list[str] = []
    for raw_line in alg_match.group(1).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        state = re.match(r"\\State\b\s*(.*)", line)
        if state:
            if pending:
                states.append(" ".join(pending).strip())
            pending = [state.group(1).strip()]
        elif pending:
            pending.append(line)
    if pending:
        states.append(" ".join(pending).strip())
    if not states:
        return block

    label_tex = f"\\label{{{label}}}" if label else ""
    items = "\n".join(f"\\item {state}" for state in states)
    return (
        "\n\\begin{center}\n"
        f"\\textbf{{算法 {number} {caption_text}}}{label_tex}\n"
        "\\end{center}\n\n"
        "\\begin{enumerate}\n"
        f"{items}\n"
        "\\end{enumerate}\n"
    )


def expand_algorithms(text: str) -> str:
    out: list[str] = []
    pos = 0
    chapter = 0
    algorithm_count = 0

    while True:
        match = EVENT_RE.search(text, pos)
        if not match:
            out.append(text[pos:])
            break

        if match.group(0).startswith(r"\section"):
            out.append(text[pos : match.end()])
            if not match.group(0).startswith(r"\section*"):
                chapter += 1
                algorithm_count = 0
            pos = match.end()
            continue

        block_end_token = r"\end{algorithm}"
        block_end = text.find(block_end_token, match.end())
        if block_end < 0:
            out.append(text[pos:])
            break
        block_end += len(block_end_token)
        block = text[match.start() : block_end]
        algorithm_count += 1
        number = f"{chapter}-{algorithm_count}" if chapter > 0 else str(algorithm_count)
        out.append(text[pos : match.start()])
        out.append(expand_algorithm_block(block, number))
        pos = block_end

    return "".join(out)


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: expand_algorithms_for_pandoc.py INPUT_TEX OUTPUT_TEX", file=sys.stderr)
        return 2

    root = Path.cwd()
    input_path = Path(sys.argv[1])
    if not input_path.is_absolute():
        input_path = root / input_path
    output_path = Path(sys.argv[2])
    if not output_path.is_absolute():
        output_path = root / output_path

    flat = strip_latex_comment_lines(flatten_inputs(input_path, root))
    expanded = expand_algorithms(flat)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(expanded, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

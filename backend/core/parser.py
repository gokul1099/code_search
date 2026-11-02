from __future__ import annotations

import ast
from dataclasses import asdict, dataclass, replace
from pathlib import Path

MAX_LINES = 150   # longer chunks are cut into windows so each one stays embeddable
WINDOW = 60       # size of those windows
OVERLAP = 10      # lines shared by neighbouring windows


@dataclass
class Chunk:
    id: str                       # "app/auth.py::UserService.login"
    path: str                     # "app/auth.py"
    type: str                     # "module" | "class" | "function" | "method"
    name: str                     # "login"
    qualname: str                 # "UserService.login"
    start_line: int
    end_line: int
    code: str                     # text that will be embedded and shown to the LLM
    signature: str = ""
    docstring: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _segment(lines: list[str], start: int, end: int) -> str:
    return "\n".join(lines[start - 1:end])   # AST lines are 1-based, lists are 0-based


def _start_line(node) -> int:
    """Include decorators: in Python 3.8+ node.lineno points at 'def', not '@'."""
    return min([d.lineno for d in node.decorator_list] + [node.lineno])


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{prefix} {node.name}({ast.unparse(node.args)}){ret}"


def _definition(node, path: str, lines: list[str], parent: str, in_class: bool) -> list[Chunk]:
    """One chunk per function or method. A class gets a skeleton chunk plus its methods' chunks."""
    qualname = f"{parent}{node.name}"
    start = _start_line(node)

    if not isinstance(node, ast.ClassDef):
        return [Chunk(
            id=f"{path}::{qualname}", path=path, type="method" if in_class else "function",
            name=node.name, qualname=qualname, start_line=start, end_line=node.end_lineno,
            code=_segment(lines, start, node.end_lineno),
            signature=_signature(node), docstring=ast.get_docstring(node),
        )]

    # Skeleton: class header, docstring, attributes, method signatures. Bodies live in method chunks.
    skeleton = [lines[node.lineno - 1]]
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            skeleton.append(f"    {_signature(item)}: ...")
        elif isinstance(item, ast.ClassDef):
            skeleton.append(f"    class {item.name}: ...")
        else:
            skeleton.append(_segment(lines, item.lineno, item.end_lineno))

    chunks = [Chunk(
        id=f"{path}::{qualname}", path=path, type="class", name=node.name, qualname=qualname,
        start_line=start, end_line=node.end_lineno, code="\n".join(skeleton),
        signature=lines[node.lineno - 1].strip(), docstring=ast.get_docstring(node),
    )]
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            chunks += _definition(item, path, lines, f"{qualname}.", in_class=True)
    return chunks


def _fit(chunk: Chunk) -> list[Chunk]:
    """Keep chunks embeddable: cut long ones into overlapping line windows."""
    lines = chunk.code.splitlines()
    if len(lines) <= MAX_LINES:
        return [chunk]
    pieces = []
    for n, offset in enumerate(range(0, len(lines), WINDOW - OVERLAP)):
        window = lines[offset:offset + WINDOW]
        pieces.append(replace(
            chunk,
            id=f"{chunk.id}#{n}",
            start_line=chunk.start_line + offset,
            end_line=chunk.start_line + offset + len(window) - 1,
            code="\n".join(window),
        ))
        if offset + WINDOW >= len(lines):   # this window reaches the end; later ones add nothing new
            break
    return pieces


def parse_file(path: Path, root: Path) -> list[Chunk]:
    rel = path.relative_to(root).as_posix()
    source = path.read_text(encoding="utf-8", errors="replace")
    lines = source.splitlines()
    stem = Path(rel).stem

    try:
        tree = ast.parse(source)
    except SyntaxError:
        # Can't split what we can't parse, so index the whole file as plain text.
        whole = Chunk(id=rel, path=rel, type="module", name=stem, qualname="",
                      start_line=1, end_line=max(len(lines), 1), code=source)
        return _fit(whole)

    chunks: list[Chunk] = []
    top_level = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            chunks += _definition(node, rel, lines, parent="", in_class=False)
        else:
            top_level.append(node)

    # Module chunk: imports, constants, app = FastAPI(), and other top-level code.
    if top_level:
        chunks.insert(0, Chunk(
            id=rel, path=rel, type="module", name=stem, qualname="",
            start_line=top_level[0].lineno, end_line=top_level[-1].end_lineno,
            code="\n".join(_segment(lines, n.lineno, n.end_lineno) for n in top_level),
            docstring=ast.get_docstring(tree),
        ))
    return [piece for chunk in chunks for piece in _fit(chunk)]

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass, field
from pathlib import Path


# =============================================================== models
@dataclass
class ImportRef:
    module: str | None   # "os.path", "app.db", or None for "from . import x"
    name: str | None     # imported name for "from x import name", else None
    alias: str           # the local name it is bound to in this file
    level: int = 0       # 0 = absolute, 1 = ".", 2 = "..", ...


@dataclass
class Chunk:
    id: str                       # "app/auth.py::UserService.login"
    type: str                     # "module" | "class" | "function" | "method"
    name: str                     # "login"
    qualname: str                 # "UserService.login"
    path: str                     # "app/auth.py"
    start_line: int
    end_line: int
    code: str                     # text that will be embedded and shown to the LLM
    signature: str = ""
    docstring: str | None = None
    parent_id: str | None = None  # module or class that contains this chunk
    decorators: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)          # raw names, resolved in Step 5
    bases: list[str] = field(default_factory=list)          # parent classes (classes only)
    imports: list[ImportRef] = field(default_factory=list)  # module chunks only
    parse_error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================== helpers
def _dotted_name(node: ast.AST) -> str | None:
    """foo -> 'foo', self.repo.get -> 'self.repo.get', foo()() -> None"""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _collect_calls(nodes: list[ast.AST]) -> list[str]:
    """Raw names of everything called inside these statements."""
    calls = set()
    for child in (c for n in nodes for c in ast.walk(n)):
        if isinstance(child, ast.Call):
            name = _dotted_name(child.func)
            if name:
                calls.add(name)
    return sorted(calls)


def _collect_imports(tree: ast.Module) -> list[ImportRef]:
    refs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                # "import a.b" binds "a"; "import a.b as c" binds "c"
                refs.append(ImportRef(module=a.name, name=None,
                                      alias=a.asname or a.name.split(".")[0]))
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                refs.append(ImportRef(module=node.module, name=a.name,
                                      alias=a.asname or a.name, level=node.level))
    return refs


def _start_line(node) -> int:
    """Include decorators: in Python 3.8+ node.lineno points at 'def', not '@'."""
    lines = [d.lineno for d in getattr(node, "decorator_list", [])]
    return min(lines + [node.lineno])


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{prefix} {node.name}({ast.unparse(node.args)}){ret}"


def _segment(lines: list[str], start: int, end: int) -> str:
    return "\n".join(lines[start - 1:end])   # AST lines are 1-based, lists are 0-based


# =============================================================== visitor
class _Visitor:
    def __init__(self, rel_path: str, lines: list[str]):
        self.path = rel_path
        self.lines = lines
        self.chunks: list[Chunk] = []

    def visit_body(self, body: list[ast.stmt], parent_id: str, prefix: str, in_class: bool):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._function(node, parent_id, prefix, in_class)
            elif isinstance(node, ast.ClassDef):
                self._class(node, parent_id, prefix)

    def _function(self, node, parent_id, prefix, in_class):
        qualname = f"{prefix}{node.name}"
        start, end = _start_line(node), node.end_lineno
        self.chunks.append(Chunk(
            id=f"{self.path}::{qualname}",
            type="method" if in_class else "function",
            name=node.name,
            qualname=qualname,
            path=self.path,
            start_line=start,
            end_line=end,
            code=_segment(self.lines, start, end),
            signature=_signature(node),
            docstring=ast.get_docstring(node),
            parent_id=parent_id,
            decorators=[ast.unparse(d) for d in node.decorator_list],
            calls=_collect_calls(node.body),   # body only, not decorators
        ))
        # Nested functions stay inside their parent's code; no separate chunk.

    def _class(self, node: ast.ClassDef, parent_id, prefix):
        qualname = f"{prefix}{node.name}"
        chunk_id = f"{self.path}::{qualname}"
        start, end = _start_line(node), node.end_lineno

        # Skeleton: header, docstring, class attributes, method signatures.
        # Method bodies live in their own chunks.
        skeleton = [self.lines[node.lineno - 1]]
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                skeleton.append(f"    {_signature(item)}: ...")
            elif isinstance(item, ast.ClassDef):
                skeleton.append(f"    class {item.name}: ...")
            else:
                skeleton.append(_segment(self.lines, item.lineno, item.end_lineno))

        self.chunks.append(Chunk(
            id=chunk_id,
            type="class",
            name=node.name,
            qualname=qualname,
            path=self.path,
            start_line=start,
            end_line=end,
            code="\n".join(skeleton),
            signature=self.lines[node.lineno - 1].strip(),
            docstring=ast.get_docstring(node),
            parent_id=parent_id,
            decorators=[ast.unparse(d) for d in node.decorator_list],
            bases=[ast.unparse(b) for b in node.bases],
        ))
        # Recurse into the class body: methods get "ClassName." as prefix
        self.visit_body(node.body, chunk_id, f"{qualname}.", in_class=True)


# =============================================================== entry point
def parse_file(path: Path, root: Path) -> list[Chunk]:
    rel_path = path.relative_to(root).as_posix()
    source = path.read_text(encoding="utf-8", errors="replace")
    lines = source.splitlines()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        # Still index the file as one plain-text chunk so it stays searchable.
        return [Chunk(
            id=rel_path, type="module", name=Path(rel_path).stem, qualname="",
            path=rel_path, start_line=1, end_line=max(len(lines), 1),
            code=source, parse_error=f"SyntaxError line {e.lineno}: {e.msg}",
        )]

    # Module chunk = top-level code that is NOT a function or class:
    # imports, constants, app = FastAPI(), router registration, __main__ blocks.
    top_level_nodes = [
        n for n in tree.body
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    module = Chunk(
        id=rel_path, type="module", name=Path(rel_path).stem, qualname="",
        path=rel_path, start_line=1, end_line=max(len(lines), 1),
        code="\n".join(_segment(lines, n.lineno, n.end_lineno) for n in top_level_nodes),
        docstring=ast.get_docstring(tree),
        calls=_collect_calls(top_level_nodes),
        imports=_collect_imports(tree),
    )

    visitor = _Visitor(rel_path, lines)
    visitor.visit_body(tree.body, parent_id=rel_path, prefix="", in_class=False)
    return [module, *visitor.chunks]
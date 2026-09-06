"""
entire_sim.graph_builder
-------------------------
A local stand-in for the `entire graph` CLI (definitions, callers, callees,
impact, diff). It parses a Python repository with the standard library
`ast` module and builds:

  - code_entities: every class/function/method, with file:line
  - code_relationships: CALLS edges between entities (best-effort, static)

This is deliberately dependency-free so the whole pipeline runs without
network access or an Entire Graph license. Swap this module out for real
`entire graph` CLI calls (via subprocess) when that binary is available —
the rest of the pipeline (databricks_sim, risk_engine, llm_agent) consumes
the same entity/relationship schema either way.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Entity:
    entity_id: str          # e.g. "payments.service.PaymentService.validate"
    kind: str                # "function" | "method" | "class"
    file: str
    line: int
    module: str
    signature: str = ""
    end_line: int = 0


@dataclass
class Relationship:
    source: str
    target: str
    relationship: str = "calls"
    confidence: float = 1.0


@dataclass
class RepoGraph:
    entities: dict[str, Entity] = field(default_factory=dict)
    relationships: list[Relationship] = field(default_factory=list)
    # reverse index: entity_id -> set of entity_ids that call it
    _callers: dict[str, set[str]] = field(default_factory=dict)
    # forward index: entity_id -> set of entity_ids it calls
    _callees: dict[str, set[str]] = field(default_factory=dict)

    def add_entity(self, e: Entity):
        self.entities[e.entity_id] = e

    def add_relationship(self, r: Relationship):
        self.relationships.append(r)
        self._callers.setdefault(r.target, set()).add(r.source)
        self._callees.setdefault(r.source, set()).add(r.target)

    def callers(self, entity_id: str) -> set[str]:
        return self._callers.get(entity_id, set())

    def callees(self, entity_id: str) -> set[str]:
        return self._callees.get(entity_id, set())

    def impact(self, entity_id: str, max_depth: int = 4) -> dict:
        """
        Blast-radius analysis: BFS over the caller graph (who is affected if
        this entity changes) and the callee graph (what this entity depends
        on). Mirrors `entire graph impact <symbol>`.
        """
        affected = self._bfs(entity_id, self._callers, max_depth)
        depends_on = self._bfs(entity_id, self._callees, max_depth)
        return {
            "entity": entity_id,
            "affected_entities": affected,      # things that break if entity changes
            "depends_on": depends_on,            # things entity relies on
        }

    def _bfs(self, start: str, index: dict, max_depth: int) -> list[dict]:
        seen = {start}
        frontier = [start]
        results = []
        depth = 0
        while frontier and depth < max_depth:
            depth += 1
            next_frontier = []
            for node in frontier:
                for neighbor in index.get(node, set()):
                    if neighbor in seen:
                        continue
                    seen.add(neighbor)
                    results.append({"entity_id": neighbor, "depth": depth})
                    next_frontier.append(neighbor)
            frontier = next_frontier
        return results


class _CallVisitor(ast.NodeVisitor):
    """Walks a single module's AST, recording defs and (best-effort) calls."""

    def __init__(self, module_name: str, file_path: str, graph: RepoGraph, class_name_map: dict):
        self.module_name = module_name
        self.file_path = file_path
        self.graph = graph
        self.class_name_map = class_name_map  # local var name -> class entity id, best-effort
        self.current_entity_stack: list[str] = []
        self.current_class: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef):
        entity_id = f"{self.module_name}.{node.name}"
        self.graph.add_entity(Entity(
            entity_id=entity_id, kind="class", file=self.file_path,
            line=node.lineno, module=self.module_name, signature=f"class {node.name}",
            end_line=getattr(node, "end_lineno", node.lineno),
        ))
        prev_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_func(node)

    def _visit_func(self, node):
        if self.current_class:
            entity_id = f"{self.module_name}.{self.current_class}.{node.name}"
            kind = "method"
        else:
            entity_id = f"{self.module_name}.{node.name}"
            kind = "function"
        args = [a.arg for a in node.args.args if a.arg != "self"]
        self.graph.add_entity(Entity(
            entity_id=entity_id, kind=kind, file=self.file_path,
            line=node.lineno, module=self.module_name,
            signature=f"{node.name}({', '.join(args)})",
            end_line=getattr(node, "end_lineno", node.lineno),
        ))
        self.current_entity_stack.append(entity_id)
        self.generic_visit(node)
        self.current_entity_stack.pop()

    def visit_Call(self, node: ast.Call):
        if not self.current_entity_stack:
            self.generic_visit(node)
            return
        caller = self.current_entity_stack[-1]
        target = self._resolve_call_target(node.func)
        if target:
            self.graph.add_relationship(Relationship(source=caller, target=target))
        self.generic_visit(node)

    def _resolve_call_target(self, func_node) -> str | None:
        """
        Best-effort static resolution: `self.x.method()` or `self.method()`
        or `Class().method()` chains, resolved against the class_name_map
        built during a first pass over __init__ assignments.
        """
        if isinstance(func_node, ast.Attribute):
            method_name = func_node.attr
            base = func_node.value
            if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name) and base.value.id == "self":
                attr_name = base.attr  # e.g. self.fraud_service -> "fraud_service"
                target_class = self.class_name_map.get((self.module_name, self.current_class, attr_name))
                if target_class:
                    return f"{target_class}.{method_name}"
            if isinstance(base, ast.Name) and base.id == "self" and self.current_class:
                return f"{self.module_name}.{self.current_class}.{method_name}"
        return None


def _first_pass_collect_attr_types(tree: ast.AST, module_name: str, module_class_index: dict) -> dict:
    """
    Scans `self.x = SomeClass()` assignments inside __init__ methods so we
    can later resolve `self.x.method()` calls to `<module>.SomeClass.method`.
    Returns {(module_name, class_name, attr_name): target_entity_id_prefix}
    """
    mapping = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            for item in node.body:
                if isinstance(item, (ast.FunctionDef,)) and item.name == "__init__":
                    for stmt in ast.walk(item):
                        if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                            call = stmt.value
                            if isinstance(call.func, ast.Name):
                                target_cls = call.func.id
                            elif isinstance(call.func, ast.Attribute):
                                target_cls = call.func.attr
                            else:
                                continue
                            resolved_module = module_class_index.get(target_cls, module_name)
                            for target in stmt.targets:
                                if (isinstance(target, ast.Attribute)
                                        and isinstance(target.value, ast.Name)
                                        and target.value.id == "self"):
                                    mapping[(module_name, class_name, target.attr)] = f"{resolved_module}.{target_cls}"
    return mapping


def _is_test_path(p: Path, repo_root: Path) -> bool:
    """True if p lives under a test directory or is itself a test file --
    matches 'test'/'tests' directories (any case) and 'test_*.py' / '*_test.py' filenames."""
    rel_parts = p.relative_to(repo_root).parts
    if any(part.lower() in ("test", "tests") for part in rel_parts[:-1]):
        return True
    name = p.name.lower()
    return name.startswith("test_") or name.endswith("_test.py")


def build_graph(repo_path: str) -> RepoGraph:
    """Parse every .py file under repo_path (excluding tests/) into a RepoGraph."""
    repo_path = Path(repo_path)
    py_files = [
        p for p in repo_path.rglob("*.py")
        if not _is_test_path(p, repo_path) and "__pycache__" not in p.parts
    ]

    trees = {}
    module_class_index = {}  # class_name -> module_name (assumes unique class names, fine for demo repo)
    for p in py_files:
        module_name = ".".join(p.relative_to(repo_path).with_suffix("").parts)
        if module_name.endswith("__init__"):
            continue
        try:
            src = p.read_text(errors="replace")
            tree = ast.parse(src, filename=str(p))
        except (SyntaxError, UnicodeDecodeError, OSError) as exc:
            # Don't let one unparsable file (e.g. Python 2 syntax, a
            # generated file, a binary misnamed .py) kill the whole graph.
            import logging
            logging.getLogger("impactlens").warning(f"skipping unparsable file {p}: {exc}")
            continue
        trees[(module_name, str(p.relative_to(repo_path)))] = tree
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                module_class_index[node.name] = module_name

    class_name_map = {}
    for (module_name, _file), tree in trees.items():
        class_name_map.update(_first_pass_collect_attr_types(tree, module_name, module_class_index))

    graph = RepoGraph()
    for (module_name, file_rel), tree in trees.items():
        visitor = _CallVisitor(module_name, file_rel, graph, class_name_map)
        visitor.visit(tree)

    return graph


def entities_touched_by_diff(repo_path: str, changed_files: list[str], changed_line_ranges: dict) -> list[str]:
    """
    Given files changed in a commit and their changed line ranges, return the
    entity_ids whose definitions overlap those lines. Mirrors `entire graph diff`.

    When a change falls inside a method, both the method and its enclosing
    class technically "overlap" the changed range; we prefer the most
    specific (function/method) entity and only report the class if no
    function/method inside it matched, so the report reads as "validate()
    changed" rather than the noisier "validate() and PaymentService changed".
    """
    graph = build_graph(repo_path)
    matches = []  # (entity_id, kind, span_size)
    for entity_id, entity in graph.entities.items():
        ranges = changed_line_ranges.get(entity.file, [])
        entity_end = entity.end_line or entity.line
        for (start, end) in ranges:
            if start <= entity_end and entity.line <= end:
                matches.append((entity_id, entity.kind, entity_end - entity.line))
                break

    # drop class-level matches that are strictly a superset of some
    # function/method match in the same file (i.e. the method already covers it)
    method_like = {m[0] for m in matches if m[1] in ("function", "method")}
    touched = [
        entity_id for entity_id, kind, _span in matches
        if kind in ("function", "method") or not method_like
    ]
    return touched

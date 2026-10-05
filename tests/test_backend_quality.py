import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src"


def test_dataclasses_do_not_share_modules_with_services():
    failures = []
    for path in SOURCE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
        data_classes = [
            node
            for node in classes
            if any(
                ast.unparse(decorator).startswith("dataclass")
                for decorator in node.decorator_list
            )
        ]
        if data_classes and len(data_classes) != len(classes):
            failures.append(str(path.relative_to(SOURCE)))
    assert not failures, failures


def test_backend_lines_fit_eighty_characters():
    failures = []
    for path in SOURCE.rglob("*.py"):
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if len(line) > 80:
                failures.append(f"{path.relative_to(SOURCE)}:{number}")
    assert not failures, failures


def test_backend_functions_fit_sixty_lines():
    failures = []
    for path in SOURCE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.end_lineno - node.lineno + 1 > 60:
                    failures.append(f"{path.relative_to(SOURCE)}:{node.name}")
    assert not failures, failures

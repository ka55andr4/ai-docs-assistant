import ast
import sys
from pathlib import Path


def check_readme(repo_path):
    """Find important sections missing from a repository's README."""
    readme_path = repo_path / "README.md"

    if not readme_path.is_file():
        return ["README.md is missing."]

    readme_text = readme_path.read_text(encoding="utf-8").lower()
    findings = []

    # For now, we check for section headings rather than asking AI to judge
    # the quality of the writing. That gives us predictable initial results.
    for section in ("installation", "usage"):
        if f"## {section}" not in readme_text:
            findings.append(f"README.md is missing an {section.title()} section.")

    return findings


def check_python_files(repo_path):
    """Find Python functions that have no docstring."""
    findings = []

    for file_path in repo_path.rglob("*.py"):
        # Dependencies and generated files are not part of the source
        # documentation we want to review.
        if any(part in {".git", ".venv", "__pycache__"} for part in file_path.parts):
            continue

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
        except (UnicodeError, SyntaxError) as error:
            findings.append(f"Could not scan {file_path}: {error}")
            continue

        # ast walks the Python code as a tree, so we can identify actual
        # functions instead of guessing from words in the source text.
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if ast.get_docstring(node) is None:
                    relative_path = file_path.relative_to(repo_path)
                    findings.append(
                        f"{relative_path}:{node.lineno} — "
                        f"function '{node.name}' has no docstring."
                    )

    return findings


def main():
    if len(sys.argv) != 2:
        print("Usage: python app.py PATH_TO_REPOSITORY")
        return

    repo_path = Path(sys.argv[1]).resolve()

    if not repo_path.is_dir():
        print(f"Repository folder not found: {repo_path}")
        return

    findings = check_readme(repo_path) + check_python_files(repo_path)

    print(f"Scanning: {repo_path}\n")

    if findings:
        for finding in findings:
            print(f"- {finding}")
    else:
        print("No missing documentation found.")


if __name__ == "__main__":
    main()
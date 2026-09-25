import ast
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:4b"
SKIP_FOLDERS = {".git", ".venv", "__pycache__"}


def check_readme(repo_path):
    """Find important sections missing from a repository's README."""
    readme_path = repo_path / "README.md"

    if not readme_path.is_file():
        return ["README.md is missing."]

    readme_text = readme_path.read_text(encoding="utf-8").lower()
    findings = []

    # These heading checks are predictable; they do not judge writing quality.
    for section in ("installation", "usage"):
        if f"## {section}" not in readme_text:
            findings.append(
                f"README.md is missing the {section.title()} section."
            )

    return findings


def check_python_files(repo_path):
    """Find Python functions that have no docstring."""
    findings = []

    for file_path in repo_path.rglob("*.py"):
        # Dependencies and generated files are not source files to document.
        if any(part in SKIP_FOLDERS for part in file_path.parts):
            continue

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
        except (UnicodeError, SyntaxError) as error:
            findings.append(f"Could not scan {file_path}: {error}")
            continue

        # AST identifies function definitions in actual Python syntax.
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if ast.get_docstring(node) is None:
                    relative_path = file_path.relative_to(repo_path)
                    findings.append(
                        f"{relative_path}:{node.lineno} — "
                        f"function '{node.name}' has no docstring."
                    )

    return findings


def suggest_fixes(findings):
    """Create template suggestions without using an AI model."""
    suggestions = []

    for finding in findings:
        if "Installation section" in finding:
            suggestions.append(
                "Suggested README addition:\n"
                "## Installation\n\n"
                "Describe what users need to install and how to set up the project."
            )

        elif "Usage section" in finding:
            suggestions.append(
                "Suggested README addition:\n"
                "## Usage\n\n"
                "Show how to use the project with a working example."
            )

        elif "has no docstring" in finding:
            suggestions.append(
                f"Suggested fix for {finding}\n"
                "Add a docstring describing the function's purpose, inputs, "
                "and return value."
            )

    return suggestions


def collect_context(repo_path):
    """Collect a limited amount of README and Python code for the model."""
    context = []
    readme_path = repo_path / "README.md"

    if readme_path.is_file():
        readme_text = readme_path.read_text(encoding="utf-8")
        context.append(f"README.md:\n{readme_text[:4000]}")
    else:
        context.append("README.md does not exist.")

    # Limit the prompt size so a small local model can handle it.
    python_files = [
        path
        for path in repo_path.rglob("*.py")
        if not any(part in SKIP_FOLDERS for part in path.parts)
    ]

    for file_path in python_files[:3]:
        try:
            source = file_path.read_text(encoding="utf-8")
        except UnicodeError:
            continue

        relative_path = file_path.relative_to(repo_path)
        context.append(f"{relative_path}:\n{source[:4000]}")

    return "\n\n".join(context)


def instruction_for_finding(finding):
    """Give the model one clearly defined documentation task."""
    if "Installation section" in finding:
        return (
            "Write ONLY a README section beginning with '## Installation'. "
            "Describe setup only when supported by the supplied files. "
            "Do not include Python function code or docstrings."
        )

    if "Usage section" in finding:
        return (
            "Write ONLY a README section beginning with '## Usage'. "
            "Show a short working example that imports the functions. "
            "Do not redefine functions or include their source code."
        )

    if "has no docstring" in finding:
        return (
            "Write ONLY the Python triple-quoted docstring for the named "
            "function. Describe its behavior, parameters, and return value "
            "based on the supplied source. Do not include a function "
            "definition or README heading."
        )

    return "Briefly describe how to resolve this documentation finding."


def suggest_fixes_with_ai(repo_path, findings):
    """Ask the local Ollama model for one suggestion per finding."""
    repository_context = collect_context(repo_path)
    suggestions = []

    for finding in findings:
        task_instruction = instruction_for_finding(finding)

        prompt = (
            f"{task_instruction}\n"
            "Use only facts shown in the repository content. Do not invent "
            "features, commands, arguments, or data fields. If a detail "
            "cannot be verified, write '[developer to confirm]'.\n"
            "Return only the requested documentation text.\n\n"
            f"FINDING:\n{finding}\n\n"
            f"REPOSITORY CONTENT:\n{repository_context}"
        )

        # This request goes to Ollama on this computer, not a paid cloud API.
        request_data = json.dumps(
            {
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
            }
        ).encode("utf-8")

        request = Request(
            OLLAMA_URL,
            data=request_data,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urlopen(request, timeout=180) as response:
                result = json.load(response)
        except (HTTPError, URLError, TimeoutError) as error:
            suggestions.append(
                f"Finding: {finding}\nCould not reach Ollama: {error}"
            )
            continue

        generated_text = result.get("response", "").strip()

        if generated_text:
            suggestions.append(f"Finding: {finding}\n{generated_text}")
        else:
            suggestions.append(
                f"Finding: {finding}\nNo suggestion was generated."
            )

    return "\n\n".join(suggestions)


def main():
    if len(sys.argv) not in (2, 3) or (
        len(sys.argv) == 3 and sys.argv[2] != "--ai"
    ):
        print("Usage: python app.py PATH_TO_REPOSITORY [--ai]")
        return

    repo_path = Path(sys.argv[1]).resolve()

    if not repo_path.is_dir():
        print(f"Repository folder not found: {repo_path}")
        return

    findings = check_readme(repo_path) + check_python_files(repo_path)

    print(f"Scanning: {repo_path}\n")

    if not findings:
        print("No missing documentation found.")
        return

    for finding in findings:
        print(f"- {finding}")

    if len(sys.argv) == 3:
        print("\nAI suggestions from local Ollama:\n")
        print(suggest_fixes_with_ai(repo_path, findings))
    else:
        print("\nTemplate suggestions:\n")
        for suggestion in suggest_fixes(findings):
            print(suggestion)
            print()


if __name__ == "__main__":
    main()
# AI GitHub Documentation Assistant

A Python command-line tool that scans a local repository for missing README sections and undocumented Python functions. It can print template suggestions or ask a locally running LLM to draft documentation for review.

## Features

- Checks for missing Installation and Usage sections in `README.md`
- Uses Python's syntax tree to find functions without docstrings
- Generates a separate AI suggestion for each finding using Ollama
- Prints suggestions without changing repository files

## Requirements

- Python 3.10 or later
- Ollama and the `gemma3:4b` model for AI suggestions

The template mode uses only Python's standard library and does not require Ollama.

## Setup

Install Ollama, then download the local model:

```cmd
ollama run gemma3:4b
```

Type `/bye` after the model starts. If Windows does not recognize `ollama`, use the full path to `ollama.exe`.

## Usage

From the `ai-docs-assistant` folder, scan a local repository with template suggestions:

```cmd
python app.py ..\docs-practice-repo
```

Generate AI suggestions using the local model:

```cmd
python app.py ..\docs-practice-repo --ai
```

Replace `..\docs-practice-repo` with the path to another local Python repository. The AI mode calls Ollama on your computer; it does not use a paid cloud API.

## Limitations

The scanner checks for missing headings and docstrings; it does not determine whether existing documentation is accurate or outdated. AI output can contain mistakes and must be reviewed before use. The tool does not edit files or open pull requests.
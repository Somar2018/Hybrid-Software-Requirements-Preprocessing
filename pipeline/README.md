# Requirement Review Gradio App

A Gradio-based requirement review and classification tool implemented in `app_rlhf.py`. It loads requirements from CSV or Excel files, supports manual classification and correction, and saves the reviewed result to a final CSV.

## Table of Contents

1. Overview
2. Features
3. Usage
   - Prerequisites
   - Install dependencies
   - Run the application
4. Input format
5. Output
6. App behavior
7. Notes

## Overview

This app is designed for human-assisted requirement validation and classification. Users can:

- Upload requirements in CSV or XLSX format
- Review requirement text one item at a time
- Assign or correct classification labels
- Generate automatic phrasing suggestions
- Export the final reviewed dataset to `final_result.csv`

## Features

- File upload for CSV and Excel
- Automatic detection of text, class, and subclass columns
- Manual approval or rejection of each item
- Suggestion mode for generating corrected requirement text
- Language selector integration using `myutils.i18n`
- Export reviewed tasks to CSV

## Usage

### Prerequisites

- Python 3.8 or newer
- `gradio`
- `pandas`

### Install dependencies

```powershell
cd G:\preprocessing
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install gradio pandas
```

### Run the application

```powershell
.\.venv\Scripts\python.exe app_rlhf.py
```

Then open the local Gradio URL shown in the terminal, typically:

```text
http://127.0.0.1:7861
```

## Input format

The app accepts CSV or XLSX files. It attempts to identify columns automatically using common names:

- Text: `text`, `requirement`, `requisito`
- Class: `class`, `classe`
- Subclass: `sub`, `subclass`

If the required text column is not found, the file may fail to load properly.

## Output

When the review completes, the app saves the task list to `final_result.csv` in the current working directory.

## App behavior

- `iniciar(file)`: loads the uploaded file, normalizes columns, and initializes review tasks
- `atualizar()`: shows the current task and enables the review controls
- `aprovar(tipo, subtipo, corrigido)`: approves the task with updated labels and text
- `rejeitar()`: marks the current task as rejected
- `ativar_sugestao()`: switches the interface into suggestion mode
- `sugerir(texto)`: generates a suggested corrected requirement sentence
- `guardar_sugestao(corrigido)`: saves the suggested correction and advances
- `finalizar()`: writes the completed task list to `final_result.csv`

## Notes

- The app relies on `myutils.i18n` for dynamic language support.
- The generated suggestion uses a simple template: `The system shall ...`.
- The saved CSV preserves original and corrected metadata for later analysis.

## License

Use or adapt this project under your preferred licensing terms.

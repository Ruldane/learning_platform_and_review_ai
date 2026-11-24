"""Create a reproduction project, with an explicit experiment and its source."""

import ast
import json

from app.agents.tools.paper_lab_port import ExperimentDraft
from app.core.errors import AppError


def notebook_files(url: str, experiment: ExperimentDraft) -> dict[str, str]:
    try:
        ast.parse(experiment.code)
    except SyntaxError:
        raise AppError("paper_lab_code", "The Python draft contains a syntax error.", 422) from None
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        },
        "cells": [
            {
                "id": "contexte",
                "cell_type": "markdown",
                "metadata": {},
                "source": f"# Guided experiment\n\nSource · {url}\n\n{experiment.method}\n\n"
                f"Expected result · {experiment.expected}",
            },
            {
                "id": "experience",
                "cell_type": "code",
                "metadata": {},
                "source": experiment.code,
                "outputs": [],
                "execution_count": None,
            },
        ],
    }
    return {
        "experience.ipynb": json.dumps(notebook, ensure_ascii=False, indent=2) + "\n",
        "main.py": experiment.code.rstrip() + "\n",
    }

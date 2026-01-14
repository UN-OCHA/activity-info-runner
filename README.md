# Activity Info Runner

A CLI tool for processing ActivityInfo internal logframe configurations. This tool automates the application of calculated field formulas, handling both internal schema updates and external record value calculations.

## Features

-   **Internal Calculations:** Updates form schema formulas based on configuration.
-   **External Calculations:** Fetches records, evaluates formulas locally, and generates updates for records.
-   **Dry Run Mode:** Preview changes without applying them.
-   **Expression Parsing:** Custom parser for ActivityInfo-style expressions.

## Prerequisites

-   Python 3.11 or higher
-   [uv](https://github.com/astral-sh/uv) (recommended for dependency management)

## Installation

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    cd activity-info-runner
    ```

2.  Install dependencies using `uv`:
    ```bash
    uv sync
    ```

## Configuration

Create a `.env` file in the root directory with your ActivityInfo API token:

```env
API_TOKEN=your_api_token_here
```

## Usage

Run the tool using the `main.py` script via `uv`.

### Basic Run

```bash
uv run main.py
```

### Dry Run

Preview changes without applying them:

```bash
uv run main.py --dry-run
```

### Debug Mode

Enable verbose logging:

```bash
uv run main.py --debug
```

### Combined Options

```bash
uv run main.py --dry-run --debug
```

## Project Structure

-   `main.py`: CLI entry point.
-   `actions.py`: Core logic for calculating changesets.
-   `api/`: ActivityInfo API client and models.
-   `parser/`: Expression parser and evaluator using `lark`.
-   `models.py`: Data models for changesets.

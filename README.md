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

## Running Tests

This project uses `pytest` for testing.

To run all tests:
```bash
uv run pytest
```

To run tests with coverage:
```bash
uv run pytest --cov=.
```

## Project Structure

-   `main.py`: CLI entry point.
-   `actions.py`: Core logic for calculating changesets.
-   `api/`: ActivityInfo API client and models.
-   `parser/`: Expression parser and evaluator using `lark`.
-   `models.py`: Data models for changesets.

## Language Syntax

The tool supports a custom expression language similar to Excel formulas.

### Operators

| Type       | Operators                       |
|------------|---------------------------------|
| Arithmetic | `+`, `-`, `*`, `/`              |
| Comparison | `==`, `!=`, `<`, `>`, `<=`, `>=` |
| Logical    | `&&` (AND), \|\| (OR), `!` (NOT) |

### Functions

#### Logical & Control Flow
- `IF(condition, true_value, [false_value])`
- `ANY(value1, value2, ...)` - Returns true if any argument is true.
- `COALESCE(value1, value2, ...)` - Returns the first non-null/non-empty value.

#### Math
- `SUM(number1, ...)`
- `AVERAGE(number1, ...)`
- `MIN(number1, ...)`
- `MAX(number1, ...)`
- `ROUND(number, [digits])`
- `CEIL(number)`
- `FLOOR(number)`
- `POWER(base, exponent)`
- `ISNUMBER(value)`

#### Text
- `CONCAT(text1, text2, ...)`
- `LEFT(text, number_of_chars)`
- `RIGHT(text, number_of_chars)`
- `MID(text, start_position, number_of_chars)`
- `LOWER(text)`
- `TRIM(text)`
- `TEXT(value)` - Converts value to string.
- `VALUE(text)` - Converts text to number.
- `SEARCH(find_text, within_text, [start_position])`
- `ISBLANK(value)`

#### Aggregation
- `COUNT(value1, ...)` - Counts non-empty values.
- `COUNTDISTINCT(value1, ...)` - Counts unique non-empty values.

#### Regex
- `REGEXMATCH(text, pattern)`
- `REGEXEXTRACT(text, pattern)`
- `REGEXREPLACE(text, pattern, replacement)`

#### Advanced & Cross-Form
- `LOOKUP(form_id, criteria, expression)` - Finds the first record in `form_id` matching `criteria` and evaluates `expression` against it.
- `AGGREGATE(function, form_id, criteria, expression)` - Aggregates `expression` values from all records in `form_id` matching `criteria`. Supported functions: `SUM`, `COUNT`, `AVERAGE`, `MIN`, `MAX`.

### Originating Record Reference

When using cross-form functions like `LOOKUP` or `AGGREGATE`, you can use the `@` prefix to refer to fields in the record currently being processed (the "originating" record).

Example:
`LOOKUP("target_form_id", category == @category, price)`
*This looks up the price in "target_form_id" where the category matches the current record's category.*
#!/usr/bin/env python3
"""Import student email entries from Excel into the seminar mailing database.

The script reads a spreadsheet containing student IDs and names, creates
`<ID>@<domain>` emails, and appends new entries to the active mailing list JSON
database. Column positions can be specified by header name, Excel-style letter,
or zero-based index to support different department exports.

Example:
    python3 scripts/import_students.py data/CIE-Department-PGStudentList.xls
        --id-column D --name-column E
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover - pandas should be available
    print(
        "Error: pandas is required to run this script. "
        "Install it with `pip install pandas`.",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    import semlist
except ImportError as exc:  # pragma: no cover
    print(
        "Error: Unable to import `semlist`. Please run the script from the "
        "repository root or adjust PYTHONPATH.",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import student contacts from an Excel file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "excel_path",
        type=Path,
        help="Path to the Excel file (.xls or .xlsx) that contains the student data.",
    )
    parser.add_argument(
        "--sheet",
        help="Worksheet name or index (0-based) to load. Defaults to the first sheet.",
    )
    parser.add_argument(
        "--id-column",
        default="D",
        help=(
            "Column containing the student ID. You can supply the column header, "
            "Excel letter (e.g., D), or zero-based index."
        ),
    )
    parser.add_argument(
        "--name-column",
        default="E",
        help=(
            "Column containing the student full name. Accepts header, Excel letter, "
            "or zero-based index."
        ),
    )
    parser.add_argument(
        "--email-domain",
        default="ku.ac.ae",
        help="Domain to use when constructing the email address.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help="Optional path to the mailing list JSON database to update.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report the new entries without modifying the database.",
    )
    parser.add_argument(
        "--preview",
        type=int,
        default=10,
        help="Number of sample rows to display in dry-run mode.",
    )
    return parser.parse_args()


def resolve_sheet_argument(sheet_arg: Optional[str]) -> Optional[str | int]:
    if sheet_arg is None:
        return None

    sheet_arg = sheet_arg.strip()
    if not sheet_arg:
        return None

    if sheet_arg.isdigit():
        return int(sheet_arg)

    return sheet_arg


def excel_column_to_index(column: str) -> int:
    """Convert an Excel column letter (e.g. 'D' or 'AA') to a zero-based index."""
    column = column.upper()
    if not re.fullmatch(r"[A-Z]+", column):
        raise ValueError(f"Invalid Excel column reference: '{column}'")

    index = 0
    for char in column:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def select_column(df: pd.DataFrame, spec: str) -> pd.Series:
    """Return the Series for the column described by `spec`."""
    spec = str(spec).strip()

    # Direct header match (case-sensitive to avoid ambiguity)
    headers = {str(col).strip(): idx for idx, col in enumerate(df.columns)}
    if spec in headers:
        return df.iloc[:, headers[spec]]

    # Case-insensitive header match
    lower_headers = {str(col).strip().lower(): idx for idx, col in enumerate(df.columns)}
    if spec.lower() in lower_headers:
        return df.iloc[:, lower_headers[spec.lower()]]

    # Excel letter reference
    if re.fullmatch(r"[A-Za-z]+", spec):
        idx = excel_column_to_index(spec)
        try:
            return df.iloc[:, idx]
        except IndexError as exc:
            raise ValueError(
                f"Column letter '{spec}' (index {idx}) is outside the sheet range."
            ) from exc

    # Numeric index (allow both positive ints and strings)
    if re.fullmatch(r"\d+", spec):
        idx = int(spec)
        try:
            return df.iloc[:, idx]
        except IndexError as exc:
            raise ValueError(f"Column index {idx} is outside the sheet range.") from exc

    raise ValueError(
        f"Could not resolve column '{spec}'. Use a header name, letter, or index."
    )


def normalize_student_id(raw_value) -> Optional[str]:
    """Convert the raw student ID cell to a clean string of digits."""
    if pd.isna(raw_value):
        return None

    if isinstance(raw_value, (int,)):
        return str(raw_value)

    if isinstance(raw_value, float):
        if raw_value.is_integer():
            return str(int(raw_value))
        return re.sub(r"\D+", "", f"{raw_value}")

    value_str = str(raw_value).strip()
    digits = re.sub(r"\D+", "", value_str)
    return digits or None


def clean_name(raw_value) -> Optional[str]:
    if pd.isna(raw_value):
        return None
    name = str(raw_value).strip()
    return name or None


def build_entries(
    id_series: pd.Series,
    name_series: pd.Series,
    email_domain: str,
) -> List[dict]:
    entries: List[dict] = []
    seen_emails: set[str] = set()

    for row_number, (raw_id, raw_name) in enumerate(zip(id_series, name_series), start=1):
        student_id = normalize_student_id(raw_id)
        name = clean_name(raw_name)

        if not student_id or not name:
            continue

        email = f"{student_id}@{email_domain}"
        if email.lower() in seen_emails:
            continue

        name_parts = semlist.parse_name(name)
        entries.append(
            {
                "email": email,
                "name": name,
                "full_entry": f'"{name}" <{email}>;',
                "first_name": name_parts.get("first_name", ""),
                "middle_names": name_parts.get("middle_names", ""),
                "last_name": name_parts.get("last_name", ""),
                "_row_number": row_number,  # for diagnostics
            }
        )
        seen_emails.add(email.lower())

    return entries


def load_dataframe(path: Path, sheet: Optional[str | int]) -> pd.DataFrame:
    try:
        # When sheet is None, pandas returns all sheets as a dict
        # We want to get the first (default) sheet as a DataFrame
        if sheet is None:
            result = pd.read_excel(path)
        else:
            result = pd.read_excel(path, sheet_name=sheet)
        
        # Handle case where multiple sheets are returned as dict
        if isinstance(result, dict):
            # Get the first sheet
            sheet_name = list(result.keys())[0]
            return result[sheet_name]
        
        return result
    except (ValueError, ImportError) as exc:
        message = str(exc).lower()
        if "xlrd" in message:
            print(
                "Error: pandas requires the 'xlrd' package to read .xls files. "
                "Install it with `pip install xlrd`.",
                file=sys.stderr,
            )
            raise SystemExit(1) from exc
        raise


def attach_entries_to_database(
    entries: Iterable[dict], database_path: Path
) -> Tuple[int, int]:
    data = semlist.read_mailing_list(str(database_path))
    if not data:
        raise SystemExit(f"Error: failed to load database '{database_path}'.")

    batches = data.setdefault("batches", [])
    added = 0
    skipped = 0

    for entry in entries:
        email = entry["email"]
        if semlist.is_email_exists(email, data):
            skipped += 1
            continue

        # Remove the helper metadata before saving.
        entry = {k: v for k, v in entry.items() if not k.startswith("_")}
        if batches and len(batches[-1]["emails"]) < semlist.MAX_EMAILS_PER_BATCH:
            batches[-1]["emails"].append(entry)
        else:
            batches.append(
                {
                    "id": len(batches) + 1,
                    "emails": [entry],
                }
            )
        added += 1

    if added:
        if not semlist.write_mailing_list(data, str(database_path)):
            raise SystemExit(
                f"Error: failed to write updates back to '{database_path}'."
            )

    return added, skipped


def main() -> None:
    args = parse_arguments()

    if not args.excel_path.exists():
        raise SystemExit(f"Error: spreadsheet '{args.excel_path}' not found.")

    sheet = resolve_sheet_argument(args.sheet)
    df = load_dataframe(args.excel_path, sheet)

    try:
        id_series = select_column(df, args.id_column)
        name_series = select_column(df, args.name_column)
    except ValueError as exc:
        raise SystemExit(f"Error: {exc}")

    entries = build_entries(id_series, name_series, args.email_domain)

    if not entries:
        raise SystemExit("No valid student rows were found in the spreadsheet.")

    database_path = (
        args.database.resolve()
        if args.database
        else Path(semlist.get_active_database_path()).resolve()
    )

    if args.dry_run:
        preview_count = max(args.preview, 0)
        print(f"[DRY RUN] Prepared {len(entries)} unique entries.")
        if preview_count:
            print("Sample entries:")
            for entry in entries[:preview_count]:
                print(
                    f"  Row {entry.get('_row_number')}: "
                    f"{entry['name']} <{entry['email']}>"
                )
        # Report duplicates against existing DB without mutating it.
        data = semlist.read_mailing_list(str(database_path))
        existing = 0
        if data:
            for entry in entries:
                if semlist.is_email_exists(entry["email"], data):
                    existing += 1

        print(
            f"Database: {database_path.name} | already present: {existing} "
            f"| new after import: {len(entries) - existing}"
        )
        return

    added, skipped = attach_entries_to_database(entries, database_path)
    print(
        f"Import complete. Added {added} new contact(s); "
        f"skipped {skipped} already present."
    )
    print(f"Database updated: {database_path}")


if __name__ == "__main__":
    main()

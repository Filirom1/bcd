#!/usr/bin/env python3
"""Convert "Liste des Classes" XLS export to BCD borrower import CSV.

Usage:
    python -m bcd_converters.xls_classes_to_csv <input.xls> [output.csv]

Output format: StudentID,FirstName,LastName,Class,BlockReason
"""

import csv
import re
import sys
from pathlib import Path

try:
    import xlrd
except ImportError as e:
    raise ImportError(
        "xlrd is required to convert XLS files. "
        "Install it with: pip install -e '.[converters]'"
    ) from e


def sheet_name_to_class(sheet_name: str) -> str:
    """Strip trailing year (e.g. ' 2025') from sheet name to get the class name."""
    return re.sub(r"\s*\d{4}$", "", sheet_name).strip()


def is_data_row(row: list) -> bool:
    """Return True if a row looks like a student entry (last name + first name)."""
    last_name = str(row[0]).strip()
    first_name = str(row[1]).strip() if len(row) > 1 else ""
    if not last_name or not first_name:
        return False
    # Skip header rows that contain teacher info (dashes, digits, parens)
    if any(c in last_name for c in ("–", "-", "(", ")")):
        return False
    if any(c.isdigit() for c in last_name):
        return False
    return True


def convert(input_path: Path, output_path: Path) -> int:
    wb = xlrd.open_workbook(str(input_path))
    rows = []
    student_id = 1

    for sheet in wb.sheets():
        class_name = sheet_name_to_class(sheet.name)
        for i in range(sheet.nrows):
            row = sheet.row_values(i)
            if not is_data_row(row):
                continue
            rows.append({
                "StudentID": student_id,
                "FirstName": str(row[1]).strip(),
                "LastName": str(row[0]).strip(),
                "Class": class_name,
                "BlockReason": "",
            })
            student_id += 1

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["StudentID", "FirstName", "LastName", "Class", "BlockReason"]
        )
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def main():
    if len(sys.argv) < 2:
        sys.exit(f"Usage: {sys.argv[0]} <input.xls> [output.csv]")

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        sys.exit(f"File not found: {input_path}")

    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path.with_suffix(".csv")

    count = convert(input_path, output_path)
    print(f"Exported {count} students -> {output_path}")


if __name__ == "__main__":
    main()

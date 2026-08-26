"""Table Processor - Extracts tables from PDFs and structured data files."""
import os
import pandas as pd
from typing import List


def extract_tables_from_pdf(pdf_path: str) -> List[str]:
    """Extract tables from a PDF file using pdfplumber."""
    try:
        import pdfplumber

        tables_text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                for table_num, table in enumerate(tables):
                    if table:
                        df = pd.DataFrame(table[1:], columns=table[0])
                        table_str = df.to_string(index=False)
                        tables_text.append(
                            f"[Table from PDF page {page_num + 1}, "
                            f"table {table_num + 1}]:\n{table_str}"
                        )
                        print(f"📊 Extracted table {table_num + 1} from page {page_num + 1}")

        return tables_text

    except ImportError:
        print("⚠️ pdfplumber not available, trying pandas-based extraction")
        return _extract_tables_pandas(pdf_path)

    except Exception as e:
        print(f"⚠️ PDF table extraction failed: {e}")
        return []


def _extract_tables_pandas(pdf_path: str) -> List[str]:
    """Fallback: extract tables using pandas read_html."""
    try:
        tables = pd.read_html(pdf_path)
        result = []
        for i, table in enumerate(tables):
            table_str = table.to_string(index=False)
            result.append(f"[Table {i + 1}]:\n{table_str}")
            print(f"📊 Extracted table {i + 1} via pandas")
        return result
    except Exception as e:
        print(f"⚠️ Pandas table extraction failed: {e}")
        return []


def process_csv(file_path: str) -> str:
    """Process a CSV file into a readable text format."""
    try:
        df = pd.read_csv(file_path)
        info = f"[CSV File]: {os.path.basename(file_path)}\n"
        info += f"Rows: {len(df)}, Columns: {len(df.columns)}\n"
        info += f"Columns: {', '.join(df.columns.tolist())}\n\n"
        info += df.to_string(index=False)
        return info
    except Exception as e:
        return f"[Error processing CSV]: {e}"


def process_excel(file_path: str) -> str:
    """Process an Excel file into a readable text format."""
    try:
        xl = pd.ExcelFile(file_path)
        parts = []
        for sheet_name in xl.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            part = f"[Excel Sheet]: {sheet_name}\n"
            part += f"Rows: {len(df)}, Columns: {len(df.columns)}\n\n"
            part += df.to_string(index=False)
            parts.append(part)
        return "\n\n---\n\n".join(parts)
    except Exception as e:
        return f"[Error processing Excel]: {e}"


def process_table_file(file_path: str) -> str:
    """Auto-detect table format and process accordingly."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".csv":
        return process_csv(file_path)
    elif ext in (".xlsx", ".xls"):
        return process_excel(file_path)
    elif ext == ".pdf":
        tables = extract_tables_from_pdf(file_path)
        if tables:
            return "\n\n---\n\n".join(tables)
        return "[No tables found in PDF]"
    else:
        return f"[Unsupported table format: {ext}]"


def is_table_file(file_path: str) -> bool:
    """Check if a file is a table format."""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in (".csv", ".xlsx", ".xls")
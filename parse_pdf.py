import pdfplumber
import fitz  # PyMuPDF
import json
import re
import os

# ---------- Utility Functions ----------

def is_heading(line: str) -> bool:
    """Detect headings or section titles."""
    return line.isupper() or bool(re.match(r'^\d+(\.\d+)*\s', line))

def extract_text_tables(page):
    """
    Extract all text-based tables from a page.
    Handles multi-line cells and numeric last column.
    """
    tables = []
    lines = page.extract_text().split('\n')
    table_block = []
    current_row = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if line ends with a numeric value (last column)
        if re.search(r'\d+\.?\d*$', line):
            # Complete previous row if multi-line
            if current_row:
                line = current_row + " " + line
                current_row = ""
            # Split row into columns by 2+ spaces
            row = re.split(r'\s{2,}', line)
            table_block.append(row)
        else:
            # Line does not end with number → likely continuation of previous row
            current_row += " " + line

        # Detect end of table: two consecutive empty lines or non-numeric line
        # (Handled implicitly by continuation logic)

    if table_block:
        tables.append(table_block)

    return tables

def detect_charts(page):
    """Detect images on a page (charts or graphics)."""
    images = page.get_images(full=True)
    charts = []
    for idx, img in enumerate(images, start=1):
        charts.append({
            "type": "chart",
            "description": f"Detected image #{idx}, possible chart or graphic",
            "table_data": []
        })
    return charts

# ---------- Main PDF Parsing ----------

def parse_pdf(pdf_path, output_json_path):
    document_data = {"pages": []}

    with pdfplumber.open(pdf_path) as pdf:
        pdf_fitz = fitz.open(pdf_path)  # for charts/images

        for page_num, page in enumerate(pdf.pages, start=1):
            print(f"Processing page {page_num}...")
            page_content = {"page_number": page_num, "content": []}

            # --- Extract paragraphs ---
            text = page.extract_text()
            current_section = None
            current_subsection = None
            if text:
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if is_heading(line):
                        current_section = line
                        current_subsection = None
                    elif re.match(r'^\d+\.\d+', line):
                        current_subsection = line
                    else:
                        # Exclude numeric-heavy lines (tables)
                        words = line.split()
                        num_count = len(re.findall(r'\d+\.?\d*', line))
                        if not (num_count >= 2 and num_count / len(words) > 0.3):
                            page_content["content"].append({
                                "type": "paragraph",
                                "section": current_section,
                                "sub_section": current_subsection,
                                "text": line
                            })

            # --- Extract tables ---
            text_tables = extract_text_tables(page)
            for idx, table in enumerate(text_tables, start=1):
                page_content["content"].append({
                    "type": "table",
                    "section": current_section,
                    "description": f"Text-based Table #{idx} on page {page_num}",
                    "table_data": table
                })

            # --- Detect charts/images ---
            fitz_page = pdf_fitz[page_num - 1]
            charts = detect_charts(fitz_page)
            page_content["content"].extend(charts)

            document_data["pages"].append(page_content)

    # Save JSON
    with open(output_json_path, "w", encoding="utf-8") as json_file:
        json.dump(document_data, json_file, indent=4, ensure_ascii=False)

    print(f"\nJSON saved successfully to {output_json_path}")

# ---------- Entry Point ----------
def main():
    pdf_path = r"C:\Users\Dell\Downloads\PDF Project\fund_factsheet_may2025.pdf"  # Replace with your PDF path
    output_path = r"C:\Users\Dell\Downloads\fund_data.json"
"

    if not os.path.exists(pdf_path):
        print(f"Error: PDF file '{pdf_path}' not found!")
        return

    parse_pdf(pdf_path, output_path)

if __name__ == "__main__":
    main()

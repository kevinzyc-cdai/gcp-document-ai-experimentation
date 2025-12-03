import os, json
from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION   = os.getenv("LOCATION", "us")
FORM_ID    = os.getenv("FORM_ID")
MIME_TYPE  = os.getenv("MIME_TYPE", "application/pdf")

def make_client(location: str):
    """
    Create a Document AI client.
    """
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    return documentai.DocumentProcessorServiceClient(client_options=opts)

def read_bytes(path: str) -> bytes:
    """
    Read the contents of a file and return it as bytes.
    """
    with open(path, "rb") as f:
        return f.read()

def anchor_text(text_anchor: documentai.Document.TextAnchor, full_text: str) -> str:
    """
    Convert from a text anchor and the associated full text to the corresponding string.
    The text anchor and full text must be both from the same Form Parser parse.
    """
    if not text_anchor or not text_anchor.text_segments:
        return ""
    parts = []
    for seg in text_anchor.text_segments:
        s = int(seg.start_index or 0)
        e = int(seg.end_index or 0)
        parts.append(full_text[s:e])
    return "".join(parts)

def table_to_rows(table: documentai.Document.Page.Table, full_text: str):
    """
    Convert from DocumentAI's table representation to a 2D list of strings.
    """
    rows = []
    # Header rows (if present)
    for hr in getattr(table, "header_rows", []):
        rows.append([anchor_text(c.layout.text_anchor, full_text).strip() for c in hr.cells])
    # Body rows
    for br in getattr(table, "body_rows", []):
        rows.append([anchor_text(c.layout.text_anchor, full_text).strip() for c in br.cells])
    return rows

def run_form_parser(pdf_path: str):
    """
    Run the form parser on a PDF document.
    """
    client = make_client(LOCATION)
    name   = f"projects/{PROJECT_ID}/locations/{LOCATION}/processors/{FORM_ID}"
    raw    = documentai.RawDocument(content=read_bytes(pdf_path), mime_type=MIME_TYPE)

    req = documentai.ProcessRequest(
        name=name,
        raw_document=raw
    )
    resp = client.process_document(request=req)
    doc  = resp.document

    # Full concatenated text
    full_text = doc.text or ""

    # Extract tables per page as 2D lists
    tables_by_page = {}
    page_text_by_page = {}

    for page in doc.pages:
        # extract page text
        # NEW: capture the text that belongs to this page
        if getattr(page, "layout", None) and getattr(page.layout, "text_anchor", None):
            page_text_by_page[page.page_number] = anchor_text(page.layout.text_anchor, full_text).strip()

        # extract page table
        page_tables = []
        for table in getattr(page, "tables", []):
            page_tables.append(table_to_rows(table, full_text))
        if page_tables:
            tables_by_page[page.page_number] = page_tables

    return full_text, tables_by_page, page_text_by_page

if __name__ == "__main__":
    PDF_PATH = os.getenv("PDF_PATH", "pdfs/sample_dayton_up.pdf")
    text, tables, page_text = run_form_parser(PDF_PATH)

    print(f"Characters in text: {len(text)}")
    print(f"Pages with tables: {sorted(tables.keys()) or 'none'}")

    # Save tables to JSON (2D lists)
    with open("tables.json", "w") as f:
        json.dump({"page_text": page_text, "tables": tables}, f, indent=2)
    print("Saved tables to tables.json")

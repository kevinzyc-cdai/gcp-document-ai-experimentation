import os
from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
OCR_ID = os.getenv("OCR_ID")
FORM_ID = os.getenv("FORM_ID")
MIME_TYPE = os.getenv("MIME_TYPE")


def make_client(location: str):
    """
    Creates a Document AI client for the specified location.
    """
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    return client

client = make_client(LOCATION)

def process_doc(client, project, location, processor_id, content, page_numbers=None):
    """
    Processes a document using the specified processor.
    """
    name = f"projects/{project}/locations/{location}/processors/{processor_id}"
    raw_document = documentai.RawDocument(content=content, mime_type=MIME_TYPE)
    
    if page_numbers:
        selector = documentai.ProcessOptions.IndividualPageSelector(pages=page_numbers)  # 1-based
        opts = documentai.ProcessOptions(individual_page_selector=selector)
        request = documentai.ProcessRequest(name=name, raw_document=raw_document, process_options=opts)
    else:
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)

    return client.process_document(request=request)

def get_file_content(file_path: str):
    """
    Reads the content of the specified file.
    """
    with open(file_path, "rb") as f:
        return f.read()

def run_ocr(content):
    """
    Runs OCR on the specified document.
    """
    response = process_doc(client, PROJECT_ID, LOCATION, OCR_ID, content, {1, 2})
    ocr_doc = response.document

    print("Total characters:", len(ocr_doc.text))
    print("Pages:", len(ocr_doc.pages))

    return ocr_doc

def find_tables(ocr_doc):
    """
    Finds and prints tables in the OCR document.
    """
    table_pages = []
    for page in ocr_doc.pages:
        #if getattr(page, 'tables', None) and len(page.tables) > 0:
            #table_pages.append(page.page_number)
        table_pages.append(page.page_number)

    print("OCR Found pages with tables:", table_pages)
    return table_pages

def run_form_parser(content, table_pages=None):
    """
    Runs form parsing on the specified pages (that contain tables) of the document.
    """
    fp_doc = None
    if table_pages:
        response = process_doc(client, PROJECT_ID, LOCATION, FORM_ID, content, page_numbers=table_pages)
        fp_doc = response.document
        print("Form Parser returned tables on pages:",
            [p.page_number for p in fp_doc.pages if getattr(p, "tables", None)])
    else:
        print("No table pages detected; OCR output is enough.")

    return fp_doc

def tables_for_page(page, ocr_doc, fp_doc):
    if fp_doc:
        for fp_page in fp_doc.pages:
            if fp_page.page_number == page.page_number and getattr(fp_page, "tables", None):
                return fp_page.tables
    return page.tables

def anchor_text(text_anchor, full_text):
    if not text_anchor or not text_anchor.text_segments:
        return ""
    parts = []
    for seg in text_anchor.text_segments:
        s = int(seg.start_index) if seg.start_index is not None else 0
        e = int(seg.end_index)   if seg.end_index   is not None else 0
        parts.append(full_text[s:e])
    return "".join(parts)

def page_text(doc, page):
    # Concatenate block texts in reading order
    items = []
    for b in page.blocks:
        # compute bbox for ordering
        xs = [v.x for v in b.layout.bounding_poly.vertices]
        ys = [v.y for v in b.layout.bounding_poly.vertices]
        bbox = (min(xs), min(ys), max(xs), max(ys))
        txt = anchor_text(b.layout.text_anchor, doc.text).strip()
        items.append((bbox, txt))
    # sort by y then x (top-left)
    items.sort(key=lambda it: (it[0][1], it[0][0]))
    return "\n".join(t for _, t in items if t)

def print_table(doc, table):
    # header rows
    for hr in getattr(table, "header_rows", []):
        row = []
        for c in hr.cells:
            row.append(anchor_text(c.layout.text_anchor, doc.text).strip())
        print(", ".join(row))
    # body rows
    for br in getattr(table, "body_rows", []):
        row = []
        for c in br.cells:
            row.append(anchor_text(c.layout.text_anchor, doc.text).strip())
        print(", ".join(row))

if __name__ == "__main__":
    file_path = "pdfs/sample_nextep.pdf"

    # Read the unprocessed content
    content = get_file_content(file_path)

    # Step 1: Run OCR
    ocr_doc = run_ocr(content)

    # Step 2: Find pages with tables
    table_pages = find_tables(ocr_doc)

    # Step 3: Run Form Parser on pages with tables
    fp_doc = run_form_parser(content, table_pages)

    print("\nTables per page:")
    for p in ocr_doc.pages:
        tlist = tables_for_page(p, ocr_doc, fp_doc)
        print(f"Page {p.page_number}: {len(tlist)} table(s)")
        if tlist:
            print(f"\n--- Page {p.page_number} — first table ---")
            # IMPORTANT: when using Form Parser tables, they still anchor into the original OCR doc text
            print_table(ocr_doc, tlist[0])
        

    for p in ocr_doc.pages:
        print(f"\n--- Page {p.page_number} ---")
        print(page_text(ocr_doc, p))
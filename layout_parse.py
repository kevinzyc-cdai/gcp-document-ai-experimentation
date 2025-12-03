import os
import json
from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION   = os.getenv("LOCATION") or "us"
LAYOUT_ID  = os.getenv("LAYOUT_ID")
MIME_TYPE  = os.getenv("MIME_TYPE") or "application/pdf"

def make_client(location: str):
    """
    Create a Document AI client for the specified region.
    """
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    return documentai.DocumentProcessorServiceClient(client_options=opts)

def get_file_content(file_path: str) -> bytes:
    """
    Read the bytes of a file from disk.
    """
    with open(file_path, "rb") as f:
        return f.read()

def call_layout_parser(client, content: bytes):
    """
    Call the Layout processor and return the Document JSON.
    """
    name = f"projects/{PROJECT_ID}/locations/{LOCATION}/processors/{LAYOUT_ID}"
    raw  = documentai.RawDocument(content=content, mime_type=MIME_TYPE)

    request = documentai.ProcessRequest(
        name=name,
        raw_document=raw,
        imageless_mode=True  # allows up to 30 pages in sync calls
    )
    response = client.process_document(request=request)
    return response.document

if __name__ == "__main__":
    PDF_PATH = "pdfs/sample_dayton_up.pdf"
    OUT_PATH = "layout_output.json"

    client = make_client(LOCATION)
    content = get_file_content(PDF_PATH)

    doc = call_layout_parser(client, content)
    print(f"Layout Parser returned {len(doc.pages)} page(s), {len(doc.text)} characters of text.")

    # Store the entire Document JSON to file
    with open(OUT_PATH, "w") as f:
        f.write(documentai.Document.to_json(doc))
    print(f"Wrote {OUT_PATH}")


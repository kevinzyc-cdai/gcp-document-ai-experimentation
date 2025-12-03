import json

def print_json(path):
    with open(path, "r") as f:
        data = json.load(f)
    
    blocks = data["documentLayout"]["blocks"]

    for block in blocks:
        recursive_parse(block)

def recursive_parse(obj):
    if "textBlock" in obj:
        #print("text block")
        children = obj["textBlock"]["blocks"]
        if not children:
            return
        for child in children:
            recursive_parse(child)
    elif "tableBlock" in obj:
        print("table block")
        rows = obj["tableBlock"]["bodyRows"]
        for row in rows:
            cells = row["cells"]
            cell_texts = []
            for item in cells:
                if "blocks" not in item:
                    continue
                cell = item["blocks"][0]
                text = " " * 25
                if "textBlock" in cell:
                    raw_text = cell["textBlock"]["text"].strip().replace("\n", " ")
                    text = raw_text[:22] + ("..." if len(raw_text) > 22 else " " * (25 - len(raw_text)))
                
                cell_texts.append(text)
            print(cell_texts)
        print("\n\n\n")

    
    
print_json("layout_output.json")
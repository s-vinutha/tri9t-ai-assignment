import hashlib
import re
import uuid
import pdfplumber

def compute_hash(heading: str, level: int, body_text: str) -> str:
    """Generates an immutable content hash for version staleness checks."""
    payload = f"{level}|{heading}|{body_text.strip()}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()

def clean_text(text: str) -> str:
    """Normalizes whitespace and removes structural line breaks."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_pdf_manual(pdf_path: str, version: int = 1) -> list[dict]:
    parsed_nodes = []
    current_node = None
    hierarchy = {}
    
    # Adjust this size threshold parameter based on the PDF's primary headings font size
    HEADING_FONT_SIZE_LIMIT = 12.5 

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            
            # --- 1. Extract and format tables into Markdown matrices ---
            tables = page.extract_tables()
            table_strings = []
            for table in tables:
                formatted_table = "\n"
                for row in table:
                    filtered_row = [clean_text(cell) if cell else "" for cell in row]
                    formatted_table += "| " + " | ".join(filtered_row) + " |\n"
                table_strings.append(formatted_table)
            
            # --- 2. Group page words into spatial horizontal lines ---
            words = page.extract_words(extra_attrs=["fontname", "size"])
            if not words:
                continue
                
            lines_dict = {}
            for word in words:
                top = round(word["top"], 1)
                matched_top = None
                for stored_top in lines_dict.keys():
                    if abs(stored_top - top) < 3.5:  # 3.5pt margin of error for line baseline alignment
                        matched_top = stored_top
                        break
                if matched_top is not None:
                    lines_dict[matched_top].append(word)
                else:
                    lines_dict[top] = [word]
            
            # --- 3. Process lines from top to bottom ---
            for top in sorted(lines_dict.keys()):
                line_words = sorted(lines_dict[top], key=lambda x: x["x0"])
                line_raw_text = " ".join([w["text"] for w in line_words]).strip()
                
                if not line_raw_text:
                    continue
                
                avg_font_size = sum([w["size"] for w in line_words]) / len(line_words)
                is_bold_font = any("bold" in w["fontname"].lower() for w in line_words)
                
                # Check for standard legal numbered heading formats (e.g., "1. Device Overview" or "2.1")
                heading_pattern = re.match(r'^(\d+(?:\.\d+)*)\.?\s+(.*)$', line_raw_text)
                
                if heading_pattern and (avg_font_size >= HEADING_FONT_SIZE_LIMIT or is_bold_font):
                    # Save the previous accumulated node text block before making a new one
                    if current_node:
                        current_node['content_hash'] = compute_hash(
                            current_node['heading'], current_node['level'], current_node['body_text']
                        )
                        parsed_nodes.append(current_node)
                    
                    section_num = heading_pattern.group(1)
                    heading_title = heading_pattern.group(2).strip()
                    
                    # Deduce structural level depth based on section dots (e.g. 2.1.1.1 = level 4)
                    level = len(section_num.split('.'))
                    
                    # Create a unique database identifier to safely insulate duplicate names
                    node_uuid = str(uuid.uuid4())[:8]
                    base_slug = re.sub(r'[^a-z0-9]', '_', heading_title.lower())
                    unique_node_id = f"node_{section_num.replace('.', '_')}_{base_slug}_{node_uuid}"
                    
                    # Reconstruct structural parents down the active chain hierarchy
                    parent_id = None
                    for l in range(level - 1, 0, -1):
                        if l in hierarchy:
                            parent_id = hierarchy[l]
                            break
                            
                    hierarchy[level] = unique_node_id
                    # Clear deeper trailing branch items
                    for l in list(hierarchy.keys()):
                        if l > level:
                            del hierarchy[l]
                            
                    current_node = {
                        "id": unique_node_id,
                        "version": version,
                        "heading": f"{section_num} {heading_title}",
                        "level": level,
                        "body_text": "",
                        "parent_id": parent_id
                    }
                else:
                    # Append text to the current active node body
                    if current_node:
                        if line_raw_text.startswith(("1.", "2.", "3.", "4.", "5.", "•", "-", "*")):
                            current_node['body_text'] += f"\n{line_raw_text}"
                        else:
                            # Skip plain table headers that were raw-extracted
                            if "Parameter Value" in line_raw_text or "Code Meaning" in line_raw_text:
                                continue
                            current_node['body_text'] += f" {line_raw_text}"
            
            # --- 4. Append parsed tables safely into active node block context ---
            if current_node and table_strings:
                for t_str in table_strings:
                    if t_str not in current_node['body_text']:
                        current_node['body_text'] += f"\n{t_str}"
                table_strings.clear()

    if current_node:
        current_node['content_hash'] = compute_hash(
            current_node['heading'], current_node['level'], current_node['body_text']
        )
        parsed_nodes.append(current_node)
        
    return parsed_nodes
#!/usr/bin/env python3
"""Convert DOCX files to Markdown by extracting text from document.xml"""

import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

def docx_to_markdown(docx_path: Path) -> str:
    """Extract text from DOCX and convert to markdown format."""

    # DOCX is a ZIP file containing XML
    with zipfile.ZipFile(docx_path, 'r') as docx_zip:
        # Read the main document XML
        xml_content = docx_zip.read('word/document.xml')

    # Parse XML
    root = ET.fromstring(xml_content)

    # Define namespace
    namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

    # Extract paragraphs
    paragraphs = []
    for paragraph in root.findall('.//w:p', namespace):
        # Get all text runs in this paragraph, handling line breaks
        texts = []
        for run in paragraph.findall('.//w:r', namespace):
            for child in run:
                tag = child.tag.split('}')[-1]
                if tag == 't' and child.text:
                    texts.append(child.text)
                elif tag == 'br':
                    texts.append('\n')

        # Join text runs and add paragraph if not empty
        para_text = ''.join(texts).strip()
        if para_text:
            paragraphs.append(para_text)

    # Join paragraphs with double newlines for markdown
    markdown_content = '\n\n'.join(paragraphs)

    return markdown_content

def main():
    if len(sys.argv) != 3:
        print("Usage: convert_docx_to_md.py <input.docx> <output.md>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    # Convert DOCX to markdown
    markdown_content = docx_to_markdown(input_path)

    # Write to output file with UTF-8 encoding
    output_path.write_text(markdown_content, encoding='utf-8')

    print(f"✓ Converted {input_path.name} → {output_path.name}")
    print(f"  Output: {len(markdown_content)} characters, {len(markdown_content.splitlines())} lines")

if __name__ == '__main__':
    main()

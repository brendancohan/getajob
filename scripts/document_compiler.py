#!/usr/bin/env python3
"""
document_compiler.py (Template)
Converts Markdown resume and cover letter files into professionally formatted Word (.docx) documents.
Uses pypandoc to ensure clean ATS-friendly XML structure with standard bulleted lists.
"""

import sys
import os

try:
    import pypandoc
except ImportError:
    print("Error: pypandoc is not installed. Run: pip install pypandoc")
    sys.exit(1)

def ensure_pandoc():
    try:
        pypandoc.get_pandoc_version()
    except OSError:
        print("Pandoc binary not found. Downloading standalone pandoc via pypandoc...")
        pypandoc.download_pandoc()

def convert_md_to_docx(input_md_path, output_docx_path=None):
    if not os.path.exists(input_md_path):
        print(f"Error: File not found: {input_md_path}")
        return False

    if not output_docx_path:
        if input_md_path.endswith(".md"):
            output_docx_path = input_md_path[:-3] + ".docx"
        else:
            output_docx_path = input_md_path + ".docx"

    ensure_pandoc()
    try:
        pypandoc.convert_file(input_md_path, "docx", outputfile=output_docx_path)
        print(f"Successfully generated: {output_docx_path}")
        return True
    except Exception as e:
        print(f"Conversion failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python document_compiler.py <path_to_markdown_file> [output_docx_path]")
        sys.exit(1)
    
    in_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    convert_md_to_docx(in_path, out_path)

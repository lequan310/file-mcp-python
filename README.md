# File MCP

A Model Context Protocol (MCP) server for document conversion using Pandoc. This server provides tools to create and convert files between various document formats through the FastMCP framework.

## Features

- **Create files from text content**: Convert markdown or HTML content to various document formats
- **Convert existing files**: Transform documents between different formats
- **Multiple format support**: Handle 10+ document formats including PDF, DOCX, HTML, Markdown, LaTeX, and more
- **Advanced Pandoc features**: Support for reference documents, custom filters, and defaults files
- **Intelligent path resolution**: Automatic filter path resolution from multiple locations

## Supported Formats

- **Text**: `.txt`, `.md` (Markdown)
- **Web**: `.html`, `.htm`
- **Office**: `.docx`, `.doc`, `.odt`
- **PDF**: `.pdf` (requires TeX Live with xelatex)
- **Publishing**: `.epub`, `.latex`, `.tex`, `.rst`
- **Notebooks**: `.ipynb` (Jupyter Notebook)

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

### Prerequisites

- Python 3.13 or higher
- [Pandoc](https://pandoc.org/installing.html) must be installed and available in your PATH
- For PDF generation: [TeX Live](https://www.tug.org/texlive/) or similar LaTeX distribution

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd file-mcp

# Install dependencies with uv
uv sync

# Or manually install dependencies
uv add fastmcp pypandoc-binary pyyaml
```

## Usage

### Running the Server

```bash
# Using uv
uv run server.py

# Or with Python directly
python server.py
```

### Available Tools

#### 1. `create_file`

Create a new file from text content (markdown or HTML).

**Parameters:**
- `content` (str): The text content to convert (markdown or HTML)
- `output_file` (str): Complete path where to save the file (including extension)
- `input_format` (str): Source format of the content (`markdown` or `html`)
- `reference_doc` (str, optional): Path to a reference DOCX file for styling (docx output only)
- `filters` (list[str], optional): List of Pandoc filter paths to apply
- `defaults_file` (str, optional): Path to a Pandoc defaults YAML file

**Example:**
```python
# Convert markdown content to PDF
create_file(
    content="# Hello World\n\nThis is a test document.",
    output_file="D:/documents/hello.pdf",
    input_format="markdown"
)

# Convert HTML to DOCX with custom styling
create_file(
    content="<h1>Report</h1><p>Content here</p>",
    output_file="/home/user/report.docx",
    input_format="html",
    reference_doc="/templates/corporate.docx"
)
```

#### 2. `convert_file`

Convert an existing file from one format to another.

**Parameters:**
- `input_file` (str): Complete path to the input file to convert
- `input_format` (str): Source format (txt, html, markdown, ipynb, odt, pdf, docx, rst, latex, epub)
- `output_file` (str): Complete path where to save the converted file (including extension)
- `reference_doc` (str, optional): Path to a reference DOCX file for styling (docx output only)
- `filters` (list[str], optional): List of Pandoc filter paths to apply
- `defaults_file` (str, optional): Path to a Pandoc defaults YAML file

**Example:**
```python
# Convert DOCX to PDF
convert_file(
    input_file="D:/documents/report.docx",
    input_format="docx",
    output_file="D:/documents/report.pdf"
)

# Convert Markdown to HTML with custom filters
convert_file(
    input_file="/home/user/notes.md",
    input_format="markdown",
    output_file="/home/user/notes.html",
    filters=["custom-filter.py"],
    defaults_file="/config/pandoc-defaults.yaml"
)
```

## Advanced Features

### Pandoc Filters

The server supports custom Pandoc filters for advanced document processing. Filters are searched in multiple locations:

1. Relative to the current working directory
2. Relative to the defaults file directory (if provided)
3. In `~/.pandoc/filters/` directory

Filters must be executable. The server will attempt to make them executable automatically if needed.

### Defaults Files

You can provide a Pandoc defaults YAML file to configure conversion options. The defaults file should be a valid YAML dictionary containing Pandoc options.

**Example defaults file:**
```yaml
variables:
  geometry: margin=1in
  fontsize: 12pt
pdf-engine: xelatex
number-sections: true
```

### Reference Documents

For DOCX output, you can provide a reference document that defines styles, fonts, and formatting. This allows you to maintain consistent branding and styling across generated documents.

## PDF Generation

PDF generation requires a LaTeX engine (xelatex is used by default). The server automatically adds:
- `--pdf-engine=xelatex`
- `-V geometry:margin=1in`

Ensure you have TeX Live or a similar LaTeX distribution installed.

## Development

### Project Structure

```
file-mcp/
├── server.py    # Main MCP server with conversion tools
├── pyproject.toml       # Project dependencies and metadata
├── ruff.toml           # Ruff linter configuration
└── README.md           # This file
```

### Dependencies

- **fastmcp**: Framework for building MCP servers
- **pypandoc-binary**: Python wrapper for Pandoc (includes Pandoc binary)
- **pyyaml**: YAML parser for defaults files

### Development Tools

```bash
# Install development dependencies
uv add --dev ruff

# Run linter
uv run ruff check .

# Format code
uv run ruff format .
```

## Error Handling

The server provides detailed error messages for common issues:

- **Missing files**: Clear messages when input files or reference documents don't exist
- **Invalid formats**: Validation of input/output format compatibility
- **Filter errors**: Helpful messages when filters are not found or not executable
- **Pandoc errors**: Detection and reporting of Pandoc-specific issues
- **Defaults file errors**: Validation of YAML structure and content

## Environment Variables

- `PANDOC_OUTPUT_DIR`: Automatically set to the output file directory during conversion

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions:
- Check that Pandoc is installed: `pandoc --version`
- For PDF issues, verify TeX Live installation: `xelatex --version`
- Review Pandoc documentation: https://pandoc.org/MANUAL.html

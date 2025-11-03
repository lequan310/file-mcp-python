"""FastMCP-based Pandoc server module."""

import asyncio
import os
from typing import Annotated, Literal

import yaml
from fastmcp import FastMCP

# Set up Pandoc path BEFORE importing pypandoc
pandoc_dir = os.path.abspath("./pandoc_bin")
pandoc_exe = os.path.join(pandoc_dir, "pandoc.exe" if os.name == "nt" else "pandoc")

# Set environment variables early
if os.path.exists(pandoc_exe):
    os.environ["PYPANDOC_PANDOC"] = pandoc_exe
    pandoc_dir_normalized = os.path.normpath(pandoc_dir)
    if pandoc_dir_normalized not in os.environ.get("PATH", ""):
        os.environ["PATH"] = (
            f"{pandoc_dir_normalized}{os.pathsep}{os.environ.get('PATH', '')}"
        )

# Now import pypandoc after environment is configured
import pypandoc  # noqa: E402

try:
    # Only download if pandoc doesn't exist
    if not os.path.exists(pandoc_exe):
        print(f"Pandoc not found. Downloading to: {pandoc_dir}")
        os.makedirs(pandoc_dir, exist_ok=True)

        # Download pandoc to the directory
        pypandoc.download_pandoc(
            targetfolder=pandoc_dir, download_folder=pandoc_dir, delete_installer=True
        )
        print("Pandoc downloaded successfully")

        # Re-set environment variables after download
        os.environ["PYPANDOC_PANDOC"] = pandoc_exe
        pandoc_dir_normalized = os.path.normpath(pandoc_dir)
        os.environ["PATH"] = (
            f"{pandoc_dir_normalized}{os.pathsep}{os.environ.get('PATH', '')}"
        )
    else:
        print(f"Using existing Pandoc at: {pandoc_exe}")

    # Verify pypandoc can find it
    if os.path.exists(pandoc_exe):
        print(f"Pandoc initialized successfully at: {pandoc_exe}")
        try:
            version = pypandoc.get_pandoc_version()
            print(f"Pandoc version: {version}")
        except Exception as ve:
            print(f"Warning: Could not verify Pandoc version: {ve}")
    else:
        print(f"Pandoc executable not found at expected location: {pandoc_exe}")
        print("Attempting to use system Pandoc...")
except Exception as e:
    print(f"Error initializing Pandoc: {e}")
    print("Attempting to use system Pandoc...")

# Initialize FastMCP server
mcp = FastMCP("File MCP")


# Helper functions
def _infer_format_from_extension(file_path: str) -> str:
    """Infer the format from file extension."""
    ext_to_format = {
        ".txt": "plain",
        ".html": "html",
        ".htm": "html",
        ".md": "markdown",
        ".markdown": "markdown",
        ".ipynb": "ipynb",
        ".odt": "odt",
        ".pdf": "pdf",
        ".docx": "docx",
        ".doc": "docx",
        ".rst": "rst",
        ".tex": "latex",
        ".latex": "latex",
        ".epub": "epub",
    }

    # Get file extension (lowercase)
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext not in ext_to_format:
        raise ValueError(
            f"Unsupported file extension: '{ext}'. "
            f"Supported extensions: {', '.join(ext_to_format.keys())}"
        )

    return ext_to_format[ext]


def _validate_conversion_params(
    output_format: str,
    reference_doc: str | None,
    filters: list[str] | None,
    defaults_file: str | None,
) -> None:
    """Validate common conversion parameters."""
    # Validate reference_doc if provided
    if reference_doc:
        if output_format != "docx":
            raise ValueError(
                "reference_doc parameter is only supported for docx output format"
            )
        if not os.path.exists(reference_doc):
            raise ValueError(f"Reference document not found: {reference_doc}")

    # Validate defaults_file if provided
    if defaults_file:
        if not os.path.exists(defaults_file):
            raise ValueError(f"Defaults file not found: {defaults_file}")

        # Check if it's a valid YAML file and readable
        try:
            with open(defaults_file) as f:
                yaml_content = yaml.safe_load(f)

            # Validate the YAML structure
            if not isinstance(yaml_content, dict):
                raise ValueError(
                    f"Invalid defaults file format: {defaults_file} - must be a YAML dictionary"
                )

            # Check if the defaults file specifies an output format that conflicts
            if "to" in yaml_content and yaml_content["to"] != output_format:
                print(
                    f"Warning: Defaults file specifies output format '{yaml_content['to']}' "
                    f"but requested format is '{output_format}'. Using requested format."
                )

        except yaml.YAMLError as e:
            raise ValueError(
                f"Error parsing defaults file {defaults_file}: {str(e)}"
            ) from e
        except PermissionError as e:
            raise ValueError(
                f"Permission denied when reading defaults file: {defaults_file}"
            ) from e
        except Exception as e:
            raise ValueError(
                f"Error reading defaults file {defaults_file}: {str(e)}"
            ) from e

    # Define supported formats
    supported_formats = {
        "html",
        "markdown",
        "pdf",
        "docx",
        "rst",
        "latex",
        "epub",
        "txt",
        "ipynb",
        "odt",
    }
    if output_format not in supported_formats:
        raise ValueError(
            f"Unsupported output format: '{output_format}'. "
            f"Supported formats are: {', '.join(supported_formats)}"
        )

    # Validate filters if provided
    if filters:
        if not isinstance(filters, list):
            raise ValueError("filters parameter must be a list of strings")

        for filter_path in filters:
            if not isinstance(filter_path, str):
                raise ValueError("Each filter must be a string path")


def _resolve_filter_path(
    filter_path: str, defaults_file: str | None = None
) -> str | None:
    """Resolve a filter path by trying multiple possible locations."""
    # If it's already an absolute path, just use it
    if os.path.isabs(filter_path):
        paths = [filter_path]
    else:
        # Try multiple locations for relative paths
        paths = [
            # 1. Relative to current working directory
            os.path.abspath(filter_path),
            # 2. Relative to the defaults file directory (if provided)
            (
                os.path.join(
                    os.path.dirname(os.path.abspath(defaults_file)), filter_path
                )
                if defaults_file
                else None
            ),
            # 3. Relative to the .pandoc/filters directory
            os.path.join(
                os.path.expanduser("~"),
                ".pandoc",
                "filters",
                os.path.basename(filter_path),
            ),
        ]
        # Remove None entries
        paths = [p for p in paths if p]

    # Try each path
    for path in paths:
        if os.path.exists(path):
            # Check if executable and try to make it executable if not
            if not os.access(path, os.X_OK):
                try:
                    os.chmod(path, os.stat(path).st_mode | 0o111)
                    print(f"Made filter executable: {path}")
                except Exception as e:
                    print(
                        f"Warning: Could not make filter executable: {path} - {str(e)}"
                    )
                    continue

            print(f"Using filter: {path}")
            return path

    return None


def _validate_filters(
    filters: list[str], defaults_file: str | None = None
) -> list[str]:
    """Validate filter paths and ensure they exist and are executable."""
    validated_filters = []

    for filter_path in filters:
        resolved_path = _resolve_filter_path(filter_path, defaults_file)
        if resolved_path:
            validated_filters.append(resolved_path)
        else:
            raise ValueError(
                f"Filter not found in any of the searched locations: {filter_path}"
            )

    return validated_filters


def _format_result_info(
    filters: list[str] | None = None,
    defaults_file: str | None = None,
    validated_filters: list[str] | None = None,
) -> tuple[str, str]:
    """Format filter and defaults file information for result messages."""
    filter_info = ""
    defaults_info = ""

    if filters and validated_filters:
        filter_names = [os.path.basename(f) for f in validated_filters]
        filter_info = f" with filters: {', '.join(filter_names)}"

    if defaults_file:
        defaults_basename = os.path.basename(defaults_file)
        defaults_info = f" using defaults file: {defaults_basename}"

    return filter_info, defaults_info


def _prepare_conversion_args(
    output_format: str,
    output_file: str | None,
    reference_doc: str | None,
    filters: list[str] | None,
    defaults_file: str | None,
) -> list[str]:
    """Prepare extra arguments for Pandoc conversion."""
    extra_args = []

    # Add defaults file if provided
    if defaults_file:
        defaults_file_abs = os.path.abspath(defaults_file)
        extra_args.extend(["--defaults", defaults_file_abs])

    # Set environment variables for filters
    if output_file:
        # Set PANDOC_OUTPUT_DIR to the directory of the output file
        output_dir = os.path.dirname(os.path.abspath(output_file))
        os.environ["PANDOC_OUTPUT_DIR"] = output_dir

    # Handle filter arguments
    if filters:
        validated_filters = _validate_filters(filters, defaults_file)
        for filter_path in validated_filters:
            extra_args.extend(["--filter", filter_path])

    # Handle PDF-specific conversion if needed
    if output_format == "pdf":
        # Try to find LaTeX engine
        latex_engines = ["xelatex", "pdflatex", "lualatex"]
        engine_found = None

        for engine in latex_engines:
            try:
                import shutil

                if shutil.which(engine):
                    engine_found = engine
                    break
            except Exception:
                continue

        if not engine_found:
            raise ValueError(
                "PDF generation requires a LaTeX engine (xelatex, pdflatex, or lualatex). "
                "Please install MiKTeX (https://miktex.org/) and ensure it's in your PATH."
            )

        extra_args.extend([f"--pdf-engine={engine_found}", "-V", "geometry:margin=1in"])

    # Handle reference doc for docx format
    if reference_doc and output_format == "docx":
        extra_args.extend(["--reference-doc", reference_doc])

    return extra_args


def _format_error_message(
    e: Exception,
    input_format: str,
    output_format: str,
    defaults_file: str | None,
    is_file: bool,
) -> str:
    """Format error message for Pandoc conversion errors."""
    error_prefix = "Error converting"
    error_details = str(e)

    if (
        "Filter not found" in error_details
        or "Filter is not executable" in error_details
    ):
        error_prefix = "Filter error during conversion"
    elif "defaults" in error_details and defaults_file:
        error_prefix = "Defaults file error during conversion"
        error_details += f" (defaults file: {defaults_file})"
    elif "pandoc" in error_details.lower() and "not found" in error_details.lower():
        error_prefix = "Pandoc executable not found"
        error_details = "Please ensure Pandoc is installed and available in your PATH"

    source_type = "file" if is_file else "content"
    error_msg = (
        f"{error_prefix} {source_type} from {input_format} to "
        f"{output_format}: {error_details}"
    )
    return error_msg


@mcp.tool()
async def create_file(
    content: Annotated[str, "The text content to convert (markdown or HTML)"],
    output_file: Annotated[
        str,
        "Complete path where to save the file including directory, filename, and extension. "
        "The output format is inferred from the file extension. "
        "Supported extensions: .txt, .html, .md, .ipynb, .odt, .pdf, .docx, .rst, .tex, .epub. "
        "Example: 'D:/documents/story.pdf' or '/home/user/report.docx'. ",
    ],
    input_format: Annotated[
        Literal["markdown", "html"],
        "Source format of the content. Supported: 'markdown', 'html'",
    ],
    reference_doc: Annotated[
        str | None,
        "Optional path to a reference DOCX file for styling (only for docx output)",
    ] = None,
    filters: Annotated[
        list[str] | None,
        "Optional list of Pandoc filter paths to apply during conversion",
    ] = None,
    defaults_file: Annotated[
        str | None,
        "Optional path to a Pandoc defaults YAML file for additional options",
    ] = None,
) -> str:
    """Create a new file from text content (markdown or HTML) and save to disk.

    Use this tool when you need to create a document file from text content.
    The output format is automatically determined from the file extension.
    Supports: .pdf, .docx, .html, .md, .txt, .rst, .tex, .epub, .ipynb, .odt"""
    # Validate required parameters
    if not content:
        raise ValueError("content cannot be empty")

    if not output_file:
        raise ValueError("output_file path is required for create_file")

    if not input_format:
        raise ValueError("input_format is required")

    # Infer output format from file extension
    output_format = _infer_format_from_extension(output_file)

    # Validate input format
    if input_format not in ["markdown", "html"]:
        raise ValueError(
            f"Unsupported input format: '{input_format}'. "
            "Supported formats for create_file: markdown, html"
        )

    # Common validation function
    _validate_conversion_params(output_format, reference_doc, filters, defaults_file)

    try:
        # Get conversion arguments
        extra_args = _prepare_conversion_args(
            output_format, output_file, reference_doc, filters, defaults_file
        )

        validated_filters = _validate_filters(filters, defaults_file) if filters else []

        # Convert content to file (run in thread to avoid blocking)
        await asyncio.to_thread(
            pypandoc.convert_text,
            content,
            output_format,
            format=input_format,
            outputfile=output_file,
            extra_args=extra_args,
        )

        # Create result message with filter and defaults information
        filter_info, defaults_info = _format_result_info(
            filters, defaults_file, validated_filters
        )
        result_message = (
            f"File successfully created{filter_info}{defaults_info} "
            f"and saved to: {output_file}"
        )
        return result_message

    except Exception as e:
        error_msg = _format_error_message(
            e, input_format, output_format, defaults_file, is_file=False
        )
        raise ValueError(error_msg) from e


@mcp.tool()
async def convert_file(
    input_file: Annotated[
        str,
        "Complete path to the input file to convert. Must be an existing file.",
    ],
    output_file: Annotated[
        str,
        "Complete path where to save the converted file including extension. "
        "The output format is inferred from the file extension. "
        "Supported extensions: .txt, .html, .md, .ipynb, .odt, .pdf, .docx, .rst, .tex, .epub. "
        "Example: 'D:/documents/output.pdf' or '/home/user/result.html'",
    ],
    reference_doc: Annotated[
        str | None,
        "Optional path to a reference DOCX file for styling (only for docx output)",
    ] = None,
    filters: Annotated[
        list[str] | None,
        "Optional list of Pandoc filter paths to apply during conversion",
    ] = None,
    defaults_file: Annotated[
        str | None,
        "Optional path to a Pandoc defaults YAML file for additional options",
    ] = None,
) -> str:
    """Convert an existing file from one format to another.

    Use this tool to convert documents between different formats.
    Both input and output formats are automatically determined from the file extensions.
    """
    # Validate required parameters
    if not input_file:
        raise ValueError("input_file is required")

    if not output_file:
        raise ValueError("output_file is required")

    # Validate input file exists
    if not os.path.exists(input_file):
        raise ValueError(f"Input file not found: {input_file}")

    # Infer input format from file extension
    input_format = _infer_format_from_extension(input_file)

    # Infer output format from file extension
    output_format = _infer_format_from_extension(output_file)

    # Common validation function
    _validate_conversion_params(output_format, reference_doc, filters, defaults_file)

    try:
        # Get conversion arguments
        extra_args = _prepare_conversion_args(
            output_format, output_file, reference_doc, filters, defaults_file
        )

        validated_filters = _validate_filters(filters, defaults_file) if filters else []

        # Convert file to file (run in thread to avoid blocking)
        await asyncio.to_thread(
            pypandoc.convert_file,
            input_file,
            output_format,
            outputfile=output_file,
            format=input_format,
            extra_args=extra_args,
        )

        # Create result message with filter and defaults information
        filter_info, defaults_info = _format_result_info(
            filters, defaults_file, validated_filters
        )
        result_message = (
            f"File successfully converted{filter_info}{defaults_info} "
            f"and saved to: {output_file}"
        )
        return result_message

    except Exception as e:
        detected_format = input_format or "auto-detected"
        error_msg = _format_error_message(
            e, detected_format, output_format, defaults_file, is_file=True
        )
        raise ValueError(error_msg) from e


if __name__ == "__main__":
    # Run the FastMCP server
    mcp.run(transport="streamable-http")

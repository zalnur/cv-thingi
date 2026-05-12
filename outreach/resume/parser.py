"""Resume and portfolio text extraction."""

from pathlib import Path

from pypdf import PdfReader

from outreach.models import ResumeProfile


SUPPORTED_RESUME_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_INPUT_FILE_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 25


def load_resume_profile(resume_path: Path, portfolio_path: Path | None, *, max_chars: int) -> ResumeProfile:
    """Load resume and optional portfolio/profile text."""
    if max_chars <= 0:
        raise ValueError("max_chars must be positive.")
    resume_text = load_text_file(resume_path)
    portfolio_text = load_text_file(portfolio_path) if portfolio_path else ""
    return ResumeProfile(
        resume_text=resume_text[:max_chars],
        portfolio_text=portfolio_text[:max_chars],
        source_paths=[path for path in [resume_path, portfolio_path] if path],
    )


def load_text_file(path: Path | None) -> str:
    """Extract text from PDF, TXT, or Markdown."""
    if path is None:
        return ""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    if path.stat().st_size > MAX_INPUT_FILE_BYTES:
        raise ValueError(f"Input file exceeds the {MAX_INPUT_FILE_BYTES} byte limit: {path}")
    extension = path.suffix.lower()
    if extension not in SUPPORTED_RESUME_EXTENSIONS:
        raise ValueError(f"Unsupported file type {extension}. Use PDF, TXT, or MD.")
    if extension == ".pdf":
        return extract_pdf_text(path)
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"No text could be extracted from file: {path}")
    return text


def extract_pdf_text(path: Path) -> str:
    """Extract text from a PDF with pypdf."""
    reader = PdfReader(str(path), strict=False)
    if len(reader.pages) > MAX_PDF_PAGES:
        raise ValueError(f"PDF exceeds the {MAX_PDF_PAGES} page limit: {path}")
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    text = "\n".join(pages).strip()
    if not text:
        raise ValueError(f"No text could be extracted from PDF: {path}")
    return text

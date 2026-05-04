from io import BytesIO

from xhtml2pdf import pisa


def render_html_to_pdf_bytes(html: str) -> bytes:
    out = BytesIO()
    context = pisa.CreatePDF(
        src=BytesIO(html.encode("utf-8")),
        dest=out,
        encoding="utf-8",
    )
    if getattr(context, "err", 0):
        raise RuntimeError("No s'ha pogut generar el PDF.")
    return out.getvalue()

"""Real LibreOffice smoke test, run inside the built worker image in CI."""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

from pypdf import PdfReader

from app.worker.operations import OperationContext, get_handler


def _write_docx(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
            'package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.'
            'openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
            'relationships"><Relationship Id="rId1" Type="http://schemas.'
            'openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/></Relationships>',
        )
        archive.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/'
            '2006/main"><w:body><w:p><w:r><w:t>PDFFlow real conversion smoke test'
            "</w:t></w:r></w:p><w:sectPr/></w:body></w:document>",
        )


def main() -> None:
    handler = get_handler("office_to_pdf")
    if handler is None:
        raise RuntimeError("office_to_pdf handler is not registered")

    with tempfile.TemporaryDirectory(prefix="office-smoke-") as temporary:
        root = Path(temporary)
        source = root / "generated.docx"
        workdir = root / "work"
        workdir.mkdir()
        _write_docx(source)

        result = handler(
            OperationContext(
                job_id="container-smoke",
                inputs=[source],
                original_names=["Office smoke test.docx"],
                options={},
                progress=lambda *_: None,
                workdir=workdir,
            )
        )

        if result.filename != "Office smoke test.pdf":
            raise RuntimeError(f"unexpected output name: {result.filename}")
        if not result.path.read_bytes().startswith(b"%PDF-"):
            raise RuntimeError("LibreOffice output is not a PDF")
        if len(PdfReader(result.path).pages) != 1:
            raise RuntimeError("LibreOffice output does not contain one page")

    print("Office to PDF container smoke test passed")


if __name__ == "__main__":
    main()

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from app.core.errors import ValidationError
from app.worker.operations import OperationContext, get_handler
from app.worker.operations.pageranges import parse


def make_context(tmp_path: Path, inputs: list[Path], **options) -> OperationContext:
    return OperationContext(
        job_id="test",
        inputs=inputs,
        original_names=[path.name for path in inputs],
        options=options,
        progress=lambda *_: None,
        workdir=tmp_path,
    )


# --- page ranges -------------------------------------------------------


def test_parse_blank_means_all_pages() -> None:
    assert parse("", 4) == [0, 1, 2, 3]
    assert parse(None, 2) == [0, 1]


def test_parse_mixed_expression_dedupes_and_sorts() -> None:
    assert parse("3,1-2,2", 5) == [0, 1, 2]


def test_parse_reversed_range() -> None:
    assert parse("5-3", 6) == [2, 3, 4]


@pytest.mark.parametrize("expression", ["0", "9", "abc", "1-99"])
def test_parse_rejects_out_of_range(expression: str) -> None:
    with pytest.raises(ValidationError):
        parse(expression, 3)


# --- operations --------------------------------------------------------


def test_merge_concatenates_in_order(tmp_path: Path, pdf_file: Path) -> None:
    second = tmp_path / "second.pdf"
    second.write_bytes(pdf_file.read_bytes())

    result = get_handler("merge")(make_context(tmp_path, [pdf_file, second]))

    assert len(PdfReader(str(result.path)).pages) == 6
    assert result.metadata["fileCount"] == 2


def test_merge_needs_two_files(tmp_path: Path, pdf_file: Path) -> None:
    with pytest.raises(ValidationError):
        get_handler("merge")(make_context(tmp_path, [pdf_file]))


def test_extract_pages(tmp_path: Path, pdf_file: Path) -> None:
    result = get_handler("extract_pages")(make_context(tmp_path, [pdf_file], pages="1,3"))
    assert len(PdfReader(str(result.path)).pages) == 2
    assert result.filename == "sample-pages.pdf"


def test_rotate_applies_only_to_selected_pages(tmp_path: Path, pdf_file: Path) -> None:
    result = get_handler("rotate")(
        make_context(tmp_path, [pdf_file], angle=90, pages="2")
    )
    pages = PdfReader(str(result.path)).pages
    assert pages[0].get("/Rotate", 0) == 0
    assert pages[1]["/Rotate"] == 90


def test_rotate_rejects_bad_angle(tmp_path: Path, pdf_file: Path) -> None:
    with pytest.raises(ValidationError):
        get_handler("rotate")(make_context(tmp_path, [pdf_file], angle=45))


def test_organize_reorders_duplicates_and_rotates_pages(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=200)
    writer.add_blank_page(width=200, height=300)
    writer.add_blank_page(width=300, height=400)
    with source.open("wb") as fh:
        writer.write(fh)

    result = get_handler("organize")(
        make_context(
            tmp_path,
            [source],
            pages=[
                {"source": 3, "rotation": 0},
                {"source": 1, "rotation": 90},
                {"source": 1, "rotation": 0},
            ],
        )
    )

    pages = PdfReader(str(result.path)).pages
    assert [float(page.mediabox.width) for page in pages] == [300, 100, 100]
    assert pages[0].get("/Rotate", 0) == 0
    assert pages[1].get("/Rotate", 0) == 90
    assert pages[2].get("/Rotate", 0) == 0
    assert result.filename == "source-organized.pdf"
    assert result.metadata == {"pageCount": 3, "sourcePageCount": 3}


@pytest.mark.parametrize(
    "pages",
    [
        [],
        [{"source": 0, "rotation": 0}],
        [{"source": 4, "rotation": 0}],
        [{"source": 1, "rotation": 45}],
        [{"source": True, "rotation": 0}],
        ["page 1"],
    ],
)
def test_organize_rejects_invalid_plans(tmp_path: Path, pdf_file: Path, pages) -> None:
    with pytest.raises(ValidationError):
        get_handler("organize")(make_context(tmp_path, [pdf_file], pages=pages))


def test_split_every_page_produces_one_pdf_each(tmp_path: Path, pdf_file: Path) -> None:
    result = get_handler("split")(make_context(tmp_path, [pdf_file], mode="every_page"))
    with zipfile.ZipFile(result.path) as archive:
        assert len(archive.namelist()) == 3
    assert result.metadata["partCount"] == 3


def test_split_by_ranges(tmp_path: Path, pdf_file: Path) -> None:
    result = get_handler("split")(
        make_context(tmp_path, [pdf_file], mode="ranges", ranges="1-2,3")
    )
    with zipfile.ZipFile(result.path) as archive:
        assert len(archive.namelist()) == 2


def test_split_ranges_requires_expression(tmp_path: Path, pdf_file: Path) -> None:
    with pytest.raises(ValidationError):
        get_handler("split")(make_context(tmp_path, [pdf_file], mode="ranges"))


def test_compress_reports_savings(tmp_path: Path, pdf_file: Path) -> None:
    result = get_handler("compress")(make_context(tmp_path, [pdf_file], level="medium"))
    meta = result.metadata
    assert meta["originalSize"] > 0
    assert meta["compressedSize"] > 0
    assert 0 <= meta["percentSaved"] <= 100


def test_compress_rejects_unknown_level(tmp_path: Path, pdf_file: Path) -> None:
    with pytest.raises(ValidationError):
        get_handler("compress")(make_context(tmp_path, [pdf_file], level="extreme"))


def test_compress_never_returns_a_file_larger_than_the_original(
    tmp_path: Path, pdf_file: Path
) -> None:
    """A tiny or already-optimised PDF grows when rewritten. Returning that
    from a tool called "compress" is worse than doing nothing."""
    original_size = pdf_file.stat().st_size

    result = get_handler("compress")(make_context(tmp_path, [pdf_file], level="high"))

    assert result.path.stat().st_size <= original_size
    assert result.metadata["compressedSize"] <= result.metadata["originalSize"]
    assert result.metadata["percentSaved"] >= 0


def test_compress_result_is_always_a_readable_pdf(tmp_path: Path, pdf_file: Path) -> None:
    result = get_handler("compress")(make_context(tmp_path, [pdf_file], level="medium"))

    assert len(PdfReader(str(result.path)).pages) == 3


def test_office_to_pdf_uses_an_isolated_headless_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.worker.operations import office_ops

    source = tmp_path / "server-generated.docx"
    source.write_bytes(b"office")
    recorded: dict = {}

    def fake_run(command, **kwargs):
        recorded["command"] = command
        recorded["kwargs"] = kwargs
        output = Path(command[command.index("--outdir") + 1]) / f"{source.stem}.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        with output.open("wb") as result:
            writer.write(result)
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(office_ops.shutil, "which", lambda _: "/usr/bin/soffice")
    monkeypatch.setattr(office_ops.subprocess, "run", fake_run)
    context = OperationContext(
        job_id="test",
        inputs=[source],
        original_names=["Revenue; rm -rf workspace.docx"],
        options={},
        progress=lambda *_: None,
        workdir=tmp_path,
    )

    result = get_handler("office_to_pdf")(context)

    assert result.filename == "Revenue; rm -rf workspace.pdf"
    assert result.path.read_bytes().startswith(b"%PDF-")
    assert result.metadata == {"sourceFormat": "DOCX"}
    assert recorded["command"][-1] == str(source)
    assert "Revenue; rm -rf workspace.docx" not in recorded["command"]
    assert recorded["kwargs"]["timeout"] == office_ops.CONVERSION_TIMEOUT_SECONDS
    assert recorded["kwargs"]["env"]["HOME"].endswith("libreoffice-profile")


def test_office_to_pdf_reports_a_conversion_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.worker.operations import office_ops

    source = tmp_path / "server-generated.xlsx"
    source.write_bytes(b"office")
    monkeypatch.setattr(office_ops.shutil, "which", lambda _: "/usr/bin/soffice")

    def time_out(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(office_ops.subprocess, "run", time_out)

    with pytest.raises(ValidationError, match="too long"):
        get_handler("office_to_pdf")(make_context(tmp_path, [source]))

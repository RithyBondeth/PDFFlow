from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from pypdf import PdfReader

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


def test_compress_result_is_always_a_readable_pdf(
    tmp_path: Path, pdf_file: Path
) -> None:
    result = get_handler("compress")(make_context(tmp_path, [pdf_file], level="medium"))

    assert len(PdfReader(str(result.path)).pages) == 3

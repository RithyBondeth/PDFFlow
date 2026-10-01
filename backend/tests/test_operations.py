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


# --- images to PDF ------------------------------------------------------


def _write(tmp_path: Path, name: str, content: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    return path


def _page_sizes(path: Path) -> list[tuple[float, float]]:
    return [
        (round(float(page.mediabox.width), 1), round(float(page.mediabox.height), 1))
        for page in PdfReader(str(path)).pages
    ]


def test_images_to_pdf_makes_one_page_per_image_in_order(
    tmp_path: Path, png_bytes: bytes, make_image
) -> None:
    wide = _write(tmp_path, "wide.png", png_bytes)
    tall = _write(tmp_path, "tall.jpg", make_image("JPEG", (20, 40)))

    result = get_handler("images_to_pdf")(make_context(tmp_path, [wide, tall]))

    # "fit" sizes each page to its image at the 96 DPI default: 40px -> 30pt.
    assert _page_sizes(result.path) == [(30.0, 15.0), (15.0, 30.0)]
    assert result.filename == "images.pdf"
    assert result.metadata["pageCount"] == 2


def test_images_to_pdf_names_a_single_image_after_it(
    tmp_path: Path, jpeg_bytes: bytes
) -> None:
    photo = _write(tmp_path, "Holiday photo.jpg", jpeg_bytes)
    result = get_handler("images_to_pdf")(make_context(tmp_path, [photo]))
    assert result.filename == "Holiday photo.pdf"


def test_images_to_pdf_matches_paper_orientation_to_the_image(
    tmp_path: Path, png_bytes: bytes
) -> None:
    wide = _write(tmp_path, "wide.png", png_bytes)
    result = get_handler("images_to_pdf")(
        make_context(tmp_path, [wide], pageSize="a4", margin="large")
    )
    assert _page_sizes(result.path) == [(841.9, 595.3)]


def test_images_to_pdf_honours_exif_orientation(tmp_path: Path, make_image) -> None:
    """Phones store pixels sideways and record the rotation in EXIF."""
    from PIL import Image

    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90° clockwise to display
    sideways = _write(
        tmp_path, "phone.jpg", make_image("JPEG", (40, 20), exif=exif.tobytes())
    )

    result = get_handler("images_to_pdf")(make_context(tmp_path, [sideways]))

    assert _page_sizes(result.path) == [(15.0, 30.0)]


def test_images_to_pdf_accepts_webp(tmp_path: Path, make_image) -> None:
    webp = _write(tmp_path, "art.webp", make_image("WEBP"))
    result = get_handler("images_to_pdf")(make_context(tmp_path, [webp]))
    assert len(PdfReader(str(result.path)).pages) == 1


@pytest.mark.parametrize(
    "options", [{"pageSize": "tabloid"}, {"margin": "huge"}]
)
def test_images_to_pdf_rejects_unknown_options(
    tmp_path: Path, png_bytes: bytes, options: dict
) -> None:
    image = _write(tmp_path, "a.png", png_bytes)
    with pytest.raises(ValidationError):
        get_handler("images_to_pdf")(make_context(tmp_path, [image], **options))


# --- PDF to images ------------------------------------------------------


def test_pdf_to_images_renders_every_page_by_default(
    tmp_path: Path, pdf_file: Path
) -> None:
    result = get_handler("pdf_to_images")(make_context(tmp_path, [pdf_file]))

    with zipfile.ZipFile(result.path) as archive:
        names = archive.namelist()
        first = archive.read(names[0])
    assert names == ["sample-page-1.png", "sample-page-2.png", "sample-page-3.png"]
    assert first.startswith(b"\x89PNG")
    assert result.filename == "sample-images.zip"
    assert result.metadata["imageCount"] == 3


@pytest.mark.parametrize(
    ("image_format", "extension", "signature"),
    [("jpeg", "jpg", b"\xff\xd8\xff"), ("webp", "webp", b"RIFF")],
)
def test_pdf_to_images_encodes_selected_pages(
    tmp_path: Path, pdf_file: Path, image_format: str, extension: str, signature: bytes
) -> None:
    result = get_handler("pdf_to_images")(
        make_context(tmp_path, [pdf_file], format=image_format, dpi=72, pages="2-3")
    )

    with zipfile.ZipFile(result.path) as archive:
        names = archive.namelist()
        assert all(archive.read(name).startswith(signature) for name in names)
    assert names == [f"sample-page-2.{extension}", f"sample-page-3.{extension}"]


def test_pdf_to_images_uses_the_requested_resolution(
    tmp_path: Path, pdf_file: Path
) -> None:
    from PIL import Image

    result = get_handler("pdf_to_images")(
        make_context(tmp_path, [pdf_file], dpi=72, pages="1")
    )
    with zipfile.ZipFile(result.path) as archive:
        image = Image.open(archive.open("sample-page-1.png"))
        assert image.size == (595, 842)


def test_pdf_to_images_downscales_oversized_pages(
    tmp_path: Path, pdf_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PIL import Image

    from app.worker.operations import image_ops

    monkeypatch.setattr(image_ops, "MAX_RENDER_PIXELS", 100_000)
    result = get_handler("pdf_to_images")(
        make_context(tmp_path, [pdf_file], dpi=300, pages="1")
    )

    with zipfile.ZipFile(result.path) as archive:
        width, height = Image.open(archive.open("sample-page-1.png")).size
    assert width * height <= 100_000
    assert result.metadata["downscaledPages"] == 1


@pytest.mark.parametrize("options", [{"format": "gif"}, {"dpi": 600}, {"dpi": "150"}])
def test_pdf_to_images_rejects_unknown_options(
    tmp_path: Path, pdf_file: Path, options: dict
) -> None:
    with pytest.raises(ValidationError):
        get_handler("pdf_to_images")(make_context(tmp_path, [pdf_file], **options))


def test_images_to_pdf_trusts_scanner_dpi_but_not_camera_placeholders(
    tmp_path: Path, make_image
) -> None:
    scan = _write(tmp_path, "scan.png", make_image("PNG", (300, 600), dpi=(300, 300)))
    photo = _write(tmp_path, "photo.png", make_image("PNG", (96, 96), dpi=(72, 72)))

    result = get_handler("images_to_pdf")(make_context(tmp_path, [scan, photo]))

    # 300px at 300 DPI is one inch; the 72 DPI placeholder falls back to 96.
    assert _page_sizes(result.path) == [(72.0, 144.0), (72.0, 72.0)]


# --- protect / unlock ---------------------------------------------------

USER_PASSWORD = "open sesame ✓"
OWNER_PASSWORD = "owner-only"


def _encrypted(tmp_path: Path, content: bytes) -> Path:
    return _write(tmp_path, "locked.pdf", content)


def test_protect_encrypts_with_aes_256(tmp_path: Path, pdf_file: Path) -> None:
    from pypdf import PasswordType

    result = get_handler("protect")(
        make_context(tmp_path, [pdf_file], password="hunter2")
    )

    reader = PdfReader(str(result.path))
    assert reader.is_encrypted
    assert reader._encryption is not None and reader._encryption.V == 5  # AES-256
    # With no restrictions the one password is also the owner password.
    assert reader.decrypt("hunter2") == PasswordType.OWNER_PASSWORD
    assert len(reader.pages) == 3
    assert result.filename == "sample-protected.pdf"
    assert "hunter2" not in str(result.metadata)


def test_protect_restrictions_use_an_owner_password_nobody_knows(
    tmp_path: Path, pdf_file: Path
) -> None:
    from pypdf import PasswordType
    from pypdf.constants import UserAccessPermissions

    result = get_handler("protect")(
        make_context(
            tmp_path,
            [pdf_file],
            password="hunter2",
            allowPrinting=False,
            allowCopying=False,
        )
    )

    reader = PdfReader(str(result.path))
    # The user password must not double as the owner password, or the
    # restrictions would be lifted for anyone who can open the file.
    assert reader.decrypt("hunter2") == PasswordType.USER_PASSWORD
    permissions = reader.user_access_permissions
    assert permissions is not None
    assert not permissions & UserAccessPermissions.PRINT
    assert not permissions & UserAccessPermissions.EXTRACT
    assert permissions & UserAccessPermissions.ASSEMBLE_DOC


def test_protect_rejects_an_already_encrypted_pdf(
    tmp_path: Path, encrypted_pdf_bytes: bytes
) -> None:
    with pytest.raises(ValidationError, match="password protected"):
        locked = _encrypted(tmp_path, encrypted_pdf_bytes)
        get_handler("protect")(make_context(tmp_path, [locked], password="x"))


@pytest.mark.parametrize("password", [USER_PASSWORD, OWNER_PASSWORD])
def test_unlock_accepts_the_user_or_owner_password(
    tmp_path: Path, encrypted_pdf_bytes: bytes, password: str
) -> None:
    locked = _encrypted(tmp_path, encrypted_pdf_bytes)

    result = get_handler("unlock")(make_context(tmp_path, [locked], password=password))

    reader = PdfReader(str(result.path))
    assert not reader.is_encrypted
    assert len(reader.pages) == 3
    assert result.filename == "locked-unlocked.pdf"


def test_unlock_rejects_a_wrong_password_without_echoing_it(
    tmp_path: Path, encrypted_pdf_bytes: bytes
) -> None:
    locked = _encrypted(tmp_path, encrypted_pdf_bytes)
    with pytest.raises(ValidationError, match="not correct") as raised:
        get_handler("unlock")(make_context(tmp_path, [locked], password="guess-123"))
    assert "guess-123" not in raised.value.message


def test_unlock_rejects_a_pdf_that_is_not_protected(
    tmp_path: Path, pdf_file: Path
) -> None:
    with pytest.raises(ValidationError, match="not password protected"):
        get_handler("unlock")(make_context(tmp_path, [pdf_file], password="x"))


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({}, "Enter a password"),
        ({"password": ""}, "Enter a password"),
        ({"password": 1234}, "Enter a password"),
        ({"password": "x" * 128}, "too long"),
        ({"password": "a\x00b"}, "invalid character"),
        ({"password": "ok", "allowPrinting": "no"}, "true or false"),
    ],
)
def test_protect_validates_its_options(
    tmp_path: Path, pdf_file: Path, options: dict, message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        get_handler("protect")(make_context(tmp_path, [pdf_file], **options))


def test_unlock_drops_the_protected_suffix_it_added(
    tmp_path: Path, encrypted_pdf_bytes: bytes
) -> None:
    locked = _write(tmp_path, "Contract-protected.pdf", encrypted_pdf_bytes)
    result = get_handler("unlock")(
        make_context(tmp_path, [locked], password=USER_PASSWORD)
    )
    assert result.filename == "Contract-unlocked.pdf"


# --- watermark ----------------------------------------------------------


def _ink(page) -> dict | None:
    """Where red watermark ink landed on the page *as viewed*.

    Returns its centre, whether it runs level or diagonally, and which end is
    heavier, which tells upright text from upside-down or mirrored text.
    """
    import fitz
    from PIL import Image

    pix = page.get_pixmap(dpi=36)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    pixels = image.load()
    points = [
        (x, y)
        for y in range(pix.height)
        for x in range(pix.width)
        if pixels[x, y][0] - pixels[x, y][1] > 40
    ]
    del fitz
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    box_x, box_y = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
    width, height = max(xs) - min(xs), max(ys) - min(ys)
    return {
        "centre": (box_x / pix.width, box_y / pix.height),
        "shape": "level" if width > 2 * height else "diagonal",
        "heavy_left": mean_x < box_x - 1,
        "heavy_low": mean_y > box_y + 1,
    }


def _source_pdf(tmp_path: Path, rotations: list[int], crop: bool = False) -> Path:
    import fitz

    doc = fitz.open()
    for rotation in rotations:
        page = doc.new_page(width=595, height=842)
        if crop:
            page.set_cropbox(fitz.Rect(20, 30, 575, 822))
        page.set_rotation(rotation)
    path = tmp_path / "source.pdf"
    doc.save(path)
    return path


# "WWWW" then dots: the ink is heaviest where the text starts, so an upright
# mark is heavy on the left (level) or lower-left (rising diagonal).
HEAVY_START = "WWWW............"


@pytest.mark.parametrize("crop", [False, True])
@pytest.mark.parametrize("angle", [0, 45])
def test_watermark_reads_correctly_on_every_page_rotation(
    tmp_path: Path, angle: int, crop: bool
) -> None:
    import fitz

    source = _source_pdf(tmp_path, [0, 90, 180, 270], crop=crop)
    result = get_handler("watermark")(
        make_context(
            tmp_path,
            [source],
            text=HEAVY_START,
            color="red",
            opacity=1,
            angle=angle,
        )
    )

    with fitz.open(result.path) as doc:
        for page in doc:
            ink = _ink(page)
            assert ink is not None, f"no watermark on a {page.rotation}° page"
            centre_x, centre_y = ink["centre"]
            assert abs(centre_x - 0.5) < 0.03, page.rotation
            assert abs(centre_y - 0.5) < 0.03, page.rotation
            assert ink["shape"] == ("level" if angle == 0 else "diagonal"), page.rotation
            assert ink["heavy_left"], f"mirrored or upside down at {page.rotation}°"
            if angle == 45:
                assert ink["heavy_low"], f"falling instead of rising at {page.rotation}°"
    # Every page keeps the rotation it came with.
    with fitz.open(result.path) as doc:
        assert [page.rotation for page in doc] == [0, 90, 180, 270]


def test_watermark_only_stamps_the_selected_pages(tmp_path: Path) -> None:
    import fitz

    source = _source_pdf(tmp_path, [0, 0, 0])
    result = get_handler("watermark")(
        make_context(tmp_path, [source], text="DRAFT", color="red", pages="2")
    )

    with fitz.open(result.path) as doc:
        assert [_ink(page) is not None for page in doc] == [False, True, False]
    assert result.metadata == {"mode": "text", "stampedPages": 1}
    assert result.filename == "source-watermarked.pdf"


def test_tiled_watermark_covers_the_page_but_embeds_the_mark_once(
    tmp_path: Path,
) -> None:
    import fitz

    source = _source_pdf(tmp_path, [0] * 40)
    result = get_handler("watermark")(
        make_context(tmp_path, [source], text="CONFIDENTIAL", layout="tile", color="red")
    )

    with fitz.open(result.path) as doc:
        # Many marks spread over the page, not one in the middle.
        assert len(doc[0].get_text("words")) >= 6
        ink = _ink(doc[0])
        assert ink is not None
        # Shared stamp, unembedded standard font: 40 pages stay small.
    assert result.path.stat().st_size < 40_000


def test_image_watermark_bakes_in_opacity(tmp_path: Path, make_image) -> None:
    import fitz

    source = _source_pdf(tmp_path, [0, 90])
    logo = _write(tmp_path, "logo.png", make_image("PNG", (200, 100)))

    result = get_handler("watermark")(
        make_context(tmp_path, [source, logo], mode="image", opacity=0.5, angle=0)
    )

    with fitz.open(result.path) as doc:
        for page in doc:
            ink = _ink(page)
            assert ink is not None
            assert abs(ink["centre"][0] - 0.5) < 0.03
            # Half-opaque red over white renders pink, not full red.
            pix = page.get_pixmap(dpi=36)
            from PIL import Image

            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            r, g, b = image.getpixel((pix.width // 2, pix.height // 2))
            assert r > 200 and 100 < g < 200, (r, g, b)
    assert result.metadata["mode"] == "image"


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"text": ""}, "Enter the watermark text"),
        ({"text": "x" * 101}, "100 characters"),
        ({"text": "សួស្តី"}, "cannot draw yet"),
        ({"text": "Kőszeg"}, "cannot draw yet"),
        # Outside Latin-1, so it would render as a stand-in glyph.
        ({"text": "100 €"}, "cannot draw yet"),
        ({"text": "OK", "opacity": 0}, "Opacity"),
        ({"text": "OK", "opacity": True}, "Opacity"),
        ({"text": "OK", "angle": 30}, "angle"),
        ({"text": "OK", "color": "pink"}, "color"),
        ({"text": "OK", "layout": "grid"}, "layout"),
        ({"mode": "image"}, "Upload an image"),
    ],
)
def test_watermark_validates_its_options(
    tmp_path: Path, pdf_file: Path, options: dict, message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        get_handler("watermark")(make_context(tmp_path, [pdf_file], **options))


def test_watermark_text_mode_refuses_a_stray_image(
    tmp_path: Path, pdf_file: Path, png_bytes: bytes
) -> None:
    logo = _write(tmp_path, "logo.png", png_bytes)
    with pytest.raises(ValidationError, match="switch to an image"):
        get_handler("watermark")(make_context(tmp_path, [pdf_file, logo], text="OK"))


def test_watermark_draws_latin_1_text_as_written(
    tmp_path: Path, pdf_file: Path
) -> None:
    result = get_handler("watermark")(
        make_context(tmp_path, [pdf_file], text="Réservé · Größe 100 £ ©")
    )
    # Drawn as written, not with stand-in glyphs.
    text = PdfReader(str(result.path)).pages[0].extract_text()
    assert "Réservé · Größe 100 £ ©" in text


def test_watermark_tiling_is_bounded_for_tiny_marks() -> None:
    from app.worker.operations import watermark_ops

    points = watermark_ops._positions(595, 842, 2, 2, "tile")
    assert 0 < len(points) <= watermark_ops.MAX_TILES

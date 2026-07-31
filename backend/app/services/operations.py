"""The tool catalog.

A single source of truth for which operations exist, what inputs they accept
and which options they take. The API serves this to the frontend so the tool
picker never drifts from what the worker can actually do.

Phase 1 wires the pipeline end-to-end for a starter set of operations; the
remaining entries are advertised as ``implemented=False`` and the UI shows them
as coming soon rather than letting a user queue a job that cannot run.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.errors import ValidationError

MAX_ORGANIZED_PAGES = 1000


@dataclass(frozen=True)
class Operation:
    key: str
    name: str
    description: str
    category: str
    accepts: frozenset[str]
    multi_file: bool = False
    min_files: int = 1
    output_extension: str = ".pdf"
    implemented: bool = False
    options_schema: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "accepts": sorted(self.accepts),
            "multiFile": self.multi_file,
            "minFiles": self.min_files,
            "outputExtension": self.output_extension,
            "implemented": self.implemented,
            "optionsSchema": self.options_schema,
        }


CATALOG: tuple[Operation, ...] = (
    Operation(
        key="merge",
        name="Merge PDF",
        description="Combine several PDFs into one, in the order you choose.",
        category="organize",
        accepts=frozenset({"pdf"}),
        multi_file=True,
        min_files=2,
        implemented=True,
        # No options: the output order is the order `fileIds` arrives in on
        # /jobs/create, not a separate parameter. An `order` option here would
        # be a second, contradictable source of truth for the same thing.
        options_schema={},
    ),
    Operation(
        key="split",
        name="Split PDF",
        description="Split every page apart, or cut the document by range.",
        category="organize",
        accepts=frozenset({"pdf"}),
        output_extension=".zip",
        implemented=True,
        options_schema={
            "mode": {"type": "string", "enum": ["every_page", "ranges"]},
            "ranges": {"type": "string", "description": "e.g. 1-3,5,8-10"},
        },
    ),
    Operation(
        key="extract_pages",
        name="Extract Pages",
        description="Build a new PDF from the pages you select.",
        category="organize",
        accepts=frozenset({"pdf"}),
        implemented=True,
        options_schema={"pages": {"type": "string", "description": "e.g. 1-3,7"}},
    ),
    Operation(
        key="rotate",
        name="Rotate PDF",
        description="Turn selected pages, or the whole document, by 90/180/270°.",
        category="organize",
        accepts=frozenset({"pdf"}),
        implemented=True,
        options_schema={
            "angle": {"type": "integer", "enum": [90, 180, 270]},
            "pages": {"type": "string", "description": "Blank means every page."},
        },
    ),
    Operation(
        key="compress",
        name="Compress PDF",
        description="Shrink a PDF while keeping it readable.",
        category="optimize",
        accepts=frozenset({"pdf"}),
        implemented=True,
        options_schema={"level": {"type": "string", "enum": ["low", "medium", "high"]}},
    ),
    Operation(
        key="organize",
        name="Organize Pages",
        description="Reorder, delete, rotate and duplicate pages visually.",
        category="organize",
        accepts=frozenset({"pdf"}),
        implemented=True,
        options_schema={
            "pages": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["source", "rotation"],
                    "properties": {
                        "source": {"type": "integer", "minimum": 1},
                        "rotation": {"type": "integer", "enum": [0, 90, 180, 270]},
                    },
                },
            }
        },
    ),
    Operation(
        key="watermark",
        name="Watermark PDF",
        description="Stamp text or an image across every page.",
        category="edit",
        accepts=frozenset({"pdf", "image"}),
        multi_file=True,
    ),
    Operation(
        key="protect",
        name="Protect PDF",
        description="Encrypt with a password and restrict printing or copying.",
        category="security",
        accepts=frozenset({"pdf"}),
    ),
    Operation(
        key="unlock",
        name="Unlock PDF",
        description="Remove protection — the correct password is required.",
        category="security",
        accepts=frozenset({"pdf"}),
    ),
    Operation(
        key="extract_images",
        name="Extract Images",
        description="Pull every embedded image out as PNG or JPEG.",
        category="convert",
        accepts=frozenset({"pdf"}),
        output_extension=".zip",
    ),
    Operation(
        key="images_to_pdf",
        name="Images to PDF",
        description="Turn JPG, PNG or WEBP images into a single PDF.",
        category="convert",
        accepts=frozenset({"image"}),
        multi_file=True,
    ),
    Operation(
        key="pdf_to_images",
        name="PDF to Images",
        description="Render each page as PNG, JPEG or WEBP.",
        category="convert",
        accepts=frozenset({"pdf"}),
        output_extension=".zip",
    ),
    Operation(
        key="office_to_pdf",
        name="Office to PDF",
        description="Convert DOCX, XLSX and PPTX using LibreOffice.",
        category="convert",
        accepts=frozenset({"office"}),
        implemented=True,
    ),
)

BY_KEY: dict[str, Operation] = {op.key: op for op in CATALOG}


def get(key: str) -> Operation | None:
    return BY_KEY.get(key)


def organization_plan(value: object, page_count: int) -> list[dict[str, int]]:
    """Validate and normalize the explicit output plan for Organize Pages.

    This runs before a job is persisted and again in the worker. Keeping the
    nested payload bounded at the API edge prevents a huge page array from
    being stored or queued before the operation gets a chance to reject it.
    """
    if not isinstance(value, list) or not value:
        raise ValidationError("Keep at least one page in the organized PDF.")
    if len(value) > MAX_ORGANIZED_PAGES:
        raise ValidationError(
            f"An organized PDF can contain at most {MAX_ORGANIZED_PAGES} pages."
        )

    plan: list[dict[str, int]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValidationError("The page arrangement is invalid.")
        source = item.get("source")
        rotation = item.get("rotation", 0)
        if type(source) is not int or not 1 <= source <= page_count:
            raise ValidationError(
                f"A selected page is out of range — this document has {page_count} pages."
            )
        if type(rotation) is not int or rotation not in (0, 90, 180, 270):
            raise ValidationError("Page rotation must be 0, 90, 180 or 270 degrees.")
        plan.append({"source": source, "rotation": rotation})
    return plan

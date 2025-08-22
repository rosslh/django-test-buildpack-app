from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Wikipedia Article Section Example",
            summary="Edit a specific section of a Wikipedia article",
            description="Provide a Wikipedia article title and section title to fetch and edit that specific section",
            value={"article_title": "Apollo", "section_title": "History"},
            request_only=True,
        ),
    ]
)
class EditRequestSerializer(serializers.Serializer):
    """Serializer for wiki content edit requests.

    Requires both article_title and section_title to fetch a specific section from Wikipedia and edit it.
    """

    article_title = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Wikipedia article title to fetch the section from.",
        label="Article Title",
    )

    section_title = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Title of the specific level 2 section (== Section ==) to edit within the Wikipedia article.",
        label="Section Title",
    )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Section Headings Request Example",
            summary="Get section headings by article title",
            description="Provide a Wikipedia article title to retrieve its section headings",
            value={"article_title": "Apollo"},
            request_only=True,
        ),
    ]
)
class SectionHeadingsRequestSerializer(serializers.Serializer):
    """Serializer for section headings requests."""

    article_title = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Wikipedia article title to retrieve section headings from.",
        label="Article Title",
    )


class SectionHeadingSerializer(serializers.Serializer):
    """Serializer for individual section headings."""

    text = serializers.CharField(help_text="The text content of the section heading")
    level = serializers.IntegerField(
        help_text="The heading level (always 2 for level 2 headings == Section ==)"
    )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Section Headings Response Example",
            summary="Response with level 2 section headings",
            description="List of level 2 section headings with their text and level",
            value={
                "headings": [
                    {"text": "Overview", "level": 2},
                    {"text": "History", "level": 2},
                    {"text": "Applications", "level": 2},
                    {"text": "See also", "level": 2},
                ],
                "article_title": "Apollo",
                "article_url": "https://en.wikipedia.org/wiki/Apollo",
            },
            response_only=True,
        ),
    ]
)
class SectionHeadingsResponseSerializer(serializers.Serializer):
    """Serializer for section headings responses."""

    headings = SectionHeadingSerializer(
        many=True, help_text="List of level 2 section headings"
    )
    article_title = serializers.CharField(help_text="Wikipedia article title")
    article_url = serializers.CharField(help_text="URL to the Wikipedia article")


class ParagraphResultSerializer(serializers.Serializer):
    """Serializer for individual paragraph edit results."""

    before = serializers.CharField(
        help_text="Original paragraph content before editing"
    )
    after = serializers.CharField(
        help_text="Edited paragraph content after AI processing"
    )
    status = serializers.ChoiceField(
        choices=["UNCHANGED", "CHANGED", "REJECTED", "SKIPPED", "ERRORED"],
        help_text="Status indicating whether the paragraph was modified and why",
    )
    status_details = serializers.CharField(
        help_text="Detailed explanation of why the paragraph has this status"
    )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Article Section Response Example",
            summary="Response when editing by article and section title",
            description="Structured response showing before/after states for each paragraph when editing a specific section",
            value={
                "paragraphs": [
                    {
                        "before": "The temple of '''Apollo Delphinios''' dates from the 7th century BC, or probably from the middle of the 8th century BC.",
                        "after": "The temple of '''Apollo Delphinios''' dates to the 7th or likely mid-8th century BC.",
                        "status": "CHANGED",
                        "status_details": "Content was successfully edited by AI and passed validation",
                    },
                    {
                        "before": "== History ==",
                        "after": "== History ==",
                        "status": "SKIPPED",
                        "status_details": "Non-prose content (heading, list, table, template, or media)",
                    },
                    {
                        "before": "The original text contained some problematic phrasing.",
                        "after": "The original text contained some problematic phrasing.",
                        "status": "REJECTED",
                        "status_details": "Edit failed validation: MetaCommentaryValidator: Added meta commentary word 'edit'",
                    },
                    {
                        "before": "Short text.",
                        "after": "Short text.",
                        "status": "SKIPPED",
                        "status_details": "Content too short to process",
                    },
                ],
                "article_title": "Apollo",
                "section_title": "History",
                "article_url": "https://en.wikipedia.org/wiki/Apollo",
            },
            response_only=True,
        ),
    ]
)
class EditResponseSerializer(serializers.Serializer):
    """Serializer for structured wiki edit responses."""

    paragraphs = ParagraphResultSerializer(
        many=True, help_text="Array of paragraph edit results"
    )
    article_title = serializers.CharField(
        required=False,
        help_text="Wikipedia article title (only present when editing by article and section title)",
    )
    section_title = serializers.CharField(
        required=False,
        help_text="Wikipedia article section title (only present when editing by article and section title)",
    )
    article_url = serializers.CharField(
        required=False,
        help_text="URL to the Wikipedia article (only present when editing by article and section title)",
    )


class EditTaskListSerializer(serializers.Serializer):
    """Serializer for EditTask list view with basic information."""

    id = serializers.UUIDField(help_text="Unique task identifier")
    editing_mode = serializers.CharField(help_text="Edit mode: copyedit, brevity, etc.")
    status = serializers.CharField(help_text="Current task status")
    article_title = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Wikipedia article title (if applicable)",
    )
    section_title = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Wikipedia section title (if applicable)",
    )
    created_at = serializers.DateTimeField(help_text="Task creation timestamp")
    completed_at = serializers.DateTimeField(
        required=False, allow_null=True, help_text="Task completion timestamp"
    )
    llm_provider = serializers.CharField(
        required=False, allow_null=True, help_text="LLM provider used"
    )
    llm_model = serializers.CharField(
        required=False, allow_null=True, help_text="Specific model used"
    )
    changes_count = serializers.IntegerField(
        required=False, allow_null=True, help_text="Number of paragraphs changed"
    )


class EditTaskDetailSerializer(serializers.Serializer):
    """Serializer for EditTask detail view with complete information."""

    id = serializers.UUIDField(help_text="Unique task identifier")
    editing_mode = serializers.CharField(help_text="Edit mode: copyedit, brevity, etc.")
    status = serializers.CharField(help_text="Current task status")
    article_title = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Wikipedia article title (if applicable)",
    )
    section_title = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Wikipedia section title (if applicable)",
    )
    created_at = serializers.DateTimeField(help_text="Task creation timestamp")
    started_at = serializers.DateTimeField(
        required=False, allow_null=True, help_text="Task start timestamp"
    )
    completed_at = serializers.DateTimeField(
        required=False, allow_null=True, help_text="Task completion timestamp"
    )
    llm_provider = serializers.CharField(
        required=False, allow_null=True, help_text="LLM provider used"
    )
    llm_model = serializers.CharField(
        required=False, allow_null=True, help_text="Specific model used"
    )
    result = serializers.JSONField(
        required=False, allow_null=True, help_text="Complete edit results"
    )
    error_message = serializers.CharField(
        required=False, allow_null=True, help_text="Error message if task failed"
    )

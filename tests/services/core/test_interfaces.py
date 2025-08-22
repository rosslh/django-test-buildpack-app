import pytest

from services.core import interfaces


class DummyParagraphProcessor(interfaces.IParagraphProcessor):
    async def process(self, content: str, context):
        return content


class DummyReferenceHandler(interfaces.IReferenceHandler):
    def replace_references_with_placeholders(self, content):
        return content, []

    def restore_references(self, content, refs_list):
        return content


class DummyValidator(interfaces.IValidator):
    def validate(self, original, edited, context):
        return edited, False

    def get_last_failure_reason(self):
        return None


class DummyAsyncValidator(interfaces.IAsyncValidator):
    async def validate(self, original, edited, context):
        return edited, False

    def get_last_failure_reason(self):
        return None


class DummyDocumentProcessor(interfaces.IDocumentProcessor):
    def process(self, content):
        return [content]


class DummyContentClassifier(interfaces.IContentClassifier):
    def get_content_type(self, content):
        return "type"

    def should_process_with_context(self, content, index, document_items):
        return True, None

    def reset_state(self):
        pass

    def is_in_footer_section(self):
        return False

    def has_first_prose_been_encountered(self):
        return False

    def is_in_lead_section(self):
        return True


class DummyEditService(interfaces.IEditService):
    async def edit(self, content):
        return content


class DummyValidationPipeline(interfaces.IValidationPipeline):
    def add_validator(self, validator):
        pass

    async def validate(self, original, edited, context):
        return edited, False


class DummyReversionTracker(interfaces.IReversionTracker):
    def record_reversion(self, reversion_type):
        pass

    def get_summary(self):
        return "summary"

    def reset(self):
        pass


def test_interfaces_instantiation():
    # Test that direct instantiation fails for ABCs
    abcs = [
        interfaces.IParagraphProcessor,
        interfaces.IReferenceHandler,
        interfaces.IValidator,
        interfaces.IAsyncValidator,
        interfaces.IDocumentProcessor,
        interfaces.IContentClassifier,
        interfaces.IEditService,
        interfaces.IValidationPipeline,
        interfaces.IReversionTracker,
    ]
    for abc in abcs:
        with pytest.raises(TypeError):
            abc()


def test_interfaces_subclass_usage():
    import asyncio

    asyncio.run(DummyParagraphProcessor().process("a", {}))
    DummyReferenceHandler().replace_references_with_placeholders("a")
    DummyReferenceHandler().restore_references("a", [])
    DummyValidator().validate("a", "b", {})
    DummyValidator().get_last_failure_reason()
    asyncio.run(DummyAsyncValidator().validate("a", "b", {}))
    DummyAsyncValidator().get_last_failure_reason()
    DummyDocumentProcessor().process("a")
    DummyContentClassifier().get_content_type("a")
    asyncio.run(DummyEditService().edit("a"))
    DummyValidationPipeline().add_validator(DummyValidator())
    asyncio.run(DummyValidationPipeline().validate("a", "b", {}))
    DummyReversionTracker().record_reversion("type")
    DummyReversionTracker().get_summary()
    DummyReversionTracker().reset()

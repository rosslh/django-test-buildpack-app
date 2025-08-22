from services.utils.text_utils import split_into_paragraphs


def test_placeholder():
    assert True


def test_split_into_paragraphs_basic():
    text = "para1\npara2\npara3"
    result = split_into_paragraphs(text)
    assert result == ["para1", "para2", "para3"]


def test_split_into_paragraphs_empty():
    text = ""
    result = split_into_paragraphs(text)
    assert result == [""]


def test_split_into_paragraphs_only_newlines():
    text = "\n\n"
    result = split_into_paragraphs(text)
    assert result == ["", "", ""]


def test_split_into_paragraphs_no_newline():
    text = "singleparagraph"
    result = split_into_paragraphs(text)
    assert result == ["singleparagraph"]

"""General text processing utilities.

This module contains text manipulation functions that are not specific to wiki text or
any particular domain.
"""

import re
from typing import List


def split_into_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs using newlines as separators.

    Args:
        text: The text to split

    Returns:
        List of paragraph strings
    """
    return re.split(r"\n", text)

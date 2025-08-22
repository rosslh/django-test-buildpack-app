"""Reversion tracking utilities."""

from enum import Enum


class ReversionType(Enum):
    """Enumeration of different types of edit reversions."""

    LINK_VALIDATION_FAILURE = "link_validation_failure"
    REFERENCE_VALIDATION_FAILURE = "reference_validation_failure"
    ADDED_CONTENT_VIOLATION = "added_content_violation"
    REFERENCE_CONTENT_CHANGE = "reference_content_change"
    API_ERROR = "api_error"
    UNEXPECTED_ERROR = "unexpected_error"


class ReversionTracker:
    """Tracks different types of edit reversions and provides summary statistics.

    This class maintains counters for various failure types that result in reverting
    edits back to their original content.
    """

    def __init__(self) -> None:
        """Initialize the reversion tracker with zero counts."""
        self.reset()

    def reset(self) -> None:
        """Reset all reversion counters to zero."""
        self._counters = {
            ReversionType.LINK_VALIDATION_FAILURE: 0,
            ReversionType.REFERENCE_VALIDATION_FAILURE: 0,
            ReversionType.ADDED_CONTENT_VIOLATION: 0,
            ReversionType.REFERENCE_CONTENT_CHANGE: 0,
            ReversionType.API_ERROR: 0,
            ReversionType.UNEXPECTED_ERROR: 0,
        }

    def record_reversion(self, reversion_type: ReversionType) -> None:
        """Record a reversion of the specified type.

        Args:
            reversion_type: The type of reversion to record.
        """
        if reversion_type in self._counters:
            self._counters[reversion_type] += 1
        else:
            raise ValueError(f"Unknown reversion type: {reversion_type}")

    def get_count(self, reversion_type: ReversionType) -> int:
        """Get the count for a specific reversion type.

        Args:
            reversion_type: The type of reversion to get the count for.

        Returns:
            The count of reversions for the specified type.
        """
        return self._counters.get(reversion_type, 0)

    def get_summary(self) -> str:
        """Generate a human-readable summary of all reversions.

        Returns:
            A formatted string summarizing all reversion counts, or empty string if no reversions.
        """
        total_reversions = sum(self._counters.values())
        if total_reversions == 0:
            return ""

        summary_lines = [
            f"\n{total_reversions} paragraph(s) had unrecoverable errors and were reverted to original content.",
            "Reversion reasons:",
        ]

        # Define user-friendly labels for each reversion type
        type_labels = {
            ReversionType.LINK_VALIDATION_FAILURE: "Link validation failures",
            ReversionType.REFERENCE_VALIDATION_FAILURE: "Reference validation failures",
            ReversionType.ADDED_CONTENT_VIOLATION: "Added content violations",
            ReversionType.REFERENCE_CONTENT_CHANGE: "Reference content changes",
            ReversionType.API_ERROR: "API errors",
            ReversionType.UNEXPECTED_ERROR: "Unexpected errors",
        }

        for reversion_type, label in type_labels.items():
            count = self._counters[reversion_type]
            if count > 0:
                summary_lines.append(f"  {label}: {count}")

        return "\n".join(summary_lines)

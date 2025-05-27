from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, TypeAlias

BlockDict: TypeAlias = Dict


# STYLE_EMOJIS: Dict[Optional[int], str] = {
#     0: "💡",  # Thought
#     1: "❞",  # Quote - Though Notion has a dedicated quote block
#     2: "⭐",  # Highlight
#     3: "📖",  # Chapter/Heading reference?
# }

COLOR_STYLES: Dict[Optional[int], str] = {
    1: "red",
    2: "purple",
    3: "blue",
    4: "green",
    5: "yellow",
    None: "default",  # Added default for safety
}

# --- Abstract Base Class --- #


class NotionBlock(ABC):
    """Abstract base class for all Notion blocks."""

    @abstractmethod
    def to_dict(self) -> BlockDict:
        """Converts the block object into its dictionary representation for the Notion API."""
        pass


# --- Concrete Block Classes --- #


@dataclass
class TableOfContentsBlock(NotionBlock):
    """Represents a Table of Contents block."""

    color: str = "default"

    def to_dict(self) -> BlockDict:
        return {"type": "table_of_contents", "table_of_contents": {"color": self.color}}


@dataclass
class HeadingBlock(NotionBlock):
    """Represents a Heading block (levels 1, 2, or 3)."""

    level: int
    content: str
    color: str = "default"
    is_toggleable: bool = False

    def to_dict(self) -> BlockDict:
        heading_type = f"heading_{min(self.level, 3)}"  # Ensure level is 1, 2, or 3
        return {
            "type": heading_type,
            heading_type: {
                "rich_text": [{"type": "text", "text": {"content": self.content}}],
                "color": self.color,
                "is_toggleable": self.is_toggleable,
            },
        }


@dataclass
class QuoteBlock(NotionBlock):
    """Represents a Quote block."""

    content: str
    color: str = "default"

    def to_dict(self) -> BlockDict:
        return {
            "type": "quote",
            "quote": {
                "rich_text": [{"type": "text", "text": {"content": self.content}}],
                "color": self.color,
            },
        }


@dataclass
class CalloutBlock(NotionBlock):
    """Represents a Callout block."""

    content: str
    style: Optional[int] = 2
    color_style: Optional[int] = None
    review_id: Optional[str] = None  # If review_id exists, style is ignored for emoji

    def to_dict(self) -> BlockDict:
        # Determine emoji: Use specific emoji if it's a review, otherwise use style, default to Note emoji
        # emoji_key = None if self.review_id is not None else self.style
        # emoji = STYLE_EMOJIS.get(emoji_key, STYLE_EMOJIS[None])
        # Determine color: Use color_style, default to 'default'
        color = COLOR_STYLES.get(self.color_style, COLOR_STYLES[None])

        return {
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": self.content}}],
                # "icon": {"emoji": emoji},
                "color": color,
            },
        }

from dataclasses import dataclass
from typing import Dict, Optional, TypeAlias

BlockDict: TypeAlias = Dict[str, any]

# Constants for styling
STYLE_EMOJIS = {
    0: "💡",  # Direct line
    1: "⭐",  # Background color
    2: "🌟",  # Wavy line
    None: "✍️",  # Note
}

COLOR_STYLES = {
    1: "red",
    2: "purple",
    3: "blue",
    4: "green",
    5: "yellow",
    None: "default",
}


class NotionBlock:
    pass


@dataclass
class NotionBlockBuilder:
    """Builder class for Notion blocks"""

    @staticmethod
    def table_of_contents() -> BlockDict:
        return {"type": "table_of_contents", "table_of_contents": {"color": "default"}}

    @staticmethod
    def heading(level: int, content: str) -> BlockDict:
        heading_type = f"heading_{min(level, 3)}"
        return {
            "type": heading_type,
            heading_type: {
                "rich_text": [{"type": "text", "text": {"content": content}}],
                "color": "default",
                "is_toggleable": False,
            },
        }

    @staticmethod
    def quote(content: str) -> BlockDict:
        return {
            "type": "quote",
            "quote": {
                "rich_text": [{"type": "text", "text": {"content": content}}],
                "color": "default",
            },
        }

    @staticmethod
    def callout(
        content: str,
        style: Optional[int] = None,
        color_style: Optional[int] = None,
        review_id: Optional[str] = None,
    ) -> BlockDict:
        emoji = STYLE_EMOJIS.get(None if review_id is not None else style, "🌟")
        color = COLOR_STYLES.get(color_style, "default")

        return {
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": content}}],
                "icon": {"emoji": emoji},
                "color": color,
            },
        }

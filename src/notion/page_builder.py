from typing import Dict, List, Tuple

from book import Book
from logger import logger
from notion.blocks import (
    BlockDict,
    CalloutBlock,
    HeadingBlock,
    QuoteBlock,
    TableOfContentsBlock,
)


class PageContentBuilder:
    """Builds the content structure for a Notion page (specifically for a book)"""

    # Removed block_builder from init as it's no longer needed
    def __init__(self):
        pass

    def build_book_content(
        self, book: Book
    ) -> Tuple[List[BlockDict], Dict[int, BlockDict]]:
        """Builds the complete content structure for a book page"""
        children = []
        grandchild = {}

        chapter = book.chapters
        summary = book.summary
        bookmark_list = book.bookmark_list

        if chapter:
            self._add_table_of_contents(children)
            self._add_chapter_content(children, grandchild, chapter, bookmark_list)
        elif bookmark_list:
            self._add_bookmarks(children, bookmark_list)

        if summary:
            self._add_summary(children, summary)

        logger.info(f"Children generated for {book.title}: {len(children)} blocks")
        logger.info(
            f"Grandchildren generated for {book.title}: {len(grandchild)} blocks"
        )
        return children, grandchild

    def _add_table_of_contents(self, children: List[BlockDict]) -> None:
        # Instantiate block directly and call to_dict()
        children.append(HeadingBlock(level=1, content="目录").to_dict())
        children.append(TableOfContentsBlock().to_dict())

    def _add_chapter_content(
        self,
        children: List[BlockDict],
        grandchild: Dict[int, BlockDict],
        chapter: Dict[int, Dict],
        bookmark_list: List[Dict],
    ) -> None:
        grouped_bookmarks = self._group_bookmarks_by_chapter(bookmark_list)

        for chapter_id, bookmarks in grouped_bookmarks.items():
            if chapter_id in chapter:
                children.append(self._create_chapter_heading(chapter, chapter_id))

            for bookmark in bookmarks:
                self._add_bookmark_with_abstract(children, grandchild, bookmark)

    def _add_bookmarks(
        self, children: List[BlockDict], bookmark_list: List[Dict]
    ) -> None:
        for bookmark in bookmark_list:
            # Instantiate CalloutBlock directly
            children.append(
                CalloutBlock(
                    content=bookmark.get("markText", ""),  # Provide default for content
                    style=bookmark.get("style"),
                    color_style=bookmark.get("colorStyle"),
                    review_id=bookmark.get("reviewId"),
                ).to_dict()
            )

    def _add_summary(self, children: List[BlockDict], summary: List[Dict]) -> None:
        # Instantiate HeadingBlock directly
        children.append(HeadingBlock(level=1, content="点评").to_dict())
        for review in summary:
            review_data = review.get("review", {})
            # Instantiate CalloutBlock directly
            children.append(
                CalloutBlock(
                    content=review_data.get("content", ""),  # Provide default
                    style=review.get("style"),  # Style might be on the outer dict
                    color_style=review.get(
                        "colorStyle"
                    ),  # colorStyle might be on the outer dict
                    review_id=review_data.get("reviewId"),
                ).to_dict()
            )

    @staticmethod
    def _group_bookmarks_by_chapter(bookmark_list: List[Dict]) -> Dict[int, List[Dict]]:
        # This method remains the same as it doesn't involve block creation
        grouped = {}
        for bookmark in bookmark_list:
            chapter_id = bookmark.get("chapterUid", 1)
            if chapter_id not in grouped:
                grouped[chapter_id] = []
            grouped[chapter_id].append(bookmark)
        return grouped

    def _create_chapter_heading(
        self, chapter: Dict[int, Dict], chapter_id: int
    ) -> BlockDict:
        chapter_info = chapter[chapter_id]
        # Instantiate HeadingBlock directly
        return HeadingBlock(
            level=chapter_info.get("level", 1),
            content=chapter_info.get("title", ""),  # Provide default
        ).to_dict()

    def _add_bookmark_with_abstract(
        self,
        children: List[BlockDict],
        grandchild: Dict[int, BlockDict],
        bookmark: Dict,
    ) -> None:
        # Instantiate CalloutBlock directly
        callout_block = CalloutBlock(
            content=bookmark.get("markText", ""),  # Provide default
            style=bookmark.get("style"),
            color_style=bookmark.get("colorStyle"),
            review_id=bookmark.get("reviewId"),
        )
        children.append(callout_block.to_dict())

        if abstract := bookmark.get("abstract"):
            # Instantiate QuoteBlock directly
            grandchild[len(children) - 1] = QuoteBlock(content=abstract).to_dict()

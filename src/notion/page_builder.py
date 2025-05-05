from typing import Dict, List, Optional, Tuple

from logger import logger
from notion.blocks import BlockDict, NotionBlockBuilder


class PageContentBuilder:
    """Builds the content structure for a Notion page (specifically for a book)"""

    def __init__(self, block_builder: NotionBlockBuilder):
        self.block_builder = block_builder

    def build_book_content(
        self,
        chapter: Optional[Dict[int, Dict]],
        summary: List[Dict],
        bookmark_list: List[Dict],
    ) -> Tuple[List[BlockDict], Dict[int, BlockDict]]:
        """Builds the complete content structure for a book page"""
        children = []
        grandchild = {}

        if chapter is not None:
            self._add_table_of_contents(children)
            self._add_chapter_content(children, grandchild, chapter, bookmark_list)
        else:
            self._add_bookmarks(children, bookmark_list)

        if summary:
            self._add_summary(children, summary)

        logger.info(f"Children: {children}")
        logger.info(f"Grandchild: {grandchild}")
        return children, grandchild

    def _add_table_of_contents(self, children: List[BlockDict]) -> None:
        children.append(self.block_builder.heading(1, "目录"))
        children.append(self.block_builder.table_of_contents())

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
            children.append(
                self.block_builder.callout(
                    bookmark.get("markText"),
                    bookmark.get("style"),
                    bookmark.get("colorStyle"),
                    bookmark.get("reviewId"),
                )
            )

    def _add_summary(self, children: List[BlockDict], summary: List[Dict]) -> None:
        children.append(self.block_builder.heading(1, "点评"))
        for review in summary:
            children.append(
                self.block_builder.callout(
                    review.get("review", {}).get("content"),
                    review.get("style"),
                    review.get("colorStyle"),
                    review.get("review", {}).get("reviewId"),
                )
            )

    @staticmethod
    def _group_bookmarks_by_chapter(bookmark_list: List[Dict]) -> Dict[int, List[Dict]]:
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
        return self.block_builder.heading(
            chapter_info.get("level", 1), chapter_info.get("title", "")
        )

    def _add_bookmark_with_abstract(
        self,
        children: List[BlockDict],
        grandchild: Dict[int, BlockDict],
        bookmark: Dict,
    ) -> None:
        callout = self.block_builder.callout(
            bookmark.get("markText"),
            bookmark.get("style"),
            bookmark.get("colorStyle"),
            bookmark.get("reviewId"),
        )
        children.append(callout)

        if abstract := bookmark.get("abstract"):
            grandchild[len(children) - 1] = self.block_builder.quote(abstract)

from dataclasses import dataclass
from typing import Optional

from book import Book
from logger import logger
from notion.block_manager import NotionBlockManager
from notion.blocks import NotionBlockBuilder
from notion.content_builder import BookContentBuilder
from notion.database import NotionDatabaseManager


@dataclass
class NotionManager:
    """Coordinates all Notion operations"""

    database_manager: NotionDatabaseManager
    block_manager: NotionBlockManager
    content_builder: BookContentBuilder

    @classmethod
    def create(cls, notion_token: str, database_id: str) -> "NotionManager":
        """Factory method to create a NotionManager with all its components"""
        from notion_client import Client

        client = Client(auth=notion_token)
        database_manager = NotionDatabaseManager(client, database_id)
        block_manager = NotionBlockManager(client)
        content_builder = BookContentBuilder(NotionBlockBuilder())

        return cls(database_manager, block_manager, content_builder)

    def process_book(self, book: Book) -> Optional[str]:
        """Process a single book"""
        try:
            # Check and delete existing entry
            self.database_manager.check_and_delete(book.bookId)

            # Create the page
            page_id = self.database_manager.create_book_page(book)

            # Build the content
            children, grandchild = self.content_builder.build_book_content(
                book.chapters, book.summary, book.bookmark_list
            )

            # Add the content
            results = self.block_manager.add_children(page_id, children)
            if results and grandchild:
                self.block_manager.add_grandchildren(results, grandchild)

            return page_id
        except Exception as e:
            logger.error(f"Error processing book {book.title}: {e}")
            return None

    def get_latest_sort(self) -> int:
        """Get the latest sort value from the database"""
        return self.database_manager.get_latest_sort()

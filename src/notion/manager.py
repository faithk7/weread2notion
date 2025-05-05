from dataclasses import dataclass
from typing import Optional

from book import Book
from logger import logger
from notion.block_manager import NotionBlockManager
from notion.blocks import NotionBlockBuilder
from notion.database import NotionDatabaseManager
from notion.page_builder import PageContentBuilder


@dataclass
class NotionManager:
    """Coordinates all Notion operations"""

    database_manager: NotionDatabaseManager
    block_manager: NotionBlockManager
    content_builder: PageContentBuilder

    @classmethod
    def create(cls, notion_token: str, database_id: str) -> "NotionManager":
        """Factory method to create a NotionManager with all its components"""
        from notion_client import Client

        client = Client(auth=notion_token)
        database_manager = NotionDatabaseManager(client, database_id)
        block_manager = NotionBlockManager(client)
        content_builder = PageContentBuilder(NotionBlockBuilder())

        return cls(database_manager, block_manager, content_builder)

    def process_book(self, book: Book) -> Optional[str]:
        """Process a single book"""
        try:
            # Check and delete existing entry
            self.database_manager.check_and_delete(book.bookId)

            # Create the page
            page_id = self.database_manager.create_book_page(book)
            if not page_id:
                logger.error(f"Failed to create Notion page for book: {book.title}")
                return None

            # Build the content using the renamed builder
            children, grandchild = self.content_builder.build_book_content(
                book.chapters, book.summary, book.bookmark_list
            )

            # Add the content only after we create the page
            if children:
                results = self.block_manager.add_children(page_id, children)
                if results and grandchild:
                    self.block_manager.add_grandchildren(results, grandchild)
            else:
                logger.info(f"No content (children) generated for book: {book.title}")

            return page_id
        except Exception as e:
            logger.error(f"Error processing book {book.title}: {e}")
            return None

    def get_latest_sort(self) -> int:
        """Get the latest sort value from the database"""
        return self.database_manager.get_latest_sort()

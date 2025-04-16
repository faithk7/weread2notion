import argparse
import random
from datetime import datetime
from typing import Any, Dict, List, Tuple

from book import Book, BookService
from logger import logger
from notion import NotionManager
from weread import WeReadClient, get_notebooklist


def parse_arguments() -> Tuple[str, str, str, bool]:
    parser = argparse.ArgumentParser()
    for arg in ["weread_cookie", "notion_token", "database_id"]:
        parser.add_argument(arg)
    parser.add_argument(
        "--dev", action="store_true", help="Run in dev mode with limited books"
    )
    options = parser.parse_args()
    return (
        options.weread_cookie,
        options.notion_token,
        options.database_id,
        options.dev,
    )


def process_books(
    books: List[Dict[str, Any]],
    latest_sort: int,
    notion_manager: NotionManager,
    book_service: BookService,
) -> None:
    """Process a list of books and sync them to Notion"""
    for book_json in books:
        try:
            current_sort = book_json.get("sort")
            if current_sort <= latest_sort:
                logger.info(f"Skipping book with sort {current_sort} <= {latest_sort}")
                continue

            book = Book.from_json(book_json)
            book = book_service.load_book_details(book)

            logger.info(f"Processing book: {book.bookId} - {book.title} - {book.isbn}")

            page_id = notion_manager.process_book(book)
            if page_id:
                logger.info(f"Successfully processed book: {book.title}")
            else:
                logger.error(f"Failed to process book: {book.title}")

        except Exception as e:
            logger.error(
                f"Error processing book {book_json.get('book', {}).get('title')}: {e}"
            )


def main() -> None:
    # Parse command line arguments
    weread_cookie, notion_token, database_id, dev_mode = parse_arguments()

    # Initialize services
    notion_manager = NotionManager.create(notion_token, database_id)
    weread_client = WeReadClient(weread_cookie)
    book_service = BookService(weread_client)

    # Get latest sort value from Notion
    latest_sort = notion_manager.get_latest_sort()
    logger.info(f"Latest sort value from Notion: {latest_sort}")

    # Get books from WeRead
    books = get_notebooklist(weread_client.session)
    if not books:
        logger.error("Failed to get books from WeRead")
        return

    # Handle dev mode
    if dev_mode:
        logger.info("Running in dev mode - randomly selecting 30 books")
        books = random.sample(books, min(30, len(books)))
        logger.info(
            f"Selected books: {[{'title': book['book']['title'], 'sort': book['sort']} for book in books]}"
        )

    # Process books
    start_time = datetime.now()
    process_books(books, latest_sort, notion_manager, book_service)
    logger.info(f"Total processing time: {datetime.now() - start_time}")


if __name__ == "__main__":
    main()

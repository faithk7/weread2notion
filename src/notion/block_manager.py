import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from notion_client import Client
from notion_client.errors import APIResponseError

from logger import logger
from notion.blocks import BlockDict


def retry(max_retries: int = 2, initial_delay: float = 1.0):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for _ in range(max_retries):
                try:
                    time.sleep(delay)  # Always wait before making a request
                    return func(*args, **kwargs)
                except APIResponseError as e:
                    logger.error(f"Error: {e}")
                    raise
            return None

        return wrapper

    return decorator


class NotionBlockManager:
    """Manages block operations in Notion"""

    client: Client

    @retry()
    def _make_request(self, operation: Callable[[], Any]) -> Any:
        """Generic method to make Notion API requests with retry logic"""
        return operation()

    def add_children(
        self, page_id: str, children: List[BlockDict]
    ) -> Optional[List[Dict]]:
        results = []
        # Increase chunk size for fewer API calls
        chunk_size = 50  # Notion allows up to 100, but using 50 for better stability

        for i in range(0, len(children), chunk_size):
            chunk = children[i : i + chunk_size]

            def append_op(chunk=chunk):
                return self.client.blocks.children.append(
                    block_id=page_id, children=chunk
                )

            # Add a small delay between chunks to avoid rate limits
            if i > 0:
                time.sleep(0.5)  # 500ms delay between chunks

            response = self._make_request(append_op)
            if response and "results" in response:
                results.extend(response["results"])

        return results if len(results) == len(children) else None

    def add_grandchildren(
        self, parent_blocks: List[Dict], grandchildren: Dict[int, BlockDict]
    ) -> None:
        for block_index, block_content in grandchildren.items():
            block_id = parent_blocks[block_index].get("id")
            if not block_id:
                continue

            def append_op(block_id=block_id, block_content=block_content):
                return self.client.blocks.children.append(
                    block_id=block_id, children=[block_content]
                )

            self._make_request(append_op)

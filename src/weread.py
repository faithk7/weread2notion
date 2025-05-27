from typing import Any, Dict, List, Optional

import requests

from constants import (
    BOOKS_KEY,
    CHAPTERS_KEY,
    LOG_PREFIX_BOOK_INFO,
    LOG_PREFIX_BOOKMARKS,
    LOG_PREFIX_CHAPTER_INFO,
    LOG_PREFIX_CONNECTION_TEST,
    LOG_PREFIX_NOTEBOOK_LIST,
    LOG_PREFIX_READ_INFO,
    LOG_PREFIX_REVIEWS,
    REVIEWS_KEY,
    SORT_KEY,
    UPDATED_KEY,
    WEREAD_BOOK_INFO,
    WEREAD_BOOKMARKLIST_URL,
    WEREAD_CHAPTER_INFO,
    WEREAD_NOTEBOOKS_URL,
    WEREAD_READ_PROGRESS_URL,
    WEREAD_REVIEW_LIST_URL,
)
from logger import logger
from utils import parse_cookie_string


class WeReadClient:
    """微信读书客户端类，用于与微信读书API交互"""

    def __init__(self, weread_cookie: str):
        """初始化微信读书客户端

        Args:
            weread_cookie: 微信读书的cookie字符串
        """
        self.session = requests.Session()
        self.session.cookies = parse_cookie_string(weread_cookie)
        self.is_valid = False
        self._connect()
        assert (
            self.is_valid
        ), "WeRead client initialization failed. Check cookie validity."

    def _fetch(
        self,
        url: str,
        params: Optional[Dict] = None,
        method: str = "GET",
        log_prefix: str = "request",
        expected_keys: Optional[List[str]] = None,
    ) -> Optional[Any]:
        """执行HTTP请求并处理常见错误

        Args:
            url: 请求的URL
            params: 请求参数
            method: HTTP方法
            log_prefix: 日志前缀
            expected_keys: 期望的响应键列表

        Returns:
            响应的JSON数据，如果失败则返回None
        """
        try:
            response = self.session.request(method, url, params=params, timeout=10)
            response_json = response.json()

            # 可选的基本验证，检查期望的键是否存在
            if expected_keys and not all(key in response_json for key in expected_keys):
                logger.warning(
                    f"Missing expected keys {expected_keys} in {log_prefix} response from {url}"
                )
                # 决定这是否应该是硬失败或只是警告
                # return None # 如果缺少键应该导致失败，请取消注释

            return response_json

        except requests.exceptions.Timeout:
            logger.error(f"Failed to fetch {log_prefix}: Request timed out.")
        except requests.exceptions.JSONDecodeError:
            logger.error(
                f"Failed to fetch {log_prefix}: Could not decode JSON response. Response: {response.text[:500]}"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {log_prefix}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching {log_prefix}: {e}")

    def get_bookinfo(self, book_id: str) -> Optional[Dict]:
        """获取书籍基本信息

        Args:
            book_id: 书籍ID

        Returns:
            书籍信息字典
        """
        return self._fetch(
            WEREAD_BOOK_INFO,
            params=dict(bookId=book_id),
            log_prefix=f"{LOG_PREFIX_BOOK_INFO} {book_id}",
        )

    def get_readinfo(self, book_id: str) -> Optional[Dict]:
        """获取书籍阅读进度信息

        Args:
            book_id: 书籍ID

        Returns:
            阅读进度信息字典
        """
        return self._fetch(
            WEREAD_READ_PROGRESS_URL,
            params=dict(
                bookId=book_id, readingDetail=1, readingBookIndex=1, finishedDate=1
            ),
            log_prefix=f"{LOG_PREFIX_READ_INFO} {book_id}",
        )

    def get_reviews(self, book_id: str) -> List[Dict]:
        """获取书籍的书评列表

        Args:
            book_id: 书籍ID

        Returns:
            书评列表
        """
        return (
            self._fetch(
                WEREAD_REVIEW_LIST_URL,
                params=dict(bookId=book_id, listType=11, mine=1, syncKey=0),
                log_prefix=f"{LOG_PREFIX_REVIEWS} {book_id}",
            )[REVIEWS_KEY]
            or []
        )

    def get_bookmarks(self, book_id: str) -> List[Dict]:
        """获取书籍的书签/划线列表

        Args:
            book_id: 书籍ID

        Returns:
            书签列表
        """
        bookmarks_list = self._fetch(
            WEREAD_BOOKMARKLIST_URL,
            params=dict(bookId=book_id),
            log_prefix=f"{LOG_PREFIX_BOOKMARKS} {book_id}",
            expected_keys=[UPDATED_KEY],
        ).get(UPDATED_KEY, [])

        return bookmarks_list

    def get_chapters(self, book_id: str) -> Optional[List[Dict]]:
        """获取书籍的章节信息列表

        Args:
            book_id: 书籍ID

        Returns:
            章节信息列表
        """
        chapter_list = self._fetch(
            WEREAD_CHAPTER_INFO,
            params=dict(bookId=book_id),
            log_prefix=f"{LOG_PREFIX_CHAPTER_INFO} {book_id}",
        ).get(CHAPTERS_KEY, [])
        return chapter_list

    def get_notebooklist(self) -> List[Dict]:
        """获取笔记本列表（用户有做笔记的所有书籍）

        Returns:
            按排序字段排序的书籍列表
        """
        notebook_response = self._fetch(
            WEREAD_NOTEBOOKS_URL, log_prefix=LOG_PREFIX_NOTEBOOK_LIST
        )

        books = notebook_response.get(BOOKS_KEY, [])
        # 按'sort'键排序，如果缺少则默认为大数字以将其放在最后
        books.sort(key=lambda x: x.get(SORT_KEY, float("inf")))
        return books

    def _connect(self) -> None:
        """尝试连接到微信读书并验证会话/cookie

        设置self.is_valid标志以指示连接是否成功
        """
        try:
            # 使用_fetch进行连接测试
            response_data = self._fetch(
                WEREAD_NOTEBOOKS_URL, log_prefix=LOG_PREFIX_CONNECTION_TEST
            )
            if response_data is not None:
                self.is_valid = True
                logger.info("WeRead client connected successfully.")
            else:
                self.is_valid = False
        except Exception as e:  # 捕获连接逻辑本身的潜在意外错误
            self.is_valid = False
            logger.error(f"An unexpected error occurred during WeRead connection: {e}")

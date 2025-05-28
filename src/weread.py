from typing import Any, Dict, List, Optional

import httpx

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
from cookie_manager import WeReadCookieManager
from logger import logger
from utils import parse_cookie_string


class WeReadClient:
    """微信读书客户端类，用于与微信读书API交互"""

    def __init__(
        self, weread_cookie: Optional[str] = None, auto_refresh_cookie: bool = True
    ):
        """初始化微信读书客户端

        Args:
            weread_cookie: 微信读书的cookie字符串（可选，如果不提供则自动获取）
            auto_refresh_cookie: 是否自动刷新过期的cookie
        """
        self.session = httpx.Client()
        self.auto_refresh_cookie = auto_refresh_cookie
        self.cookie_manager = WeReadCookieManager() if auto_refresh_cookie else None
        self.is_valid = False

        # 设置初始cookie
        if weread_cookie:
            self._set_cookies(weread_cookie)
        elif auto_refresh_cookie:
            # 尝试获取有效的cookie
            cookie_string = self.cookie_manager.get_valid_cookie()
            if cookie_string:
                self._set_cookies(cookie_string)

        self._connect()
        assert (
            self.is_valid
        ), "WeRead client initialization failed. Check cookie validity."

    def _set_cookies(self, cookie_string: str) -> None:
        """设置会话的cookies

        Args:
            cookie_string: cookie字符串
        """
        self.session.cookies = parse_cookie_string(cookie_string)

    def _refresh_cookies(self) -> bool:
        """刷新cookies

        Returns:
            是否成功刷新
        """
        if not self.auto_refresh_cookie or not self.cookie_manager:
            return False

        logger.info("尝试刷新Cookie...")
        new_cookie = self.cookie_manager.get_valid_cookie(force_refresh=True)
        if new_cookie:
            self._set_cookies(new_cookie)
            logger.info("Cookie刷新成功")
            return True
        else:
            logger.error("Cookie刷新失败")
            return False

    def _fetch(
        self,
        url: str,
        params: Optional[Dict] = None,
        method: str = "GET",
        log_prefix: str = "request",
        expected_keys: Optional[List[str]] = None,
        retry_on_auth_error: bool = True,
    ) -> Optional[Any]:
        """执行HTTP请求并处理常见错误

        Args:
            url: 请求的URL
            params: 请求参数
            method: HTTP方法
            log_prefix: 日志前缀
            expected_keys: 期望的响应键列表
            retry_on_auth_error: 是否在认证错误时重试

        Returns:
            响应的JSON数据，如果失败则返回None
        """
        try:
            logger.info(f"Making {method} request to {url} with params: {params}")
            response = self.session.request(method, url, params=params, timeout=10)
            logger.info(f"Response status code: {response.status_code}")

            # 检查是否是认证错误（401, 403等）
            if (
                response.status_code in [401, 403]
                and retry_on_auth_error
                and self.auto_refresh_cookie
            ):
                logger.warning(
                    f"认证失败 (状态码: {response.status_code})，尝试刷新Cookie"
                )
                if self._refresh_cookies():
                    # 重试请求
                    return self._fetch(
                        url, params, method, log_prefix, expected_keys, False
                    )
                else:
                    logger.error("Cookie刷新失败，无法继续请求")
                    return None

            # Check if response is successful
            if response.status_code != 200:
                logger.error(
                    f"HTTP error {response.status_code} for {log_prefix}: {response.text[:500]}"
                )
                return None

            response_json = response.json()
            logger.info(f"Response: {response_json}")

            # Check for WeRead API error codes
            if isinstance(response_json, dict) and "errCode" in response_json:
                err_code = response_json.get("errCode")
                err_msg = response_json.get("errMsg", "Unknown error")
                if err_code != 0:  # 0 usually means success in WeRead API
                    logger.error(
                        f"WeRead API error for {log_prefix}: errCode={err_code}, errMsg={err_msg}"
                    )
                    return None

            # 可选的基本验证，检查期望的键是否存在
            if expected_keys and not all(key in response_json for key in expected_keys):
                logger.warning(
                    f"Missing expected keys {expected_keys} in {log_prefix} response from {url}"
                )
                # 决定这是否应该是硬失败或只是警告
                # return None # 如果缺少键应该导致失败，请取消注释

            return response_json

        except httpx.TimeoutException:
            logger.error(f"Failed to fetch {log_prefix}: Request timed out.")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for {log_prefix}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {log_prefix}: {e}")
            return None

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
        return self._fetch(
            WEREAD_REVIEW_LIST_URL,
            params=dict(bookId=book_id, listType=11, mine=1, syncKey=0),
            log_prefix=f"{LOG_PREFIX_REVIEWS} {book_id}",
        ).get(REVIEWS_KEY, [])

    def get_bookmarks(self, book_id: str) -> List[Dict]:
        """获取书籍的书签/划线列表

        Args:
            book_id: 书籍ID

        Returns:
            书签列表
        """
        result = self._fetch(
            WEREAD_BOOKMARKLIST_URL,
            params=dict(bookId=book_id),
            log_prefix=f"{LOG_PREFIX_BOOKMARKS} {book_id}",
            expected_keys=[UPDATED_KEY],
        )
        return result.get(UPDATED_KEY, []) if result else []

    def get_chapters(self, book_id: str) -> Optional[List[Dict]]:
        """获取书籍的章节信息列表

        Args:
            book_id: 书籍ID

        Returns:
            章节信息列表
        """
        result = self._fetch(
            WEREAD_CHAPTER_INFO,
            params=dict(bookId=book_id),
            log_prefix=f"{LOG_PREFIX_CHAPTER_INFO} {book_id}",
        )
        return result.get(CHAPTERS_KEY, []) if result else []

    def get_notebooklist(self) -> List[Dict]:
        """获取笔记本列表（用户有做笔记的所有书籍）

        Returns:
            按排序字段排序的书籍列表
        """
        result = self._fetch(WEREAD_NOTEBOOKS_URL, log_prefix=LOG_PREFIX_NOTEBOOK_LIST)

        if not result:
            return []

        books = result.get(BOOKS_KEY, [])
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

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        self.close()

    def close(self):
        """Close the HTTP client session"""
        if hasattr(self, "session") and self.session:
            self.session.close()

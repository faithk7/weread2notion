import json
import time
from pathlib import Path
from typing import Dict, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from logger import logger


class WeReadCookieManager:
    """微信读书Cookie管理器，用于自动获取和刷新Cookie"""

    def __init__(self, cookie_file: str = "weread_cookies.json"):
        """初始化Cookie管理器

        Args:
            cookie_file: Cookie存储文件路径
        """
        self.cookie_file = Path(cookie_file)
        self.cookies: Optional[Dict] = None

    def load_cookies(self) -> Optional[str]:
        """从文件加载已保存的Cookie

        Returns:
            Cookie字符串，如果文件不存在或过期则返回None
        """
        if not self.cookie_file.exists():
            logger.info("Cookie文件不存在，需要重新获取")
            return None

        try:
            with open(self.cookie_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 检查Cookie是否过期（这里简单检查时间戳）
            if self._is_cookie_expired(data.get("timestamp", 0)):
                logger.info("Cookie已过期，需要重新获取")
                return None

            logger.info("成功加载已保存的Cookie")
            return data.get("cookie_string", "")

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"读取Cookie文件失败: {e}")
            return None

    def save_cookies(self, cookie_string: str) -> None:
        """保存Cookie到文件

        Args:
            cookie_string: Cookie字符串
        """
        data = {"cookie_string": cookie_string, "timestamp": int(time.time())}

        try:
            with open(self.cookie_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Cookie已保存到 {self.cookie_file}")
        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")

    def fetch_cookies_with_browser(self, headless: bool = True) -> Optional[str]:
        """使用浏览器自动化获取Cookie

        Args:
            headless: 是否使用无头模式

        Returns:
            Cookie字符串
        """
        driver = None
        try:
            # 配置Chrome选项
            chrome_options = Options()
            if headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            # 启动浏览器
            driver = webdriver.Chrome(options=chrome_options)
            driver.get("https://weread.qq.com/")

            # 等待用户登录（如果是无头模式，这里需要其他方式）
            if not headless:
                logger.info("请在浏览器中完成登录，然后按回车继续...")
                input("登录完成后按回车键继续...")
            else:
                # 无头模式下，等待登录元素出现或使用其他自动登录方式
                self._wait_for_login(driver)

            # 获取所有Cookie
            cookies = driver.get_cookies()
            cookie_string = self._format_cookies(cookies)

            if cookie_string:
                self.save_cookies(cookie_string)
                logger.info("成功获取并保存Cookie")
                return cookie_string
            else:
                logger.error("未能获取有效的Cookie")
                return None

        except Exception as e:
            logger.error(f"获取Cookie时发生错误: {e}")
            return None
        finally:
            if driver:
                driver.quit()

    def _wait_for_login(self, driver: webdriver.Chrome, timeout: int = 300) -> None:
        """等待用户登录完成

        Args:
            driver: WebDriver实例
            timeout: 超时时间（秒）
        """
        try:
            # 等待登录后的特征元素出现（比如用户头像、书架等）
            wait = WebDriverWait(driver, timeout)

            # 这里需要根据实际的WeRead页面结构调整选择器
            # 可能的登录后元素：用户头像、书架、个人中心等
            login_indicators = [
                "//div[contains(@class, 'avatar')]",  # 用户头像
                "//div[contains(@class, 'bookshelf')]",  # 书架
                "//div[contains(@class, 'user')]",  # 用户信息
            ]

            for indicator in login_indicators:
                try:
                    wait.until(EC.presence_of_element_located((By.XPATH, indicator)))
                    logger.info("检测到登录成功")
                    return
                except:
                    continue

            logger.warning("未检测到登录成功的标志，但继续尝试获取Cookie")

        except Exception as e:
            logger.warning(f"等待登录时出现异常: {e}")

    def _format_cookies(self, cookies: list) -> str:
        """将Cookie列表格式化为字符串

        Args:
            cookies: Selenium获取的Cookie列表

        Returns:
            格式化的Cookie字符串
        """
        cookie_pairs = []
        for cookie in cookies:
            name = cookie.get("name", "")
            value = cookie.get("value", "")
            if name and value:
                cookie_pairs.append(f"{name}={value}")

        return "; ".join(cookie_pairs)

    def _is_cookie_expired(self, timestamp: int, max_age_hours: int = 24) -> bool:
        """检查Cookie是否过期

        Args:
            timestamp: Cookie保存时间戳
            max_age_hours: Cookie最大有效期（小时）

        Returns:
            是否过期
        """
        current_time = int(time.time())
        max_age_seconds = max_age_hours * 3600
        return (current_time - timestamp) > max_age_seconds

    def get_valid_cookie(self, force_refresh: bool = False) -> Optional[str]:
        """获取有效的Cookie

        Args:
            force_refresh: 是否强制刷新Cookie

        Returns:
            有效的Cookie字符串
        """
        if not force_refresh:
            # 尝试加载已保存的Cookie
            cookie_string = self.load_cookies()
            if cookie_string:
                return cookie_string

        # 如果没有有效的Cookie，则重新获取
        logger.info("正在获取新的Cookie...")
        return self.fetch_cookies_with_browser(headless=False)


def get_weread_cookie(force_refresh: bool = False) -> Optional[str]:
    """便捷函数：获取WeRead Cookie

    Args:
        force_refresh: 是否强制刷新

    Returns:
        Cookie字符串
    """
    manager = WeReadCookieManager()
    return manager.get_valid_cookie(force_refresh=force_refresh)

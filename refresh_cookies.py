#!/usr/bin/env python3
"""
微信读书Cookie刷新工具

使用方法:
1. 自动刷新: python refresh_cookies.py
2. 强制刷新: python refresh_cookies.py --force
3. 查看当前cookie状态: python refresh_cookies.py --status
"""

import argparse
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.cookie_manager import WeReadCookieManager
from src.logger import logger


def main():
    parser = argparse.ArgumentParser(description="微信读书Cookie管理工具")
    parser.add_argument(
        "--force", action="store_true", help="强制刷新Cookie，即使当前Cookie仍然有效"
    )
    parser.add_argument("--status", action="store_true", help="查看当前Cookie状态")
    parser.add_argument(
        "--headless", action="store_true", help="使用无头模式（不显示浏览器窗口）"
    )

    args = parser.parse_args()

    manager = WeReadCookieManager()

    if args.status:
        # 查看Cookie状态
        cookie = manager.load_cookies()
        if cookie:
            print("✅ 找到有效的Cookie")
            print(f"Cookie文件: {manager.cookie_file}")
            print(f"Cookie长度: {len(cookie)} 字符")
        else:
            print("❌ 没有找到有效的Cookie")
        return

    # 获取或刷新Cookie
    try:
        if args.force:
            print("🔄 强制刷新Cookie...")
            cookie = manager.fetch_cookies_with_browser(headless=args.headless)
        else:
            print("🔍 检查Cookie状态...")
            cookie = manager.get_valid_cookie()

        if cookie:
            print("✅ Cookie获取成功!")
            print(f"Cookie已保存到: {manager.cookie_file}")

            # 测试Cookie是否有效
            print("🧪 测试Cookie有效性...")
            from src.weread import WeReadClient

            try:
                client = WeReadClient(weread_cookie=cookie, auto_refresh_cookie=False)
                if client.is_valid:
                    print("✅ Cookie测试通过，可以正常使用")
                else:
                    print("❌ Cookie测试失败，可能需要重新获取")
            except Exception as e:
                print(f"❌ Cookie测试时出错: {e}")
        else:
            print("❌ Cookie获取失败")
            print("请确保:")
            print("1. Chrome浏览器已安装")
            print("2. 网络连接正常")
            print("3. 能够正常访问微信读书网站")

    except KeyboardInterrupt:
        print("\n⏹️ 用户取消操作")
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        logger.error(f"Cookie刷新工具出错: {e}")


if __name__ == "__main__":
    main()

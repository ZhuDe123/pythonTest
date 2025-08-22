import asyncio
from playwright.async_api import async_playwright, TimeoutError, Page
import os
import datetime
import sys

# 确保 login_and_save_state.py 在当前脚本可访问的路径中
# 如果不在同一目录，请根据实际情况调整 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 从 login_and_save_state 模块导入 login_and_save_state 函数
try:
    from login_and_save_state import login_and_save_state as perform_login_action
except ImportError:
    print(
        f"[{datetime.datetime.now()}] [错误] 无法导入 'login_and_save_state.py'。请确保该文件与 'refresh_huggingface.py' 在同一目录下。")
    sys.exit(1)  # 无法导入关键模块，直接退出

# --- 配置参数 ---
STORAGE_STATE_PATH = "/home/zhudeshuai/software/huggingface_refresh/huggingface_state.json"  # 确保路径与保存时一致
# STORAGE_STATE_PATH = "huggingface_state.json"  # 确保路径与保存时一致
TARGET_URL = "https://huggingface.co/spaces/zhuhuggingface/zhuhuggingfacevv1"

# Hugging Face Space 内部的 Jupyter 密码
HF_JUPYTER_TOKEN = "zds139"  # 替换为你的实际密码

# iframe 的选择器和 src 前缀
IFRAME_SELECTOR = 'iframe[id="iFrameResizer0"]'
IFRAME_SRC_PREFIX = "https://zhuhuggingface-zhuhuggingfacevv1.hf.space/"

MAX_REFRESH_RETRIES = 3  # 最大刷新重试次数
MAX_LOGIN_RETRIES = 2  # 最大登录重试次数


async def refresh_page_internal(p: async_playwright) -> bool:
    """
    执行一次 Hugging Face Space 的刷新操作。
    如果成功返回 True，否则返回 False（表示可能需要重新登录或遇到其他错误）。
    """
    browser = None
    try:
        # 启动无头浏览器，并加载之前保存的会话状态
        browser = await p.chromium.launch(headless=True)  # 刷新时通常使用无头模式
        context = await browser.new_context(storage_state=STORAGE_STATE_PATH)
        page: Page = await context.new_page()

        print(f"[{datetime.datetime.now()}] [刷新模块] 导航到目标URL: {TARGET_URL}，使用已保存的会话状态...")
        await page.goto(TARGET_URL, timeout=60000)  # 60秒超时

        print(f"[{datetime.datetime.now()}] [刷新模块] 页面加载完成。当前标题: {await page.title()}")
        print(f"[{datetime.datetime.now()}] [刷新模块] 当前URL: {page.url}")

        # --- 检查是否需要重新登录 ---
        # 1. 检查当前URL是否跳转到了登录页面
        if "login" in page.url or "oauth" in page.url:
            print(f"[{datetime.datetime.now()}] [警告] 当前URL '{page.url}' 似乎是登录页面，会话可能已过期。")
            return False  # 返回 False，指示需要重新登录

        # 2. 尝试查找登录页面的特定元素，以防URL未完全跳转但内容已变为登录页
        try:
            # 检查页面中是否存在登录表单的用户名输入框
            await page.wait_for_selector('input[name="username"]', timeout=5000)
            print(f"[{datetime.datetime.now()}] [警告] 页面中检测到登录表单元素，会话可能已过期。")
            return False  # 返回 False，指示需要重新登录
        except TimeoutError:
            # 未找到登录元素，说明可能不是登录页，继续执行
            pass

        # 3. 检查是否是 404 错误页面 (根据提供的截图)
        try:
            # 检查是否存在 h1 标签包含 "404" 文本
            h1_404_element = await page.query_selector('h1:has-text("404")')
            # 检查是否存在 p 标签包含 "Sorry, we can't find the page you are looking for." 文本
            p_not_found_element = await page.query_selector(
                'p:has-text("Sorry, we can\'t find the page you are looking for.")')

            if h1_404_element and p_not_found_element:
                print(f"[{datetime.datetime.now()}] [警告] 页面检测到 404 错误信息，会话可能已过期或目标Space不可访问。")
                return False  # 返回 False，指示需要重新登录
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [刷新模块] 检查 404 页面时发生错误: {e}")
            # 即使检查 404 失败，也不应立即返回 False，因为可能是其他问题，让后续流程判断

        # --- 步骤1: 等待 iframe 元素本身加载 ---
        print(f"[{datetime.datetime.now()}] [刷新模块] 等待 iframe 元素: {IFRAME_SELECTOR} 加载...")
        iframe_element_handle = None
        try:
            iframe_element_handle = await page.wait_for_selector(IFRAME_SELECTOR, timeout=30000)
            print(f"[{datetime.datetime.now()}] [刷新模块] 成功找到 iframe 元素。")
        except TimeoutError:
            print(f"[{datetime.datetime.now()}] [错误] 未能在30秒内找到主页面上的 iframe 元素 '{IFRAME_SELECTOR}'。")
            return False

        # --- 步骤2: 获取 iframe 的内容上下文 ---
        print(f"[{datetime.datetime.now()}] [刷新模块] 尝试获取 iframe 的内容框架...")
        iframe_frame = None
        if iframe_element_handle:
            iframe_frame = await iframe_element_handle.content_frame()
            if iframe_frame:
                try:
                    # 等待 iframe 内部的密码输入框，确认内容已加载
                    await iframe_frame.wait_for_selector('input[name="password"]', timeout=30000)
                    print(f"[{datetime.datetime.now()}] [刷新模块] 成功获取 iframe 框架并确认内容已加载。")
                    print(f"[{datetime.datetime.now()}] [刷新模块] iframe 框架的URL: {iframe_frame.url}")
                except TimeoutError:
                    print(f"[{datetime.datetime.now()}] [错误] iframe 内容（例如密码输入框）未能在30秒内加载。")
                    return False
            else:
                print(f"[{datetime.datetime.now()}] [错误] 无法从 iframe 元素句柄获取内容框架。")
                return False
        else:
            print(f"[{datetime.datetime.now()}] [错误] 未获取到 iframe 元素句柄。")
            return False

        # --- 步骤3: 在 iframe 内部进行操作 ---
        print(f"[{datetime.datetime.now()}] [刷新模块] 在 iframe 内部进行交互...")
        try:
            # 填充密码
            await iframe_frame.fill('input[name="password"]', HF_JUPYTER_TOKEN)
            print(f"[{datetime.datetime.now()}] [刷新模块] 密码已填充。")

            # 点击提交按钮
            await iframe_frame.click('button[type="submit"]')
            print(f"[{datetime.datetime.now()}] [刷新模块] 提交按钮已点击。")

            # 等待 iframe 内部内容更新或加载完成
            await asyncio.sleep(5)  # 给 iframe 内部的提交操作一些时间
            print(f"[{datetime.datetime.now()}] [刷新模块] 提交后等待5秒。")

        except TimeoutError:
            print(f"[{datetime.datetime.now()}] [错误] iframe 内部元素（密码字段或提交按钮）未能在超时时间内找到。")
            return False
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [错误] 与 iframe 交互时发生异常: {e}")
            return False

        # --- 步骤4: 模拟用户活跃 ---
        print(f"[{datetime.datetime.now()}] [刷新模块] 模拟用户活跃（滚动页面）...")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(10)  # 模拟用户停留10秒

        print(f"[{datetime.datetime.now()}] [刷新模块] 刷新过程成功完成。")
        return True

    except Exception as e:
        print(f"[{datetime.datetime.now()}] [错误] 刷新过程中发生意外错误: {e}")
        return False
    finally:
        if browser:
            await browser.close()
            print(f"[{datetime.datetime.now()}] [刷新模块] 浏览器已关闭。")


async def main():
    async with async_playwright() as p:
        for refresh_attempt in range(MAX_REFRESH_RETRIES):
            print(
                f"\n[{datetime.datetime.now()}] [主流程] 开始第 {refresh_attempt + 1}/{MAX_REFRESH_RETRIES} 次刷新尝试...")

            # 1. 检查会话状态文件是否存在
            if not os.path.exists(STORAGE_STATE_PATH):
                print(f"[{datetime.datetime.now()}] [主流程] 会话状态文件 '{STORAGE_STATE_PATH}' 不存在。")
                login_success = False
                for login_attempt in range(MAX_LOGIN_RETRIES):
                    print(
                        f"[{datetime.datetime.now()}] [主流程] 尝试进行第 {login_attempt + 1}/{MAX_LOGIN_RETRIES} 次登录并保存会话状态...")
                    # 只有第一次登录尝试使用 headless=False，后续重试使用 headless=True
                    login_success = await perform_login_action(STORAGE_STATE_PATH, headless=(login_attempt != 0))
                    if login_success:
                        print(f"[{datetime.datetime.now()}] [主流程] 登录成功，会话状态已保存。")
                        break
                    else:
                        print(f"[{datetime.datetime.now()}] [主流程] 第 {login_attempt + 1} 次登录尝试失败。")
                        if login_attempt < MAX_LOGIN_RETRIES - 1:
                            print(f"[{datetime.datetime.now()}] [主流程] 等待5秒后重试登录...")
                            await asyncio.sleep(5)

                if not login_success:
                    print(f"[{datetime.datetime.now()}] [主流程] 达到最大登录重试次数，无法获取有效的会话状态。退出程序。")
                    return  # 登录失败，直接退出整个程序

            # 2. 执行刷新操作
            refresh_successful = await refresh_page_internal(p)

            if refresh_successful:
                print(f"[{datetime.datetime.now()}] [主流程] 第 {refresh_attempt + 1} 次刷新尝试成功完成。")
                return  # 刷新成功，退出

            else:
                print(f"[{datetime.datetime.now()}] [主流程] 第 {refresh_attempt + 1} 次刷新尝试失败。")
                # 如果刷新失败，且不是最后一次尝试，则尝试重新登录并重试刷新
                if refresh_attempt < MAX_REFRESH_RETRIES - 1:
                    print(f"[{datetime.datetime.now()}] [主流程] 尝试重新登录以修复会话问题...")
                    login_success = False
                    for login_attempt in range(MAX_LOGIN_RETRIES):
                        print(
                            f"[{datetime.datetime.now()}] [主流程] 尝试进行第 {login_attempt + 1}/{MAX_LOGIN_RETRIES} 次重新登录...")
                        # 只有第一次重新登录尝试使用 headless=False，后续重试使用 headless=True
                        login_success = await perform_login_action(STORAGE_STATE_PATH, headless=(login_attempt != 0))
                        if login_success:
                            print(f"[{datetime.datetime.now()}] [主流程] 重新登录成功，会话状态已更新。")
                            break
                        else:
                            print(f"[{datetime.datetime.now()}] [主流程] 第 {login_attempt + 1} 次重新登录尝试失败。")
                            if login_attempt < MAX_LOGIN_RETRIES - 1:
                                print(f"[{datetime.datetime.now()}] [主流程] 等待5秒后重试重新登录...")
                                await asyncio.sleep(5)

                    if not login_success:
                        print(
                            f"[{datetime.datetime.now()}] [主流程] 达到最大重新登录重试次数，无法获取有效的会话状态。退出程序。")
                        return  # 重新登录失败，退出整个程序

                    print(f"[{datetime.datetime.now()}] [主流程] 等待5秒后，进行下一次刷新尝试...")
                    await asyncio.sleep(5)  # 重新登录后等待片刻再重试刷新
                else:
                    print(f"[{datetime.datetime.now()}] [主流程] 已达到最大刷新重试次数，且未能成功刷新。退出程序。")


if __name__ == "__main__":
    asyncio.run(main())

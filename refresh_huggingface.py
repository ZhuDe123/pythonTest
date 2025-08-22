import asyncio
from playwright.async_api import async_playwright, TimeoutError, Page
import os
import datetime

# --- 配置参数 ---
STORAGE_STATE_PATH = "/home/zhudeshuai/software/huggingface_refresh/huggingface_state.json" # 确保路径与保存时一致
TARGET_URL = "https://huggingface.co/spaces/zhuhuggingface/zhuhuggingfacevv1"

# Hugging Face Space 内部的 Jupyter 密码
# 强烈建议使用环境变量来存储敏感信息，例如：
# HF_JUPYTER_TOKEN = os.getenv("HF_JUPYTER_TOKEN", "default_token_if_not_set")
HF_JUPYTER_TOKEN = "zds139" # 替换为你的实际密码

# iframe 的选择器和 src 前缀
# 根据你提供的 iframe 标签，id="iFrameResizer0" 是一个稳定的选择器
IFRAME_SELECTOR = 'iframe[id="iFrameResizer0"]'
# iframe 的 src URL 的固定前缀，用于定位 iframe 的内容
# 注意：使用 content_frame() 后，通常不需要依赖 src 前缀来定位 iframe 本身，
# 但可以用于后续验证 iframe 内容是否正确加载。
IFRAME_SRC_PREFIX = "https://zhuhuggingface-zhuhuggingfacevv1.hf.space/"

async def refresh_page():
    # 检查会话状态文件是否存在
    if not os.path.exists(STORAGE_STATE_PATH):
        print(f"[{datetime.datetime.now()}] Error: {STORAGE_STATE_PATH} not found. Please run login_and_save_state.py first.")
        return

    browser = None # 初始化为 None，确保在 finally 块中可以安全关闭
    try:
        async with async_playwright() as p:
            # 启动无头浏览器，并加载之前保存的会话状态
            # 在生产环境中，将 headless 设置为 True
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=STORAGE_STATE_PATH)
            page: Page = await context.new_page() # 明确类型提示，有助于IDE检查

            print(f"[{datetime.datetime.now()}] Navigating to {TARGET_URL} with saved session...")
            await page.goto(TARGET_URL, timeout=60000) # 60秒超时

            print(f"[{datetime.datetime.now()}] Page loaded. Current title: {await page.title()}")

            # --- 步骤1: 等待 iframe 元素本身加载 ---
            print(f"[{datetime.datetime.now()}] Waiting for iframe element: {IFRAME_SELECTOR}...")
            iframe_element_handle = None
            try:
                # 等待 iframe 元素在主页面上出现
                iframe_element_handle = await page.wait_for_selector(IFRAME_SELECTOR, timeout=30000)
                print(f"[{datetime.datetime.now()}] Iframe element found.")
            except TimeoutError:
                print(f"[{datetime.datetime.now()}] Error: Iframe element {IFRAME_SELECTOR} not found on main page within timeout.")
                return

            # --- 步骤2: 获取 iframe 的内容上下文 ---
            # 使用 element_handle.content_frame() 来获取 iframe 的 Frame 对象
            print(f"[{datetime.datetime.now()}] Attempting to get iframe frame from element handle...")
            iframe_frame = None
            if iframe_element_handle:
                iframe_frame = await iframe_element_handle.content_frame()
                if iframe_frame:
                    # 额外检查 iframe 的 URL 是否符合预期，确保是正确的 iframe
                    # content_frame() 返回的 Frame 对象可能在加载中，需要等待其URL稳定
                    # 可以通过等待一个 iframe 内部的元素来确保其内容已加载
                    try:
                        # 等待 iframe 内部的某个元素，例如密码输入框，来确认 iframe 内容已加载
                        # 这一步也隐式地确认了 iframe_frame 已经加载了预期的内容
                        await iframe_frame.wait_for_selector('input[name="password"]', timeout=30000)
                        print(f"[{datetime.datetime.now()}] Successfully obtained iframe frame and confirmed content loaded.")
                        print(f"[{datetime.datetime.now()}] Iframe frame URL: {iframe_frame.url}")
                    except TimeoutError:
                        print(f"[{datetime.datetime.now()}] Error: Iframe content (e.g., password field) did not load within timeout after getting frame.")
                        return
                else:
                    print(f"[{datetime.datetime.now()}] Error: Could not get content frame from iframe element handle.")
                    return
            else:
                print(f"[{datetime.datetime.now()}] Error: Iframe element handle was not obtained.")
                return

            # --- 步骤3: 在 iframe 内部进行操作 ---
            print(f"[{datetime.datetime.now()}] Interacting within the iframe...")
            try:
                # 密码输入框的等待已经在上面完成，这里直接使用
                # await iframe_frame.wait_for_selector('input[name="password"]', timeout=30000) # 这一行可以移除或注释掉
                # print(f"[{datetime.datetime.now()}] Password input field found inside iframe.")

                # 填充密码
                await iframe_frame.fill('input[name="password"]', HF_JUPYTER_TOKEN)
                print(f"[{datetime.datetime.now()}] Password filled.")

                # 点击提交按钮
                await iframe_frame.click('button[type="submit"]')
                print(f"[{datetime.datetime.now()}] Submit button clicked.")

                # 等待 iframe 内部内容更新或加载完成
                # 可以根据实际情况调整等待时间或等待特定元素出现
                await asyncio.sleep(5) # 给 iframe 内部的提交操作一些时间
                print(f"[{datetime.datetime.now()}] Waited 5 seconds after submission.")

            except TimeoutError:
                print(f"[{datetime.datetime.now()}] Error: Elements inside iframe (password field or submit button) not found within timeout.")
                return
            except Exception as e:
                print(f"[{datetime.datetime.now()}] Error interacting with iframe: {e}")
                return

            # --- 步骤4: 模拟用户活跃 ---
            # 页面加载后，可以执行一些简单的交互，例如滚动，以模拟用户活跃
            print(f"[{datetime.datetime.now()}] Simulating user activity (scrolling)...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(10) # 模拟用户停留10秒

            print(f"[{datetime.datetime.now()}] Refresh process completed successfully.")

    except Exception as e:
        print(f"[{datetime.datetime.now()}] An unexpected error occurred: {e}")
    finally:
        if browser:
            await browser.close()
            print(f"[{datetime.datetime.now()}] Browser closed.")

if __name__ == "__main__":
    asyncio.run(refresh_page())

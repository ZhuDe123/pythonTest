import asyncio
from playwright.async_api import async_playwright
import datetime # 确保 datetime 在这里导入，以便函数内部使用

# 你的 Hugging Face 账号信息
# 建议使用环境变量或配置文件来存储，不要直接写在代码里
HF_USERNAME = "zhuhuggingface" # 替换为你的用户名
HF_PASSWORD = "Zds.13938431145" # 替换为你的密码

async def login_and_save_state(storage_state_path: str, headless: bool = True) -> bool:
    """
    执行 Hugging Face 登录并保存会话状态。
    Args:
        storage_state_path (str): 保存会话状态的文件路径。
        headless (bool): 是否以无头模式运行浏览器。
    Returns:
        bool: 登录并保存状态是否成功。
    """
    browser = None
    try:
        async with async_playwright() as p:
            # 启动浏览器，headless 参数由调用者决定
            browser = await p.chromium.launch(headless=headless)
            page = await browser.new_page()

            print(f"[{datetime.datetime.now()}] [登录模块] 导航到 Hugging Face 登录页面...")
            await page.goto("https://huggingface.co/login")

            # 等待登录表单加载
            try:
                await page.wait_for_selector('input[name="username"]', timeout=30000)
            except TimeoutError:
                print(f"[{datetime.datetime.now()}] [登录模块] 错误：未能在30秒内找到登录表单元素。")
                return False # 登录失败

            print(f"[{datetime.datetime.now()}] [登录模块] 填充登录表单...")
            await page.fill('input[name="username"]', HF_USERNAME)
            await page.fill('input[name="password"]', HF_PASSWORD)
            await page.click('button[type="submit"]') # 点击登录按钮

            print(f"[{datetime.datetime.now()}] [登录模块] 等待登录完成...")
            try:
                # 等待页面跳转到登录后的页面，或者等待某个登录后的元素出现
                # 这里假设登录成功后会跳转到主页或个人页面
                await page.wait_for_url("https://huggingface.co", timeout=60000) # 登录成功后通常会跳转到个人设置页
                print(f"[{datetime.datetime.now()}] [登录模块] 登录成功！")
            except TimeoutError:
                print(f"[{datetime.datetime.now()}] [登录模块] 错误：登录超时或未跳转到预期页面。当前URL: {page.url}")
                return False # 登录失败

            # 保存会话状态
            await page.context.storage_state(path=storage_state_path)
            print(f"[{datetime.datetime.now()}] [登录模块] 会话状态已保存到 {storage_state_path}")

            return True # 登录成功
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [登录模块] 登录过程中发生意外错误: {e}")
        return False
    finally:
        if browser:
            await browser.close()
            print(f"[{datetime.datetime.now()}] [登录模块] 浏览器已关闭。")

if __name__ == "__main__":
    # 这里的 STORAGE_STATE_PATH 应该与 refresh_huggingface.py 中的一致，或者作为参数传入
    # 为了演示，这里使用一个默认值，实际使用时应确保一致性
    default_storage_path = "huggingface_state.json"
    print(f"[{datetime.datetime.now()}] [登录模块] 作为独立脚本运行，将尝试登录并保存到 '{default_storage_path}'。")
    asyncio.run(login_and_save_state(default_storage_path, headless=False)) # 首次运行时有头

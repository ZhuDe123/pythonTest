import asyncio
from playwright.async_api import async_playwright

# 你的 Hugging Face 账号信息
# 建议使用环境变量或配置文件来存储，不要直接写在代码里
HF_USERNAME = "zhuhuggingface" # 替换为你的用户名
HF_PASSWORD = "Zds.13938431145" # 替换为你的密码
STORAGE_STATE_PATH = "huggingface_state.json" # 保存会话状态的文件名

async def login_and_save_state():
    async with async_playwright() as p:
        # 启动有头浏览器，方便你观察登录过程
        browser = await p.chromium.launch(headless=False) # 首次登录时设置为 False
        page = await browser.new_page()

        print("Navigating to Hugging Face login page...")
        await page.goto("https://huggingface.co/login")

        # 等待登录表单加载
        await page.wait_for_selector('input[name="username"]', timeout=30000)

        print("Filling login form...")
        await page.fill('input[name="username"]', HF_USERNAME)
        await page.fill('input[name="password"]', HF_PASSWORD)
        await page.click('button[type="submit"]') # 点击登录按钮

        print("Waiting for login to complete...")
        # 等待页面跳转到登录后的页面，或者等待某个登录后的元素出现
        # 这里假设登录成功后会跳转到主页或个人页面
        await page.wait_for_url("https://huggingface.co", timeout=60000) # 登录成功后通常会跳转到个人设置页
        print("Login successful!")

        # 保存会话状态
        await page.context.storage_state(path=STORAGE_STATE_PATH)
        print(f"Session state saved to {STORAGE_STATE_PATH}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(login_and_save_state())

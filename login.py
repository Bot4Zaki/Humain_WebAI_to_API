from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir="browser_data",
        headless=False,
    )
    page = browser.new_page()
    page.goto("https://chat.humain.ai")
    print("Please log in. Close the browser when done.")
    try:
        page.wait_for_timeout(60000)
    except:
        pass
    browser.close()

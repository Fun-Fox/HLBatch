import os
from time import sleep
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()


async def create_video_by_image(page, logging, reference_image_path, prompt, num=1):
    if not page.is_closed():
        await page.goto("https://hailuoai.com/create")
        logging.info('页面加载完成')
    else:
        logging.error("页面已关闭，无法导航")
        return

    # 选择图片
    input_element = page.locator('div.ant-upload > span.ant-upload > input')
    await input_element.set_input_files(reference_image_path)  # Specify your file path here
    # 等待图片上传成功
    await page.wait_for_timeout(10000)
    # 输入提示词
    editable_div = page.locator('div[role="textbox"][aria-multiline="true"]')
    await editable_div.click()  # 点击可编辑区域，使其获得焦点
    await page.keyboard.type(prompt)  # 模拟键盘输入
    # text_element = page.locator('p[data-slate-node="element"] > span > span > span[data-slate-string="true"]')

    # 设置提示词
    # await text_element.evaluate(f'(element) => element.textContent = "{prompt}"')

    # 定位到"生成数量" input field
    generation_count_input = page.locator('div.ant-input-number-input-wrap > input.ant-input-number-input')

    # 设置"生成数量"
    await generation_count_input.fill(f"{num}")  # Replace "新的数量值" with the desired value

    # 点击生成
    button_locator = page.locator('div.relative > button.new-color-btn-bg')  # 定位按钮
    await button_locator.click()  # 点击按钮
    await page.wait_for_timeout(2000)


async def batch_download_video(page, download_dir, logging, batch_num=1):
    if page.is_closed():
        logging.error("页面已关闭，无法操作")
        return

    await page.goto("https://hailuoai.com/create")
    logging.info('页面加载完成')

    # 定位到滚动区域
    scroll_container = page.locator('#preview-video-scroll-container')

    downloaded_count = 0
    seen_buttons = set()  # 记录已经处理过的按钮索引，防止重复点击

    while downloaded_count < batch_num:
        # 查找当前页面中的下载按钮
        download_buttons = scroll_container.locator('div > button.ant-dropdown-trigger:nth-child(2)')
        button_count = await download_buttons.count()

        logging.info(f'当前找到 {button_count} 个下载按钮')

        for i in range(button_count):
            if downloaded_count >= batch_num:
                break
            if i in seen_buttons:
                continue

            async with page.expect_download() as download_info:
                await download_buttons.nth(i).click()
            download = await download_info.value

            # path = await download.path()
            suggested_filename = download.suggested_filename
            target_path = os.path.join(download_dir, suggested_filename)
            await download.save_as(target_path)
            logging.info(f'已保存: {target_path}')

            seen_buttons.add(i)
            downloaded_count += 1

        if downloaded_count >= batch_num:
            break

        # 向下滚动以加载更多内容
        await scroll_container.evaluate('element => element.scrollTop = element.scrollHeight')
        logging.info('正在滚动以加载更多内容...')
        await page.wait_for_timeout(3000)  # 等待新内容加载

        # 判断是否已加载到底部（高度未变化）
        new_button_count = await download_buttons.count()
        if new_button_count == button_count:
            logging.warning('已加载到底部，没有更多视频可下载')
            break

    logging.info(f'共下载了 {downloaded_count} 个视频')

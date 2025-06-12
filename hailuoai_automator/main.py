import asyncio
import os
import random
from pathlib import Path

import pandas as pd

from hailuoai_automator.core import init_browser, close_browser
from loguru import logger

from hailuoai_automator.core.create_video import create_video_by_image, batch_download_video


async def start(reference_image_dir, excel_file, sheet_name, logging, batch_size=5, sleep_minutes=20,
                only_download=False, total_downloads=0):
    # 读取 Excel 数据
    df = pd.read_excel(excel_file, sheet_name=sheet_name)

    p, browser, context, page = await init_browser(logging)

    total_batches = 0
    total_executions = 0

    try:
        if only_download is False:

            for i in range(0, len(df), batch_size):
                if total_executions >= len(df):
                    break

                batch_prompts = df.iloc[i:i + batch_size]
                total_batches += 1
                executed_in_batch = 0

                for index, row in batch_prompts.iterrows():
                    if not pd.isna(row['reference_image_path']):
                        continue  # 已处理过，跳过

                    prompt = row['prompt']
                    image_files = list(Path(reference_image_dir).glob('*.*'))
                    if not image_files:
                        logging.error("未找到可用图片文件")
                        break

                    reference_image_path = str(random.choice(image_files))
                    logging.info(f'使用图片：{reference_image_path}，提示词：{prompt}')

                    try:
                        await create_video_by_image(page, logging, reference_image_path, prompt, num=1)
                        df.at[index, 'reference_image_path'] = reference_image_path
                        total_executions += 1
                        executed_in_batch += 1
                    except Exception as e:
                        logging.error(f"生成视频失败: {e}")
                        continue

                # 保存当前状态到 Excel
                df.to_excel(excel_file, index=False, sheet_name=sheet_name)
                logging.info(f'已更新Excel')

                logging.info(f'第 {total_batches} 批完成，本批次共执行 {executed_in_batch} 次')
                if executed_in_batch > 0:
                    if i + batch_size < len(df):
                        logging.info(f'等待 {sleep_minutes} 分钟以继续下一批...')
                        await asyncio.sleep(sleep_minutes * 60)

            logging.info(f'总计执行了：{total_executions}')
        if only_download:
            total_executions = total_downloads
        download_dir = "downloads"
        os.makedirs(download_dir, exist_ok=True)

        await batch_download_video(page, download_dir, logging, batch_num=total_executions)

    finally:
        # 关闭浏览器
        await page.close()
        await context.close()
        await close_browser(p, browser, logging)

    logging.info(f'总共执行了 {total_executions} 次，共 {total_batches} 批')


def main():
    """
    主程序入口函数
    """
    print("=== Hailuo AI 自动化工具 ===")

    # reference_image_dir = "record/labubu"
    # excel_file = "record/prompts-labubu.xlsx"
    # sheet_name = "Sheet1"
    # # 最多只能有5个队列
    # asyncio.run(
    #     start(
    #         reference_image_dir,
    #         excel_file,
    #         sheet_name,
    #         logging=logger,
    #         batch_size=5,
    #         sleep_minutes=10,
    #         only_download=True,
    #         total_downloads=386
    #     )
    # )
    reference_image_dir = "record/wwe"
    excel_file = "record/prompts-wwe.xlsx"
    sheet_name = "Sheet1"
    # 最多只能有5个队列
    asyncio.run(
        start(
            reference_image_dir,
            excel_file,
            sheet_name,
            logging=logger,
            batch_size=5,
            sleep_minutes=5,
            only_download=False,
            total_downloads=500
        )
    )


if __name__ == "__main__":
    main()

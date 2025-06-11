from datetime import datetime

import requests
import json
import time
import os
import base64
import argparse
import concurrent.futures
from tqdm import tqdm
from orm.video_task import VideoTask
from orm.base import init_db, SessionLocal

max_workers = 1


class MiniMaxVideoBatchGenerator:
    def __init__(self, api_key, base_url="https://api.minimaxi.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        # 初始化数据库
        init_db()

        # 写入数据库
        self.db = SessionLocal()

    def encode_image(self, image_path):
        """将图片编码为base64格式"""
        with open(image_path, 'rb') as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')

    def create_video_task(self, model, prompt="", first_frame_image=None,
                          prompt_optimizer=True, subject_reference=None):
        """创建视频生成任务"""
        url = f"{self.base_url}/v1/video_generation"

        payload = {
            "model": model,
            "prompt": prompt,
            "promptOptimizer": prompt_optimizer
        }

        # 添加首帧图片（如果提供）
        if first_frame_image:
            if os.path.exists(first_frame_image):
                image_base64 = self.encode_image(first_frame_image)
                payload["firstFrameImage"] = f"data:image/jpeg;base64,{image_base64}"
            else:
                # 假设提供的是URL
                payload["firstFrameImage"] = first_frame_image

        # 添加主体参考（如果提供且模型是S2V-01）
        if subject_reference and model == "S2V-01":
            if isinstance(subject_reference, list):
                payload["subjectReference"] = subject_reference
            else:
                # 单个主体参考图片
                if os.path.exists(subject_reference):
                    image_base64 = self.encode_image(subject_reference)
                    payload["subjectReference"] = [f"data:image/jpeg;base64,{image_base64}"]
                else:
                    # 假设提供的是URL
                    payload["subjectReference"] = [subject_reference]

        response = requests.post(url, headers=self.headers, json=payload)
        print(f"任务提交后返回的结果：{response.json()}")
        # 判断task_id 为空则提示异常
        # {'task_id': '', 'base_resp': {'status_code': 1008, 'status_msg': 'insufficient balance'}}
        return response.json()

    def check_task_status(self, task_id):

        if task_id != "" or task_id is not None:
            """检查任务状态"""
            url = f"{self.base_url}/v1/query/video_generation?task_id={task_id}"
            print(self.headers,url)
            response = requests.get(url, headers=self.headers)
            print(f"任务状态查询结果：{response.json()}")
            return response.json()
        else:
            return {"task_id": "", "base_resp": {"status_code": 1008, "status_msg": "task_id为空，麻烦检查费用"}}

    def download_video(self, file_id, output_path):
        print("---------------视频生成成功，下载中---------------")
        url = "https://api.minimaxi.com/v1/files/retrieve?file_id="+file_id


        response = requests.request("GET", url, headers=self.headers)
        print(response.text)

        download_url = response.json()['file']['download_url']
        print("视频下载链接：" + download_url)
        with open(output_path, 'wb') as f:
            f.write(requests.get(download_url).content)
        print("已下载在："+os.getcwd()+'/'+output_path)
        return output_path

    def process_batch(self, tasks, output_dir="output", max_workers=3, check_interval=5):
        """
        批量处理视频生成任务
        
        参数:
        - tasks: 任务列表，每个任务是包含model、prompt、first_frame_image等参数的字典
        - output_dir: 输出目录
        - max_workers: 最大并行任务数
        - check_interval: 检查任务状态的时间间隔（秒）
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 提交所有任务
        task_ids = []
        task_info = []

        print(f"提交 {len(tasks)} 个视频生成任务...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 将所有任务提交到线程池
            future_to_task = {executor.submit(self.create_video_task,
                                              task.get('model'),
                                              task.get('prompt'),
                                              task.get('first_frame_image'),
                                              task.get('prompt_optimizer'),
                                              task.get('subject_reference')): task for i, task in enumerate(tasks)}

            # 处理完成的任务
            for i, future in enumerate(concurrent.futures.as_completed(future_to_task)):
                original_task = future_to_task[future]
                try:
                    response = future.result()
                    if 'task_id' in response:
                        task_id = response['task_id']
                        task_ids.append(task_id)
                        task_info.append({
                            'task_id': task_id,
                            'status': 'Submitted',
                            'output_file': os.path.join(output_dir, f"video_{i + 1}_{task_id}.mp4"),
                            'original_task': original_task
                        })
                        print(f"任务 {i + 1}/{len(tasks)} 已提交，任务ID: {task_id}")
                    else:
                        print(f"任务 {i + 1}/{len(tasks)} 提交失败: {response}")
                        task_info.append({
                            'task_id': None,
                            'status': 'Failed',
                            'error': response,
                            'original_task': original_task
                        })
                except Exception as e:
                    print(f"任务 {i + 1}/{len(tasks)} 提交出错: {str(e)}")
                    task_info.append({
                        'task_id': None,
                        'status': 'Error',
                        'error': str(e),
                        'original_task': original_task
                    })

            # 添加短暂延迟避免API限流
            time.sleep(10)

        # 生成任务提交记录
        print("\n=== 批量提交视频任务 ===")
        print(f"总提交任务数: {len(task_info)}")

        for task in task_info:
            db_task = VideoTask(
                task_id=task.get('task_id'),
                model=task['original_task'].get('model'),
                prompt=task['original_task'].get('prompt'),
                first_frame_image=task['original_task'].get('first_frame_image'),
                prompt_optimizer=task['original_task'].get('prompt_optimizer'),
                subject_reference=json.dumps(task['original_task'].get('subject_reference')),
                video_url=task['original_task'].get('video_url'),
                status=task.get('status'),
                error=json.dumps(task.get('error')),
                output_file=task.get('output_file'),
                submit_time=datetime.now()
            )
            self.db.add(db_task)

        self.db.commit()
        self.db.close()

        # 跟踪所有任务的完成情况
        print("\n开始跟踪任务状态...")
        pending_tasks = [t for t in task_info if t['task_id'] is not None]
        print(pending_tasks)
        # print(f"pengding的任务： {",".join(pending_tasks)}")
        completed_tasks = [t for t in task_info if t['task_id'] is None]

        progress_bar = tqdm(total=len(pending_tasks), desc="视频生成进度")
        completed_count = 0

        while pending_tasks:
            for task in pending_tasks:
                try:
                    status_info = self.check_task_status(task['task_id'])
                    current_status = status_info.get('status')
                    task['current_status'] = current_status
                    if current_status == 'Success':
                        # 下载成功生成的视频
                        file_id = status_info.get('file_id')

                        if file_id:
                            self.download_video(file_id, task['output_file'])
                            task['status'] = 'Completed'
                            task['video_url'] = file_id
                            # 更新数据库状态和完成时间
                            db_task = self.db.query(VideoTask).filter(VideoTask.task_id == task['task_id']).first()
                            if db_task:
                                db_task.status = 'Completed'
                                db_task.complete_time = datetime.now()
                                db_task.video_url = file_id
                                self.db.commit()
                            pending_tasks.remove(task)
                            completed_tasks.append(task)
                            completed_count += 1
                            progress_bar.update(1)
                    elif current_status == 'Fail':
                        task['status'] = 'Failed'
                        task['error'] = status_info
                        # 更新数据库状态、错误信息和完成时间
                        db_task = self.db.query(VideoTask).filter(VideoTask.task_id == task['task_id']).first()
                        if db_task:
                            db_task.status = 'Failed'
                            db_task.error = json.dumps(status_info)
                            db_task.complete_time = datetime.now()
                            self.db.commit()

                        pending_tasks.remove(task)
                        completed_tasks.append(task)
                        completed_count += 1
                        progress_bar.update(1)
                except Exception as e:
                    print(f"检查任务 {task['task_id']} 状态出错: {str(e)}")

            if pending_tasks:
                time.sleep(check_interval)

        progress_bar.close()

        # 保存任务报告
        report_path = os.path.join(output_dir, "generation_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(task_info, f, ensure_ascii=False, indent=2)

        print(f"\n报告已保存至: {report_path}")
        print(f"生成的视频已保存至: {output_dir}")

        return task_info

    def check_tasks_batch(self, task_ids):
        """批量检查多个任务的状态"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_id = {executor.submit(self.check_task_status, task_id): task_id for task_id in task_ids}
            results = {}
            for future in concurrent.futures.as_completed(future_to_id):
                task_id = future_to_id[future]
                try:
                    results[task_id] = future.result()
                except Exception as e:
                    results[task_id] = {"error": str(e)}
            return results

    def download_videos_batch(self, tasks_with_urls):
        """批量下载多个视频"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.download_video, task['video_url'], task['output_file'])
                       for task in tasks_with_urls]
            concurrent.futures.wait(futures)


def read_tasks_from_file(file_path):
    """从JSON文件读取任务配置"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description='MiniMax海螺AI视频批量生成工具')
    parser.add_argument('--api_key', required=True, help='API密钥')
    parser.add_argument('--tasks_file', required=True, help='任务配置JSON文件路径')
    parser.add_argument('--output_dir', default='output', help='视频输出目录')
    parser.add_argument('--max_workers', type=int, default=3, help='最大并行任务数')
    parser.add_argument('--check_interval', type=int, default=5, help='任务状态检查间隔(秒)')

    args = parser.parse_args()

    tasks = read_tasks_from_file(args.tasks_file)
    generator = MiniMaxVideoBatchGenerator(args.api_key)
    generator.process_batch(
        tasks=tasks,
        output_dir=args.output_dir,
        max_workers=args.max_workers,
        check_interval=args.check_interval
    )


if __name__ == "__main__":
    main()

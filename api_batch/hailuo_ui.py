from datetime import datetime

import streamlit as st
import json
import os
from hailuo import MiniMaxVideoBatchGenerator, read_tasks_from_file
import pandas as pd
from PIL import Image
import base64
from dotenv import load_dotenv
from orm.base import SessionLocal
from orm.video_config import VideoConfig
from orm.video_task import VideoTask

load_dotenv()
# 设置页面标题和图标
st.set_page_config(
    page_title="海螺AI视频批量生成工具",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "# 海螺AI视频批量生成工具"
    }
)


def refresh_task_status():
    db = SessionLocal()
    try:
        tasks_in_db = db.query(VideoTask).all()
        new_task_status = {}
        for idx, task in enumerate(tasks_in_db):
            new_task_status[idx] = {
                'task_id': task.task_id,
                'model': task.model,
                'status': task.status,
                'submit_time': task.submit_time,
                'video_url': task.video_url
            }
        st.session_state.task_status = new_task_status
    except Exception as e:
        st.error(f"❌ 加载任务状态失败: {str(e)}")
    finally:
        db.close()


# 自定义CSS
st.markdown("""
<style>
    /* 全局背景设置为深色 */
    .main, .stApp, body {
        background-color: #121212 !important;
        color: #ffffff !important;
    }
    .stButton button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        width: 100%;
        transition: all 0.3s ease;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .stButton button:hover {
        background-color: #45a049;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .success {
        color: #4CAF50;
        font-weight: bold;
        padding: 0.5rem;
        background-color: rgba(76, 175, 80, 0.1);
        border-radius: 5px;
    }
    .error {
        color: #f44336;
        font-weight: bold;
        padding: 0.5rem;
        background-color: rgba(244, 67, 54, 0.1);
        border-radius: 5px;
    }
    .info-box {
        background-color: rgba(33, 150, 243, 0.1);
        border-left: 5px solid #2196F3;
        padding: 1.2rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        color: #ffffff !important;
    }
    /* 标签栏样式优化 */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1e1e1e !important;
        border-radius: 10px 10px 0 0;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
        padding: 0 10px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #e0e0e0 !important;
        font-weight: bold !important;
        padding: 12px 24px !important;
        margin: 0 5px;
        transition: all 0.3s ease;
        font-size: 16px !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #2d2d2d !important;
        color: #4CAF50 !important;
        border-bottom: 3px solid #4CAF50;
        border-radius: 8px 8px 0 0;
    }
    /* 修复深色背景下的文字可见性问题 */
    .main-bg-dark {
        background-color: #1a1a1a !important;
    }
    /* 确保所有文字在深色背景上可见 */
    body, p, span, label, div, h1, h2, h3, h4, h5, h6, .sidebar .sidebar-content, 
    .stTextInput label, .stTextArea label, .stSelectbox label, 
    .stMultiselect label, .stSlider label, .stRadio label, .stCheckbox label {
        color: #ffffff !important;
    }
    /* 输入框和文本区域样式 */
    .stTextInput input, .stTextArea textarea {
        border-radius: 8px;
        border: 1px solid #cccccc;
        padding: 12px;
        font-size: 16px;
        color: #333333 !important;
        background-color: #ffffff !important;
    }
    /* 确保占位符文字可见 */
    input::placeholder, textarea::placeholder {
        color: #888888 !important;
        opacity: 1 !important;
    }
    /* 特别处理标签页内的文字，确保在深色背景下可见 */
    .stTabs .stMarkdown p, .stTabs h1, .stTabs h2, .stTabs h3, .stTabs h4, .stTabs h5, .stTabs h6, 
    .stTabs span, .stTabs div, .stTabs .stText {
        color: #ffffff !important;
    }
    /* 确保主内容区域文字可见 */
    .main .block-container {
        color: #ffffff !important;
    }
    /* 卡片样式 */
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 24px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin-bottom: 24px;
    }
    /* 卡片内文字颜色 */
    .card p, .card h1, .card h2, .card h3, .card span, .card label, .card div {
        color: #333333 !important;
    }
    /* 标题样式 */
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 700;
    }
    /* 文本样式 */
    p, label, .stRadio label, .stCheckbox label {
        font-size: 16px;
        color: #e0e0e0 !important;
    }
    /* 表格样式 */
    .dataframe {
        font-size: 15px !important;
    }
    /* 选择框样式 */
    .stSelectbox label, .stMultiselect label {
        font-size: 16px;
        font-weight: 500;
        color: #e0e0e0 !important;
    }
    /* 输入框标签颜色 */
    .stTextInput label, .stTextArea label, .stSelectbox label span, .stMultiselect label span {
        color: #e0e0e0 !important;
    }
    /* 提示信息样式 */
    .stAlert {
        font-size: 16px;
        border-radius: 8px;
        padding: 16px;
        background-color: #1e1e1e !important;
        color: #e0e0e0 !important;
    }
    /* 数据框样式 */
    .dataframe {
        color: #e0e0e0 !important;
        background-color: #1e1e1e !important;
    }
    /* 数据框中的文字 */
    .dataframe th, .dataframe td {
        color: #e0e0e0 !important;
    }
    /* 滑块样式 */
    .stSlider {
        padding-top: 10px;
        padding-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# 初始化会话状态
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'tasks' not in st.session_state:
    st.session_state.tasks = []
if 'generator' not in st.session_state:
    st.session_state.generator = None
if 'results' not in st.session_state:
    st.session_state.results = None
if 'task_status' not in st.session_state:
    st.session_state.task_status = {}

# 标题和介绍
st.title("🎬 海螺AI视频批量生成工具")
st.markdown("""
<div class="info-box">
这是一个基于MiniMax海螺API的AI视频批量生成工具，支持文本生成视频(T2V)、图像生成视频(I2V)和角色参考视频(S2V)。
</div>
""", unsafe_allow_html=True)

# 创建两个选项卡
tab1, tab2, tab3, tab4 = st.tabs(["配置任务", "任务监控", "生成结果", "批量JSON配置"])

with tab1:
    st.header("第一步：API配置")
    st.session_state.api_key = os.getenv("API_KEY")  # API配置区域
    api_key = st.text_input("MiniMax API密钥",
                            value=st.session_state.api_key,
                            type="password",
                            help="输入您的MiniMax API密钥，用于访问海螺AI视频生成服务")

    if api_key:
        st.session_state.api_key = api_key
        st.session_state.generator = MiniMaxVideoBatchGenerator(api_key)
        st.success("✅ API密钥已设置")

    st.header("第二步：创建视频生成任务")

    # 创建任务区域
    task_method = st.radio("选择任务创建方式",
                           ["通过表单创建单个任务", "导入JSON任务配置文件"],
                           help="选择如何创建视频生成任务")

    if task_method == "通过表单创建单个任务":
        with st.form("task_form"):
            st.subheader("视频生成参数")

            # 基本参数
            model = st.selectbox("选择模型",
                                 ["T2V-01-Director", "I2V-01-Director", "I2V-01-live", "S2V-01", "T2V-01", "I2V-01"],
                                 help="T2V: 文本生成视频, I2V: 图像生成视频, S2V: 角色参考视频")

            prompt = st.text_area("提示词/场景描述",
                                  height=100,
                                  help="详细描述您想要生成的视频场景，可以添加运镜指令，如[左移,上升]")

            prompt_optimizer = st.checkbox("启用提示词优化",
                                           value=True,
                                           help="开启后，系统将自动优化您的提示词以提升生成质量")

            # 根据模型类型动态显示不同参数
            image_file = None
            subject_file = None

            if "I2V" in model:
                st.subheader("首帧图片 (必选)")
                image_file = st.file_uploader("上传首帧图片",
                                              type=["jpg", "jpeg", "png"],
                                              help="上传作为视频首帧的图片，建议分辨率不低于720p")

            if model == "S2V-01":
                st.subheader("角色参考图 (必选)")
                subject_file = st.file_uploader("上传角色参考图",
                                                type=["jpg", "jpeg", "png"],
                                                help="上传角色参考图片，用于在视频中复现该角色")

            submitted = st.form_submit_button("添加到任务队列")

            if submitted:
                # 验证必填参数
                valid = True
                error_msg = []

                if not api_key:
                    valid = False
                    error_msg.append("请先设置API密钥")

                if not prompt and "T2V" in model:
                    valid = False
                    error_msg.append("使用T2V模型时必须提供提示词")

                if "I2V" in model and image_file is None:
                    valid = False
                    error_msg.append("使用I2V模型时必须上传首帧图片")

                if model == "S2V-01" and subject_file is None:
                    valid = False
                    error_msg.append("使用S2V模型时必须上传角色参考图")

                if valid:
                    # 处理图片文件
                    image_path = None
                    if image_file:
                        # 保存上传的图片到临时目录
                        if not os.path.exists("temp_images"):
                            os.makedirs("temp_images")
                        image_path = f"temp_images/{image_file.name}"
                        with open(image_path, "wb") as f:
                            f.write(image_file.getbuffer())

                    subject_path = None
                    if subject_file:
                        if not os.path.exists("temp_images"):
                            os.makedirs("temp_images")
                        subject_path = f"temp_images/{subject_file.name}"
                        with open(subject_path, "wb") as f:
                            f.write(subject_file.getbuffer())

                    # 创建任务对象
                    task = {
                        "model": model,
                        "prompt": prompt,
                        "prompt_optimizer": prompt_optimizer,
                    }

                    if image_path:
                        task["first_frame_image"] = image_path

                    if subject_path:
                        task["subject_reference"] = subject_path

                    # 添加到任务列表
                    st.session_state.tasks.append(task)
                    st.success(f"✅ 已添加任务到队列，当前队列中有 {len(st.session_state.tasks)} 个任务")
                else:
                    for msg in error_msg:
                        st.error(msg)
    else:
        # 通过JSON文件导入
        uploaded_file = st.file_uploader("上传任务配置JSON文件",
                                         type=["json"],
                                         help="上传包含多个任务配置的JSON文件")

        if uploaded_file:
            try:
                tasks = json.load(uploaded_file)
                if isinstance(tasks, list):
                    st.session_state.tasks = tasks
                    st.success(f"✅ 已成功导入 {len(tasks)} 个任务")
                else:
                    st.error("❌ JSON文件格式错误，应为任务对象的数组")
            except Exception as e:
                st.error(f"❌ 解析JSON文件时出错: {str(e)}")

    # 显示当前任务队列
    if st.session_state.tasks:
        st.subheader(f"当前任务队列 ({len(st.session_state.tasks)} 个任务)")

        # 创建任务预览表格
        task_data = []
        for i, task in enumerate(st.session_state.tasks):
            preview = {
                "序号": i + 1,
                "模型": task.get("model", ""),
                "提示词": task.get("prompt", "")[:50] + "..." if len(task.get("prompt", "")) > 50 else task.get(
                    "prompt", ""),
                "首帧图片": "已上传" if task.get("first_frame_image") else "无",
                "角色参考": "已上传" if task.get("subject_reference") else "无",
            }
            task_data.append(preview)

        st.dataframe(pd.DataFrame(task_data), use_container_width=True)

        # 任务操作按钮
        col1, col2 = st.columns(2)
        with col1:
            if st.button("清空任务队列", key="clear_tasks"):
                st.session_state.tasks = []
                st.session_state.results = None
                st.session_state.task_status = {}
                st.rerun()

        with col2:
            if st.button("导出任务配置", key="export_tasks"):
                task_json = json.dumps(st.session_state.tasks, ensure_ascii=False, indent=2)
                b64 = base64.b64encode(task_json.encode()).decode()
                href = f'<a href="data:application/json;base64,{b64}" download="tasks_config.json">下载任务配置文件</a>'
                st.markdown(href, unsafe_allow_html=True)

    # 开始生成按钮区域
    st.header("第三步：开始批量生成")

    output_dir = st.text_input("输出目录",
                               value="output",
                               help="生成的视频和报告将保存到这个目录")

    max_workers = st.slider("最大并行任务数",
                            min_value=1,
                            max_value=10,
                            value=3,
                            help="设置同时处理的最大任务数，根据您的网络条件调整")

    check_interval = st.slider("状态检查间隔 (秒)",
                               min_value=1,
                               max_value=30,
                               value=5,
                               help="设置检查任务状态的时间间隔")

    start_col1, start_col2 = st.columns([3, 1])
    with start_col1:
        if st.button("开始批量生成视频", disabled=not st.session_state.tasks or not api_key):
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 开始生成任务
            with st.spinner("正在提交任务..."):
                try:
                    results = st.session_state.generator.process_batch(
                        tasks=st.session_state.tasks,
                        output_dir=output_dir,
                        max_workers=max_workers,
                        check_interval=check_interval
                    )
                    st.session_state.results = results
                    st.success("✅ 所有任务处理完成！")

                    # 自动切换到结果页面
                    st.query_params(tab="result")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 处理任务时出错: {str(e)}")

    with start_col2:
        if st.button("保存配置"):
            st.session_state.output_dir = output_dir
            st.session_state.max_workers = max_workers
            st.session_state.check_interval = check_interval

            # 保存到数据库
            db = SessionLocal()
            try:
                config = VideoConfig(
                    output_dir=output_dir,
                    max_workers=max_workers,
                    check_interval=check_interval
                )
                db.add(config)
                db.commit()
                st.success("✅ 配置已保存到数据库")
            except Exception as e:
                db.rollback()
                st.error(f"❌ 保存配置失败: {str(e)}")
            finally:
                db.close()
            st.success("✅ 配置已保存")

# 任务监控选项卡
with tab2:
    st.header("任务执行监控")

    # if not st.session_state.tasks:
    #     st.warning("⚠️ 请先在「配置任务」选项卡中添加任务")
    if not st.session_state.generator:
        st.warning("⚠️ 请先设置API密钥")
    else:
        # 手动刷新监控
        if st.button("刷新任务状态"):
            # 获取所有已提交任务的ID
            refresh_task_status()
            task_ids = [task.get('task_id') for task in st.session_state.task_status.values()
                        if task.get('task_id') is not None and task.get('task_id') != '']
            print(f"批量刷新任务状态{task_ids}")

            if task_ids:
                try:
                    # 批量查询状态
                    results = st.session_state.generator.check_tasks_batch(task_ids)
                    # 更新任务状态并同步到数据库
                    db = SessionLocal()
                    try:
                        for task_id, result in results.items():
                            for idx, task in st.session_state.task_status.items():
                                if task.get('task_id') == task_id:
                                    # 更新 session_state 中的状态
                                    st.session_state.task_status[idx]['status'] = result['status']

                                    # 更新数据库中的状态
                                    db_task = db.query(VideoTask).filter(VideoTask.task_id == task_id).first()
                                    if db_task:
                                        db_task.status = result['status']
                                        db_task.video_url = result['file_id']
                                        db_task.complete_time = datetime.now() if result['status'] in ['Success',
                                                                                                       'Completed',
                                                                                                       'Fail',
                                                                                                       'Failed'] else None
                                        db.commit()
                    finally:
                        db.close()

                    st.success("✅ 任务状态已更新")
                except Exception as e:
                    st.error(f"❌ 更新任务状态出错: {str(e)}")
            else:
                st.info("ℹ️ 没有正在进行的任务")

        # 显示任务状态表格
        if st.session_state.task_status:
            st.subheader("任务执行状态")

            status_data = []
            for idx, task in st.session_state.task_status.items():
                status = task.get('status', '未知')
                if isinstance(status, dict):
                    status = json.dumps(status, ensure_ascii=False)  # 或提取关键字段如 status.get('status', 'Unknown')

                status_info = {
                    "序号": idx + 1,
                    "任务ID": task.get('task_id', 'N/A'),
                    "模型": task.get('model', ''),
                    "状态": status,
                    "提交时间": task.get('submit_time', ''),
                }
                status_data.append(status_info)

            st.dataframe(pd.DataFrame(status_data), use_container_width=True)

            # 进度统计
            total = len(status_data)
            completed = sum(1 for task in status_data if task['状态'] in ['Success', 'Completed'])
            failed = sum(1 for task in status_data if task['状态'] in ['Failed', 'Fail'])
            pending = total - completed - failed

            # 进度条
            st.progress(completed / total if total > 0 else 0)

            # 进度详情
            col1, col2, col3 = st.columns(3)
            col1.metric("总任务", total)
            col2.metric("已完成", completed)
            col3.metric("失败", failed)
        else:
            st.info("ℹ️ 没有任务执行记录，请在「配置任务」选项卡中开始批量生成")
    # 增加批量下载操作，选择taskid video_url以及  output_file

    st.subheader("📥 批量下载已完成视频")

    if st.session_state.task_status:
        # 获取所有有 video_url 的已完成任务
        print(st.session_state.task_status.values())
        downloadable_tasks = [
            task for task in st.session_state.task_status.values()
            if task.get('status') in ['Success', 'Completed'] and task.get('video_url')
        ]

        if downloadable_tasks:
            # 多选框选择任务
            selected_indices = st.multiselect(
                "选择要下载的视频任务",
                options=range(len(downloadable_tasks)),
                format_func=lambda
                    i: f"任务ID: {downloadable_tasks[i]['task_id']} - URL: {downloadable_tasks[i]['video_url']}"
            )

            # 构建参数
            tasks_to_download = [
                {
                    "video_url": t["video_url"],
                    "output_file": t.get("output_file", os.path.join("output", f"{t['task_id']}.mp4"))
                }
                for i in selected_indices
                if (t := downloadable_tasks[i])
            ]

            if st.button("开始批量下载"):
                if tasks_to_download:
                    try:
                        with st.spinner("正在下载视频..."):
                            results = st.session_state.generator.download_videos_batch(tasks_to_download)

                        # 显示下载结果
                        st.success("✅ 视频下载完成")
                        # st.json(results)
                    except Exception as e:
                        st.error(f"❌ 下载失败: {str(e)}")
                else:
                    st.warning("⚠️ 请选择至少一个任务进行下载")
        else:
            st.info("ℹ️ 没有可下载的视频任务")
    else:
        st.info("ℹ️ 暂无任务记录，请先提交任务")

# 结果展示选项卡
with tab3:
    st.header("生成结果查看")

    if st.session_state.results:
        # 生成结果表格
        result_data = []
        for task in st.session_state.results:
            task_result = {
                "任务ID": task.get('task_id', 'N/A'),
                "状态": task.get('status', '未知'),
                "输出文件": task.get('output_file', ''),
            }
            result_data.append(task_result)

        st.dataframe(pd.DataFrame(result_data), use_container_width=True)

        # 视频预览区域
        st.subheader("视频预览")

        # 选择要预览的视频
        completed_tasks = [task for task in st.session_state.results
                           if task.get('status') == 'Completed' and task.get('output_file')]

        if completed_tasks:
            selected_task = st.selectbox(
                "选择要预览的视频",
                options=range(len(completed_tasks)),
                format_func=lambda i: f"视频 {i + 1}: {os.path.basename(completed_tasks[i]['output_file'])}"
            )

            video_path = completed_tasks[selected_task]['output_file']
            if os.path.exists(video_path):
                # 显示视频
                video_file = open(video_path, 'rb')
                video_bytes = video_file.read()
                st.video(video_bytes)

                # 提供下载链接
                st.download_button(
                    label="下载视频",
                    data=video_bytes,
                    file_name=os.path.basename(video_path),
                    mime="video/mp4"
                )
            else:
                st.error(f"❌ 视频文件不存在: {video_path}")
        else:
            st.info("ℹ️ 没有成功生成的视频可供预览")

        # 报告查看
        st.subheader("生成报告")
        report_json = json.dumps(st.session_state.results, ensure_ascii=False, indent=2)
        st.json(report_json)

        # 导出报告
        if st.button("导出生成报告"):
            b64 = base64.b64encode(report_json.encode()).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="generation_report.json">下载生成报告</a>'
            st.markdown(href, unsafe_allow_html=True)
    else:
        st.info("ℹ️ 没有生成结果，请在「配置任务」选项卡中开始批量生成")

# 批量JSON配置选项卡
with tab4:
    st.header("批量JSON配置")

    st.markdown("""
    <div class="info-box">
    在此页面，您可以批量创建和配置JSON任务文件，无需手动编辑JSON代码。
    </div>
    """, unsafe_allow_html=True)

    # 批量任务模板选择
    template_type = st.radio(
        "选择批量任务模板类型",
        ["文本生成视频(T2V)批量任务", "图片生成视频(I2V)批量任务", "角色参考视频(S2V)批量任务", "混合类型批量任务"]
    )

    # 任务数量设置
    task_count = st.number_input("设置任务数量", min_value=1, max_value=100, value=5)

    # 创建任务编辑界面
    tasks_config = []

    # 公共参数设置
    st.subheader("公共参数设置")
    common_model = st.selectbox(
        "默认模型",
        ["T2V-01-Director", "I2V-01-Director", "I2V-01-live", "S2V-01", "T2V-01", "I2V-01"],
        help="选择默认模型，将应用于所有任务"
    )

    common_prompt_optimizer = st.checkbox("启用提示词优化", value=True)

    # 根据模板类型提供不同的配置选项
    if template_type == "文本生成视频(T2V)批量任务":
        st.subheader("批量提示词输入")

        # 提供两种输入方式
        prompt_input_method = st.radio("提示词输入方式", ["逐行输入", "文件导入"])

        if prompt_input_method == "逐行输入":
            prompts_text = st.text_area(
                "请输入提示词，每行一个",
                height=200,
                help="每行输入一个提示词，将生成对应数量的任务"
            )

            if prompts_text:
                prompts = [p.strip() for p in prompts_text.split("\n") if p.strip()]
                if len(prompts) > 0:
                    task_count = len(prompts)  # 更新任务数量
                    for prompt in prompts:
                        tasks_config.append({
                            "model": common_model,
                            "prompt": prompt,
                            "prompt_optimizer": common_prompt_optimizer
                        })
        else:
            uploaded_file = st.file_uploader(
                "上传提示词文本文件",
                type=["txt"],
                help="上传一个文本文件，每行一个提示词"
            )

            if uploaded_file:
                content = uploaded_file.getvalue().decode("utf-8")
                prompts = [p.strip() for p in content.split("\n") if p.strip()]
                if len(prompts) > 0:
                    task_count = len(prompts)  # 更新任务数量
                    for prompt in prompts:
                        tasks_config.append({
                            "model": common_model,
                            "prompt": prompt,
                            "prompt_optimizer": common_prompt_optimizer
                        })

    elif template_type == "图片生成视频(I2V)批量任务":
        st.subheader("批量图片上传")

        # 上传多个图片文件
        uploaded_images = st.file_uploader(
            "上传多个图片作为首帧",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            help="上传多个图片，每个图片将生成一个视频任务"
        )

        # 提示词设置方式
        prompt_setting = st.radio(
            "提示词设置方式",
            ["为每张图片单独设置提示词", "使用公共提示词", "使用图片文件名作为提示词", "从文件导入图片-提示词映射"]
        )

        if prompt_setting == "使用公共提示词":
            # 公共提示词（可选）
            common_prompt = st.text_area(
                "公共提示词",
                height=100,
                help="为所有图片任务设置相同的提示词"
            )

        elif prompt_setting == "从文件导入图片-提示词映射":
            mapping_file = st.file_uploader(
                "上传图片-提示词映射文件",
                type=["csv", "txt"],
                help="上传一个CSV或TXT文件，格式为：图片名称,提示词"
            )

            if mapping_file:
                content = mapping_file.getvalue().decode("utf-8")
                prompt_map = {}
                for line in content.strip().split("\n"):
                    if "," in line:
                        img_name, prompt = line.split(",", 1)
                        prompt_map[img_name.strip()] = prompt.strip()

                if prompt_map:
                    st.success(f"成功导入 {len(prompt_map)} 个图片-提示词映射")

        if uploaded_images:
            # 创建临时目录保存图片
            if not os.path.exists("temp_images"):
                os.makedirs("temp_images")

            task_count = len(uploaded_images)
            saved_images = []

            # 先保存所有图片
            for img in uploaded_images:
                img_path = f"temp_images/{img.name}"
                with open(img_path, "wb") as f:
                    f.write(img.getbuffer())
                saved_images.append({"name": img.name, "path": img_path})

            # 为每张图片单独设置提示词
            if prompt_setting == "为每张图片单独设置提示词":
                st.subheader("为每张图片设置提示词")

                # 使用列表和表单展示每张图片和对应的提示词输入框
                for i, img_info in enumerate(saved_images):
                    col1, col2 = st.columns([1, 3])

                    with col1:
                        # 显示图片缩略图
                        img = Image.open(img_info["path"])
                        st.image(img, caption=img_info["name"], width=150)

                    with col2:
                        # 为每张图片提供提示词输入框
                        img_prompt = st.text_area(
                            f"图片 {i + 1} 提示词",
                            value=os.path.splitext(img_info["name"])[0],  # 使用文件名作为默认提示词
                            height=100,
                            key=f"prompt_{i}"
                        )

                        # 创建任务
                        task = {
                            "model": common_model,
                            "first_frame_image": img_info["path"],
                            "prompt": img_prompt,
                            "prompt_optimizer": common_prompt_optimizer
                        }

                        tasks_config.append(task)

                    st.markdown("---")

            else:
                # 其他提示词设置方式
                for img_info in saved_images:
                    # 创建基本任务
                    task = {
                        "model": common_model,
                        "first_frame_image": img_info["path"],
                        "prompt_optimizer": common_prompt_optimizer
                    }

                    # 根据不同的提示词设置方式设置提示词
                    if prompt_setting == "使用公共提示词":
                        if common_prompt:
                            task["prompt"] = common_prompt

                    elif prompt_setting == "使用图片文件名作为提示词":
                        file_name = os.path.splitext(img_info["name"])[0]
                        task["prompt"] = file_name

                    elif prompt_setting == "从文件导入图片-提示词映射":
                        if img_info["name"] in prompt_map:
                            task["prompt"] = prompt_map[img_info["name"]]
                        else:
                            # 如果没有映射，使用文件名作为默认值
                            task["prompt"] = os.path.splitext(img_info["name"])[0]

                    tasks_config.append(task)

    elif template_type == "角色参考视频(S2V)批量任务":
        st.subheader("角色参考图上传")

        # 上传角色参考图
        subject_image = st.file_uploader(
            "上传角色参考图",
            type=["jpg", "jpeg", "png"],
            help="上传一个角色参考图，将用于所有S2V任务"
        )

        st.subheader("批量动作提示词")

        # 提供两种输入方式
        action_input_method = st.radio("动作提示词输入方式", ["逐行输入", "文件导入"])

        if action_input_method == "逐行输入":
            actions_text = st.text_area(
                "请输入角色动作提示词，每行一个",
                height=200,
                help="每行输入一个动作描述，将为同一角色生成不同动作的视频"
            )

            if subject_image and actions_text:
                # 保存角色图片
                if not os.path.exists("temp_images"):
                    os.makedirs("temp_images")

                subject_path = f"temp_images/{subject_image.name}"
                with open(subject_path, "wb") as f:
                    f.write(subject_image.getbuffer())

                # 处理提示词
                actions = [a.strip() for a in actions_text.split("\n") if a.strip()]
                if len(actions) > 0:
                    task_count = len(actions)  # 更新任务数量

                    for action in actions:
                        tasks_config.append({
                            "model": "S2V-01",  # S2V只支持S2V-01模型
                            "subject_reference": subject_path,
                            "prompt": action,
                            "prompt_optimizer": common_prompt_optimizer
                        })
        else:
            uploaded_file = st.file_uploader(
                "上传动作提示词文本文件",
                type=["txt"],
                help="上传一个文本文件，每行一个动作提示词"
            )

            if subject_image and uploaded_file:
                # 保存角色图片
                if not os.path.exists("temp_images"):
                    os.makedirs("temp_images")

                subject_path = f"temp_images/{subject_image.name}"
                with open(subject_path, "wb") as f:
                    f.write(subject_image.getbuffer())

                # 处理提示词
                content = uploaded_file.getvalue().decode("utf-8")
                actions = [a.strip() for a in content.split("\n") if a.strip()]
                if len(actions) > 0:
                    task_count = len(actions)  # 更新任务数量

                    for action in actions:
                        tasks_config.append({
                            "model": "S2V-01",  # S2V只支持S2V-01模型
                            "subject_reference": subject_path,
                            "prompt": action,
                            "prompt_optimizer": common_prompt_optimizer
                        })

    elif template_type == "混合类型批量任务":
        st.warning("在此页面创建批量任务模板后，您可以下载JSON文件进行进一步编辑和定制")

        # 创建示例模板
        st.subheader("创建示例模板")

        t2v_count = st.number_input("T2V任务数量", min_value=0, max_value=100, value=1)
        i2v_count = st.number_input("I2V任务数量", min_value=0, max_value=100, value=1)
        s2v_count = st.number_input("S2V任务数量", min_value=0, max_value=100, value=1)

        # 更新总任务数
        task_count = t2v_count + i2v_count + s2v_count

        # 创建示例任务
        for i in range(t2v_count):
            tasks_config.append({
                "model": "T2V-01-Director",
                "prompt": f"示例T2V提示词 #{i + 1}，请在下载后修改",
                "prompt_optimizer": common_prompt_optimizer
            })

        for i in range(i2v_count):
            tasks_config.append({
                "model": "I2V-01-Director",
                "prompt": f"示例I2V提示词 #{i + 1}，请在下载后修改",
                "first_frame_image": "请替换为实际图片路径",
                "prompt_optimizer": common_prompt_optimizer
            })

        for i in range(s2v_count):
            tasks_config.append({
                "model": "S2V-01",
                "prompt": f"示例S2V动作提示词 #{i + 1}，请在下载后修改",
                "subject_reference": "请替换为实际角色图片路径",
                "prompt_optimizer": common_prompt_optimizer
            })

    # 显示生成的任务预览
    if tasks_config:
        st.subheader(f"已生成 {len(tasks_config)} 个任务配置")

        # 显示任务预览
        with st.expander("查看任务配置预览"):
            st.json(tasks_config)

        # 导出JSON配置
        if st.button("导出任务配置JSON"):
            tasks_json = json.dumps(tasks_config, ensure_ascii=False, indent=2)
            b64 = base64.b64encode(tasks_json.encode()).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="batch_tasks_config.json">下载任务配置JSON文件</a>'
            st.markdown(href, unsafe_allow_html=True)

        # 添加到任务队列
        if st.button("添加到当前任务队列"):
            # 将生成的任务添加到session state中的任务列表
            st.session_state.tasks.extend(tasks_config)
            st.success(
                f"✅ 已成功添加 {len(tasks_config)} 个任务到队列，当前队列中共有 {len(st.session_state.tasks)} 个任务")

            # 跳转到配置任务选项卡
            st.query_params(tab="task")
            st.rerun()

# 页脚
st.markdown("---")
st.markdown("🎬 **海螺AI视频批量生成工具** | 基于MiniMax API开发")

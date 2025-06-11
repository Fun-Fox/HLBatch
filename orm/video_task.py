from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey

from orm.base import Base


class VideoTask(Base):
    __tablename__ = 'video_tasks'

    id = Column(Integer, primary_key=True)
    task_id = Column(String)
    model = Column(String)
    prompt = Column(Text)
    first_frame_image = Column(String)
    prompt_optimizer = Column(Boolean)
    subject_reference = Column(Text)  # JSON list
    status = Column(String)
    video_url = Column(String)  # 下载链接
    error = Column(Text)
    output_file = Column(String)
    submit_time = Column(DateTime)
    complete_time = Column(DateTime)




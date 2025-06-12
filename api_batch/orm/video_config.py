from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from orm.base import Base


class VideoConfig(Base):
    __tablename__ = 'video_config'

    id = Column(Integer, primary_key=True)
    output_dir = Column(String)
    max_workers = Column(Integer)
    check_interval = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
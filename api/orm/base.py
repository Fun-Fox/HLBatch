# 初始化数据库连接
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
engine = create_engine('sqlite:///hailuo_tasks.db', echo=False)
SessionLocal = sessionmaker(bind=engine)


# 初始化数据库
def init_db():
    Base.metadata.create_all(engine)
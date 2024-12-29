from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class Target(Base):
    __tablename__ = 'targets'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    followers_followings = relationship("FollowerFollowing", back_populates="target")

class FollowerFollowing(Base):
    __tablename__ = 'followers_followings'
    
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('targets.id'), nullable=False)
    follower_following_username = Column(String, nullable=False)
    is_follower = Column(Boolean, nullable=False)  # True for follower, False for following
    added_at = Column(DateTime, nullable=False)
    lost_at = Column(DateTime)
    is_lost = Column(Boolean, default=False, nullable=False)

    target = relationship("Target", back_populates="followers_followings")

class ChangeLog(Base):
    __tablename__ = 'change_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    change_type = Column(String, nullable=False)  # 'follower_gained', 'follower_lost', 'following_added', 'following_removed'
    username = Column(String, nullable=False)

class Counts(Base):
    __tablename__ = 'counts'

    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('targets.id'), nullable=False)
    count_type = Column(String, nullable=False)  # 'followers', 'followings'
    count = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

class Database:
    def __init__(self):
        self.engine = create_engine('sqlite:///instagram_tracker.db')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def get_target(self, username):
        return self.session.query(Target).filter_by(username=username).first()

    def add_target(self, username):
        target = Target(username=username)
        self.session.add(target)
        self.session.commit()
        return target

    def add_follower_following(self, target_id, username, is_follower, added_at=None):
        ff = FollowerFollowing(
            target_id=target_id,
            follower_following_username=username,
            is_follower=is_follower,
            added_at=added_at if added_at else datetime.now()
        )
        self.session.add(ff)
        self.session.commit()

    def close(self):
        self.session.close()

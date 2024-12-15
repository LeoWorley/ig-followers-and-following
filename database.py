from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class FollowerSnapshot(Base):
    __tablename__ = 'follower_snapshots'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    followers = Column(JSON, nullable=False)
    
class FollowingSnapshot(Base):
    __tablename__ = 'following_snapshots'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    following = Column(JSON, nullable=False)

class ChangeLog(Base):
    __tablename__ = 'change_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    change_type = Column(String, nullable=False)  # 'follower_gained', 'follower_lost', 'following_added', 'following_removed'
    username = Column(String, nullable=False)

class FollowersCount(Base):
    __tablename__ = 'followers_counts'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    count = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False)

class Database:
    def __init__(self):
        self.engine = create_engine('sqlite:///instagram_tracker.db')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def save_follower_snapshot(self, followers):
        snapshot = FollowerSnapshot(
            timestamp=datetime.now(),
            followers=followers
        )
        self.session.add(snapshot)
        self.session.commit()
    
    def save_following_snapshot(self, following):
        snapshot = FollowingSnapshot(
            timestamp=datetime.now(),
            following=following
        )
        self.session.add(snapshot)
        self.session.commit()
    
    def log_change(self, change_type, username):
        change = ChangeLog(
            timestamp=datetime.now(),
            change_type=change_type,
            username=username
        )
        self.session.add(change)
        self.session.commit()
    
    def store_followers_count(self, username, count, timestamp):
        followers_count = FollowersCount(
            username=username,
            count=count,
            timestamp=timestamp
        )
        self.session.add(followers_count)
        self.session.commit()
        print(f"Stored followers count: {count} for user {username}")
    
    def get_latest_follower_snapshot(self):
        return self.session.query(FollowerSnapshot).order_by(FollowerSnapshot.timestamp.desc()).first()
    
    def get_latest_following_snapshot(self):
        return self.session.query(FollowingSnapshot).order_by(FollowingSnapshot.timestamp.desc()).first()
    
    def close(self):
        self.session.close()

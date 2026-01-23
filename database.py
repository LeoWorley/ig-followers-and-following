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


class RunHistory(Base):
    __tablename__ = 'run_history'

    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('targets.id'), nullable=False)
    run_started_at = Column(DateTime, nullable=False)
    run_finished_at = Column(DateTime)
    status = Column(String, nullable=False, default="running")  # running|success|failed
    followers_collected = Column(Integer, default=0)
    followings_collected = Column(Integer, default=0)

    target = relationship("Target")


class FollowerFollowing(Base):
    __tablename__ = 'followers_followings'

    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('targets.id'), nullable=False)
    follower_following_username = Column(String, nullable=False)
    is_follower = Column(Boolean, nullable=False)  # True for follower, False for following
    added_at = Column(DateTime, nullable=False)
    lost_at = Column(DateTime)
    is_lost = Column(Boolean, default=False, nullable=False)
    # New tracking fields
    first_seen_run_at = Column(DateTime)
    last_seen_run_at = Column(DateTime)
    lost_at_run_at = Column(DateTime)
    estimated_added_at = Column(DateTime)
    estimated_removed_at = Column(DateTime)

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
    run_id = Column(Integer, ForeignKey('run_history.id'))


class Database:
    def __init__(self):
        self.engine = create_engine('sqlite:///instagram_tracker.db')
        Base.metadata.create_all(self.engine)
        self._ensure_schema()
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def _ensure_schema(self):
        """Lightweight migrations for SQLite to add new columns when missing."""
        with self.engine.connect() as conn:
            def has_column(table, column):
                result = conn.exec_driver_sql(f"PRAGMA table_info({table});")
                return any(row[1] == column for row in result)

            def add_column(table, ddl):
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {ddl};")

            # followers_followings new columns
            ff_cols = {
                "first_seen_run_at": "DATETIME",
                "last_seen_run_at": "DATETIME",
                "lost_at_run_at": "DATETIME",
                "estimated_added_at": "DATETIME",
                "estimated_removed_at": "DATETIME",
            }
            for col, ddl in ff_cols.items():
                if not has_column("followers_followings", col):
                    add_column("followers_followings", f"{col} {ddl}")

            # counts.run_id
            if has_column("counts", "INTEGER") and not has_column("counts", "run_id"):
                # Fix previous bad migration: column literally named "INTEGER"
                try:
                    conn.exec_driver_sql('ALTER TABLE counts RENAME COLUMN "INTEGER" TO run_id;')
                except Exception as e:
                    print(f"Warning: failed to rename bad column INTEGER -> run_id: {e}")
            if not has_column("counts", "run_id"):
                add_column("counts", "run_id INTEGER")

        # Backfill timestamp fields for existing rows
        from sqlalchemy import update
        with self.engine.begin() as conn:
            # first_seen_run_at default to added_at
            conn.execute(
                update(FollowerFollowing)
                .where(FollowerFollowing.first_seen_run_at.is_(None))
                .values(first_seen_run_at=FollowerFollowing.added_at)
            )
            # last_seen_run_at default to added_at
            conn.execute(
                update(FollowerFollowing)
                .where(FollowerFollowing.last_seen_run_at.is_(None))
                .values(last_seen_run_at=FollowerFollowing.added_at)
            )
            # lost_at_run_at default to lost_at when lost
            conn.execute(
                update(FollowerFollowing)
                .where(FollowerFollowing.is_lost.is_(True))
                .where(FollowerFollowing.lost_at_run_at.is_(None))
                .values(lost_at_run_at=FollowerFollowing.lost_at)
            )

    def get_target(self, username):
        return self.session.query(Target).filter_by(username=username).first()

    def add_target(self, username):
        target = Target(username=username)
        self.session.add(target)
        self.session.commit()
        return target

    def get_or_create_target(self, username):
        target = self.get_target(username)
        if target:
            return target
        return self.add_target(username)

    def add_follower_following(self, target_id, username, is_follower, added_at=None,
                               first_seen=None, last_seen=None, estimated_added_at=None):
        now = added_at if added_at else datetime.utcnow()
        ff = FollowerFollowing(
            target_id=target_id,
            follower_following_username=username,
            is_follower=is_follower,
            added_at=now,
            first_seen_run_at=first_seen or now,
            last_seen_run_at=last_seen or now,
            estimated_added_at=estimated_added_at
        )
        self.session.add(ff)
        self.session.commit()
        return ff

    def start_run(self, target_id, run_started_at, status="running"):
        run = RunHistory(
            target_id=target_id,
            run_started_at=run_started_at,
            status=status
        )
        self.session.add(run)
        self.session.commit()
        return run

    def finish_run(self, run_id, status, followers_collected=0, followings_collected=0, finished_at=None):
        run = self.session.query(RunHistory).get(run_id)
        if not run:
            return
        run.status = status
        run.followers_collected = followers_collected
        run.followings_collected = followings_collected
        run.run_finished_at = finished_at if finished_at else datetime.utcnow()
        self.session.commit()

    def get_last_run(self, target_id):
        return (
            self.session.query(RunHistory)
            .filter_by(target_id=target_id)
            .order_by(RunHistory.run_started_at.desc())
            .first()
        )

    def add_count(self, target_id, count_type, count, timestamp=None, run_id=None):
        entry = Counts(
            target_id=target_id,
            count_type=count_type,
            count=count,
            timestamp=timestamp if timestamp else datetime.utcnow(),
            run_id=run_id
        )
        self.session.add(entry)
        self.session.commit()
        return entry

    def close(self):
        self.session.close()

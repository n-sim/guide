import logging
import os
import time

from sqlalchemy import create_engine, MetaData, Table, Column, PrimaryKeyConstraint, ForeignKey, select, func, case, \
    literal
from sqlalchemy.engine import URL
from sqlalchemy.exc import OperationalError
from sqlalchemy.types import (
    TEXT, BIGINT, VARCHAR, INTEGER, TIMESTAMP, Enum as SQLAlchemyEnum
)

DB_USER = os.getenv('DB_USER', 'webhook_user')
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '5433'))
DB_NAME = os.getenv('DB_NAME', 'webhook_data')
DATABASE_URL = URL.create('postgresql+psycopg2', username=DB_USER,
                          password=DB_PASSWORD, host=DB_HOST, port=DB_PORT,
                          database=DB_NAME)

metadata = MetaData()

change_type_enum = SQLAlchemyEnum(
    'ADDED', 'MODIFIED', 'DELETED',
    name='change_type',
    metadata=metadata
)

student = Table(
    'student',
    metadata,
    Column('email', TEXT, primary_key=True),
    Column('name', TEXT)
)

project = Table(
    'project',
    metadata,
    Column('id', BIGINT, primary_key=True),
    Column('name', TEXT, nullable=False),
    Column('web_url', TEXT, nullable=False),
    Column('semester_code', TEXT, nullable=False)
)

branch = Table(
    'branch',
    metadata,
    Column('project_id', BIGINT, ForeignKey('project.id', ondelete='CASCADE'), nullable=False),
    Column('name', TEXT, nullable=False),
    PrimaryKeyConstraint('project_id', 'name')
)

git_commit = Table(
    'git_commit',
    metadata,
    Column('hash', VARCHAR(40), primary_key=True),
    Column('project_id', BIGINT, ForeignKey('project.id', ondelete='CASCADE'), nullable=False),
    Column('author_email', TEXT, ForeignKey('student.email', ondelete='RESTRICT')),
    Column('authored_timestamp', TIMESTAMP(timezone=True), nullable=False),
    Column('message_subject', TEXT),
    Column('message_body', TEXT),
    Column('number_of_lines_added', INTEGER),
    Column('number_of_lines_removed', INTEGER)
)

file_change = Table(
    'file_change',
    metadata,
    Column('commit_hash', VARCHAR(40), ForeignKey('git_commit.hash', ondelete='CASCADE'), nullable=False),
    Column('file_path', TEXT, nullable=False),
    Column('used_change_type', change_type_enum),
    PrimaryKeyConstraint('commit_hash', 'file_path')
)

git_commit_parents = Table(
    'git_commit_parents',
    metadata,
    Column('commit_hash', VARCHAR(40), ForeignKey('git_commit.hash', ondelete='CASCADE'), nullable=False),
    Column('parent_hash', VARCHAR(40), ForeignKey('git_commit.hash', ondelete='CASCADE'), nullable=False),
    PrimaryKeyConstraint('commit_hash', 'parent_hash')
)


def initialize_database():
    engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    for attempt in range(30):
        try:
            with engine.connect():
                pass
            logging.info('Database connection ready.')
            return engine
        except OperationalError:
            if attempt == 29:
                engine.dispose()
                raise
            logging.warning('Database not ready; retrying in 2 seconds.')
            time.sleep(2)


class StatementsNamespace:
    def __init__(self):
        self.get_all_projects = select(project.c.id, project.c.semester_code, project.c.name)
        self.get_project_by_id = lambda project_id: select(project).where(project.c.id == project_id)
        self.get_commits_by_project_id = lambda project_id: (select(git_commit, student.c.name.label("author_name"))
        .join(student, git_commit.c.author_email == student.c.email)
        .where(git_commit.c.project_id == project_id))
        self.get_branches_by_project_id = lambda project_id: select(branch.c.name).where(branch.c.project_id == project_id)
        self.get_commit_parents_by_project_id = lambda project_id: (select(git_commit_parents)
                                                                    .join(git_commit,
                                                                          git_commit_parents.c.commit_hash == git_commit.c.hash)
                                                                    .where(git_commit.c.project_id == project_id))
        self.get_number_of_changes_by_file_and_student = lambda project_id: ((select(
            git_commit.c.author_email,
            file_change.c.file_path,
            func.count(file_change.c.commit_hash).label('num_changes')
        )
                                                                   .join(git_commit,
                                                                         file_change.c.commit_hash == git_commit.c.hash))
                                                                  .where(git_commit.c.project_id == project_id)
                                                                  .group_by(git_commit.c.author_email, file_change.c.file_path)
                                                                  .order_by(git_commit.c.author_email, file_change.c.file_path))


engine = initialize_database()
statements = StatementsNamespace()

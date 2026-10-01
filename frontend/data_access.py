"""Load dashboard data using the existing schema and SQL expressions."""

from dataclasses import dataclass

import pandas as pd

import database


@dataclass(frozen=True)
class ProjectData:
    commits: pd.DataFrame
    branches: pd.DataFrame
    commit_parents: pd.DataFrame
    details: pd.DataFrame
    file_changes: pd.DataFrame


def load_projects(connection=None) -> pd.DataFrame:
    connection = database.engine if connection is None else connection
    return pd.read_sql_query(database.statements.get_all_projects, connection)


def load_project(project_id, connection=None) -> ProjectData:
    connection = database.engine if connection is None else connection
    statements = database.statements
    return ProjectData(
        commits=pd.read_sql_query(statements.get_commits_by_project_id(project_id), connection),
        branches=pd.read_sql_query(statements.get_branches_by_project_id(project_id), connection),
        commit_parents=pd.read_sql_query(statements.get_commit_parents_by_project_id(project_id), connection),
        details=pd.read_sql_query(statements.get_project_by_id(project_id), connection),
        file_changes=pd.read_sql_query(statements.get_number_of_changes_by_file_and_student(project_id), connection),
    )

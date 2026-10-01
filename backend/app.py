from flask import Flask, request, jsonify
import requests
import json
import logging
import os
import time
import datetime
import hmac
from urllib.parse import urlsplit
from sqlalchemy.engine import URL

from sqlalchemy import create_engine, MetaData, Table, Column, PrimaryKeyConstraint, ForeignKey, select
from sqlalchemy.types import (
    TEXT, BIGINT, VARCHAR, INTEGER, TIMESTAMP, Enum as SQLAlchemyEnum
)
from sqlalchemy.exc import OperationalError, SQLAlchemyError, IntegrityError
from sqlalchemy.dialects.postgresql import insert

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration is supplied by Compose or the process environment.
DB_USER = os.getenv('DB_USER', 'webhook_user')
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '5433'))
DB_NAME = os.getenv('DB_NAME', 'webhook_data')
DATABASE_URL = URL.create('postgresql+psycopg2', username=DB_USER,
                          password=DB_PASSWORD, host=DB_HOST, port=DB_PORT,
                          database=DB_NAME)
GITLAB_API_URL = os.environ['GITLAB_API_URL'].rstrip('/')
parsed_gitlab_url = urlsplit(GITLAB_API_URL)
if parsed_gitlab_url.scheme not in ('http', 'https') or not parsed_gitlab_url.netloc:
    raise ValueError('GITLAB_API_URL must be a full HTTP(S) API URL')
GITLAB_PRIVATE_TOKEN = os.environ['GITLAB_PRIVATE_TOKEN']
GITLAB_WEBHOOK_SECRET = os.environ['GITLAB_WEBHOOK_SECRET']
if not GITLAB_PRIVATE_TOKEN or not GITLAB_WEBHOOK_SECRET:
    raise ValueError('GitLab API token and webhook secret must not be empty')
GITLAB_REQUEST_TIMEOUT = float(os.getenv('GITLAB_REQUEST_TIMEOUT', '30'))
if GITLAB_REQUEST_TIMEOUT <= 0:
    raise ValueError('GITLAB_REQUEST_TIMEOUT must be positive')
GITLAB_HEADERS = {'PRIVATE-TOKEN': GITLAB_PRIVATE_TOKEN, 'Accept': 'application/json'}

engine = None
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
    global engine
    candidate = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    for attempt in range(30):
        try:
            with candidate.begin() as connection:
                metadata.create_all(connection)
            engine = candidate
            logging.info('Database connection and schema ready.')
            return
        except OperationalError:
            if attempt == 29:
                candidate.dispose()
                raise
            logging.warning('Database not ready; retrying in 2 seconds.')
            time.sleep(2)


def insert_on_conflict_do_nothing(connection, table, data):
    stmt = insert(table).values(data)
    stmt = stmt.on_conflict_do_nothing()
    try:
        connection.execute(stmt)
        logging.debug(f"Executed insert (ON CONFLICT DO NOTHING) for {table.name} with data: {data}")
    except IntegrityError as ie:
        logging.warning(f"Integrity error during insert (ON CONFLICT DO NOTHING) for {table.name}: {ie}")
        raise
    except SQLAlchemyError as e:
        logging.error(f"SQLAlchemyError during insert (ON CONFLICT DO NOTHING) for {table.name}: {e}")
        raise


def process_webhook_data(connection, webhook_data):
    project_data = webhook_data.get('project')
    if not project_data:
        logging.error("Payload missing 'project' information.")
        return jsonify({"message": "Invalid payload: Missing project data"}), 400

    todays_date = datetime.date.today()
    if todays_date.month in range(8, 12 + 1):
        semester_code = f"{todays_date.year}WS"
    elif todays_date.month in range(1, 2 + 1):
        semester_code = f"{todays_date.year - 1}WS"
    else:
        semester_code = f"{todays_date.year}SS"

    project_id = project_data['id']
    project_values = {
        'id': project_id,
        'name': project_data['name'],
        'web_url': project_data['web_url'],
        'semester_code': semester_code,
    }

    insert_on_conflict_do_nothing(connection, project, project_values)
    logging.info(f"Processed project: {project_id}")

    ref = webhook_data.get('ref', '')
    branch_name = ref.split('/')[-1] if ref.startswith('refs/heads/') else None

    if branch_name:
        branch_values = {
            'project_id': project_id,
            'name': branch_name
        }
        insert_on_conflict_do_nothing(connection, branch, branch_values)
        logging.info(f"Processed branch: {branch_name}")
    else:
        logging.warning(f"Could not determine branch name from ref: {ref}")

    commit_hashes = [commit['id'] for commit in webhook_data.get('commits', [])]

    return project_id, commit_hashes


def process_git_commit_recursive(connection, project_id, commit_hash, processed_commits_in_this_request):
    if commit_hash in processed_commits_in_this_request:
        logging.info(f"Commit {commit_hash} already processed in this request.")
        return False

    stmt_check_db = select(git_commit.c.hash).where(git_commit.c.hash == commit_hash)
    if connection.execute(stmt_check_db).scalar():
        logging.info(f"Commit {commit_hash} already in the database.")
        return False


    processed_commits_in_this_request.add(commit_hash)

    logging.info(f"Commit {commit_hash} not found in DB. Fetching from GitLab API...")
    gitlab_response = requests.get(f"{GITLAB_API_URL}/projects/{project_id}/repository/commits/{commit_hash}",
                                   headers=GITLAB_HEADERS, timeout=GITLAB_REQUEST_TIMEOUT)
    gitlab_response.raise_for_status()
    gitlab_data = gitlab_response.json()

    logging.info(f"Successfully fetched data for commit {commit_hash}")

    author_name = gitlab_data['author_name']
    author_email = gitlab_data['author_email']

    student_values = {
        'email': author_email,
        'name': author_name
    }
    insert_on_conflict_do_nothing(connection, student, student_values)
    logging.info(f"Processed student: {author_email}")

    subject = gitlab_data['title']
    body = gitlab_data['message']
    lines_added = gitlab_data["stats"]["additions"]
    lines_removed = gitlab_data["stats"]["deletions"]
    authored_timestamp = datetime.datetime.fromisoformat(gitlab_data["authored_date"])

    commit_values = {
        'hash': commit_hash,
        'project_id': project_id,
        'author_email': author_email,
        'authored_timestamp': authored_timestamp,
        'message_subject': subject,
        'message_body': body,
        'number_of_lines_added': lines_added,
        'number_of_lines_removed': lines_removed
    }

    insert_on_conflict_do_nothing(connection, git_commit, commit_values)
    processed_commits_in_this_request.add(commit_hash)
    logging.info(f"Processed commit: {commit_hash}")

    diff_response = requests.get(
        f"{GITLAB_API_URL}/projects/{project_id}/repository/commits/{commit_hash}/diff",
        headers=GITLAB_HEADERS, timeout=GITLAB_REQUEST_TIMEOUT)
    diff_response.raise_for_status()
    diff_data = diff_response.json()

    logging.info(f"Fetched diff data for commit {commit_hash}")

    for diff_item in diff_data:
        if diff_item['deleted_file']:
            file_path = diff_item['old_path']
            change_type = 'DELETED'
        elif diff_item['new_file']:
            file_path = diff_item['new_path']
            change_type = 'ADDED'
        else:  # TODO: handle renames better
            file_path = diff_item['new_path']
            change_type = 'MODIFIED'

        file_change_values = {
            'commit_hash': commit_hash,
            'file_path': file_path,
            'used_change_type': change_type
        }
        insert_on_conflict_do_nothing(connection, file_change, file_change_values)
        logging.info(f"Processed file change: {change_type} {file_path} in commit {commit_hash}")

    parent_hashes = gitlab_data.get('parent_ids', [])
    logging.info(f"Commit {commit_hash} has parents: {parent_hashes}")
    for parent_hash in parent_hashes:
        process_git_commit_recursive(
            connection,
            project_id,
            parent_hash,
            processed_commits_in_this_request
        )

        parent_values = {
            'commit_hash': commit_hash,
            'parent_hash': parent_hash
        }
        insert_on_conflict_do_nothing(connection, git_commit_parents, parent_values)
        logging.info(f"Processed parent link: {commit_hash} -> {parent_hash}")
    return True


@app.route('/webhook', methods=['POST'])
def gitlab_webhook():
    provided_secret = request.headers.get('X-Gitlab-Token', '')
    if not hmac.compare_digest(provided_secret, GITLAB_WEBHOOK_SECRET):
        return jsonify({'message': 'Invalid webhook secret'}), 403
    if engine is None:
        logging.error("Database engine not initialized.")
        return jsonify({"message": "Internal server error: Database not ready"}), 503

    event_type = request.headers.get('X-Gitlab-Event', 'Unknown Event')
    logging.info(f"Received GitLab event: {event_type}")

    if event_type != 'Push Hook':
        logging.error(f"Ignoring event type: {event_type}")
        return jsonify({"message": f"Event type '{event_type}' not processed"}), 200

    try:
        webhook_data = request.get_json()
        if not isinstance(webhook_data, dict) or not isinstance(webhook_data.get('project'), dict):
            return jsonify({'message': 'Invalid payload: Missing project data'}), 400
        logging.debug("Webhook payload (JSON): %s", json.dumps(webhook_data, indent=2))
    except Exception as e:
        logging.warning(f"Could not parse payload as JSON: {e}")
        return jsonify({"message": "Invalid JSON payload"}), 400

    processed_commits_in_this_request = set()

    try:
        with engine.begin() as connection:
            logging.info("Beginning database transaction.")

            project_id, commit_hashes = process_webhook_data(connection, webhook_data)

            if not commit_hashes:
                logging.info("No commits found in the push event.")
                return jsonify({"message": "Webhook received, no commits to process"}), 200

            for commit_hash in reversed(commit_hashes):
                process_git_commit_recursive(connection, project_id, commit_hash, processed_commits_in_this_request)

            logging.info("Webhook received and stored successfully.")

        return jsonify({"message": "Webhook received and stored successfully"}), 200

    except requests.exceptions.HTTPError as http_error:
        logging.error(f"Request http error  {http_error}")
        return jsonify({"message": f"An http error occurred during the gitlab request: {http_error}"}), 500
    except requests.exceptions.JSONDecodeError as json_error:
        logging.error(f"Could not parse payload as JSON: {json_error}")
        return jsonify({"message": "Invalid JSON payload"}), 400
    except requests.exceptions.RequestException as req_error:
        logging.error(f"Request error: {req_error}")
        return jsonify({"message": f"An unexpected error occurred during the gitlab request: {req_error}"}), 500
    except IntegrityError as integrity_error:
        logging.error(f"Database Integrity Error during transaction: {integrity_error}")
        return jsonify({"message": "Error processing webhook data due to data integrity issue"}), 500
    except SQLAlchemyError as db_error:
        logging.error(f"Database error during transaction: {db_error}")
        return jsonify({"message": "Error storing webhook data"}), 500
    except KeyError as key_error:
        logging.error(f"Missing expected key in webhook payload: {key_error}")
        return jsonify({"message": f"Invalid payload structure: Missing key {key_error}"}), 400
    except Exception as e:
        logging.error(f"An unexpected error occurred during webhook processing: {e}", exc_info=True)
        return jsonify({"message": "Internal server error"}), 500


@app.route('/', methods=['GET'])
def index():
    """ A simple health check endpoint """
    if engine is None:
        return "Webhook receiver is running. DB connection pending initialization.", 503

    try:
        with engine.connect():
            pass
        return "Webhook receiver is running. DB connection successful.", 200
    except OperationalError as e:
        logging.error(f"Health check DB connection error: {e}")
        return f"Webhook receiver is running. DB connection error: {e}", 500
    except Exception as e:
        logging.error(f"Health check unexpected error: {e}")
        return f"Webhook receiver is running. Health check failed: {e}", 500


if __name__ == '__main__':
    initialize_database()
    app.run(host='0.0.0.0', port=5000, debug=False)

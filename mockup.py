import sqlite3
from flask import Flask, g, request, jsonify, abort

# /mnt/d/tungdt/auto-pm/webserver/mockup.py
# Simple mock API + SQLite "database" for projects, tasks, users, and membership
# Usage: python mockup.py
# Endpoints:
#  POST /users            -> create user {"name": "...", "email": "..."}
#  POST /projects         -> create project {"name": "...", "description": "..."}
#  POST /tasks            -> create task {"title": "...", "description": "...", "project_id": int, "assignee_id": int (optional)}
#  POST /projects/<id>/assign -> assign user to project {"user_id": int, "role": "member" (optional)}
#  GET  /users
#  GET  /projects
#  GET  /projects/<id>/tasks
#  GET  /projects/<id>/members
# Minimal dependencies: Flask (pip install flask)


DB_PATH = "mockup.db"
app = Flask(__name__)


def get_db():
    db = getattr(g, "_db", None)
    if db is None:
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        g._db = db
    return db


def init_db():
    db = get_db()
    cur = db.cursor()
    # Create tables if not exist
    cur.executescript(
        """
    PRAGMA foreign_keys = ON;
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL
    );
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT
    );
    CREATE TABLE IF NOT EXISTS project_members (
        project_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role TEXT DEFAULT 'member',
        PRIMARY KEY (project_id, user_id),
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        project_id INTEGER NOT NULL,
        assignee_id INTEGER,
        status TEXT DEFAULT 'todo',
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        FOREIGN KEY (assignee_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """
    )
    db.commit()


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()


def row_to_dict(row):
    return dict(row) if row is not None else None


@app.route("/users", methods=["POST"])
def create_user():
    payload = request.get_json(force=True)
    name = payload.get("name")
    email = payload.get("email")
    if not name or not email:
        return jsonify({"error": "name and email are required"}), 400
    db = get_db()
    try:
        cur = db.execute("INSERT INTO users (name, email) VALUES (?, ?)", (name, email))
        db.commit()
        uid = cur.lastrowid
        user = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        return jsonify(row_to_dict(user)), 201
    except sqlite3.IntegrityError as e:
        return jsonify({"error": "email must be unique"}), 400


@app.route("/projects", methods=["POST"])
def create_project():
    payload = request.get_json(force=True)
    name = payload.get("name")
    description = payload.get("description", "")
    if not name:
        return jsonify({"error": "name is required"}), 400
    db = get_db()
    cur = db.execute("INSERT INTO projects (name, description) VALUES (?, ?)", (name, description))
    db.commit()
    pid = cur.lastrowid
    project = db.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    return jsonify(row_to_dict(project)), 201


@app.route("/tasks", methods=["POST"])
def create_task():
    payload = request.get_json(force=True)
    title = payload.get("title")
    description = payload.get("description", "")
    project_id = payload.get("project_id")
    assignee_id = payload.get("assignee_id")
    if not title or not project_id:
        return jsonify({"error": "title and project_id are required"}), 400
    db = get_db()
    # Validate project
    proj = db.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not proj:
        return jsonify({"error": "project not found"}), 404
    # Validate assignee (if provided)
    if assignee_id is not None:
        user = db.execute("SELECT id FROM users WHERE id = ?", (assignee_id,)).fetchone()
        if not user:
            return jsonify({"error": "assignee user not found"}), 404
    cur = db.execute(
        "INSERT INTO tasks (title, description, project_id, assignee_id) VALUES (?, ?, ?, ?)",
        (title, description, project_id, assignee_id),
    )
    db.commit()
    tid = cur.lastrowid
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (tid,)).fetchone()
    return jsonify(row_to_dict(task)), 201


@app.route("/projects/<int:project_id>/assign", methods=["POST"])
def assign_member(project_id):
    payload = request.get_json(force=True)
    user_id = payload.get("user_id")
    role = payload.get("role", "member")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    db = get_db()
    # Validate project and user
    proj = db.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not proj:
        return jsonify({"error": "project not found"}), 404
    user = db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return jsonify({"error": "user not found"}), 404
    try:
        db.execute(
            "INSERT INTO project_members (project_id, user_id, role) VALUES (?, ?, ?)",
            (project_id, user_id, role),
        )
        db.commit()
    except sqlite3.IntegrityError:
        # already a member -> update role
        db.execute(
            "UPDATE project_members SET role = ? WHERE project_id = ? AND user_id = ?",
            (role, project_id, user_id),
        )
        db.commit()
    member = db.execute(
        "SELECT pm.project_id, pm.user_id, pm.role, u.name, u.email FROM project_members pm JOIN users u ON pm.user_id = u.id WHERE pm.project_id = ? AND pm.user_id = ?",
        (project_id, user_id),
    ).fetchone()
    return jsonify(row_to_dict(member)), 200


# Basic read endpoints for convenience
@app.route("/users", methods=["GET"])
def list_users():
    db = get_db()
    rows = db.execute("SELECT * FROM users ORDER BY id").fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/projects", methods=["GET"])
def list_projects():
    db = get_db()
    rows = db.execute("SELECT * FROM projects ORDER BY id").fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/projects/<int:project_id>/tasks", methods=["GET"])
def list_project_tasks(project_id):
    db = get_db()
    rows = db.execute("SELECT * FROM tasks WHERE project_id = ? ORDER BY id", (project_id,)).fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/projects/<int:project_id>/members", methods=["GET"])
def list_project_members(project_id):
    db = get_db()
    rows = db.execute(
        "SELECT pm.user_id, pm.role, u.name, u.email FROM project_members pm JOIN users u ON pm.user_id = u.id WHERE pm.project_id = ?",
        (project_id,),
    ).fetchall()
    return jsonify([row_to_dict(r) for r in rows])


if __name__ == "__main__":
    # Initialize DB on first run
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
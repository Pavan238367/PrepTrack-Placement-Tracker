import os
import sqlite3
import math
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
DB_PATH = Path(__file__).with_name("placement_tracker.db")

VALID_DIFFICULTIES = {"Easy", "Medium", "Hard"}


def is_valid_date(date_str: str) -> bool:
    """Validate date strings in YYYY-MM-DD format with realistic calendar year."""
    if not date_str or not isinstance(date_str, str):
        return False
    date_str = date_str.strip()
    if len(date_str) != 10:
        return False
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if dt.year < 2000 or dt.year > 2099:
            return False
        return True
    except ValueError:
        return False


@contextmanager
def get_db():
    """Context manager for SQLite connections ensuring clean commit/rollback and close."""
    db_file = app.config.get("DATABASE", DB_PATH)
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize SQLite tables without dropping existing data."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS dsa_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                topic TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS aptitude_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                questions_solved INTEGER NOT NULL,
                minutes_spent INTEGER NOT NULL,
                practice_date TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS mock_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_name TEXT NOT NULL,
                score REAL NOT NULL,
                total_marks REAL NOT NULL,
                test_date TEXT NOT NULL
            );
        """)
        # Safely migrate existing tables if completed_at column is missing
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(dsa_questions)").fetchall()]
        if "completed_at" not in columns:
            conn.execute("ALTER TABLE dsa_questions ADD COLUMN completed_at TIMESTAMP")


def get_practice_dates(conn) -> set:
    """Collect unique practice dates across DSA questions, aptitude logs, and mock tests."""
    dates = set()

    # 1. DSA creation dates
    rows = conn.execute("SELECT created_at FROM dsa_questions WHERE created_at IS NOT NULL").fetchall()
    for row in rows:
        val = str(row["created_at"]).strip()
        if len(val) >= 10:
            try:
                dates.add(datetime.strptime(val[:10], "%Y-%m-%d").date())
            except ValueError:
                pass

    # 2. DSA completion dates
    rows = conn.execute("SELECT completed_at FROM dsa_questions WHERE completed_at IS NOT NULL").fetchall()
    for row in rows:
        val = str(row["completed_at"]).strip()
        if len(val) >= 10:
            try:
                dates.add(datetime.strptime(val[:10], "%Y-%m-%d").date())
            except ValueError:
                pass

    # 3. Aptitude practice dates
    rows = conn.execute("SELECT practice_date FROM aptitude_logs WHERE practice_date IS NOT NULL").fetchall()
    for row in rows:
        val = str(row["practice_date"]).strip()
        if len(val) >= 10:
            try:
                dates.add(datetime.strptime(val[:10], "%Y-%m-%d").date())
            except ValueError:
                pass

    # 4. Mock test dates
    rows = conn.execute("SELECT test_date FROM mock_tests WHERE test_date IS NOT NULL").fetchall()
    for row in rows:
        val = str(row["test_date"]).strip()
        if len(val) >= 10:
            try:
                dates.add(datetime.strptime(val[:10], "%Y-%m-%d").date())
            except ValueError:
                pass

    return dates


def calculate_streak(conn, as_of_date=None) -> int:
    """Calculate daily practice streak from recorded practice dates.
    
    Counts consecutive days backward. If practice exists today, counts starting today.
    If no practice today but practiced yesterday, the streak remains active from yesterday.
    Multiple activities on the same date count as a single day.
    """
    if as_of_date is None:
        target_date = datetime.now().date()
    elif isinstance(as_of_date, str):
        target_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
    else:
        target_date = as_of_date

    practice_dates = get_practice_dates(conn)
    if not practice_dates:
        return 0

    if target_date in practice_dates:
        streak = 0
        curr = target_date
        while curr in practice_dates:
            streak += 1
            curr -= timedelta(days=1)
        return streak

    yesterday = target_date - timedelta(days=1)
    if yesterday in practice_dates:
        streak = 0
        curr = yesterday
        while curr in practice_dates:
            streak += 1
            curr -= timedelta(days=1)
        return streak

    return 0


def has_practiced_today(conn, as_of_date=None) -> bool:
    """Check if any practice was recorded for the target date."""
    if as_of_date is None:
        target_date = datetime.now().date()
    elif isinstance(as_of_date, str):
        target_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
    elif isinstance(as_of_date, datetime):
        target_date = as_of_date.date()
    else:
        target_date = as_of_date
    return target_date in get_practice_dates(conn)


def get_weekly_stats(conn, as_of_date=None) -> dict:
    """Calculate rolling 7-day progress statistics from actual database records.

    Includes:
    - Active study days (unique practice dates in the 7-day window)
    - Total aptitude questions solved in the 7-day window
    - Total aptitude minutes practiced in the 7-day window
    - DSA questions completed in the 7-day window
    - Mock tests taken and average score in the 7-day window
    - Day-by-day activity breakdown for the 7-day timeline
    """
    if as_of_date is None:
        target_date = datetime.now().date()
    elif isinstance(as_of_date, str):
        target_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
    elif isinstance(as_of_date, datetime):
        target_date = as_of_date.date()
    else:
        target_date = as_of_date

    start_date = target_date - timedelta(days=6)
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = target_date.strftime("%Y-%m-%d")

    # 1. DSA questions completed in 7-day window
    dsa_rows = conn.execute(
        "SELECT id, created_at, completed_at, status FROM dsa_questions WHERE status = 'Completed'"
    ).fetchall()

    weekly_dsa_completed = 0
    for row in dsa_rows:
        comp_val = row["completed_at"]
        if comp_val:
            comp_str = str(comp_val).strip()[:10]
            if start_date_str <= comp_str <= end_date_str:
                weekly_dsa_completed += 1
        else:
            creat_val = row["created_at"]
            if creat_val:
                creat_str = str(creat_val).strip()[:10]
                if start_date_str <= creat_str <= end_date_str:
                    weekly_dsa_completed += 1

    # 2. Aptitude questions and minutes in 7-day window
    apt_row = conn.execute(
        """SELECT COALESCE(SUM(questions_solved), 0) AS total_q,
                  COALESCE(SUM(minutes_spent), 0) AS total_m
           FROM aptitude_logs
           WHERE practice_date >= ? AND practice_date <= ?""",
        (start_date_str, end_date_str),
    ).fetchone()
    weekly_aptitude_questions = int(apt_row["total_q"]) if apt_row else 0
    weekly_aptitude_minutes = int(apt_row["total_m"]) if apt_row else 0

    # 3. Mock tests in 7-day window
    mock_row = conn.execute(
        """SELECT COUNT(*) AS test_count,
                  AVG((score / total_marks) * 100) AS avg_score
           FROM mock_tests
           WHERE test_date >= ? AND test_date <= ? AND total_marks > 0""",
        (start_date_str, end_date_str),
    ).fetchone()
    weekly_mock_count = int(mock_row["test_count"]) if mock_row else 0
    weekly_mock_avg = round(float(mock_row["avg_score"]), 1) if (mock_row and mock_row["avg_score"] is not None) else 0.0

    # 4. Active days in 7-day window
    all_practice_dates = get_practice_dates(conn)
    active_dates_in_window = {d for d in all_practice_dates if start_date <= d <= target_date}
    weekly_active_days = len(active_dates_in_window)

    # Day-by-day breakdown
    days_breakdown = []
    curr = start_date
    while curr <= target_date:
        days_breakdown.append({
            "date": curr.strftime("%Y-%m-%d"),
            "day_name": curr.strftime("%a"),
            "is_today": curr == target_date,
            "active": curr in active_dates_in_window,
        })
        curr += timedelta(days=1)

    return {
        "start_date": start_date_str,
        "end_date": end_date_str,
        "active_days": weekly_active_days,
        "total_days": 7,
        "aptitude_questions": weekly_aptitude_questions,
        "aptitude_minutes": weekly_aptitude_minutes,
        "dsa_completed": weekly_dsa_completed,
        "mock_tests_taken": weekly_mock_count,
        "mock_avg_score": weekly_mock_avg,
        "days_breakdown": days_breakdown,
    }


@app.route("/")
def dashboard():
    search = request.args.get("search", request.args.get("q", "")).strip()
    topic = request.args.get("topic", "").strip()
    difficulty = request.args.get("difficulty", "").strip()
    status = request.args.get("status", "").strip()

    with get_db() as conn:
        # Build filtered query for DSA questions safely
        query = "SELECT * FROM dsa_questions WHERE 1=1"
        params = []
        if search:
            query += " AND LOWER(title) LIKE ?"
            params.append(f"%{search.lower()}%")
        if topic and topic.lower() != "all":
            query += " AND LOWER(topic) = LOWER(?)"
            params.append(topic)
        if difficulty and difficulty in VALID_DIFFICULTIES:
            query += " AND difficulty = ?"
            params.append(difficulty)
        if status and status in {"Pending", "Completed"}:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY id DESC"

        questions = conn.execute(query, params).fetchall()

        # Collect distinct topics for the filter dropdown
        distinct_topics_rows = conn.execute(
            "SELECT DISTINCT topic FROM dsa_questions WHERE topic IS NOT NULL AND TRIM(topic) != '' ORDER BY topic ASC"
        ).fetchall()
        distinct_topics = [row["topic"] for row in distinct_topics_rows]

        aptitude_logs = conn.execute(
            "SELECT * FROM aptitude_logs ORDER BY practice_date DESC, id DESC"
        ).fetchall()
        mock_tests = conn.execute(
            "SELECT * FROM mock_tests ORDER BY test_date DESC, id DESC"
        ).fetchall()

        total_dsa = conn.execute("SELECT COUNT(*) FROM dsa_questions").fetchone()[0]
        completed_dsa = conn.execute(
            "SELECT COUNT(*) FROM dsa_questions WHERE status = 'Completed'"
        ).fetchone()[0]
        pending_dsa = max(0, total_dsa - completed_dsa)
        aptitude_questions = conn.execute(
            "SELECT COALESCE(SUM(questions_solved), 0) FROM aptitude_logs"
        ).fetchone()[0]
        avg_score_row = conn.execute(
            "SELECT AVG((score / total_marks) * 100) FROM mock_tests WHERE total_marks > 0"
        ).fetchone()[0]

        streak = calculate_streak(conn)
        practiced_today = has_practiced_today(conn)

        # Chronological mock tests for performance chart
        mock_chart_rows = conn.execute(
            "SELECT test_name, score, total_marks, test_date FROM mock_tests ORDER BY test_date ASC, id ASC"
        ).fetchall()
        mock_chart_data = [
            {
                "name": row["test_name"],
                "date": row["test_date"],
                "score": float(row["score"]),
                "total_marks": float(row["total_marks"]),
                "percentage": round((float(row["score"]) / float(row["total_marks"])) * 100, 1) if float(row["total_marks"]) > 0 else 0,
            }
            for row in mock_chart_rows
        ]

        # Chronological grouped aptitude sessions for practice volume chart
        aptitude_chart_rows = conn.execute(
            """SELECT practice_date, 
                      SUM(questions_solved) AS total_questions, 
                      SUM(minutes_spent) AS total_minutes,
                      COUNT(*) AS session_count
               FROM aptitude_logs 
               GROUP BY practice_date 
               ORDER BY practice_date ASC"""
        ).fetchall()
        aptitude_chart_data = [
            {
                "date": row["practice_date"],
                "questions": int(row["total_questions"]),
                "minutes": int(row["total_minutes"]),
                "sessions": int(row["session_count"]),
            }
            for row in aptitude_chart_rows
        ]

        # Rolling 7-day weekly progress statistics
        weekly_stats = get_weekly_stats(conn)

    completion = round((completed_dsa / total_dsa) * 100) if total_dsa else 0
    average_score = round(avg_score_row, 1) if avg_score_row is not None else 0

    analytics = {
        "dsa": {
            "total": total_dsa,
            "completed": completed_dsa,
            "pending": pending_dsa,
            "completion_rate": completion,
        },
        "mock_tests": mock_chart_data,
        "aptitude": aptitude_chart_data,
        "weekly": weekly_stats,
    }

    return render_template(
        "index.html",
        questions=questions,
        distinct_topics=distinct_topics,
        aptitude_logs=aptitude_logs,
        mock_tests=mock_tests,
        total_dsa=total_dsa,
        completed_dsa=completed_dsa,
        pending_dsa=pending_dsa,
        completion=completion,
        aptitude_questions=aptitude_questions,
        average_score=average_score,
        streak=streak,
        practiced_today=practiced_today,
        search_query=search,
        selected_topic=topic,
        selected_difficulty=difficulty,
        selected_status=status,
        weekly_stats=weekly_stats,
        analytics=analytics,
    )


@app.post("/add-dsa")
def add_dsa():
    title = request.form.get("title", "").strip()
    topic = request.form.get("topic", "").strip()
    difficulty = request.form.get("difficulty", "Easy").strip()

    if not title or not topic:
        flash("Please enter both a question title and topic.", "error")
        return redirect(url_for("dashboard"))
    if len(title) > 120:
        flash("Question title must not exceed 120 characters.", "error")
        return redirect(url_for("dashboard"))
    if len(topic) > 60:
        flash("Topic must not exceed 60 characters.", "error")
        return redirect(url_for("dashboard"))
    if difficulty not in VALID_DIFFICULTIES:
        difficulty = "Easy"

    with get_db() as conn:
        conn.execute(
            "INSERT INTO dsa_questions (title, topic, difficulty) VALUES (?, ?, ?)",
            (title, topic, difficulty),
        )
    flash("DSA question added!", "success")
    return redirect(url_for("dashboard"))


@app.route("/edit-dsa/<int:question_id>", methods=["GET", "POST"])
def edit_dsa(question_id):
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        topic = request.form.get("topic", "").strip()
        difficulty = request.form.get("difficulty", "Easy").strip()

        if not title or not topic:
            flash("Please enter both a question title and topic.", "error")
            return redirect(url_for("dashboard"))
        if len(title) > 120:
            flash("Question title must not exceed 120 characters.", "error")
            return redirect(url_for("dashboard"))
        if len(topic) > 60:
            flash("Topic must not exceed 60 characters.", "error")
            return redirect(url_for("dashboard"))
        if difficulty not in VALID_DIFFICULTIES:
            flash("Please select a valid difficulty (Easy, Medium, or Hard).", "error")
            return redirect(url_for("dashboard"))

        with get_db() as conn:
            row = conn.execute("SELECT id FROM dsa_questions WHERE id = ?", (question_id,)).fetchone()
            if not row:
                flash("Question not found.", "error")
                return redirect(url_for("dashboard"))
            conn.execute(
                "UPDATE dsa_questions SET title = ?, topic = ?, difficulty = ? WHERE id = ?",
                (title, topic, difficulty, question_id),
            )
        flash("DSA question updated!", "success")
        return redirect(url_for("dashboard"))

    # GET request - render standalone edit page
    with get_db() as conn:
        question = conn.execute("SELECT * FROM dsa_questions WHERE id = ?", (question_id,)).fetchone()
    if not question:
        flash("Question not found.", "error")
        return redirect(url_for("dashboard"))
    return render_template("edit_dsa.html", question=question)


@app.post("/toggle-dsa/<int:question_id>")
def toggle_dsa(question_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT status FROM dsa_questions WHERE id = ?", (question_id,)
        ).fetchone()
        if row:
            if row["status"] == "Completed":
                new_status = "Pending"
                conn.execute(
                    "UPDATE dsa_questions SET status = ?, completed_at = NULL WHERE id = ?",
                    (new_status, question_id),
                )
            else:
                new_status = "Completed"
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.execute(
                    "UPDATE dsa_questions SET status = ?, completed_at = ? WHERE id = ?",
                    (new_status, now_str, question_id),
                )
            flash(f"Question status updated to {new_status}.", "success")
        else:
            flash("Question not found.", "error")
    return redirect(url_for("dashboard"))


@app.post("/delete-dsa/<int:question_id>")
def delete_dsa(question_id):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM dsa_questions WHERE id = ?", (question_id,))
        if cursor.rowcount == 0:
            flash("Question not found.", "error")
        else:
            flash("DSA question deleted.", "success")
    return redirect(url_for("dashboard"))


@app.post("/add-aptitude")
def add_aptitude():
    topic = request.form.get("aptitude_topic", "").strip()
    questions = request.form.get("questions_solved", type=int)
    minutes = request.form.get("minutes_spent", type=int)
    practice_date = request.form.get("practice_date", "").strip()

    if not topic or questions is None or minutes is None or not practice_date:
        flash("Please fill in all aptitude fields.", "error")
        return redirect(url_for("dashboard"))
    if len(topic) > 80:
        flash("Topic must not exceed 80 characters.", "error")
        return redirect(url_for("dashboard"))
    if questions < 0 or minutes < 0:
        flash("Questions and minutes cannot be negative.", "error")
        return redirect(url_for("dashboard"))
    if questions > 10000 or minutes > 1440:
        flash("Questions solved must not exceed 10,000 and minutes must not exceed 1,440.", "error")
        return redirect(url_for("dashboard"))
    if not is_valid_date(practice_date):
        flash("Please provide a valid date in YYYY-MM-DD format.", "error")
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        conn.execute(
            """INSERT INTO aptitude_logs
               (topic, questions_solved, minutes_spent, practice_date)
               VALUES (?, ?, ?, ?)""",
            (topic, questions, minutes, practice_date),
        )
    flash("Aptitude practice saved!", "success")
    return redirect(url_for("dashboard"))


@app.post("/delete-aptitude/<int:log_id>")
def delete_aptitude(log_id):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM aptitude_logs WHERE id = ?", (log_id,))
        if cursor.rowcount == 0:
            flash("Aptitude practice record not found.", "error")
        else:
            flash("Aptitude practice log deleted.", "success")
    return redirect(url_for("dashboard"))


@app.post("/add-mock")
def add_mock():
    name = request.form.get("test_name", "").strip()
    score_raw = request.form.get("score")
    total_raw = request.form.get("total_marks")
    test_date = request.form.get("test_date", "").strip()

    if not name or score_raw is None or total_raw is None or not test_date:
        flash("Please fill in all mock-test fields.", "error")
        return redirect(url_for("dashboard"))

    try:
        score = float(score_raw)
        total = float(total_raw)
    except (ValueError, TypeError):
        flash("Score and total marks must be valid numbers.", "error")
        return redirect(url_for("dashboard"))

    if math.isnan(score) or math.isinf(score) or math.isnan(total) or math.isinf(total):
        flash("Score and total marks must be finite numbers.", "error")
        return redirect(url_for("dashboard"))

    if len(name) > 100:
        flash("Test name must not exceed 100 characters.", "error")
        return redirect(url_for("dashboard"))

    if total <= 0 or score < 0 or score > total:
        flash("Score must be between 0 and total marks; total must be above zero.", "error")
        return redirect(url_for("dashboard"))

    if total > 10000:
        flash("Total marks cannot exceed 10,000.", "error")
        return redirect(url_for("dashboard"))

    if not is_valid_date(test_date):
        flash("Please provide a valid date in YYYY-MM-DD format.", "error")
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        conn.execute(
            """INSERT INTO mock_tests (test_name, score, total_marks, test_date)
               VALUES (?, ?, ?, ?)""",
            (name, score, total, test_date),
        )
    flash("Mock-test score saved!", "success")
    return redirect(url_for("dashboard"))


@app.post("/delete-mock/<int:test_id>")
def delete_mock(test_id):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM mock_tests WHERE id = ?", (test_id,))
        if cursor.rowcount == 0:
            flash("Mock-test record not found.", "error")
        else:
            flash("Mock-test record deleted.", "success")
    return redirect(url_for("dashboard"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)

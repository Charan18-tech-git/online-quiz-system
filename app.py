from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "quiz_secret_key"


# ---------------- DATABASE ----------------
def get_db_connection():
    conn = sqlite3.connect("quiz.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            option1 TEXT NOT NULL,
            option2 TEXT NOT NULL,
            option3 TEXT NOT NULL,
            option4 TEXT NOT NULL,
            correct_answer TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            date TEXT NOT NULL
        )
    """)

    # default admin and student
    cur.execute("SELECT * FROM users WHERE username=?", ("admin",))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    ("admin", "admin123", "admin"))

    cur.execute("SELECT * FROM users WHERE username=?", ("student",))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    ("student", "student123", "student"))

    conn.commit()
    conn.close()


# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session["username"] = user["username"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("student_dashboard"))
        else:
            flash("Invalid username or password!")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/admin")
def admin_dashboard():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    questions = conn.execute("SELECT * FROM questions").fetchall()
    conn.close()

    return render_template("admin_dashboard.html", questions=questions)


@app.route("/add_question", methods=["GET", "POST"])
def add_question():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        question = request.form["question"]
        option1 = request.form["option1"]
        option2 = request.form["option2"]
        option3 = request.form["option3"]
        option4 = request.form["option4"]
        correct_answer = request.form["correct_answer"]

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO questions (question, option1, option2, option3, option4, correct_answer)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (question, option1, option2, option3, option4, correct_answer))
        conn.commit()
        conn.close()

        flash("Question added successfully!")
        return redirect(url_for("admin_dashboard"))

    return render_template("add_question.html")


@app.route("/delete_question/<int:q_id>")
def delete_question(q_id):
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    conn.execute("DELETE FROM questions WHERE id=?", (q_id,))
    conn.commit()
    conn.close()

    flash("Question deleted successfully!")
    return redirect(url_for("admin_dashboard"))


@app.route("/student")
def student_dashboard():
    if "role" not in session or session["role"] != "student":
        return redirect(url_for("login"))

    return render_template("student_dashboard.html")


@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if "role" not in session or session["role"] != "student":
        return redirect(url_for("login"))

    conn = get_db_connection()
    questions = conn.execute("SELECT * FROM questions").fetchall()

    if request.method == "POST":
        score = 0
        total = len(questions)

        for q in questions:
            selected = request.form.get(str(q["id"]))
            if selected == q["correct_answer"]:
                score += 1

        conn.execute("""
            INSERT INTO results (username, score, total, date)
            VALUES (?, ?, ?, ?)
        """, (session["username"], score, total, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

        return redirect(url_for("result", score=score, total=total))

    conn.close()
    return render_template("quiz.html", questions=questions)


@app.route("/result")
def result():
    score = request.args.get("score", 0)
    total = request.args.get("total", 0)
    return render_template("result.html", score=score, total=total)


@app.route("/leaderboard")
def leaderboard():
    conn = get_db_connection()
    results = conn.execute("""
        SELECT username, MAX(score) as best_score, total
        FROM results
        GROUP BY username
        ORDER BY best_score DESC
    """).fetchall()
    conn.close()

    return render_template("leaderboard.html", results=results)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
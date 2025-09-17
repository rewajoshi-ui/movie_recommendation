from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import requests
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")

API_KEY = os.environ.get("TMDB_API_KEY", "4e32dd97a23c40cd87ad9a0267f7ccee")
BASE_URL = "https://api.themoviedb.org/3"

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    movie_id INTEGER,
                    rating INTEGER,
                    review TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    url = f"{BASE_URL}/trending/movie/week?api_key={API_KEY}"
    response = requests.get(url)
    movies = response.json().get("results", []) if response.status_code == 200 else []
    return render_template("index.html", movies=movies, user=session.get("user"))

@app.route("/search")
def search():
    query = request.args.get("q", "")  # match the input name in your HTML
    movies = []
    if query:
        url = f"{BASE_URL}/search/movie?api_key={API_KEY}&query={query}"
        response = requests.get(url)
        if response.status_code == 200:
            movies = response.json().get("results", [])
    return render_template("index.html", movies=movies, search_query=query, user=session.get("user"))

@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}?api_key={API_KEY}&append_to_response=credits"
    response = requests.get(url)
    movie = response.json() if response.status_code == 200 else {}

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT username, rating, review FROM reviews WHERE movie_id=?", (movie_id,))
    reviews = c.fetchall()
    conn.close()

    return render_template("movie.html", movie=movie, reviews=reviews, user=session.get("user"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user"] = username
            flash("Logged in successfully!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password", "danger")
            return redirect(url_for("login"))  

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists!", "danger")
            return redirect(url_for("register"))  # <- changed here
        finally:
            conn.close()

    return render_template("register.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("home"))

@app.route("/review/<int:movie_id>", methods=["POST"])
def review(movie_id):
    if "user" not in session:
        flash("You must be logged in to submit a review.", "warning")
        return redirect(url_for("login"))

    rating = int(request.form["rating"])
    review_text = request.form["review"]

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM reviews WHERE username=? AND movie_id=?", (session["user"], movie_id))
    if not c.fetchone():
        c.execute("INSERT INTO reviews (username, movie_id, rating, review) VALUES (?, ?, ?, ?)",
                  (session["user"], movie_id, rating, review_text))
        conn.commit()
        flash("Review submitted successfully!", "success")
    else:
        flash("You have already reviewed this movie.", "warning")
    conn.close()

    return redirect(url_for("movie_detail", movie_id=movie_id))

if __name__ == "__main__":
    app.run(debug=True)

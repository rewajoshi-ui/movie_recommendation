from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import requests

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change this if deploying

API_KEY = "4e32dd97a23c40cd87ad9a0267f7ccee"
BASE_URL = "https://api.themoviedb.org/3"


def init_db():
    conn = sqlite3.connect("database.db")
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
    response = requests.get(url).json()
    movies = response.get("results", [])
    return render_template("index.html", movies=movies)

@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q")
    url = f"{BASE_URL}/search/movie?api_key={API_KEY}&query={query}"
    response = requests.get(url).json()
    movies = response.get("results", [])
    return render_template("index.html", movies=movies, search_query=query)

@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}?api_key={API_KEY}&append_to_response=credits"
    movie = requests.get(url).json()

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT username, rating, review FROM reviews WHERE movie_id=?", (movie_id,))
    reviews = c.fetchall()
    conn.close()

    return render_template("movie.html", movie=movie, reviews=reviews)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except:
            pass
        conn.close()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))

@app.route("/review/<int:movie_id>", methods=["POST"])
def review(movie_id):
    if "user" not in session:
        return redirect(url_for("login"))

    rating = request.form["rating"]
    review_text = request.form["review"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO reviews (username, movie_id, rating, review) VALUES (?, ?, ?, ?)",
              (session["user"], movie_id, rating, review_text))
    conn.commit()
    conn.close()
    return redirect(url_for("movie_detail", movie_id=movie_id))


if __name__ == "__main__":
    app.run(debug=True)

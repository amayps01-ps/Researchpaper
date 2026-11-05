import os
import re
import json
import math
import sqlite3
import secrets
import hashlib
from collections import Counter
from datetime import datetime, timedelta, timezone
from functools import wraps
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv

load_dotenv()

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

DATABASE = os.environ.get(
    "DATABASE_PATH",
    os.path.join(INSTANCE_DIR, "researchai.sqlite3")
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "CHANGE-THIS-LOCAL-SECRET-BEFORE-DEPLOYMENT")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,
)
# PythonAnywhere is behind a proxy. This helps Flask recognize HTTPS requests.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "").strip()
APP_BASE_URL = os.environ.get("APP_BASE_URL", "").strip().rstrip("/")

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "with", "we", "using", "use", "based", "via", "into", "their",
    "these", "those", "can", "could", "may", "more", "new", "our"
}

# Demonstration seed data. Add or replace records in this list with verified papers.
SEED_PAPERS = [
    {
        "title": "Attention Is All You Need",
        "authors": "Ashish Vaswani et al.",
        "year": 2017,
        "abstract": "We propose the Transformer, a model architecture based entirely on attention mechanisms, dispensing with recurrence and convolutions for sequence transduction.",
        "paper_url": "https://arxiv.org/abs/1706.03762"
    },
    {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "authors": "Jacob Devlin et al.",
        "year": 2018,
        "abstract": "BERT obtains state of the art results on a wide range of natural language processing tasks by pre-training deep bidirectional representations.",
        "paper_url": "https://arxiv.org/abs/1810.04805"
    },
    {
        "title": "Deep Residual Learning for Image Recognition",
        "authors": "Kaiming He et al.",
        "year": 2015,
        "abstract": "We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously for image recognition.",
        "paper_url": "https://arxiv.org/abs/1512.03385"
    },
    {
        "title": "A Survey on Machine Learning",
        "authors": "Demo dataset record",
        "year": 2022,
        "abstract": "An introductory survey of supervised learning, unsupervised learning, classification, regression, clustering, and model evaluation."
    },
    {
        "title": "Convolutional Neural Networks for Visual Recognition",
        "authors": "Demo dataset record",
        "year": 2021,
        "abstract": "This paper introduces convolutional neural network concepts for image classification, feature extraction, computer vision, and visual recognition."
    },
    {
        "title": "Generative Adversarial Networks",
        "authors": "Ian Goodfellow et al.",
        "year": 2014,
        "abstract": "We propose a framework for estimating generative models via an adversarial process in which two models are trained simultaneously."
    },
    {
        "title": "Deep Learning",
        "authors": "Yoshua Bengio, Ian Goodfellow, Aaron Courville",
        "year": 2016,
        "abstract": "A broad introduction to deep learning methods, neural networks, optimization, representation learning, and applications."
    },
    {
        "title": "Random Forests",
        "authors": "Leo Breiman",
        "year": 2001,
        "abstract": "Random forests are a combination of tree predictors such that each tree depends on the values of a random vector sampled independently."
    },
    {
        "title": "XGBoost: A Scalable Tree Boosting System",
        "authors": "Tianqi Chen and Carlos Guestrin",
        "year": 2016,
        "abstract": "We describe a scalable end-to-end tree boosting system widely used for classification and regression problems."
    },
    {
        "title": "The Anatomy of a Large-Scale Hypertextual Web Search Engine",
        "authors": "Sergey Brin and Lawrence Page",
        "year": 1998,
        "abstract": "This paper describes Google, a prototype of a large-scale search engine that makes heavy use of the structure present in hypertext."
    },
    {
        "title": "MapReduce: Simplified Data Processing on Large Clusters",
        "authors": "Jeffrey Dean and Sanjay Ghemawat",
        "year": 2004,
        "abstract": "MapReduce is a programming model and implementation for processing and generating large data sets with a parallel distributed algorithm."
    },
    {
        "title": "Dynamo: Amazon's Highly Available Key-value Store",
        "authors": "Giuseppe DeCandia et al.",
        "year": 2007,
        "abstract": "Dynamo is a highly available key value storage system that provides a simple primary key interface to meet reliability requirements."
    },
    {
        "title": "Bitcoin: A Peer-to-Peer Electronic Cash System",
        "authors": "Satoshi Nakamoto",
        "year": 2008,
        "abstract": "A peer to peer electronic cash system using a distributed ledger and proof of work to solve double spending."
    },
    {
    "title": "A Survey of Data Mining and Machine Learning Methods for Cyber Security Intrusion Detection",
    "authors": "Anna L. Buczak and Erhan Guven",
    "year": 2016,
    "abstract": "A survey of machine learning and data mining methods used for cybersecurity analytics and intrusion detection.",
    "paper_url": "https://ieeexplore.ieee.org/document/7307098"
    },
    {
        "title": "Federated Learning: Challenges, Methods, and Future Directions",
        "authors": "Demo dataset record",
        "year": 2023,
        "abstract": "Federated learning trains machine learning models across decentralized devices while keeping raw data at local clients."
    },
    {
        "title": "Explainable Artificial Intelligence: A Survey",
        "authors": "Demo dataset record",
        "year": 2022,
        "abstract": "A survey of explainable AI methods that help people understand predictions from machine learning and deep learning models."
    },
    {
        "title": "A Survey of Data Mining and Machine Learning Methods for Cyber Security Intrusion Detection",
        "authors": "Anna L. Buczak and Erhan Guven",
        "year": 2016,
        "abstract": "A survey of machine learning and data mining methods used for cybersecurity analytics and intrusion detection.",
        "paper_url": "https://ieeexplore.ieee.org/document/7307098"
    },
    {
        "title": "Recommender Systems Handbook: Collaborative Filtering",
        "authors": "Demo dataset record",
        "year": 2020,
        "abstract": "Collaborative filtering predicts user interests from user item interactions and similarities between users or items."
    },
    {
        "title": "Natural Language Processing with Transformers",
        "authors": "Demo dataset record",
        "year": 2021,
        "abstract": "A practical overview of transformer models, tokenization, text classification, question answering, and language generation."
    },
    {
        "title": "Edge Computing: A Survey",
        "authors": "Demo dataset record",
        "year": 2019,
        "abstract": "Edge computing moves computation closer to data sources to reduce latency and bandwidth use in Internet of Things systems."
    }
]

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                authors TEXT NOT NULL,
                year INTEGER NOT NULL,
                abstract TEXT NOT NULL
            )
        """)
        # Add paper URL column if it does not exist
        columns = [
            row["name"]
            for row in db.execute("PRAGMA table_info(papers)").fetchall()
        ]
        count = db.execute("SELECT COUNT(*) FROM papers").fetchone()[0]

        if count == 0:
            db.executemany(
                """INSERT INTO papers
                (title, authors, year, abstract, paper_url)
                VALUES (?, ?, ?, ?, ?)""",
                [
                    (
                        p["title"],
                        p["authors"],
                        p["year"],
                        p["abstract"],
                        p.get("paper_url", "")
                    )
                    for p in SEED_PAPERS
                ]
            )

        db.commit()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "info")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def tokenize(text):
    words = re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]

def tfidf_recommend(query, papers, limit=8):
    """Small pure-Python TF-IDF + cosine-similarity recommender."""
    docs = [
        tokenize(p["title"] + " " + p["authors"] + " " + p["abstract"])
        for p in papers
    ]
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    df = Counter()
    for doc in docs:
        df.update(set(doc))
    total_docs = max(len(docs), 1)

    def vector(tokens):
        counts = Counter(tokens)
        result = {}
        length = max(len(tokens), 1)
        for term, count in counts.items():
            if term in df:
                tf = count / length
                idf = math.log((1 + total_docs) / (1 + df[term])) + 1
                result[term] = tf * idf
        return result

    qv = vector(query_tokens)
    qnorm = math.sqrt(sum(v * v for v in qv.values()))
    if qnorm == 0:
        return []

    scored = []
    for paper, tokens in zip(papers, docs):
        dv = vector(tokens)
        dnorm = math.sqrt(sum(v * v for v in dv.values()))
        if dnorm == 0:
            score = 0.0
        else:
            dot = sum(value * dv.get(term, 0.0) for term, value in qv.items())
            score = dot / (qnorm * dnorm)
        if score > 0:
            item = dict(paper)
            item["score"] = round(score * 100, 2)
            scored.append(item)

    return sorted(scored, key=lambda x: x["score"], reverse=True)[:limit]

def send_reset_email(receiver_email, reset_link):
    if not RESEND_API_KEY or not RESEND_FROM_EMAIL:
        raise RuntimeError("Email service is not configured. Set RESEND_API_KEY and RESEND_FROM_EMAIL.")

    payload = {
        "from": RESEND_FROM_EMAIL,
        "to": [receiver_email],
        "subject": "ResearchAI - Password reset",
        "text": (
            "Hello,\n\n"
            "We received a request to reset your ResearchAI password.\n\n"
            f"Open this link to choose a new password:\n{reset_link}\n\n"
            "This link expires in 30 minutes. If you did not request this, ignore this email.\n\n"
            "ResearchAI Team"
        )
    }
    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=12
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Email provider returned {response.status_code}: {response.text[:300]}")
    return response.json()

def make_reset_url(token):
    path = url_for("reset_password", token=token)
    if APP_BASE_URL:
        return urljoin(APP_BASE_URL + "/", path.lstrip("/"))
    return url_for("reset_password", token=token, _external=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("Please complete all fields.", "error")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        else:
            try:
                with get_db() as db:
                    db.execute(
                        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                        (name, email, generate_password_hash(password), datetime.now(timezone.utc).isoformat())
                    )
                    db.commit()
                flash("Registration successful. Please log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("This email is already registered.", "error")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    query = request.form.get("query", "").strip() if request.method == "POST" else request.args.get("q", "").strip()

    results = []

    if query:
        with get_db() as db:
            papers = [
                dict(row)
                for row in db.execute("SELECT * FROM papers").fetchall()
            ]

        results = tfidf_recommend(query, papers)

        if not results:
            flash("No close matches found. Try different keywords.", "info")

    return render_template(
        "dashboard.html",
        query=query,
        results=results
    )
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        # Keep the response generic so the page does not reveal whether an account exists.
        with get_db() as db:
            user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if user:
                token = secrets.token_urlsafe(32)
                token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
                expires = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
                db.execute("DELETE FROM password_resets WHERE email = ?", (email,))
                db.execute(
                    "INSERT INTO password_resets (email, token_hash, expires_at, created_at) VALUES (?, ?, ?, ?)",
                    (email, token_hash, expires, datetime.now(timezone.utc).isoformat())
                )
                db.commit()
            else:
                token = None

        if token:
            try:
                send_reset_email(email, make_reset_url(token))
            except Exception as exc:
                app.logger.exception("Password reset email failed: %s", exc)
                # Remove the unusable token if email could not be sent.
                with get_db() as db:
                    db.execute("DELETE FROM password_resets WHERE email = ?", (email,))
                    db.commit()
                flash("We could not send the reset email. Please try again later.", "error")
                return render_template("forgot_password.html")

        flash("If this email is registered, a password-reset link will be sent.", "success")
        return redirect(url_for("login"))
    return render_template("forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with get_db() as db:
        reset = db.execute(
            "SELECT * FROM password_resets WHERE token_hash = ?",
            (token_hash,)
        ).fetchone()

    valid = False
    if reset:
        try:
            expiry = datetime.fromisoformat(reset["expires_at"])
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            valid = expiry > datetime.now(timezone.utc)
        except ValueError:
            valid = False

    if not valid:
        flash("This reset link is invalid or expired. Please request a new one.", "error")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        else:
            with get_db() as db:
                db.execute(
                    "UPDATE users SET password_hash = ? WHERE email = ?",
                    (generate_password_hash(password), reset["email"])
                )
                db.execute("DELETE FROM password_resets WHERE email = ?", (reset["email"],))
                db.commit()
            flash("Password changed successfully. Please log in.", "success")
            return redirect(url_for("login"))
    return render_template("reset_password.html")

@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", message="The page you requested was not found."), 404

@app.errorhandler(500)
def server_error(error):
    app.logger.exception("Unexpected server error")
    return render_template("error.html", message="Something went wrong. Please try again."), 500

init_db()

if __name__ == "__main__":
    app.run(debug=True)

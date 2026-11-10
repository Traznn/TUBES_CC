import os, time
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request

app = Flask(__name__)
app.json.default = lambda o: o.isoformat() if hasattr(o, "isoformat") else str(o)


def get_conn():
    last = None
    for _ in range(10):
        try:
            return psycopg2.connect(
                host=os.getenv("DB_HOST", "db"),
                dbname=os.getenv("DB_NAME", "perpustakaan"),
                user=os.getenv("DB_USER", "admin"),
                password=os.getenv("DB_PASSWORD", "admin123"),
            )
        except psycopg2.OperationalError as e:
            last = e
            time.sleep(2)
    raise last


def query(sql, params=(), fetch="all"):
    conn = get_conn()
    try:
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetch == "all":
                return cur.fetchall()
            if fetch == "one":
                return cur.fetchone()
            return None
    finally:
        conn.close()


def err(msg, code):
    return jsonify({"error": msg}), code


BOOK_URL = os.getenv("BOOK_SERVICE_URL", "http://book-service:5001")
MEMBER_URL = os.getenv("MEMBER_SERVICE_URL", "http://member-service:5002")


@app.get("/health")
def health():
    return jsonify({"service": "loan-service", "status": "ok"})


@app.get("/loans")
def list_loans():
    return jsonify(query("SELECT * FROM loans ORDER BY id"))


@app.get("/loans/<int:loan_id>")
def get_loan(loan_id):
    row = query("SELECT * FROM loans WHERE id=%s", (loan_id,), "one")
    return jsonify(row) if row else err("Peminjaman tidak ditemukan", 404)


@app.post("/loans")
def create_loan():
    d = request.get_json(silent=True) or {}
    if not d.get("book_id") or not d.get("member_id"):
        return err("book_id dan member_id wajib diisi", 400)
    try:
        m = requests.get(f"{MEMBER_URL}/members/{d['member_id']}", timeout=5)
        if m.status_code == 404:
            return err("Anggota tidak ditemukan", 404)
        b = requests.get(f"{BOOK_URL}/books/{d['book_id']}", timeout=5)
        if b.status_code == 404:
            return err("Buku tidak ditemukan", 404)
        if b.json()["stock"] < 1:
            return err("Stok buku habis", 409)
        s = requests.patch(f"{BOOK_URL}/books/{d['book_id']}/stock", json={"delta": -1}, timeout=5)
        if s.status_code != 200:
            return err("Gagal mengurangi stok", 409)
    except requests.RequestException:
        return err("Service lain tidak dapat dihubungi", 503)
    days = int(d.get("due_days", 7))
    row = query(
        """INSERT INTO loans (book_id, member_id, due_date)
           VALUES (%s,%s,CURRENT_DATE + %s) RETURNING *""",
        (d["book_id"], d["member_id"], days), "one")
    return jsonify(row), 201


@app.put("/loans/<int:loan_id>")
def update_loan(loan_id):
    d = request.get_json(silent=True) or {}
    cur = query("SELECT * FROM loans WHERE id=%s", (loan_id,), "one")
    if not cur:
        return err("Peminjaman tidak ditemukan", 404)
    if d.get("status") == "returned" and cur["status"] != "returned":
        try:
            requests.patch(f"{BOOK_URL}/books/{cur['book_id']}/stock", json={"delta": 1}, timeout=5)
        except requests.RequestException:
            return err("book-service tidak dapat dihubungi", 503)
        row = query("UPDATE loans SET status='returned', return_date=CURRENT_DATE WHERE id=%s RETURNING *",
                    (loan_id,), "one")
    else:
        row = query("UPDATE loans SET due_date=COALESCE(%s,due_date) WHERE id=%s RETURNING *",
                    (d.get("due_date"), loan_id), "one")
    return jsonify(row)


@app.delete("/loans/<int:loan_id>")
def delete_loan(loan_id):
    cur = query("SELECT * FROM loans WHERE id=%s", (loan_id,), "one")
    if not cur:
        return err("Peminjaman tidak ditemukan", 404)
    if cur["status"] == "borrowed":
        try:
            requests.patch(f"{BOOK_URL}/books/{cur['book_id']}/stock", json={"delta": 1}, timeout=5)
        except requests.RequestException:
            pass
    query("DELETE FROM loans WHERE id=%s", (loan_id,), "none")
    return jsonify({"message": "Peminjaman dihapus", "id": loan_id})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)

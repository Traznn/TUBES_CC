import os, time
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


@app.get("/health")
def health():
    return jsonify({"service": "book-service", "status": "ok"})


@app.get("/books")
def list_books():
    return jsonify(query("SELECT * FROM books ORDER BY id"))


@app.get("/books/<int:book_id>")
def get_book(book_id):
    row = query("SELECT * FROM books WHERE id=%s", (book_id,), "one")
    return jsonify(row) if row else err("Buku tidak ditemukan", 404)


@app.post("/books")
def create_book():
    d = request.get_json(silent=True) or {}
    if not d.get("title") or not d.get("author"):
        return err("title dan author wajib diisi", 400)
    row = query(
        "INSERT INTO books (title, author, isbn, stock) VALUES (%s,%s,%s,%s) RETURNING *",
        (d["title"], d["author"], d.get("isbn"), int(d.get("stock", 1))), "one")
    return jsonify(row), 201


@app.put("/books/<int:book_id>")
def update_book(book_id):
    d = request.get_json(silent=True) or {}
    row = query(
        """UPDATE books SET title=COALESCE(%s,title), author=COALESCE(%s,author),
           isbn=COALESCE(%s,isbn), stock=COALESCE(%s,stock) WHERE id=%s RETURNING *""",
        (d.get("title"), d.get("author"), d.get("isbn"), d.get("stock"), book_id), "one")
    return jsonify(row) if row else err("Buku tidak ditemukan", 404)


@app.patch("/books/<int:book_id>/stock")
def change_stock(book_id):
    """Dipanggil loan-service: delta -1 saat dipinjam, +1 saat dikembalikan."""
    delta = int((request.get_json(silent=True) or {}).get("delta", 0))
    row = query(
        "UPDATE books SET stock=stock+%s WHERE id=%s AND stock+%s>=0 RETURNING *",
        (delta, book_id, delta), "one")
    return jsonify(row) if row else err("Buku tidak ada atau stok tidak cukup", 409)


@app.delete("/books/<int:book_id>")
def delete_book(book_id):
    row = query("DELETE FROM books WHERE id=%s RETURNING id", (book_id,), "one")
    return jsonify({"message": "Buku dihapus", "id": book_id}) if row else err("Buku tidak ditemukan", 404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

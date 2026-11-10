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
    return jsonify({"service": "member-service", "status": "ok"})


@app.get("/members")
def list_members():
    return jsonify(query("SELECT * FROM members ORDER BY id"))


@app.get("/members/<int:member_id>")
def get_member(member_id):
    row = query("SELECT * FROM members WHERE id=%s", (member_id,), "one")
    return jsonify(row) if row else err("Anggota tidak ditemukan", 404)


@app.post("/members")
def create_member():
    d = request.get_json(silent=True) or {}
    if not d.get("name"):
        return err("name wajib diisi", 400)
    row = query(
        "INSERT INTO members (name, email, phone) VALUES (%s,%s,%s) RETURNING *",
        (d["name"], d.get("email"), d.get("phone")), "one")
    return jsonify(row), 201


@app.put("/members/<int:member_id>")
def update_member(member_id):
    d = request.get_json(silent=True) or {}
    row = query(
        """UPDATE members SET name=COALESCE(%s,name), email=COALESCE(%s,email),
           phone=COALESCE(%s,phone) WHERE id=%s RETURNING *""",
        (d.get("name"), d.get("email"), d.get("phone"), member_id), "one")
    return jsonify(row) if row else err("Anggota tidak ditemukan", 404)


@app.delete("/members/<int:member_id>")
def delete_member(member_id):
    row = query("DELETE FROM members WHERE id=%s RETURNING id", (member_id,), "one")
    return jsonify({"message": "Anggota dihapus", "id": member_id}) if row else err("Anggota tidak ditemukan", 404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)

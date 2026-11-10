CREATE TABLE IF NOT EXISTS books (
  id SERIAL PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(120) NOT NULL,
  isbn VARCHAR(30),
  stock INTEGER NOT NULL DEFAULT 1 CHECK (stock >= 0)
);
CREATE TABLE IF NOT EXISTS members (
  id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(120),
  phone VARCHAR(30)
);
CREATE TABLE IF NOT EXISTS loans (
  id SERIAL PRIMARY KEY,
  book_id INTEGER NOT NULL,
  member_id INTEGER NOT NULL,
  loan_date DATE NOT NULL DEFAULT CURRENT_DATE,
  due_date DATE NOT NULL,
  return_date DATE,
  status VARCHAR(20) NOT NULL DEFAULT 'borrowed'
);
INSERT INTO books (title, author, isbn, stock) VALUES
  ('Laskar Pelangi', 'Andrea Hirata', '9789793062792', 3),
  ('Bumi Manusia', 'Pramoedya Ananta Toer', '9789799731234', 2);
INSERT INTO members (name, email, phone) VALUES
  ('Budi Santoso', 'budi@example.com', '081234567890');

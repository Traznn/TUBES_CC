# Project 1 Cloud Computing - Perpustakaan (Microservices, Docker, SQL)

Arsitektur: gateway (Nginx, port 8080) -> book-service (5001), member-service (5002),
loan-service (5003) -> PostgreSQL (volume `db_data`). Hanya gateway yang dibuka ke host.

## Menjalankan
    docker compose up --build -d
    docker compose ps
Buka http://localhost:8080 (UI) atau uji API lewat Postman/curl.

## Contoh uji API
    curl http://localhost:8080/api/books
    curl -X POST http://localhost:8080/api/books -H "Content-Type: application/json" \
         -d '{"title":"Negeri 5 Menara","author":"A. Fuadi","isbn":"9789792248616","stock":2}'
    curl -X PUT http://localhost:8080/api/books/1 -H "Content-Type: application/json" -d '{"stock":5}'
    curl -X DELETE http://localhost:8080/api/books/3
    curl -X POST http://localhost:8080/api/loans -H "Content-Type: application/json" \
         -d '{"member_id":1,"book_id":1}'
    curl -X PUT http://localhost:8080/api/loans/1 -H "Content-Type: application/json" -d '{"status":"returned"}'

## Menghentikan
    docker compose down        # data tetap ada di volume
    docker compose down -v     # hapus data juga

# FLASK API - QUICK REFERENCE

**Base URL:** `http://127.0.0.1:5000`

---

## 🔐 AUTH

- **POST** `/register` — Body: `{ "email", "password", "role" }` — Register user
  - Email must be valid format (e.g., user@example.com)
  - Password must be at least 6 characters
  - Role defaults to "user" if not provided
- **POST** `/login` — Body: `{ "email", "password" }` — Get token
  - Email must be valid format
- **POST** `/logout` — Header: `Authorization: Bearer <token>` — Logout
- **GET** `/` — `[Token optional]` — Home

---

## 📦 PRODUCTS (Admin Only for CUD)

- **POST** `/create` — Body: `{ "name", "description", "price" }` — Create product
- **POST** `/create_bulk` — Body: array of products — Bulk create
- **GET** `/show` — Query: `?page&per_page&sort_by&order&min_price&max_price&name`
- **PUT** `/update/<id>` — Body: `{ "name", "description", "price" }` — Update product
- **DELETE** `/delete/<id>` — Soft delete

---

## 🔍 SEARCH

- **GET** `/search` — Query: `?name&description&min_price&max_price&sort_by&order&page&per_page`

---

## 🛒 ORDERS

- **POST** `/orders` — Body: `{ "items": [{ "product_id", "quantity" }] }` — Create order
- **GET** `/orders` — Query: `?page&per_page` — List orders
- **GET** `/orders/<id>` — Order detail
- **PUT** `/orders/<id>/cancel` — Cancel order

---

## 💳 PAYMENTS

- **POST** `/payments` — Body: `{ "order_id", "payment_method" }` — Pay (card/cash/bank_transfer)
- **GET** `/payments` — Query: `?page&per_page` — List (Admin)

---

## 📊 REPORTS (Admin)

- **GET** `/reports/monthly-sales` — Query: `?year&month` — Stored Procedure
- **GET** `/reports/sales-summary` — Query: `?year&month` — Python Query

---

## 📝 AUDIT LOGS (Admin)

- **GET** `/audit-logs` — Query: `?page&per_page&table&action`

---

## 🔑 HEADERS

```
Authorization: Bearer <token>
Content-Type: application/json
```

---

## 👥 ROLES

- **user** → Orders, Payments (own only)
- **admin** → Everything + Reports + Logs

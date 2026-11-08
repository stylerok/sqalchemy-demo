# SQLAlchemy Store Dashboard

A command-line store management application built with Python, SQLAlchemy, and PostgreSQL.

## Features

- Display total users, products, and orders.
- View the product catalog.
- Show the top 3 customers by total items ordered.
- Add new products.
- Place orders and automatically update product stock.
- Prevent orders when stock is insufficient.
- Display low-stock products.
- Calculate revenue by product.
- Find users without orders.

## Technologies

- Python
- SQLAlchemy
- PostgreSQL
- python-dotenv

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project directory.

3. Add your database connection:

```env
DATABASE_URL=your_database_url
```

4. Run the application:

```bash
python dashboard.py
```

## Project Purpose

This project was created as part of SQLAlchemy and database programming practice.
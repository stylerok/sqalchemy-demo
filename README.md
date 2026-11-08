# SQLAlchemy Store Dashboard

This is a small Python project for working with a store database.

I created this project to practice Python, SQLAlchemy and PostgreSQL.

## Technologies

- Python
- SQLAlchemy
- PostgreSQL
- python-dotenv

## Project Features

The program can:

- Show the number of users, products and orders.
- Display the product list.
- Show the top 3 customers by order amount.
- Add a new product to the database.
- Create an order and update product stock.
- Check if there is enough stock before creating an order.
- Show products with low stock.
- Calculate revenue for each product.
- Find users who have not placed any orders.

## Installation

Clone the repository:

```bash
git clone https://github.com/stylerok/sqalchemy-demo.git
cd sqalchemy-demo
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the required packages:

```bash
python -m pip install -r requirements.txt
```

## Database Configuration

Create a `.env` file in the project folder.

Copy the example configuration:

```powershell
Copy-Item .env.example .env
```

Open `.env` and add your PostgreSQL connection string:

```env
DATABASE_URL=postgresql+psycopg2://username:password@localhost:5432/database_name
```

Replace the example values with your database username, password and database name.

Do not upload the `.env` file to GitHub because it contains private connection information.

## Run the Project

Start the program:

```bash
python dashboard.py
```

The program connects to PostgreSQL and displays the store dashboard in the terminal.

## Notes

This project was made as part of my Python and SQLAlchemy learning.

The main goal was to practice database queries, transactions and working with product and order data.

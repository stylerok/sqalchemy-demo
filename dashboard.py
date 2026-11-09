import os
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

LOW_STOCK_LIMIT = 10
TOP_CUSTOMERS_LIMIT = 3


def get_engine():
    """Create and return a SQLAlchemy engine from DATABASE_URL."""
    url = os.getenv("DATABASE_URL")

    if not url:
        raise ValueError("DATABASE_URL is missing in .env file")

    return create_engine(url, pool_pre_ping=True)


# ---------- Reports ----------

def get_counts(conn):
    return {
        table: conn.execute(
            text(f"SELECT COUNT(*) FROM {table}")
        ).scalar()
        for table in ("users", "products", "orders")
    }


def get_catalog(conn):
    return conn.execute(text("""
        SELECT name, price, stock
        FROM products
        ORDER BY name
    """)).fetchall()


def get_top_customers(conn):
    return conn.execute(
        text("""
            SELECT users.email, SUM(orders.quantity) AS total_items
            FROM users
            JOIN orders ON users.id = orders.user_id
            GROUP BY users.id, users.email
            ORDER BY total_items DESC
            LIMIT :limit
        """),
        {"limit": TOP_CUSTOMERS_LIMIT},
    ).fetchall()


def get_low_stock(conn):
    return conn.execute(
        text("""
            SELECT name, stock
            FROM products
            WHERE stock < :limit
            ORDER BY stock, name
        """),
        {"limit": LOW_STOCK_LIMIT},
    ).fetchall()


def get_revenue(conn):
    return conn.execute(text("""
        SELECT products.name,
               COALESCE(SUM(products.price * orders.quantity), 0) AS revenue
        FROM products
        LEFT JOIN orders
            ON orders.product_id = products.id
        GROUP BY products.id, products.name
        ORDER BY revenue DESC
    """)).fetchall()


def get_users_without_orders(conn):
    return conn.execute(text("""
        SELECT users.email
        FROM users
        LEFT JOIN orders ON orders.user_id = users.id
        WHERE orders.id IS NULL
        ORDER BY users.id
    """)).fetchall()


def print_section(title, rows, formatter, empty_message):
    print(f"\n{title}:")

    if not rows:
        print(f"  {empty_message}")

    for row in rows:
        print(f"  {formatter(row)}")


def store_report(engine):
    """Print counts, catalog, top customers, and additional reports."""

    with engine.connect() as conn:
        counts = get_counts(conn)
        catalog = get_catalog(conn)
        top_customers = get_top_customers(conn)
        low_stock = get_low_stock(conn)
        revenue = get_revenue(conn)
        no_orders = get_users_without_orders(conn)

    print("\n=== Store Dashboard ===")

    print(
        f"Users: {counts['users']} | "
        f"Products: {counts['products']} | "
        f"Orders: {counts['orders']}"
    )

    print_section(
        "Catalog",
        catalog,
        lambda p: f"{p.name}  ${p.price}  (stock {p.stock})",
        "No products yet",
    )

    print_section(
        "Top customers",
        top_customers,
        lambda c: f"{c.email} - {c.total_items} items",
        "No orders yet",
    )

    print_section(
        "Low stock products",
        low_stock,
        lambda p: f"{p.name} - stock {p.stock}",
        "No products with low stock",
    )

    print_section(
        "Revenue per product",
        revenue,
        lambda p: f"{p.name} - ${p.revenue:.2f}",
        "No products yet",
    )

    print_section(
        "Users without orders",
        no_orders,
        lambda u: u.email,
        "All users have placed orders",
    )


# ---------- Actions ----------

def add_product(engine, name, category, price, stock):
    """Insert a new product and return its id."""

    name = name.strip()
    category = category.strip()

    if not name:
        raise ValueError("Product name cannot be empty")

    if not category:
        raise ValueError("Category cannot be empty")

    if price < 0:
        raise ValueError("Price cannot be negative")

    if stock < 0:
        raise ValueError("Stock cannot be negative")

    with engine.begin() as conn:
        product_id = conn.execute(
            text("""
                INSERT INTO products (name, category, price, stock)
                VALUES (:name, :category, :price, :stock)
                RETURNING id
            """),
            {
                "name": name,
                "category": category,
                "price": price,
                "stock": stock,
            },
        ).scalar_one()

    return product_id


def place_order(engine, email, product_name, quantity):
    """Create an order and decrease stock in one transaction."""

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero")

    with engine.begin() as conn:

        user_id = conn.execute(
            text("""
                SELECT id
                FROM users
                WHERE lower(email) = lower(:email)
            """),
            {"email": email.strip()},
        ).scalar_one_or_none()

        if user_id is None:
            raise ValueError("User not found")

        # Lock the product row to prevent simultaneous orders
        # from reducing stock below zero.
        product = conn.execute(
            text("""
                SELECT id, stock
                FROM products
                WHERE name = :name
                FOR UPDATE
            """),
            {"name": product_name.strip()},
        ).mappings().one_or_none()

        if product is None:
            raise ValueError("Product not found")

        if product["stock"] < quantity:
            raise ValueError(
                f"Not enough stock. Available: {product['stock']}"
            )

        order_id = conn.execute(
            text("""
                INSERT INTO orders (user_id, product_id, quantity, status)
                VALUES (:user_id, :product_id, :quantity, 'pending')
                RETURNING id
            """),
            {
                "user_id": user_id,
                "product_id": product["id"],
                "quantity": quantity,
            },
        ).scalar_one()

        conn.execute(
            text("""
                UPDATE products
                SET stock = stock - :qty
                WHERE id = :id
            """),
            {
                "qty": quantity,
                "id": product["id"],
            },
        )

    return order_id


# ---------- Menu ----------

def read_price(prompt):
    try:
        price = Decimal(input(prompt))
    except InvalidOperation:
        raise ValueError("Price must be a number")

    if not price.is_finite():
        raise ValueError("Price must be a finite number")

    return price


def handle_add_product(engine):
    name = input("Product name: ")
    category = input("Category: ")
    price = read_price("Price: ")
    stock = int(input("Stock quantity: "))

    product_id = add_product(
        engine,
        name,
        category,
        price,
        stock,
    )

    print(f"\nProduct added. ID: {product_id}")


def handle_place_order(engine):
    email = input("Customer email: ")
    product_name = input("Product name: ")
    quantity = int(input("Quantity: "))

    order_id = place_order(
        engine,
        email,
        product_name,
        quantity,
    )

    print(f"\nOrder created. ID: {order_id}")


def main():
    try:
        engine = get_engine()
        store_report(engine)

    except (ValueError, SQLAlchemyError) as error:
        print("\nDatabase error:", error)
        return

    actions = {
        "1": handle_add_product,
        "2": handle_place_order,
        "3": store_report,
    }

    while True:
        print("\n=== Store Menu ===")
        print("1. Add product")
        print("2. Place order")
        print("3. Show report")
        print("0. Exit")

        choice = input("\nChoose an option: ").strip()

        if choice == "0":
            print("Goodbye!")
            break

        action = actions.get(choice)

        if action is None:
            print("Invalid option. Try again.")
            continue

        try:
            action(engine)

        except ValueError as error:
            print("\nInput error:", error)

        except SQLAlchemyError as error:
            print("\nDatabase error:", error)


if __name__ == "__main__":
    main()
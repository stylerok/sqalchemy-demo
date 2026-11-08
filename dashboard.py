
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


load_dotenv()


def get_engine():
    """Create and return a database engine."""

    url = os.getenv("DATABASE_URL")

    if not url:
        raise ValueError("DATABASE_URL is missing in .env file")

    return create_engine(url)


def store_report(engine):
    """Print store statistics and reports."""

    with engine.connect() as conn:

        users_count = conn.execute(
            text("SELECT COUNT(*) FROM users")
        ).scalar()

        products_count = conn.execute(
            text("SELECT COUNT(*) FROM products")
        ).scalar()

        orders_count = conn.execute(
            text("SELECT COUNT(*) FROM orders")
        ).scalar()

        products = conn.execute(
            text("""
                SELECT name, price, stock
                FROM products
                ORDER BY name
            """)
        ).fetchall()

        top_customers = conn.execute(
            text("""
                SELECT users.email, SUM(orders.quantity) AS total_items
                FROM users
                JOIN orders ON users.id = orders.user_id
                GROUP BY users.id, users.email
                ORDER BY total_items DESC
                LIMIT 3
            """)
        ).fetchall()

        low_stock = conn.execute(
            text("""
                SELECT name, stock
                FROM products
                WHERE stock < 10
                ORDER BY stock ASC
            """)
        ).fetchall()

        product_revenue = conn.execute(
            text("""
                SELECT
                    products.name,
                    COALESCE(
                        SUM(products.price * orders.quantity),
                        0
                    ) AS revenue
                FROM products
                LEFT JOIN orders
                    ON products.id = orders.product_id
                GROUP BY products.id, products.name
                ORDER BY revenue DESC
            """)
        ).fetchall()

        users_without_orders = conn.execute(
            text("""
                SELECT users.id, users.email
                FROM users
                LEFT JOIN orders
                    ON users.id = orders.user_id
                WHERE orders.id IS NULL
                ORDER BY users.id
            """)
        ).fetchall()

        print("\n=== Store Dashboard ===")

        print(
            f"Users: {users_count} | "
            f"Products: {products_count} | "
            f"Orders: {orders_count}"
        )

        print("\nCatalog:")

        for product in products:
            print(
                f"  {product.name}   "
                f"${product.price}   "
                f"(stock {product.stock})"
            )

        print("\nTop customers:")

        for customer in top_customers:
            print(
                f"  {customer.email} - "
                f"{customer.total_items} items"
            )

        print("\nLow stock products:")

        if low_stock:
            for product in low_stock:
                print(
                    f"  {product.name} - "
                    f"stock {product.stock}"
                )
        else:
            print("  No products with low stock")

        print("\nRevenue per product:")

        for product in product_revenue:
            print(
                f"  {product.name} - "
                f"${product.revenue:.2f}"
            )

        print("\nUsers without orders:")

        if users_without_orders:
            for user in users_without_orders:
                print(f"  {user.email}")
        else:
            print("  All users have placed orders")


def add_product(engine, name, category, price, stock):
    """Insert a new product and return its ID."""

    if not name.strip():
        raise ValueError("Product name cannot be empty")

    if not category.strip():
        raise ValueError("Category cannot be empty")

    if price < 0:
        raise ValueError("Price cannot be negative")

    if stock < 0:
        raise ValueError("Stock cannot be negative")

    with engine.begin() as conn:

        result = conn.execute(
            text("""
                INSERT INTO products (name, category, price, stock)
                VALUES (:name, :category, :price, :stock)
                RETURNING id
            """),
            {
                "name": name.strip(),
                "category": category.strip(),
                "price": price,
                "stock": stock,
            }
        )

        product_id = result.scalar_one()

    return product_id


def place_order(engine, email, product_name, quantity):
    """Create an order and decrease product stock in one transaction."""

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero")

    with engine.begin() as conn:

        user_id = conn.execute(
            text("""
                SELECT id
                FROM users
                WHERE email = :email
            """),
            {"email": email.strip()}
        ).scalar_one_or_none()

        if user_id is None:
            raise ValueError("User not found")

        product = conn.execute(
            text("""
                SELECT id, stock
                FROM products
                WHERE name = :product_name
                FOR UPDATE
            """),
            {"product_name": product_name.strip()}
        ).mappings().one_or_none()

        if product is None:
            raise ValueError("Product not found")

        if product["stock"] < quantity:
            raise ValueError(
                f"Not enough stock. Available: {product['stock']}"
            )

        order_id = conn.execute(
            text("""
                INSERT INTO orders (
                    user_id,
                    product_id,
                    quantity,
                    status
                )
                VALUES (
                    :user_id,
                    :product_id,
                    :quantity,
                    :status
                )
                RETURNING id
            """),
            {
                "user_id": user_id,
                "product_id": product["id"],
                "quantity": quantity,
                "status": "pending",
            }
        ).scalar_one()

        conn.execute(
            text("""
                UPDATE products
                SET stock = stock - :quantity
                WHERE id = :product_id
            """),
            {
                "quantity": quantity,
                "product_id": product["id"],
            }
        )

    return order_id


def main():

    try:
        engine = get_engine()
        store_report(engine)

    except (ValueError, SQLAlchemyError) as error:
        print("\nDatabase error:", error)
        return

    while True:

        print("\n=== Store Menu ===")
        print("1. Add product")
        print("2. Place order")
        print("0. Exit")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":

            try:
                name = input("Product name: ").strip()
                category = input("Category: ").strip()
                price = float(input("Price: "))
                stock = int(input("Stock quantity: "))

                product_id = add_product(
                    engine,
                    name,
                    category,
                    price,
                    stock
                )

                print("\nProduct added successfully!")
                print("Product ID:", product_id)

            except ValueError as error:
                print("\nInput error:", error)

            except SQLAlchemyError as error:
                print("\nDatabase error:", error)

        elif choice == "2":

            try:
                email = input("Customer email: ").strip()
                product_name = input("Product name: ").strip()
                quantity = int(input("Quantity: "))

                order_id = place_order(
                    engine,
                    email,
                    product_name,
                    quantity
                )

                print("\nOrder created successfully!")
                print("Order ID:", order_id)

            except ValueError as error:
                print("\nOrder error:", error)

            except SQLAlchemyError as error:
                print("\nDatabase error:", error)

        elif choice == "0":
            print("Goodbye!")
            break

        else:
            print("Invalid option. Try again.")


if __name__ == "__main__":
    main()

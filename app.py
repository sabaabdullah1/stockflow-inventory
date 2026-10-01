from flask import Flask, render_template, request, jsonify, Response
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import csv
import io
from datetime import datetime, timezone


app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")


# ========================================
# DATABASE HELPERS
# ========================================

def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set."
        )

    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor,
        connect_timeout=10
        
    )


def execute(connection, query, params=()):
    cursor = connection.cursor()
    cursor.execute(query, params)
    return cursor


def time_ago(timestamp):
    if not timestamp:
        return ""

    if isinstance(timestamp, str):
        try:
            activity_time = datetime.fromisoformat(timestamp)
        except ValueError:
            activity_time = datetime.strptime(
                timestamp,
                "%Y-%m-%d %H:%M:%S"
            )
    else:
        activity_time = timestamp

    if activity_time.tzinfo is not None:
        now = datetime.now(timezone.utc)
        activity_time = activity_time.astimezone(timezone.utc)
    else:
        now = datetime.utcnow()

    difference = now - activity_time
    seconds = difference.total_seconds()

    if seconds < 60:
        return "Just now"

    minutes = int(seconds // 60)

    if minutes < 60:
        return (
            "1 min ago"
            if minutes == 1
            else f"{minutes} min ago"
        )

    hours = int(minutes // 60)

    if hours < 24:
        return (
            "1 hour ago"
            if hours == 1
            else f"{hours} hours ago"
        )

    days = int(hours // 24)

    if days == 1:
        return "Yesterday"

    if days < 7:
        return f"{days} days ago"

    return activity_time.strftime("%b %d, %Y")


def log_activity(
    connection,
    product_id,
    action,
    product_name,
    details
):
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO activity_log
        (product_id, action, product_name, details)
        VALUES (%s, %s, %s, %s)
    """, (
        product_id,
        action,
        product_name,
        details
    ))

    cursor.close()


# ========================================
# DATABASE SETUP
# ========================================

def create_database():
    connection = get_db_connection()
    cursor = connection.cursor()

    # Products
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            price DOUBLE PRECISION NOT NULL DEFAULT 0,
            supplier TEXT,
            status TEXT NOT NULL DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Categories
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Suppliers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Activity Log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id SERIAL PRIMARY KEY,
            product_id INTEGER,
            action TEXT NOT NULL,
            product_name TEXT,
            details TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration safety
    cursor.execute("""
        ALTER TABLE activity_log
        ADD COLUMN IF NOT EXISTS product_id INTEGER
    """)

    # Connect older history records
    cursor.execute("""
        UPDATE activity_log
        SET product_id = (
            SELECT products.id
            FROM products
            WHERE products.name = activity_log.product_name
            LIMIT 1
        )
        WHERE product_id IS NULL
    """)

    # Copy existing categories
    cursor.execute("""
        INSERT INTO categories (name)
        SELECT DISTINCT category
        FROM products
        WHERE category IS NOT NULL
        AND TRIM(category) != ''
        ON CONFLICT (name) DO NOTHING
    """)

    # Copy existing suppliers
    cursor.execute("""
        INSERT INTO suppliers (name)
        SELECT DISTINCT supplier
        FROM products
        WHERE supplier IS NOT NULL
        AND TRIM(supplier) != ''
        ON CONFLICT (name) DO NOTHING
    """)

    connection.commit()
    cursor.close()
    connection.close()


# ========================================
# DASHBOARD
# ========================================

@app.route("/")
def home():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM products
        ORDER BY id DESC
    """)
    products = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM activity_log
        ORDER BY id DESC
        LIMIT 5
    """)
    activities = cursor.fetchall()

    cursor.close()
    connection.close()

    activities = [
        {
            **dict(activity),
            "time_ago": time_ago(activity["created_at"])
        }
        for activity in activities
    ]

    inventory_value = sum(
        product["quantity"] * product["price"]
        for product in products
    )

    categories = {}

    for product in products:
        category = product["category"]
        categories[category] = (
            categories.get(category, 0) + 1
        )

    return render_template(
        "index.html",
        products=products,
        inventory_value=inventory_value,
        category_names=list(categories.keys()),
        category_counts=list(categories.values()),
        activities=activities
    )


# ========================================
# PRODUCTS
# ========================================

@app.route("/products")
def products_page():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM products
        ORDER BY id DESC
    """)
    products = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM categories
        ORDER BY name
    """)
    categories = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM suppliers
        ORDER BY name
    """)
    suppliers = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "products.html",
        products=products,
        categories=categories,
        suppliers=suppliers
    )


# ========================================
# ADD PRODUCT
# ========================================

@app.route("/api/products", methods=["POST"])
def add_product():
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    category = data.get("category", "").strip()
    supplier = data.get("supplier", "").strip()

    try:
        quantity = int(data.get("quantity", 0))
        price = float(data.get("price", 0))
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message":
                "Quantity and price must be valid numbers."
        }), 400

    if not name or not category:
        return jsonify({
            "success": False,
            "message":
                "Product name and category are required."
        }), 400

    if quantity < 0 or price < 0:
        return jsonify({
            "success": False,
            "message":
                "Quantity and price cannot be negative."
        }), 400

    status = (
        "Low Stock"
        if quantity <= 5
        else "Active"
    )

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO products
        (
            name,
            category,
            quantity,
            price,
            supplier,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        name,
        category,
        quantity,
        price,
        supplier,
        status
    ))

    product_id = cursor.fetchone()["id"]

    log_activity(
        connection,
        product_id,
        "Product Added",
        name,
        f"{name} was added with {quantity} units."
    )

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({
        "success": True,
        "id": product_id,
        "message": "Product added successfully."
    })


# ========================================
# UPDATE PRODUCT
# ========================================

@app.route(
    "/api/products/<int:product_id>",
    methods=["PUT"]
)
def update_product(product_id):
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    category = data.get("category", "").strip()
    supplier = data.get("supplier", "").strip()

    try:
        quantity = int(data.get("quantity", 0))
        price = float(data.get("price", 0))
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message":
                "Quantity and price must be valid numbers."
        }), 400

    if not name or not category:
        return jsonify({
            "success": False,
            "message":
                "Product name and category are required."
        }), 400

    if quantity < 0 or price < 0:
        return jsonify({
            "success": False,
            "message":
                "Quantity and price cannot be negative."
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM products
        WHERE id = %s
    """, (product_id,))

    old_product = cursor.fetchone()

    if not old_product:
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message": "Product not found."
        }), 404

    old_quantity = old_product["quantity"]

    status = (
        "Low Stock"
        if quantity <= 5
        else "Active"
    )

    cursor.execute("""
        UPDATE products
        SET name = %s,
            category = %s,
            quantity = %s,
            price = %s,
            supplier = %s,
            status = %s
        WHERE id = %s
    """, (
        name,
        category,
        quantity,
        price,
        supplier,
        status,
        product_id
    ))

    if quantity > old_quantity:
        action = "Product Restocked"
        details = (
            f"{name} restocked from "
            f"{old_quantity} to {quantity} units."
        )

    elif quantity < old_quantity:
        action = "Stock Updated"
        details = (
            f"{name} stock changed from "
            f"{old_quantity} to {quantity} units."
        )

    else:
        action = "Product Updated"
        details = (
            f"{name} information was updated."
        )

    log_activity(
        connection,
        product_id,
        action,
        name,
        details
    )

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({
        "success": True,
        "message": "Product updated successfully."
    })


# ========================================
# STOCK MOVEMENT
# ========================================

@app.route(
    "/api/products/<int:product_id>/stock",
    methods=["POST"]
)
def update_stock(product_id):
    data = request.get_json() or {}

    movement_type = (
        data.get("type", "")
        .strip()
        .lower()
    )

    try:
        amount = int(data.get("amount", 0))
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message":
                "Quantity must be a valid number."
        }), 400

    if movement_type not in ["in", "out"]:
        return jsonify({
            "success": False,
            "message":
                "Invalid stock movement type."
        }), 400

    if amount <= 0:
        return jsonify({
            "success": False,
            "message":
                "Quantity must be greater than zero."
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM products
        WHERE id = %s
        FOR UPDATE
    """, (product_id,))

    product = cursor.fetchone()

    if not product:
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message": "Product not found."
        }), 404

    old_quantity = product["quantity"]
    product_name = product["name"]

    unit_word = (
        "unit"
        if amount == 1
        else "units"
    )

    if movement_type == "in":
        new_quantity = old_quantity + amount

        action = "Stock In"

        details = (
            f"{amount} {unit_word} added. "
            f"Stock changed from "
            f"{old_quantity} to "
            f"{new_quantity} units."
        )

    else:
        if amount > old_quantity:
            cursor.close()
            connection.close()

            available_word = (
                "unit"
                if old_quantity == 1
                else "units"
            )

            return jsonify({
                "success": False,
                "message":
                    f"Not enough stock. "
                    f"Only {old_quantity} "
                    f"{available_word} available."
            }), 400

        new_quantity = old_quantity - amount

        action = "Stock Out"

        details = (
            f"{amount} {unit_word} removed. "
            f"Stock changed from "
            f"{old_quantity} to "
            f"{new_quantity} units."
        )

    status = (
        "Low Stock"
        if new_quantity <= 5
        else "Active"
    )

    cursor.execute("""
        UPDATE products
        SET quantity = %s,
            status = %s
        WHERE id = %s
    """, (
        new_quantity,
        status,
        product_id
    ))

    log_activity(
        connection,
        product_id,
        action,
        product_name,
        details
    )

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({
        "success": True,
        "message": (
            "Stock added successfully."
            if movement_type == "in"
            else "Stock removed successfully."
        ),
        "quantity": new_quantity,
        "status": status
    })


# ========================================
# DELETE PRODUCT
# ========================================

@app.route(
    "/api/products/<int:product_id>",
    methods=["DELETE"]
)
def delete_product(product_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM products
        WHERE id = %s
    """, (product_id,))

    product = cursor.fetchone()

    if not product:
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message": "Product not found."
        }), 404

    product_name = product["name"]

    log_activity(
        connection,
        product_id,
        "Product Deleted",
        product_name,
        f"{product_name} was removed from inventory."
    )

    cursor.execute(
        "DELETE FROM products WHERE id = %s",
        (product_id,)
    )

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({
        "success": True,
        "message": "Product deleted successfully."
    })


# ========================================
# PRODUCT HISTORY
# ========================================

@app.route(
    "/api/products/<int:product_id>/history",
    methods=["GET"]
)
def product_history(product_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM products
        WHERE id = %s
    """, (product_id,))

    product = cursor.fetchone()

    if not product:
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message": "Product not found."
        }), 404

    cursor.execute("""
        SELECT *
        FROM activity_log
        WHERE product_id = %s
        ORDER BY id DESC
    """, (product_id,))

    activities = cursor.fetchall()

    cursor.close()
    connection.close()

    history = [
        {
            "id": activity["id"],
            "action": activity["action"],
            "details": activity["details"],
            "time": time_ago(
                activity["created_at"]
            )
        }
        for activity in activities
    ]

    return jsonify({
        "success": True,
        "product": product["name"],
        "history": history
    })


# ========================================
# CATEGORIES
# ========================================

@app.route("/categories")
def categories():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            c.id,
            c.name AS category,
            COUNT(p.id) AS product_count,
            COALESCE(
                SUM(p.quantity),
                0
            ) AS total_stock,
            COALESCE(
                SUM(p.quantity * p.price),
                0
            ) AS total_value
        FROM categories c
        LEFT JOIN products p
            ON p.category = c.name
        GROUP BY c.id, c.name
        ORDER BY c.name
    """)

    category_list = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "categories.html",
        categories=category_list
    )


@app.route(
    "/api/categories",
    methods=["POST"]
)
def add_category():
    data = request.get_json() or {}
    name = data.get("name", "").strip()

    if not name:
        return jsonify({
            "success": False,
            "message":
                "Category name is required."
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO categories (name)
            VALUES (%s)
            RETURNING id
        """, (name,))

        category_id = cursor.fetchone()["id"]

        connection.commit()

    except psycopg2.IntegrityError:
        connection.rollback()
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message":
                "This category already exists."
        }), 400

    cursor.close()
    connection.close()

    return jsonify({
        "success": True,
        "id": category_id,
        "message":
            "Category added successfully."
    })


@app.route(
    "/api/categories/<int:category_id>",
    methods=["PUT"]
)
def update_category(category_id):
    data = request.get_json() or {}

    new_name = (
        data.get("name", "")
        .strip()
    )

    if not new_name:
        return jsonify({
            "success": False,
            "message":
                "Category name is required."
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM categories
        WHERE id = %s
    """, (category_id,))

    category = cursor.fetchone()

    if not category:
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message": "Category not found."
        }), 404

    old_name = category["name"]

    try:
        cursor.execute("""
            UPDATE categories
            SET name = %s
            WHERE id = %s
        """, (
            new_name,
            category_id
        ))

        cursor.execute("""
            UPDATE products
            SET category = %s
            WHERE category = %s
        """, (
            new_name,
            old_name
        ))

        connection.commit()

    except psycopg2.IntegrityError:
        connection.rollback()
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message":
                "This category already exists."
        }), 400

    cursor.close()
    connection.close()

    return jsonify({
        "success": True,
        "message":
            "Category updated successfully."
    })


@app.route(
    "/api/categories/<int:category_id>",
    methods=["DELETE"]
)
def delete_category(category_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM categories
        WHERE id = %s
    """, (category_id,))

    category = cursor.fetchone()

    if not category:
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message": "Category not found."
        }), 404

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM products
        WHERE category = %s
    """, (category["name"],))

    product_count = (
        cursor.fetchone()["count"]
    )

    if product_count > 0:
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message":
                "This category cannot be deleted "
                "because it contains products."
        }), 400

    cursor.execute(
        "DELETE FROM categories WHERE id = %s",
        (category_id,)
    )

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({
        "success": True,
        "message":
            "Category deleted successfully."
    })


# ========================================
# SUPPLIERS
# ========================================

@app.route("/suppliers")
def suppliers():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            s.id,
            s.name AS supplier,
            COUNT(p.id) AS product_count,
            COALESCE(
                SUM(p.quantity),
                0
            ) AS total_stock,
            COALESCE(
                SUM(p.quantity * p.price),
                0
            ) AS total_value
        FROM suppliers s
        LEFT JOIN products p
            ON p.supplier = s.name
        GROUP BY s.id, s.name
        ORDER BY s.name
    """)

    supplier_list = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "suppliers.html",
        suppliers=supplier_list
    )


@app.route(
    "/api/suppliers",
    methods=["POST"]
)
def add_supplier():
    data = request.get_json() or {}
    name = data.get("name", "").strip()

    if not name:
        return jsonify({
            "success": False,
            "message":
                "Supplier name is required."
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id
        FROM suppliers
        WHERE LOWER(name) = LOWER(%s)
    """, (name,))

    existing_supplier = cursor.fetchone()

    if existing_supplier:
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message":
                "This supplier already exists."
        }), 400

    cursor.execute("""
        INSERT INTO suppliers (name)
        VALUES (%s)
        RETURNING id
    """, (name,))

    supplier_id = cursor.fetchone()["id"]

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({
        "success": True,
        "id": supplier_id,
        "message":
            "Supplier added successfully."
    })


@app.route(
    "/api/suppliers/<int:supplier_id>",
    methods=["PUT"]
)
def update_supplier(supplier_id):
    data = request.get_json() or {}

    new_name = (
        data.get("name", "")
        .strip()
    )

    if not new_name:
        return jsonify({
            "success": False,
            "message":
                "Supplier name is required."
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM suppliers
        WHERE id = %s
    """, (supplier_id,))

    supplier = cursor.fetchone()

    if not supplier:
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message": "Supplier not found."
        }), 404

    cursor.execute("""
        SELECT id
        FROM suppliers
        WHERE LOWER(name) = LOWER(%s)
        AND id != %s
    """, (
        new_name,
        supplier_id
    ))

    existing = cursor.fetchone()

    if existing:
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message":
                "This supplier already exists."
        }), 400

    old_name = supplier["name"]

    cursor.execute("""
        UPDATE suppliers
        SET name = %s
        WHERE id = %s
    """, (
        new_name,
        supplier_id
    ))

    cursor.execute("""
        UPDATE products
        SET supplier = %s
        WHERE supplier = %s
    """, (
        new_name,
        old_name
    ))

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({
        "success": True,
        "message":
            "Supplier updated successfully."
    })


@app.route(
    "/api/suppliers/<int:supplier_id>",
    methods=["DELETE"]
)
def delete_supplier(supplier_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM suppliers
        WHERE id = %s
    """, (supplier_id,))

    supplier = cursor.fetchone()

    if not supplier:
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message": "Supplier not found."
        }), 404

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM products
        WHERE supplier = %s
    """, (supplier["name"],))

    product_count = (
        cursor.fetchone()["count"]
    )

    if product_count > 0:
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message":
                "This supplier cannot be deleted "
                "because it contains products."
        }), 400

    cursor.execute(
        "DELETE FROM suppliers WHERE id = %s",
        (supplier_id,)
    )

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({
        "success": True,
        "message":
            "Supplier deleted successfully."
    })


# ========================================
# REPORTS
# ========================================

@app.route("/reports")
def reports_page():
    return render_template("reports.html")


@app.route(
    "/api/reports",
    methods=["GET"]
)
def reports_data():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM products
        ORDER BY name
    """)

    products = cursor.fetchall()

    cursor.close()
    connection.close()

    total_products = len(products)

    total_stock = sum(
        product["quantity"]
        for product in products
    )

    inventory_value = sum(
        product["quantity"]
        * product["price"]
        for product in products
    )

    low_stock_count = sum(
        1
        for product in products
        if product["quantity"] <= 5
    )

    healthy_stock_count = (
        total_products - low_stock_count
    )

    category_counts = {}
    category_values = {}

    for product in products:
        category = product["category"]

        if category not in category_counts:
            category_counts[category] = 0
            category_values[category] = 0

        category_counts[category] += 1

        category_values[category] += (
            product["quantity"]
            * product["price"]
        )

    product_names = [
        product["name"]
        for product in products
    ]

    product_quantities = [
        product["quantity"]
        for product in products
    ]

    return jsonify({
        "total_products":
            total_products,

        "total_stock":
            total_stock,

        "inventory_value":
            round(inventory_value, 2),

        "low_stock_count":
            low_stock_count,

        "category_names":
            list(category_counts.keys()),

        "category_counts":
            list(category_counts.values()),

        "category_value_names":
            list(category_values.keys()),

        "category_values": [
            round(value, 2)
            for value in category_values.values()
        ],

        "product_names":
            product_names,

        "product_quantities":
            product_quantities,

        "stock_health_labels": [
            "Healthy Stock",
            "Low Stock"
        ],

        "stock_health_counts": [
            healthy_stock_count,
            low_stock_count
        ]
    })


# ========================================
# EXPORT CSV
# ========================================

@app.route("/export/csv")
def export_csv():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM products
        ORDER BY id DESC
    """)

    products = cursor.fetchall()

    cursor.close()
    connection.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Product",
        "Category",
        "Quantity",
        "Price",
        "Supplier",
        "Status"
    ])

    for product in products:
        writer.writerow([
            product["name"],
            product["category"],
            product["quantity"],
            product["price"],
            product["supplier"],
            product["status"]
        ])

    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; "
                "filename=inventory_report.csv"
        }
    )


# ========================================
# INITIALIZE DATABASE
# ========================================

create_database()


# ========================================
# START APPLICATION
# ========================================

if __name__ == "__main__":
    app.run(
        debug=True,
        port=5001
    )
from flask import Flask, render_template, request, jsonify, Response
import sqlite3
import csv
import io
from datetime import datetime


app = Flask(__name__)
DATABASE = "inventory.db"


# ========================================
# DATABASE HELPERS
# ========================================

def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def time_ago(timestamp):
    if not timestamp:
        return ""

    activity_time = datetime.strptime(
        timestamp,
        "%Y-%m-%d %H:%M:%S"
    )

    difference = datetime.utcnow() - activity_time
    seconds = difference.total_seconds()

    if seconds < 60:
        return "Just now"

    minutes = int(seconds // 60)

    if minutes < 60:
        return "1 min ago" if minutes == 1 else f"{minutes} min ago"

    hours = int(minutes // 60)

    if hours < 24:
        return "1 hour ago" if hours == 1 else f"{hours} hours ago"

    days = int(hours // 24)

    if days == 1:
        return "Yesterday"

    if days < 7:
        return f"{days} days ago"

    return activity_time.strftime("%b %d, %Y")


def log_activity(connection, product_id, action, product_name, details):
    """Save a product activity to the activity log."""

    connection.execute("""
        INSERT INTO activity_log
        (product_id, action, product_name, details)
        VALUES (?, ?, ?, ?)
    """, (
        product_id,
        action,
        product_name,
        details
    ))


# ========================================
# DATABASE SETUP
# ========================================

def create_database():
    connection = get_db_connection()

    # Products
    connection.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            price REAL NOT NULL DEFAULT 0,
            supplier TEXT,
            status TEXT NOT NULL DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Categories
    connection.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Suppliers
    connection.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Activity Log
    connection.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            action TEXT NOT NULL,
            product_name TEXT,
            details TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration for databases created before product_id existed
    activity_columns = connection.execute(
        "PRAGMA table_info(activity_log)"
    ).fetchall()

    activity_column_names = [
        column["name"]
        for column in activity_columns
    ]

    if "product_id" not in activity_column_names:
        connection.execute("""
            ALTER TABLE activity_log
            ADD COLUMN product_id INTEGER
        """)

    # Connect old history records to current products
    connection.execute("""
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
    connection.execute("""
        INSERT OR IGNORE INTO categories (name)
        SELECT DISTINCT category
        FROM products
        WHERE category IS NOT NULL
        AND TRIM(category) != ''
    """)

    # Copy existing suppliers
    connection.execute("""
        INSERT OR IGNORE INTO suppliers (name)
        SELECT DISTINCT supplier
        FROM products
        WHERE supplier IS NOT NULL
        AND TRIM(supplier) != ''
    """)

    connection.commit()
    connection.close()


# ========================================
# DASHBOARD
# ========================================

@app.route("/")
def home():
    connection = get_db_connection()

    products = connection.execute("""
        SELECT *
        FROM products
        ORDER BY id DESC
    """).fetchall()

    activities = connection.execute("""
        SELECT *
        FROM activity_log
        ORDER BY id DESC
        LIMIT 5
    """).fetchall()

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
        categories[category] = categories.get(category, 0) + 1

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

    products = connection.execute("""
        SELECT *
        FROM products
        ORDER BY id DESC
    """).fetchall()

    categories = connection.execute("""
        SELECT *
        FROM categories
        ORDER BY name
    """).fetchall()

    suppliers = connection.execute("""
        SELECT *
        FROM suppliers
        ORDER BY name
    """).fetchall()

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
            "message": "Quantity and price must be valid numbers."
        }), 400

    if not name or not category:
        return jsonify({
            "success": False,
            "message": "Product name and category are required."
        }), 400

    if quantity < 0 or price < 0:
        return jsonify({
            "success": False,
            "message": "Quantity and price cannot be negative."
        }), 400

    status = "Low Stock" if quantity <= 5 else "Active"

    connection = get_db_connection()

    cursor = connection.execute("""
        INSERT INTO products
        (name, category, quantity, price, supplier, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        name,
        category,
        quantity,
        price,
        supplier,
        status
    ))

    product_id = cursor.lastrowid

    log_activity(
        connection,
        product_id,
        "Product Added",
        name,
        f"{name} was added with {quantity} units."
    )

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "id": product_id,
        "message": "Product added successfully."
    })


# ========================================
# UPDATE PRODUCT
# ========================================

@app.route("/api/products/<int:product_id>", methods=["PUT"])
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
            "message": "Quantity and price must be valid numbers."
        }), 400

    if not name or not category:
        return jsonify({
            "success": False,
            "message": "Product name and category are required."
        }), 400

    if quantity < 0 or price < 0:
        return jsonify({
            "success": False,
            "message": "Quantity and price cannot be negative."
        }), 400

    connection = get_db_connection()

    old_product = connection.execute("""
        SELECT *
        FROM products
        WHERE id = ?
    """, (product_id,)).fetchone()

    if not old_product:
        connection.close()

        return jsonify({
            "success": False,
            "message": "Product not found."
        }), 404

    old_quantity = old_product["quantity"]

    status = "Low Stock" if quantity <= 5 else "Active"

    connection.execute("""
        UPDATE products
        SET name = ?,
            category = ?,
            quantity = ?,
            price = ?,
            supplier = ?,
            status = ?
        WHERE id = ?
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
        details = f"{name} information was updated."

    log_activity(
        connection,
        product_id,
        action,
        name,
        details
    )

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message": "Product updated successfully."
    })

# ========================================
# STOCK MOVEMENT
# ========================================

@app.route("/api/products/<int:product_id>/stock", methods=["POST"])
def update_stock(product_id):
    data = request.get_json() or {}

    movement_type = data.get("type", "").strip().lower()

    try:
        amount = int(data.get("amount", 0))

    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Quantity must be a valid number."
        }), 400

    if movement_type not in ["in", "out"]:
        return jsonify({
            "success": False,
            "message": "Invalid stock movement type."
        }), 400

    if amount <= 0:
        return jsonify({
            "success": False,
            "message": "Quantity must be greater than zero."
        }), 400


    connection = get_db_connection()


    product = connection.execute("""
        SELECT *
        FROM products
        WHERE id = ?
    """, (product_id,)).fetchone()


    if not product:

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


    # ========================================
    # STOCK IN
    # ========================================

    if movement_type == "in":

        new_quantity = (
            old_quantity + amount
        )

        action = "Stock In"

        details = (
            f"{amount} {unit_word} added. "
            f"Stock changed from "
            f"{old_quantity} to "
            f"{new_quantity} units."
        )


    # ========================================
    # STOCK OUT
    # ========================================

    else:

        if amount > old_quantity:

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


        new_quantity = (
            old_quantity - amount
        )

        action = "Stock Out"

        details = (
            f"{amount} {unit_word} removed. "
            f"Stock changed from "
            f"{old_quantity} to "
            f"{new_quantity} units."
        )


    # ========================================
    # UPDATE STATUS
    # ========================================

    status = (
        "Low Stock"
        if new_quantity <= 5
        else "Active"
    )


    connection.execute("""
        UPDATE products
        SET quantity = ?,
            status = ?
        WHERE id = ?
    """, (
        new_quantity,
        status,
        product_id
    ))


    # ========================================
    # SAVE HISTORY
    # ========================================

    log_activity(
        connection,
        product_id,
        action,
        product_name,
        details
    )


    connection.commit()
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

@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    connection = get_db_connection()

    product = connection.execute("""
        SELECT *
        FROM products
        WHERE id = ?
    """, (product_id,)).fetchone()

    if not product:
        connection.close()

        return jsonify({
            "success": False,
            "message": "Product not found."
        }), 404

    product_name = product["name"]

    # Keep history before deleting product
    log_activity(
        connection,
        product_id,
        "Product Deleted",
        product_name,
        f"{product_name} was removed from inventory."
    )

    connection.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message": "Product deleted successfully."
    })


# ========================================
# PRODUCT HISTORY
# ========================================

@app.route("/api/products/<int:product_id>/history", methods=["GET"])
def product_history(product_id):
    connection = get_db_connection()

    product = connection.execute("""
        SELECT *
        FROM products
        WHERE id = ?
    """, (product_id,)).fetchone()

    if not product:
        connection.close()

        return jsonify({
            "success": False,
            "message": "Product not found."
        }), 404

    activities = connection.execute("""
        SELECT *
        FROM activity_log
        WHERE product_id = ?
        ORDER BY id DESC
    """, (product_id,)).fetchall()

    connection.close()

    history = [
        {
            "id": activity["id"],
            "action": activity["action"],
            "details": activity["details"],
            "time": time_ago(activity["created_at"])
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

    category_list = connection.execute("""
        SELECT
            c.id,
            c.name AS category,
            COUNT(p.id) AS product_count,
            COALESCE(SUM(p.quantity), 0) AS total_stock,
            COALESCE(SUM(p.quantity * p.price), 0) AS total_value
        FROM categories c
        LEFT JOIN products p
            ON p.category = c.name
        GROUP BY c.id, c.name
        ORDER BY c.name
    """).fetchall()

    connection.close()

    return render_template(
        "categories.html",
        categories=category_list
    )


@app.route("/api/categories", methods=["POST"])
def add_category():
    data = request.get_json() or {}
    name = data.get("name", "").strip()

    if not name:
        return jsonify({
            "success": False,
            "message": "Category name is required."
        }), 400

    connection = get_db_connection()

    try:
        cursor = connection.execute(
            "INSERT INTO categories (name) VALUES (?)",
            (name,)
        )

        connection.commit()
        category_id = cursor.lastrowid

    except sqlite3.IntegrityError:
        connection.close()

        return jsonify({
            "success": False,
            "message": "This category already exists."
        }), 400

    connection.close()

    return jsonify({
        "success": True,
        "id": category_id,
        "message": "Category added successfully."
    })


@app.route("/api/categories/<int:category_id>", methods=["PUT"])
def update_category(category_id):
    data = request.get_json() or {}
    new_name = data.get("name", "").strip()

    if not new_name:
        return jsonify({
            "success": False,
            "message": "Category name is required."
        }), 400

    connection = get_db_connection()

    category = connection.execute("""
        SELECT *
        FROM categories
        WHERE id = ?
    """, (category_id,)).fetchone()

    if not category:
        connection.close()

        return jsonify({
            "success": False,
            "message": "Category not found."
        }), 404

    old_name = category["name"]

    try:
        connection.execute("""
            UPDATE categories
            SET name = ?
            WHERE id = ?
        """, (
            new_name,
            category_id
        ))

        connection.execute("""
            UPDATE products
            SET category = ?
            WHERE category = ?
        """, (
            new_name,
            old_name
        ))

        connection.commit()

    except sqlite3.IntegrityError:
        connection.close()

        return jsonify({
            "success": False,
            "message": "This category already exists."
        }), 400

    connection.close()

    return jsonify({
        "success": True,
        "message": "Category updated successfully."
    })


@app.route("/api/categories/<int:category_id>", methods=["DELETE"])
def delete_category(category_id):
    connection = get_db_connection()

    category = connection.execute("""
        SELECT *
        FROM categories
        WHERE id = ?
    """, (category_id,)).fetchone()

    if not category:
        connection.close()

        return jsonify({
            "success": False,
            "message": "Category not found."
        }), 404

    product_count = connection.execute("""
        SELECT COUNT(*) AS count
        FROM products
        WHERE category = ?
    """, (category["name"],)).fetchone()["count"]

    if product_count > 0:
        connection.close()

        return jsonify({
            "success": False,
            "message":
            "This category cannot be deleted because it contains products."
        }), 400

    connection.execute(
        "DELETE FROM categories WHERE id = ?",
        (category_id,)
    )

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message": "Category deleted successfully."
    })


# ========================================
# SUPPLIERS
# ========================================

@app.route("/suppliers")
def suppliers():
    connection = get_db_connection()

    supplier_list = connection.execute("""
        SELECT
            s.id,
            s.name AS supplier,
            COUNT(p.id) AS product_count,
            COALESCE(SUM(p.quantity), 0) AS total_stock,
            COALESCE(SUM(p.quantity * p.price), 0) AS total_value
        FROM suppliers s
        LEFT JOIN products p
            ON p.supplier = s.name
        GROUP BY s.id, s.name
        ORDER BY s.name
    """).fetchall()

    connection.close()

    return render_template(
        "suppliers.html",
        suppliers=supplier_list
    )


@app.route("/api/suppliers", methods=["POST"])
def add_supplier():
    data = request.get_json() or {}
    name = data.get("name", "").strip()

    if not name:
        return jsonify({
            "success": False,
            "message": "Supplier name is required."
        }), 400

    connection = get_db_connection()

    existing_supplier = connection.execute("""
        SELECT id
        FROM suppliers
        WHERE LOWER(name) = LOWER(?)
    """, (name,)).fetchone()

    if existing_supplier:
        connection.close()

        return jsonify({
            "success": False,
            "message": "This supplier already exists."
        }), 400

    cursor = connection.execute(
        "INSERT INTO suppliers (name) VALUES (?)",
        (name,)
    )

    connection.commit()
    supplier_id = cursor.lastrowid
    connection.close()

    return jsonify({
        "success": True,
        "id": supplier_id,
        "message": "Supplier added successfully."
    })


@app.route("/api/suppliers/<int:supplier_id>", methods=["PUT"])
def update_supplier(supplier_id):
    data = request.get_json() or {}
    new_name = data.get("name", "").strip()

    if not new_name:
        return jsonify({
            "success": False,
            "message": "Supplier name is required."
        }), 400

    connection = get_db_connection()

    supplier = connection.execute("""
        SELECT *
        FROM suppliers
        WHERE id = ?
    """, (supplier_id,)).fetchone()

    if not supplier:
        connection.close()

        return jsonify({
            "success": False,
            "message": "Supplier not found."
        }), 404

    existing = connection.execute("""
        SELECT id
        FROM suppliers
        WHERE LOWER(name) = LOWER(?)
        AND id != ?
    """, (
        new_name,
        supplier_id
    )).fetchone()

    if existing:
        connection.close()

        return jsonify({
            "success": False,
            "message": "This supplier already exists."
        }), 400

    old_name = supplier["name"]

    connection.execute("""
        UPDATE suppliers
        SET name = ?
        WHERE id = ?
    """, (
        new_name,
        supplier_id
    ))

    connection.execute("""
        UPDATE products
        SET supplier = ?
        WHERE supplier = ?
    """, (
        new_name,
        old_name
    ))

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message": "Supplier updated successfully."
    })


@app.route("/api/suppliers/<int:supplier_id>", methods=["DELETE"])
def delete_supplier(supplier_id):
    connection = get_db_connection()

    supplier = connection.execute("""
        SELECT *
        FROM suppliers
        WHERE id = ?
    """, (supplier_id,)).fetchone()

    if not supplier:
        connection.close()

        return jsonify({
            "success": False,
            "message": "Supplier not found."
        }), 404

    product_count = connection.execute("""
        SELECT COUNT(*) AS count
        FROM products
        WHERE supplier = ?
    """, (supplier["name"],)).fetchone()["count"]

    if product_count > 0:
        connection.close()

        return jsonify({
            "success": False,
            "message":
            "This supplier cannot be deleted because it contains products."
        }), 400

    connection.execute(
        "DELETE FROM suppliers WHERE id = ?",
        (supplier_id,)
    )

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message": "Supplier deleted successfully."
    })


# ========================================
# REPORTS
# ========================================

@app.route("/reports")
def reports_page():
    return render_template("reports.html")


@app.route("/api/reports", methods=["GET"])
def reports_data():

    connection = get_db_connection()

    products = connection.execute("""
        SELECT *
        FROM products
        ORDER BY name
    """).fetchall()

    connection.close()


    # ========================================
    # SUMMARY
    # ========================================

    total_products = len(products)

    total_stock = sum(
        product["quantity"]
        for product in products
    )

    inventory_value = sum(
        product["quantity"] * product["price"]
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


    # ========================================
    # CATEGORY DATA
    # ========================================

    category_counts = {}
    category_values = {}


    for product in products:

        category = product["category"]

        if category not in category_counts:
            category_counts[category] = 0
            category_values[category] = 0


        # Number of products
        category_counts[category] += 1


        # Inventory value
        category_values[category] += (
            product["quantity"]
            * product["price"]
        )


    # ========================================
    # PRODUCT STOCK DATA
    # ========================================

    product_names = [
        product["name"]
        for product in products
    ]

    product_quantities = [
        product["quantity"]
        for product in products
    ]


    # ========================================
    # RETURN REPORT DATA
    # ========================================

    return jsonify({

        # Summary cards
        "total_products":
            total_products,

        "total_stock":
            total_stock,

        "inventory_value":
            round(inventory_value, 2),

        "low_stock_count":
            low_stock_count,


        # Products by category
        "category_names":
            list(category_counts.keys()),

        "category_counts":
            list(category_counts.values()),


        # Inventory value by category
        "category_value_names":
            list(category_values.keys()),

        "category_values": [
            round(value, 2)
            for value in category_values.values()
        ],


        # Stock levels
        "product_names":
            product_names,

        "product_quantities":
            product_quantities,


        # Stock health
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

    products = connection.execute("""
        SELECT *
        FROM products
        ORDER BY id DESC
    """).fetchall()

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
            "attachment; filename=inventory_report.csv"
        }
    )


# ========================================
# START APPLICATION
# ========================================

if __name__ == "__main__":
    create_database()
    app.run(debug=True, port=5001)
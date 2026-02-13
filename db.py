import sqlite3

# Name of the database file on disk
DB_NAME = "inventory.db"

class StockError(Exception):
    """Raised when stock rules are broken (e.g., trying to go negative)."""
    pass


def get_connection():
    """
    Opens a connection to the SQLite database.
    Every database action starts by calling this.
    """
    return sqlite3.connect(DB_NAME)

def setup_database(): 
    """
    Creates the products table if it does not already exist.
    This function is safe to run every time the program starts.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # SQL statement to create a table
    # IF NOT EXISTS prevents errors if the table is already there
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- unique ID created automatically
            sku TEXT UNIQUE,                       -- product code, must be unique
            name TEXT,                             -- product name
            price REAL                             -- product price
        )
    """)

        # This table records every stock change (IN or OUT)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT,
            movement_type TEXT,     -- "IN" or "OUT"
            quantity INTEGER,       -- how many
            reason TEXT,            -- e.g. delivery, damage, order
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

        # Stores the order itself (who, when, status)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            status TEXT NOT NULL, -- CREATED, PACKED, DISPATCHED, CANCELLED
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Stores each product inside the order
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            sku TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price_at_order REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
    """)

        # Stores the order itself (who ordered + status)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            status TEXT NOT NULL, -- CREATED, PACKED, DISPATCHED, CANCELLED
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Stores each item inside an order
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            sku TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price_at_order REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
    """)




    conn.commit()   # save changes to the database
    conn.close()    # close the connection

def add_product(sku, name, price):
    """
    Saves a new product into the database.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # The ? symbols protect against SQL injection and formatting issues
    cursor.execute(
        "INSERT INTO products (sku, name, price) VALUES (?, ?, ?)",
        (sku, name, price)
    )

    conn.commit()
    conn.close()

def get_all_products():
    """
    Returns all products as a list of rows.
    Each row contains: (sku, name, price)
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT sku, name, price FROM products")
    products = cursor.fetchall()  # list of tuples

    conn.close()
    return products

def add_stock_movement(sku, movement_type, quantity, reason):
    """
    Records stock going IN or OUT, with validation.
    - Prevents quantity <= 0
    - Prevents OUT that would make stock negative
    - Prevents stock updates for unknown SKUs
    """
    sku = sku.strip()
    movement_type = movement_type.strip().upper()

    if quantity <= 0:
        raise StockError("Quantity must be greater than 0.")

    if movement_type not in ("IN", "OUT"):
        raise StockError("movement_type must be 'IN' or 'OUT'.")

    conn = get_connection()
    cursor = conn.cursor()

    # 1) Check the product exists (so you can't add stock to a fake SKU)
    cursor.execute("SELECT 1 FROM products WHERE sku = ?", (sku,))
    exists = cursor.fetchone()
    if not exists:
        conn.close()
        raise StockError(f"Unknown SKU: {sku}. Add the product first.")

    # 2) If OUT, check we have enough stock BEFORE inserting
    if movement_type == "OUT":
        current_stock = get_stock_level(sku)  # uses IN - OUT calculation
        if quantity > current_stock:
            conn.close()
            raise StockError(
                f"Not enough stock for {sku}. Current stock: {current_stock}, tried to remove: {quantity}"
            )

    # 3) If checks pass, record the movement
    cursor.execute(
        "INSERT INTO stock_movements (sku, movement_type, quantity, reason) VALUES (?, ?, ?, ?)",
        (sku, movement_type, quantity, reason.strip())
    )

    conn.commit()
    conn.close()


def get_stock_level(sku):
    """
    Returns current stock level for a SKU:
    total IN - total OUT
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN movement_type = 'IN' THEN quantity ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN movement_type = 'OUT' THEN quantity ELSE 0 END), 0)
        FROM stock_movements
        WHERE sku = ?
    """, (sku,))

    stock = cursor.fetchone()[0]  # first column of the result
    conn.close()
    return stock

class OrderError(Exception):
    """Raised when order rules are broken (invalid status changes, etc)."""
    pass

def create_order(customer_name, items):
    """
    Creates an order and reduces stock.

    items format:
    [("SKU1", 2), ("SKU2", 1)]
    """
    if not items:
        raise OrderError("Order must have at least 1 item.")
    
        # Merge duplicate SKUs (e.g. SKU1 twice becomes one line with combined quantity)
    merged = {}
    for sku, qty in items:
        sku = sku.strip()
        merged[sku] = merged.get(sku, 0) + qty

    # Turn it back into a list of (sku, qty)
    items = list(merged.items())


    conn = get_connection()
    cursor = conn.cursor()

    # Validate all items BEFORE writing anything (prevents half-created orders)
    for sku, qty in items:
        sku = sku.strip()
        if qty <= 0:
            conn.close()
            raise OrderError("Item quantity must be greater than 0.")

        # Product must exist
        cursor.execute("SELECT price FROM products WHERE sku = ?", (sku,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise OrderError(f"Unknown SKU: {sku}")

        # Must have enough stock
        current_stock = get_stock_level(sku)
        if qty > current_stock:
            conn.close()
            raise OrderError(f"Not enough stock for {sku}. Have {current_stock}, need {qty}")

    # Create order header
    cursor.execute(
        "INSERT INTO orders (customer_name, status) VALUES (?, ?)",
        (customer_name.strip(), "CREATED")
    )
    order_id = cursor.lastrowid

    # Add order items + reduce stock via movements
    for sku, qty in items:
        cursor.execute("SELECT price FROM products WHERE sku = ?", (sku.strip(),))
        price = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO order_items (order_id, sku, quantity, price_at_order) VALUES (?, ?, ?, ?)",
            (order_id, sku.strip(), qty, price)
        )

        # Reduce stock by recording OUT movement
        cursor.execute(
            "INSERT INTO stock_movements (sku, movement_type, quantity, reason) VALUES (?, 'OUT', ?, ?)",
            (sku.strip(), qty, f"order:{order_id}")
        )

    conn.commit()
    conn.close()
    return order_id


def get_order(order_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, customer_name, status, created_at FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    if not order:
        conn.close()
        raise OrderError("Order not found.")

    cursor.execute("""
        SELECT sku, quantity, price_at_order
        FROM order_items
        WHERE order_id = ?
    """, (order_id,))
    items = cursor.fetchall()

    conn.close()
    return order, items

def update_order_status(order_id, new_status):
    """
    Enforces allowed status transitions and restores stock on CANCELLED.
    """
    new_status = new_status.strip().upper()
    allowed_statuses = {"CREATED", "PACKED", "DISPATCHED", "CANCELLED"}
    if new_status not in allowed_statuses:
        raise OrderError("Invalid status. Use CREATED, PACKED, DISPATCHED, or CANCELLED.")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise OrderError("Order not found.")

    current_status = row[0]

    # Allowed transitions
    allowed = {
        "CREATED": {"PACKED", "CANCELLED"},
        "PACKED": {"DISPATCHED", "CANCELLED"},
        "DISPATCHED": set(),
        "CANCELLED": set(),
    }

    if new_status not in allowed[current_status]:
        conn.close()
        raise OrderError(f"Cannot change status from {current_status} to {new_status}")

    # If cancelling, restore stock by recording IN movements
    if new_status == "CANCELLED":
        cursor.execute("SELECT sku, quantity FROM order_items WHERE order_id = ?", (order_id,))
        items = cursor.fetchall()

        for sku, qty in items:
            cursor.execute(
                "INSERT INTO stock_movements (sku, movement_type, quantity, reason) VALUES (?, 'IN', ?, ?)",
                (sku, qty, f"order_cancel:{order_id}")
            )

    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    conn.commit()
    conn.close()

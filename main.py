from db import (
    setup_database,
    add_product,
    add_products_with_initial_stock,
    get_all_products,
    add_stock_movement,
    get_stock_level,
    StockError,
    create_order,
    get_order,
    update_order_status,
    OrderError
)



# Start the program and make sure the database + tables exist
print("Starting inventory system...")
setup_database()
print("Database ready.")

# Get all products from the database
print("\nCurrent products:")
products = get_all_products()

# If no products exist yet, tell the user
if not products:
    print("No products yet.")
else:
    # Loop through each product and calculate its current stock
    for sku, name, price in products:
        stock = get_stock_level(sku)  # IN - OUT calculation happens inside this function
        print(f"- {sku} | {name} | £{price} | Stock: {stock}")

# Simple text menu for user actions
choice = input(
    "\nChoose an action:\n"
    "1 = Add product\n"
    "2 = Add stock (IN)\n"
    "3 = Remove stock (OUT)\n"
    "4 = Create order\n"
    "5 = View order\n"
    "6 = Update order status\n"
    "7 = Bulk add products + initial stock\n"
    "Choice: "
).strip()


if choice == "1":
    # Collect product details from the user
    sku = input("Enter SKU: ").strip()
    name = input("Enter product name: ").strip()
    price = float(input("Enter price: ").strip())

    add_product(sku, name, price)
    print("Product saved!")

elif choice == "2":
    sku = input("SKU to add stock to: ").strip()
    qty = int(input("Quantity IN: ").strip())
    reason = input("Reason (delivery/return): ").strip()

    try:
        add_stock_movement(sku, "IN", qty, reason)
        print("Stock added!")
    except StockError as e:
        print(f"ERROR: {e}")

elif choice == "3":
    sku = input("SKU to remove stock from: ").strip()
    qty = int(input("Quantity OUT: ").strip())
    reason = input("Reason (damage/transfer): ").strip()

    try:
        add_stock_movement(sku, "OUT", qty, reason)
        print("Stock removed!")
    except StockError as e:
        print(f"ERROR: {e}")

elif choice == "4":
    customer = input("Customer name: ").strip()

    print("Enter items for the order (leave SKU blank to finish)")
    items = []
    while True:
        sku = input("SKU: ").strip()
        if sku == "":
            break
        qty = int(input("Quantity: ").strip())
        items.append((sku, qty))

    try:
        order_id = create_order(customer, items)
        print(f"Order created! Order ID: {order_id}")
    except OrderError as e:
        print(f"ERROR: {e}")

elif choice == "5":
    try:
        order_id = int(input("Order ID: ").strip())
        order, items = get_order(order_id)

        print(f"\nOrder {order[0]} | Customer: {order[1]} | Status: {order[2]} | Created: {order[3]}")
        for sku, qty, price in items:
            print(f"- {sku} x{qty} @ £{price}")
    except OrderError as e:
        print(f"ERROR: {e}")

elif choice == "6":
    try:
        order_id = int(input("Order ID: ").strip())
        new_status = input("New status (PACKED/DISPATCHED/CANCELLED): ").strip()
        update_order_status(order_id, new_status)
        print("Order updated!")
    except OrderError as e:
        print(f"ERROR: {e}")

elif choice == "7":
    print("\nEnter products in this format:")
    print("SKU, Name, Price, InitialQty")
    print("Example: SKU3, Blue T-Shirt, 19.99, 10")
    print("Press Enter on a blank line to finish.\n")

    products_to_add = []

    while True:
        line = input("Product: ").strip()
        if line == "":
            break

        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 4:
            print("ERROR: Use exactly: SKU, Name, Price, InitialQty")
            continue

        sku, name, price_text, qty_text = parts

        try:
            price = float(price_text)
            qty = int(qty_text)
            if qty < 0:
                print("ERROR: InitialQty cannot be negative.")
                continue
            products_to_add.append((sku, name, price, qty))
        except ValueError:
            print("ERROR: Price must be a number (e.g. 19.99) and InitialQty must be a whole number (e.g. 10).")

    if not products_to_add:
        print("No products entered.")
    else:
        added, skipped = add_products_with_initial_stock(products_to_add)

        print(f"\nAdded {added} products successfully.")

    if skipped:
            print("Skipped duplicate SKUs:")
            for sku in skipped:
                print(f"- {sku}")




else:
    print("No action selected.")

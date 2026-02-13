# Inventory & Order System (Python)

A command-line inventory and order management system built in Python using SQLite.
The system models real-world stock control using stock movements (IN/OUT) and enforces
business rules such as preventing negative stock and managing order lifecycle states.

## Key Features
- Product catalogue with unique SKUs
- Stock tracking using IN/OUT movements (no manual stock numbers)
- Validation to prevent negative stock levels
- Customer orders that automatically reduce stock
- Order lifecycle management (CREATED → PACKED → DISPATCHED / CANCELLED)
- Order cancellation restores stock automatically
- Bulk add products with initial stock (skips duplicate SKUs safely)

## Tech Stack
- Python 3
- SQLite
- Git
- Command Line Interface (CLI)

## How to Run
## Bulk Add Products + Initial Stock (Option 7)

You can add multiple products and their starting stock in one go.

### Input format
Each line must be:
SKU, Name, Price, InitialQty

Example:
SKU100, Hoodie, 29.99, 10
SKU101, Cap, 12.50, 25

- Press Enter on a blank line to finish.
- Duplicate SKUs are skipped and reported (the program continues).
- Initial Qty must be 0 or more.

### What happens behind the scenes
- A product row is inserted into the `products` table
- If InitialQty > 0, an `IN` stock movement is recorded in `stock_movements` with reason `initial_stock`



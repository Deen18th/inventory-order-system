# inventory-order-system

## FEATURES

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
- InitialQty must be 0 or more.

### What happens behind the scenes
- A product row is inserted into the `products` table
- If InitialQty > 0, an `IN` stock movement is recorded in `stock_movements` with reason `initial_stock`

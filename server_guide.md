# Robinhood MCP Server Usage Guide

## Best Practices for LLM Agents

This guide will help you efficiently interact with the Robinhood MCP Server while minimizing token usage and optimizing responses.

### 1. Token Efficiency

Financial data from Robinhood APIs contains large amounts of text including UUIDs, timestamps, and JSON structures that can rapidly consume tokens. To avoid this:

- **DO NOT** request full raw data dumps (like complete order histories)
- **USE** targeted queries (specific dates, specific stocks)
- **LIMIT** results by using date ranges, pagination, or filtering
- **PREFER** summary tools over raw data tools when possible

**Example: Bad Approach**
```
Get all my trading history from Robinhood.
```

**Example: Good Approach**
```
First, let me get a summary of your trading activity for the most recent date.
If that works, I'll analyze the results and offer a focused follow-up.
```

### 2. Stepwise Analysis

Break complex analyses into smaller steps:

1. First check if a tool works with a small sample (e.g., a single stock or single date)
2. Then build on successful results for deeper analysis
3. Process data incrementally rather than all at once

**Example: Stepwise Implementation**
```python
# Step 1: Check if we can access a single day's orders
date = "2025-05-02"
day_orders = get_orders_by_date(date)

# Step 2: If that works, process the data in code rather than showing raw JSON
if day_orders["status"] == "success":
    # Analyze the data
    buy_orders = [o for o in day_orders["orders"] if o["side"] == "buy" and o["state"] == "filled"]
    sell_orders = [o for o in day_orders["orders"] if o["side"] == "sell" and o["state"] == "filled"]
    
    # Step 3: Present summary findings rather than raw data
    print(f"On {date}, you made {len(buy_orders)} buy orders and {len(sell_orders)} sell orders.")
```

### 3. Code-First Approach

When analyzing trading data:

- Write client-side code to process the data rather than dumping all raw data
- Use Python's data analysis capabilities
- Only make API calls for the specific data you need
- Perform calculations in code rather than retrieving excessive data

**Example: Code-First Pattern**
```python
def calculate_daily_profit(date):
    orders = get_orders_by_date(date)
    if orders["status"] != "success":
        return "Failed to retrieve orders"
    
    filled_orders = [o for o in orders["orders"] if o["state"] == "filled"]
    
    buys = {}  # ticker -> {quantity, cost}
    sells = {}  # ticker -> {quantity, revenue}
    
    for order in filled_orders:
        ticker = order["ticker"]
        side = order["side"]
        quantity = order["quantity"]
        price = order["average_price"] or order["price"]
        
        if side == "buy":
            if ticker not in buys:
                buys[ticker] = {"quantity": 0, "cost": 0}
            buys[ticker]["quantity"] += quantity
            buys[ticker]["cost"] += quantity * price
        else:  # sell
            if ticker not in sells:
                sells[ticker] = {"quantity": 0, "revenue": 0}
            sells[ticker]["quantity"] += quantity
            sells[ticker]["revenue"] += quantity * price
    
    # Calculate profit/loss
    profit = 0
    for ticker in sells:
        if ticker in buys:
            # Simple calculation - assumes you sold shares you bought on the same day
            if sells[ticker]["quantity"] <= buys[ticker]["quantity"]:
                avg_buy_price = buys[ticker]["cost"] / buys[ticker]["quantity"]
                profit += sells[ticker]["revenue"] - (sells[ticker]["quantity"] * avg_buy_price)
    
    return f"Estimated day trading profit for {date}: ${profit:.2f}"
```

### 4. Tool Selection Tips

- Use `get_latest_price` instead of `get_stock_quote` when you only need the current price
- Use summarized portfolio data rather than individual position details when possible
- For historical analysis, query one ticker at a time rather than all holdings at once
- When analyzing a date range, process one day at a time

### 5. Security and Privacy

- Do not display full order IDs, account numbers, or unique identifiers
- Summarize financial findings rather than displaying full transaction details  
- Focus on trends, patterns, and metrics rather than specific details
- Avoid showing exact timestamps or other personally identifiable information

Following these guidelines will result in faster, more reliable responses and better user experience with the Robinhood MCP Server.
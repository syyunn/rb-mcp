# Robinhood MCP Server

A Model Context Protocol (MCP) server that provides Robinhood trading functionality to LLM clients like Claude Desktop.

## Overview

This MCP server exposes Robinhood's trading API as a set of tools and resources that can be used by Claude or other LLM clients. It allows you to:

- Check stock quotes and market data
- Place various types of stock orders (market, limit)
- Monitor your portfolio and positions
- Track open orders and trading history

## Setup

### Prerequisites

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) package manager (recommended for Claude Desktop integration)
- A Robinhood account

### Installation

1. Clone this repository:

```bash
git clone https://github.com/syyunn/rb-mcp.git
cd rb-mcp
```

2. Install dependencies:

```bash
pip install fastmcp robin_stocks pydantic
```

3. Install the server in Claude Desktop:

```bash
fastmcp install server.py
```

Or run it in development mode:

```bash
fastmcp dev server.py
```

## Usage

### Authentication

Before using trading functionality, you must authenticate with Robinhood:

```
To use the Robinhood trading capabilities, please log in first.

[Call the login tool with your Robinhood credentials]
```

### Tools

The server provides the following tools:

#### Authentication
- `login` - Authenticate with Robinhood
- `logout` - End your Robinhood session

#### Stock Information
- `get_stock_quote` - Get detailed quote for a stock
- `get_latest_price` - Get the current price of a stock

#### Trading Operations
- `buy_stock_market_order` - Place a market order to buy a stock
- `sell_stock_market_order` - Place a market order to sell a stock
- `buy_stock_limit_order` - Place a limit order to buy a stock
- `sell_stock_limit_order` - Place a limit order to sell a stock
- `cancel_order` - Cancel an open order

#### Portfolio Information
- `get_portfolio` - Get portfolio summary and account balance
- `get_positions` - View all current stock positions
- `get_open_orders` - View all open orders

### Resources

The server also provides these resources:

- `robinhood://stocks/{ticker}/info` - Detailed stock information
- `robinhood://portfolio/summary` - Portfolio summary
- `robinhood://account/history/{timespan}` - Account history over specified time period

### Example Conversations

#### Getting a Stock Quote

```
User: What's the current price of Apple stock?

Claude: Let me check the current price of Apple stock for you.

[Claude calls get_stock_quote with ticker="AAPL"]

The current price of Apple (AAPL) is $182.25.
Bid: $182.24
Ask: $182.26
Volume: 23,451,872
```

#### Placing a Buy Order

```
User: I'd like to buy 5 shares of Microsoft.

Claude: I can help you place an order for Microsoft stock.

[Claude calls get_latest_price with ticker="MSFT"]

Microsoft (MSFT) is currently trading at $417.82 per share.

Would you like to place a market order for 5 shares at the current price (approximately $2,089.10 total), or would you prefer to set a limit order at a specific price?

User: Let's do a market order.

Claude: I'll place a market order for 5 shares of Microsoft (MSFT).

[Claude calls buy_stock_market_order with ticker="MSFT", quantity=5]

Your market order has been placed successfully!
Order ID: 12345abc-6789-def0-1234-56789abcdef0
Status: queued
```

## Security Notes

- This tool requires your Robinhood login credentials
- Credentials are not stored in the MCP server itself
- Authentication tokens are managed by the robin_stocks library in a local pickle file
- Always verify the content of any trades before confirming

## License

This project uses the Apache 2.0 license.

## Disclaimer

This tool is not affiliated with or endorsed by Robinhood. Use at your own risk. Trading stocks involves risk of financial loss.
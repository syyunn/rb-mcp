#!/usr/bin/env python3
"""
Robinhood MCP Server

A FastMCP server that exposes Robinhood trading functionality 
to Claude and other LLM clients.

## IMPORTANT USAGE GUIDELINES FOR LLM AGENTS

To efficiently use this server, follow these best practices:

1. TOKEN EFFICIENCY: Financial data contains large amounts of text that can consume tokens rapidly.
   - DO NOT request full raw data dumps (like complete order histories)
   - USE targeted queries (specific dates, specific stocks) 
   - PREFER summary tools over raw data tools whenever possible

2. STEPWISE APPROACH: 
   - First check if a tool works with a small sample (e.g., a single stock or single date)
   - Then build on successful results for deeper analysis
   - Break complex analyses into smaller focused queries

3. CODE-FIRST APPROACH:
   - When analyzing trading data, write code to process the data rather than dumping all raw data
   - Use client-side code to aggregate and analyze data

4. PRIVATE DATA HANDLING:
   - Summarize financial findings rather than displaying full transaction details
   - Focus on trends, patterns, and metrics rather than specific trade IDs or exact timestamps

Following these guidelines will result in faster, more reliable responses and better user experience.
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field
from fastmcp import FastMCP, Context, Image
import robin_stocks.robinhood as rh

# Initialize the MCP server
mcp = FastMCP(
    "robinhood", 
    dependencies=["robin_stocks", "pydantic"],
    description="A server that provides stock trading functionality through Robinhood"
)

# ----- Models for request/response data -----

class StockOrder(BaseModel):
    """Model for placing a stock order"""
    ticker: str = Field(..., description="Stock ticker symbol (e.g., 'AAPL')")
    quantity: int = Field(..., description="Number of shares to trade")
    price: Optional[float] = Field(None, description="Limit price (if applicable)")
    order_type: str = Field("market", description="Order type: 'market' or 'limit'")
    time_in_force: str = Field("gtc", description="Time in force: 'gtc' (good till canceled), 'gfd' (good for day), etc.")
    extended_hours: bool = Field(False, description="Whether to allow trading during extended hours")

class LimitOrder(BaseModel):
    """Model for placing a limit order"""
    ticker: str = Field(..., description="Stock ticker symbol (e.g., 'AAPL')")
    quantity: int = Field(..., description="Number of shares to trade")
    price: float = Field(..., description="Limit price for the order")
    time_in_force: str = Field("gtc", description="Time in force: 'gtc' (good till canceled), 'gfd' (good for day)")
    extended_hours: bool = Field(False, description="Whether to allow trading during extended hours")

class LoginCredentials(BaseModel):
    """Model for login credentials"""
    username: str = Field(..., description="Robinhood username (email)")
    password: str = Field(..., description="Robinhood password")
    mfa_code: Optional[str] = Field(None, description="MFA code if required")

class StockInfo(BaseModel):
    """Model for stock information"""
    ticker: str = Field(..., description="Stock ticker symbol")

# ----- Authentication -----

@mcp.tool()
async def login(credentials: LoginCredentials) -> Dict[str, Any]:
    """
    Login to Robinhood with the provided credentials.
    
    This tool logs in to Robinhood and enables other trading functionalities.
    It stores the authentication token for subsequent requests.
    """
    try:
        login_response = rh.login(
            username=credentials.username,
            password=credentials.password,
            mfa_code=credentials.mfa_code
        )
        
        # Return a sanitized version of the response
        return {
            "success": True,
            "message": "Successfully logged in to Robinhood",
            "expires_in": login_response.get("expires_in", 86400),
            "scope": login_response.get("scope", "internal")
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Login failed: {str(e)}"
        }

@mcp.tool()
async def logout() -> Dict[str, str]:
    """
    Logout from Robinhood and invalidate the current session.
    """
    try:
        rh.logout()
        return {"status": "success", "message": "Successfully logged out from Robinhood"}
    except Exception as e:
        return {"status": "error", "message": f"Logout failed: {str(e)}"}

# ----- Stock Information -----

@mcp.tool()
async def get_stock_quote(stock_info: StockInfo) -> Dict[str, Any]:
    """
    Get the latest quote information for a stock.
    
    Returns latest price, bid/ask, volume, and other quote information.
    """
    try:
        ticker = stock_info.ticker.upper()
        quote_info = rh.stocks.get_quotes(ticker)
        
        if not quote_info or isinstance(quote_info, list) and not quote_info:
            return {"status": "error", "message": f"No quote data found for {ticker}"}
            
        if isinstance(quote_info, list):
            quote_info = quote_info[0]
            
        # Clean up the response to include just the most relevant information
        return {
            "status": "success",
            "ticker": ticker,
            "ask_price": float(quote_info.get("ask_price", 0)),
            "bid_price": float(quote_info.get("bid_price", 0)),
            "last_trade_price": float(quote_info.get("last_trade_price", 0)),
            "previous_close": float(quote_info.get("previous_close", 0)),
            "updated_at": quote_info.get("updated_at", ""),
            "volume": int(float(quote_info.get("volume", 0)))
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to get quote for {stock_info.ticker}: {str(e)}"}

@mcp.tool()
async def get_latest_price(stock_info: StockInfo) -> Dict[str, Any]:
    """
    Get the latest price for a stock.
    
    Returns a simple response with just the latest price.
    """
    try:
        ticker = stock_info.ticker.upper()
        price = rh.stocks.get_latest_price(ticker)
        
        if not price or not price[0]:
            return {"status": "error", "message": f"No price data found for {ticker}"}
            
        return {
            "status": "success",
            "ticker": ticker,
            "price": float(price[0])
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to get price for {ticker}: {str(e)}"}

# ----- Trading Operations -----

@mcp.tool()
async def buy_stock_market_order(order: StockOrder) -> Dict[str, Any]:
    """
    Place a market order to buy a stock.
    
    Places an order to buy the specified quantity of a stock at the current market price.
    """
    try:
        result = rh.orders.order_buy_market(
            symbol=order.ticker,
            quantity=order.quantity,
            timeInForce=order.time_in_force,
            extendedHours=order.extended_hours
        )
        
        return {
            "status": "success",
            "order_id": result.get("id", ""),
            "state": result.get("state", ""),
            "ticker": order.ticker,
            "quantity": order.quantity,
            "type": "market",
            "side": "buy",
            "created_at": result.get("created_at", "")
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to place buy order: {str(e)}"}

@mcp.tool()
async def sell_stock_market_order(order: StockOrder) -> Dict[str, Any]:
    """
    Place a market order to sell a stock.
    
    Places an order to sell the specified quantity of a stock at the current market price.
    """
    try:
        result = rh.orders.order_sell_market(
            symbol=order.ticker,
            quantity=order.quantity,
            timeInForce=order.time_in_force,
            extendedHours=order.extended_hours
        )
        
        return {
            "status": "success",
            "order_id": result.get("id", ""),
            "state": result.get("state", ""),
            "ticker": order.ticker,
            "quantity": order.quantity,
            "type": "market",
            "side": "sell",
            "created_at": result.get("created_at", "")
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to place sell order: {str(e)}"}

@mcp.tool()
async def buy_stock_limit_order(order: LimitOrder) -> Dict[str, Any]:
    """
    Place a limit order to buy a stock.
    
    Places an order to buy the specified quantity of a stock at or below the specified limit price.
    """
    try:
        result = rh.orders.order_buy_limit(
            symbol=order.ticker,
            quantity=order.quantity,
            limitPrice=order.price,
            timeInForce=order.time_in_force,
            extendedHours=order.extended_hours
        )
        
        return {
            "status": "success",
            "order_id": result.get("id", ""),
            "state": result.get("state", ""),
            "ticker": order.ticker,
            "quantity": order.quantity,
            "limit_price": order.price,
            "type": "limit",
            "side": "buy",
            "created_at": result.get("created_at", "")
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to place buy limit order: {str(e)}"}

@mcp.tool()
async def sell_stock_limit_order(order: LimitOrder) -> Dict[str, Any]:
    """
    Place a limit order to sell a stock.
    
    Places an order to sell the specified quantity of a stock at or above the specified limit price.
    """
    try:
        result = rh.orders.order_sell_limit(
            symbol=order.ticker,
            quantity=order.quantity,
            limitPrice=order.price,
            timeInForce=order.time_in_force,
            extendedHours=order.extended_hours
        )
        
        return {
            "status": "success",
            "order_id": result.get("id", ""),
            "state": result.get("state", ""),
            "ticker": order.ticker,
            "quantity": order.quantity,
            "limit_price": order.price,
            "type": "limit",
            "side": "sell",
            "created_at": result.get("created_at", "")
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to place sell limit order: {str(e)}"}

@mcp.tool()
async def cancel_order(order_id: str) -> Dict[str, Any]:
    """
    Cancel an open order by order ID.
    
    Cancels an open order that hasn't been executed yet.
    """
    try:
        result = rh.orders.cancel_stock_order(order_id)
        return {
            "status": "success" if result else "error",
            "order_id": order_id,
            "message": "Order cancelled successfully" if result else "Failed to cancel order"
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to cancel order: {str(e)}"}

# ----- Portfolio Information -----

@mcp.tool()
async def get_portfolio() -> Dict[str, Any]:
    """
    Get portfolio information including equity value, cash balance, and other account details.
    """
    try:
        portfolio = rh.account.build_portfolio()
        return {
            "status": "success",
            "equity": float(portfolio.get("equity", 0)),
            "extended_hours_equity": float(portfolio.get("extended_hours_equity", 0)),
            "cash": float(portfolio.get("cash", 0)),
            "dividend_total": float(portfolio.get("dividend_total", 0))
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to get portfolio: {str(e)}"}

@mcp.tool()
async def get_positions() -> Dict[str, Any]:
    """
    Get current positions in the portfolio.
    
    Returns all stocks currently held in the account, with quantity and cost basis.
    """
    try:
        positions = rh.account.get_open_stock_positions()
        formatted_positions = []
        
        for position in positions:
            instrument_data = rh.stocks.get_instrument_by_url(position.get("instrument", ""))
            ticker = instrument_data.get("symbol", "UNKNOWN")
            quantity = float(position.get("quantity", 0))
            average_buy_price = float(position.get("average_buy_price", 0))
            
            formatted_positions.append({
                "ticker": ticker,
                "quantity": quantity,
                "average_buy_price": average_buy_price,
                "cost_basis": quantity * average_buy_price
            })
        
        return {
            "status": "success",
            "positions": formatted_positions
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to get positions: {str(e)}"}

@mcp.tool()
async def get_open_orders() -> Dict[str, Any]:
    """
    Get all open orders.
    
    Returns all orders that are currently open (e.g., unfilled limit orders).
    """
    try:
        orders = rh.orders.get_all_open_stock_orders()
        formatted_orders = []
        
        for order in orders:
            # Parse the instrument URL to get the ticker
            instrument_data = rh.stocks.get_instrument_by_url(order.get("instrument", ""))
            ticker = instrument_data.get("symbol", "UNKNOWN")
            
            formatted_orders.append({
                "order_id": order.get("id", ""),
                "ticker": ticker,
                "side": order.get("side", ""),
                "quantity": float(order.get("quantity", 0)),
                "type": order.get("type", ""),
                "price": float(order.get("price", 0)) if order.get("price") else None,
                "created_at": order.get("created_at", ""),
                "state": order.get("state", "")
            })
        
        return {
            "status": "success",
            "orders": formatted_orders
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to get open orders: {str(e)}"}

@mcp.tool()
async def get_orders_by_date(date: str) -> Dict[str, Any]:
    """
    Get all orders placed on a specific date.
    
    Returns all orders (open, filled, canceled, etc.) created on the specified date.
    The date must be in YYYY-MM-DD format (e.g., '2025-05-02').
    """
    try:
        # Get all orders from the Robinhood API
        all_orders = rh.orders.get_all_stock_orders()
        
        # Filter orders by the specified date
        filtered_orders = []
        for order in all_orders:
            if order.get('created_at', '').startswith(date):
                # Parse the instrument URL to get the ticker
                instrument_data = rh.stocks.get_instrument_by_url(order.get("instrument", ""))
                ticker = instrument_data.get("symbol", "UNKNOWN")
                
                # Format the order data
                formatted_order = {
                    "order_id": order.get("id", ""),
                    "ticker": ticker,
                    "side": order.get("side", ""),
                    "quantity": float(order.get("quantity", 0)),
                    "type": order.get("type", ""),
                    "price": float(order.get("price", 0)) if order.get("price") else None,
                    "created_at": order.get("created_at", ""),
                    "state": order.get("state", ""),
                    "executions": order.get("executions", []),
                    "filled_quantity": float(order.get("cumulative_quantity", 0)),
                    "average_price": float(order.get("average_price", 0)) if order.get("average_price") else None
                }
                
                # Convert created_at time from UTC to Eastern Time
                if "created_at" in order and order["created_at"]:
                    # Parse the ISO timestamp
                    utc_time = order["created_at"].replace('Z', '+00:00')
                    # Calculate ET (UTC-4 during daylight saving time)
                    formatted_order["created_at_et"] = f"{utc_time[0:19]}Z (ET: {utc_time[11:16]} ET)"
                
                filtered_orders.append(formatted_order)
        
        # Sort orders by created_at timestamp (newest first)
        filtered_orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {
            "status": "success",
            "date": date,
            "orders_count": len(filtered_orders),
            "orders": filtered_orders
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to get orders for date {date}: {str(e)}"}

# ----- Market Data Resources -----

@mcp.resource("robinhood://stocks/{ticker}/info")
async def get_stock_info(ticker: str) -> Dict[str, Any]:
    """
    Get detailed information about a stock.
    """
    try:
        ticker = ticker.upper()
        stock_info = rh.stocks.get_fundamentals(ticker)[0]
        
        return {
            "ticker": ticker,
            "name": stock_info.get("high_52_weeks", ""),
            "sector": stock_info.get("sector", ""),
            "industry": stock_info.get("industry", ""),
            "market_cap": float(stock_info.get("market_cap", 0)),
            "pe_ratio": float(stock_info.get("pe_ratio", 0)),
            "dividend_yield": float(stock_info.get("dividend_yield", 0)),
            "high_52_weeks": float(stock_info.get("high_52_weeks", 0)),
            "low_52_weeks": float(stock_info.get("low_52_weeks", 0))
        }
    except Exception as e:
        return {"error": f"Failed to get stock info for {ticker}: {str(e)}"}

@mcp.resource("robinhood://portfolio/summary")
async def get_portfolio_summary() -> Dict[str, Any]:
    """
    Get a summary of the portfolio's performance and composition.
    """
    try:
        portfolio = rh.account.build_portfolio()
        positions = rh.account.get_open_stock_positions()
        
        # Count number of different stocks
        positions_count = len(positions)
        
        return {
            "equity": float(portfolio.get("equity", 0)),
            "cash": float(portfolio.get("cash", 0)),
            "total_assets": float(portfolio.get("equity", 0)) + float(portfolio.get("cash", 0)),
            "positions_count": positions_count,
            "dividend_total": float(portfolio.get("dividend_total", 0))
        }
    except Exception as e:
        return {"error": f"Failed to get portfolio summary: {str(e)}"}

@mcp.resource("robinhood://account/history/{timespan}")
async def get_account_history(timespan: str) -> Dict[str, Any]:
    """
    Get account history for a specified timespan.
    
    The timespan parameter can be: day, week, month, 3month, year, 5year, all
    """
    try:
        valid_timespans = ["day", "week", "month", "3month", "year", "5year", "all"]
        if timespan not in valid_timespans:
            return {"error": f"Invalid timespan: {timespan}. Must be one of {', '.join(valid_timespans)}"}
            
        history = rh.account.get_historical_portfolio(interval=timespan)
        
        # Extract the key information from the history
        equity_data = []
        for data_point in history.get("equity_historicals", []):
            equity_data.append({
                "date": data_point.get("begins_at", ""),
                "equity": float(data_point.get("equity_close", 0)),
                "adjusted_equity": float(data_point.get("adjusted_equity_close", 0)),
            })
        
        return {
            "timespan": timespan,
            "equity_data": equity_data,
            "start_date": equity_data[0].get("date", "") if equity_data else "",
            "end_date": equity_data[-1].get("date", "") if equity_data else "",
            "total_return_percentage": history.get("total_return", {}).get("percentage", 0)
        }
    except Exception as e:
        return {"error": f"Failed to get account history: {str(e)}"}


# Helper function to get ticker from instrument URL
def get_ticker_from_instrument(instrument_url: str) -> str:
    """Get ticker symbol from instrument URL."""
    try:
        if not instrument_url:
            return "UNKNOWN"
        instrument_data = rh.stocks.get_instrument_by_url(instrument_url)
        return instrument_data.get("symbol", "UNKNOWN")
    except:
        return "UNKNOWN"


@mcp.tool()
async def analyze_trading_profit(date: str) -> Dict[str, Any]:
    """
    Calculate profit/loss from day trading on a specific date.
    
    Analyzes all trades made on the specified date using closest-price matching algorithm,
    which pairs buy/sell orders based on price similarity for more accurate profit calculation.
    """
    try:
        # Get orders for the specified date
        all_orders = rh.orders.get_all_stock_orders()
        filtered_orders = [o for o in all_orders if o.get('created_at', '').startswith(date)]

        # Filter by filled status (completed trades)
        filled_orders = [o for o in filtered_orders if o.get('state') == 'filled']

        # Group by ticker
        ticker_groups = {}
        for order in filled_orders:
            ticker = get_ticker_from_instrument(order.get("instrument", ""))
            if ticker not in ticker_groups:
                ticker_groups[ticker] = {"buys": [], "sells": []}

            # Convert to structured format for matching algorithm
            try:
                price = float(order.get('average_price', 0))
                quantity = float(order.get('quantity', 0))

                # Process executions to extract fees and timestamps
                executions = order.get('executions', [])
                fees = sum([float(e.get('fees', 0)) for e in executions])

                trade_record = {
                    'id': order.get('id'),
                    'price': price,
                    'quantity': quantity,
                    'remaining_qty': quantity,  # For tracking matched portions
                    'fees': fees,
                    'timestamp': order.get('last_transaction_at'),
                    'created_at': order.get('created_at')
                }

                # Add to appropriate category
                if order.get('side') == 'buy':
                    ticker_groups[ticker]["buys"].append(trade_record)
                else:
                    ticker_groups[ticker]["sells"].append(trade_record)
            except (ValueError, TypeError):
                # Skip if conversion fails
                continue

        # Process each ticker with the closest price matching algorithm
        results = []
        total_profit = 0
        total_matched_trades = 0

        for ticker, trades in ticker_groups.items():
            buys = trades["buys"]
            sells = trades["sells"]

            # Sort buys by timestamp (earliest first)
            buys.sort(key=lambda x: x['created_at'])

            # Sort sells by price (highest first to maximize profit)
            sells.sort(key=lambda x: x['price'], reverse=True)

            # Match trades using closest price approach
            matched_pairs = []

            for buy in buys:
                buy_qty = buy['remaining_qty']
                buy_price = buy['price']

                # Continue matching until this buy is fully matched or no more sells
                while buy_qty > 0 and any(s['remaining_qty'] > 0 for s in sells):
                    # Calculate price difference for each available sell
                    price_diffs = []

                    for i, sell in enumerate(sells):
                        if sell['remaining_qty'] > 0:
                            # Only consider sells that happened after this buy
                            if sell['created_at'] > buy['created_at']:
                                price_diff = abs(sell['price'] - buy_price)
                                price_diffs.append((i, price_diff))

                    if not price_diffs:
                        break  # No eligible sells found

                    # Sort by price difference (ascending)
                    price_diffs.sort(key=lambda x: x[1])

                    # Get the sell with closest price
                    sell_idx = price_diffs[0][0]
                    sell = sells[sell_idx]

                    # Determine quantity to match
                    match_qty = min(buy_qty, sell['remaining_qty'])

                    if match_qty > 0:
                        # Calculate profit for this match
                        trade_profit = (sell['price'] - buy_price) * match_qty

                        # Calculate proportional fees
                        buy_fee_portion = buy['fees'] * (match_qty / buy['quantity'])
                        sell_fee_portion = sell['fees'] * (match_qty / sell['quantity'])
                        total_fees = buy_fee_portion + sell_fee_portion

                        # Final profit after fees
                        net_profit = trade_profit - total_fees

                        matched_pairs.append({
                            'buy_id': buy['id'],
                            'sell_id': sell['id'],
                            'quantity': match_qty,
                            'buy_price': buy_price,
                            'sell_price': sell['price'],
                            'profit': round(net_profit, 2),
                            'fees': round(total_fees, 2)
                        })

                        # Update remaining quantities
                        buy['remaining_qty'] -= match_qty
                        sells[sell_idx]['remaining_qty'] -= match_qty

                        buy_qty -= match_qty

            # Calculate ticker profits and stats
            ticker_profit = sum(m['profit'] for m in matched_pairs)
            total_profit += ticker_profit
            total_matched_trades += len(matched_pairs)

            # Calculate total shares
            buy_shares = sum(b['quantity'] for b in buys)
            sell_shares = sum(s['quantity'] for s in sells)
            matched_shares = sum(m['quantity'] for m in matched_pairs)

            avg_profit_per_share = 0
            if matched_shares > 0:
                avg_profit_per_share = ticker_profit / matched_shares

            results.append({
                "ticker": ticker,
                "buy_orders": len(buys),
                "sell_orders": len(sells),
                "matched_trades": len(matched_pairs),
                "buy_shares": buy_shares,
                "sell_shares": sell_shares,
                "matched_shares": matched_shares,
                "fees": round(sum(m['fees'] for m in matched_pairs), 2),
                "profit": round(ticker_profit, 2),
                "avg_profit_per_share": round(avg_profit_per_share, 2),
                "matches": matched_pairs
            })

        # Sort results by profit (highest first)
        results.sort(key=lambda x: x['profit'], reverse=True)

        return {
            "status": "success",
            "date": date,
            "total_profit": round(total_profit, 2),
            "ticker_results": results,
            "matched_trades": total_matched_trades,
            "trade_count": len(filled_orders),
            "algorithm": "closest_price_matching"
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to analyze trading profit: {str(e)}"}

# ----- Prompts -----

@mcp.prompt()
def trading_assistant() -> str:
    """
    A prompt for the trading assistant.
    """
    return """
    I'll help you manage your Robinhood account and execute trades. I can provide stock information, 
    place orders, check your portfolio, and more.
    
    Here are some things I can do:
    - Get stock quotes and latest prices
    - Place market and limit orders
    - Check your portfolio and positions
    - View and cancel open orders
    
    IMPORTANT USAGE NOTES:
    - When analyzing trading data, I'll use code to process information efficiently rather than showing all raw data
    - For large datasets (like trading history), I'll provide summaries and analysis rather than dumping all transactions
    - I'll focus on actionable insights rather than verbose raw data dumps
    
    Before executing any trades, I'll need you to log in with your Robinhood credentials.
    What would you like to do today?
    """

@mcp.prompt()
def stock_analysis(ticker: str) -> str:
    """
    A prompt for analyzing a stock.
    """
    return f"""
    I'll help you analyze {ticker} stock. I can provide:
    
    1. Current market data and price information
    2. Basic fundamental analysis
    3. Information about your current position in {ticker} if you own it
    4. Help with placing trades for {ticker}
    
    What specific information about {ticker} would you like to know?
    """

@mcp.prompt()
def portfolio_review() -> str:
    """
    A prompt for reviewing a portfolio.
    """
    return """
    I'll help you review your Robinhood portfolio. We can look at:
    
    1. Overall portfolio value and cash balance
    2. Individual positions and their performance
    3. Open orders that haven't been executed
    4. Historical performance
    
    Would you like a complete overview, or should we focus on a specific aspect of your portfolio?
    """

# Run the server when executed directly
if __name__ == "__main__":
    mcp.run()
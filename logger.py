import logging

logging.basicConfig(
    filename="api_monitor.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_api_call(symbol, period):
    logging.info(f"API call made for {symbol} with period {period}")

def log_api_error(error):
    logging.error(f"API error: {error}")
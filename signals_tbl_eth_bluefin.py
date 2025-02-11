import os
import sys

here = os.path.dirname(__file__)
sys.path.append(os.path.join(here, '../'))
from datetime import datetime
import binance_client
import mining.utils as utils
from mining.utils_config import DataConfig
import pprint, logging
import data_processor, argparse
import time
from feature_selection_tbl_single_backtest import *
from order_manager_bluefin import BluefinOrderManager
from datetime import datetime, timedelta
from bluefin_v2_client import MARKET_SYMBOLS
pp = pprint.PrettyPrinter(indent=4)

BASE_URL = 'http://127.0.0.1:9000'
LEVERAGE_INCREMENT = 0.3
DRAWDOWN_THRESHOLD = -0.005
TAKE_PROFIT_THRESHOLD = 0.005
ADD_POSITION_TIME_THROTTLE = 300
TIME_INTERVAL = 15
TICKER_TO_DATA_TICKER = {
    'EURUSD': 'C:EURUSD',
    'BTCUSD': 'X:BTCUSD',
    'ETHUSD': 'X:ETHUSD',
    'SOLUSD': 'X:SOLUSD',
    'AUDCAD': 'C:AUDCAD'
}
BINANCE_TICKER_TO_BINANCE_TICKER = {
    'ETHUSD': 'ETHUSDT',
    'BTCUSD': 'BTCUSDT'
}
TICKER_TO_BLUEFIN_TICKER = {
    'ETHUSD': MARKET_SYMBOLS.ETH,
    'BTCUSD': MARKET_SYMBOLS.BTC
}


def setup_logging(debug=False):
    # Set the logging level to DEBUG if debug mode is enabled, otherwise set it to INFO
    log_level = logging.DEBUG if debug else logging.INFO

    # Set up the logging configuration
    logging.basicConfig(
        level=log_level,  # Set dynamically based on the debug flag
        format='%(asctime)s: %(message)s',  # Include timestamp
        datefmt='%Y-%m-%d %H:%M:%S',  # Timestamp format
    )


def check_position(position: dict) -> dict:
    """
    Checks the current position status (long/short/none), notional value, entry price,
    and position amount from a parsed Bluefin position.

    Assumes that the values have already been converted to floats (i.e. scaled from 10**18).

    Expected keys in the input dictionary:
      - "avgEntryPrice": float, the average entry price.
      - "positionValue": float, the notional value of the position.
      - "quantity": float, the position amount.
      - "side": string, either "BUY" for long positions or "SELL" for short positions.

    Parameters:
        position (dict): The parsed position dictionary.

    Returns:
        dict: A dictionary with the following keys:
            - 'position': "long", "short", or "none"
            - 'notional': the notional value (float)
            - 'entry_price': the entry price (float)
            - 'positionAmt': the position amount (float)
    """
    # If the position dict is empty or quantity is zero, return no active position.
    if not position or float(position.get("quantity", 0)) == 0:
        return {
            'position': 'none',
            'notional': 0,
            'entry_price': 0,
            'positionAmt': 0
        }

    side = position.get("side", "").upper()
    if side == "BUY":
        pos_type = "long"
    elif side == "SELL":
        pos_type = "short"
    else:
        pos_type = "none"

    return {
        'position': pos_type,
        'notional': float(position.get("positionValue", 0)),
        'entry_price': float(position.get("avgEntryPrice", 0)),
        'positionAmt': float(position.get("quantity", 0))
    }


class SignalStrategy:
    def __init__(self, ticker, client_data,
                 quote_symbol_quantity,
                 trading_fee,
                 prob_threshold,
                 smoothing_method,
                 span,
                 stop_loss,
                 take_profit,
                 model_path,
                 features_path,
                 api_key='xxxx',
                 data_processor=None):
        self.ticker = ticker
        self.data_client = client_data
        self.order_manager = BluefinOrderManager(private_key=api_key,
                                                 symbol=TICKER_TO_BLUEFIN_TICKER[ticker],
                                                 trading_fee=trading_fee,
                                                 quantity=quote_symbol_quantity)
        self.api_key = api_key
        self.data_processor = data_processor
        self.binance_data_ticker = BINANCE_TICKER_TO_BINANCE_TICKER[ticker]
        self.current_position = 0
        self.entry_time = 0
        self.span = span
        self.smoothing_method = smoothing_method
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.prob_threshold = prob_threshold
        self.model_path = model_path
        self.features_path = features_path
        self.trading_fee = trading_fee
        self.quantity = quote_symbol_quantity
        self.current_signal = None
        self.sent_neutral_signal_flag = False
        self.sent_reverse_signal_flag = False
        self.take_profit_price = np.nan
        self.stop_loss_price = np.nan

    def main(self):
        # 1) Initialize the very first next_5min boundary
        now = datetime.now()
        minute_rounded_down = now.replace(second=0, microsecond=0)
        minute_offset = (5 - (minute_rounded_down.minute % 5)) % 5
        # For the first cycle, pick the next boundary (plus 2s)
        next_5min = minute_rounded_down + timedelta(minutes=minute_offset, seconds=2)

        while True:
            now = datetime.now()
            time_left = (next_5min - now).total_seconds()

            if time_left <= 0:
                # It's time to run the 5-min signal
                try:
                    self.generate_signal()
                    logging.info(f"Data fetched at: {datetime.now()}")
                except Exception as e:
                    logging.error(f"Ran into exception: {e}")

                # 2) Advance `next_5min` by exactly 5 minutes
                next_5min += timedelta(minutes=5)

            else:
                # We haven't reached the 5-min boundary yet.
                # Monitor position if it's a multiple of 10 seconds, or you can do it unconditionally
                if now.second % 10 == 0:
                    try:
                        self.generate_position_value(df=None, signal_column=None, current_time=now)
                    except Exception as e:
                        logging.error(f"Ran into exception while monitoring position: {e}")

                # Sleep until either 10 seconds pass or we reach next_5min, whichever is sooner
                sleep_for = min(10, time_left)
                time.sleep(sleep_for)

    def generate_signal(self):
        data = self.data_client.pull_binance_data(self.binance_data_ticker)
        logging.info(f'Current shape of data is: {data.shape}')
        # Compare last row's close_time to "now"
        last_close_time = data.iloc[-1]['close_time']

        # In many cases, Binance's klines are in UTC. Make sure 'now' is also UTC or that both are naive.
        # If your times are all naive datetimes in Python and from Binance, you can just compare them directly.
        # But if 'close_time' is in UTC, you might do: now_utc = pd.Timestamp.utcnow()

        now_local = datetime.utcnow()  # or .utcnow() if everything is UTC
        if last_close_time > now_local:
            logging.info(f"Last bar is not fully closed yet because current_time is: {now_local} "
                         f"and last close_time is :{last_close_time}; dropping the row.")
            data = data.iloc[:-1]
        else:
            logging.info("Last bar is closed; keeping all rows.")

        self.generate_tbl_signal(data)
        return

    def generate_tbl_signal(self, data):
        df = self.data_processor.generate_features(data)
        model = joblib.load(self.model_path)
        features = joblib.load(self.features_path)
        x_test = df[features]

        numeric_features = x_test[features].select_dtypes(include=['number']).columns.tolist()
        cat_features = x_test[features].select_dtypes(include=['category']).columns.tolist()
        cat_features = [x for x in cat_features if 'CDL' not in x]
        x_test_features = x_test[numeric_features + cat_features]
        x_test_features, numeric_features, cat_features = process_feature_name_format(x_test_features, numeric_features,
                                                                                      cat_features)
        x_test_features, label_encoders = encode_categorical_features(x_test_features, cat_features)

        ypred_prob, y_pred = get_predictions_for_lgb(model, x_test_features)
        self.process_predictions(ypred_prob, df)
        return None, None

    def process_predictions(self, ypred_prob, x_test):
        ytest_pred_prob_temp = ypred_prob.copy()
        x_test_temp = apply_smoothing(x_test.copy(), ytest_pred_prob_temp, self.span, self.smoothing_method)

        probabilities = x_test_temp[[f'prob_class_{i}_mean' for i in range(3)]].values

        x_test_temp['ypred'] = np.where(
            (probabilities[:, 0] >= self.prob_threshold) | (probabilities[:, 2] >= self.prob_threshold),
            # Check if -1 or 1 exceeds the threshold
            np.argmax(probabilities, axis=1),  # Predict the class with the highest probability
            1  # Default to class 0 (neutral) if neither exceeds the threshold
        )

        x_test_temp['ypred'] = x_test_temp['ypred'].map({0: -1, 1: 0, 2: 1})

        self.generate_position_value(x_test_temp, signal_column='ypred')
        return

    def generate_position_value(self, df=None, signal_column=None, neutral_tolerance=3, current_time=None,
                                reverse_tolerance=0):
        # Ensure df and signal_column are not None
        # if df is not None and signal_column is not None and signal_column in df.columns:
        #     current_signal = df[signal_column].iloc[-1]
        current_signal = -1
        self.current_signal = current_signal
        # else:
        #     current_signal = None

        data = self.data_client.pull_binance_data(self.binance_data_ticker)
        current_price = data['close'].iloc[-1]

        if current_signal is not None:
            message = f'Current signal is: {current_signal} at price: {current_price}'
            logging.info(message)
            if current_signal != 0:
                utils.send_discord_message(DataConfig.discord_logs_webhook, message)

        # Fetch updated positions from the client
        current_positions = self.order_manager.fetch_current_positions()
        # if len(current_positions) > 0:
        position_info = check_position(current_positions)
        # else:
        #     return

        # Debug logging - only shown in debug mode
        logging.debug(f'Current positions: {current_positions}')
        logging.debug(f'Position info: {position_info}')

        # Get current position and notional value from real-time data
        real_time_position = position_info['position']  # 'long', 'short', or 'none'
        real_time_entry_price = position_info['entry_price']
        position_amount = position_info['positionAmt']
        pprint.pprint(position_info)
        if current_time is not None and current_time.second % 30 == 0:
            logging.info(f'Monitoring positions: current price is: {current_price}')
            self.order_manager.cancel_all_orders()

        # Initialize neutral signal count tracking variable if it doesn't exist
        if not hasattr(self, 'neutral_signal_count'):
            self.neutral_signal_count = 0
            self.sent_neutral_signal_flag = False

        if not hasattr(self, 'reverse_signal_count'):
            self.reverse_signal_count = 0
            self.sent_reverse_signal_flag = False

        # Process the current position based on real-time data
        if real_time_position == 'none' and current_signal != 0 and current_signal is not None:
            # No current position, open a new position
            self.current_position = current_signal
            self.entry_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Reset neutral signal count when opening a new position
            self.neutral_signal_count = 0
            self.reverse_signal_count = 0
            self.sent_neutral_signal_flag = False
            self.sent_reverse_signal_flag = False

            message = f'Opened new position with signal: {current_signal} at price: {current_price} <@176806410066067456>'
            utils.send_discord_message(DataConfig.discord_webhook, content=message)

            # Use the place order function to open a position
            order = self.order_manager.open_position_at_market(signal=current_signal, quantity=self.quantity)

            if order:
                current_positions = check_position(self.order_manager.fetch_current_positions())
                avg_fill_price = float(current_positions['entry_price'])
                message = f'Last order (open) average fill price: {avg_fill_price}, Current price: {current_price} <@176806410066067456>'
                utils.send_discord_message(DataConfig.discord_webhook, content=message)
                logging.info(message)

                self.order_manager.cancel_all_orders()
                real_time_position = 'short' if current_signal == -1 else 'long'
                real_time_entry_price = round(avg_fill_price, 1)
                stop_loss_price = real_time_entry_price * (
                            1 - self.stop_loss) if current_signal == 1 else real_time_entry_price * (1 + self.stop_loss)
                take_profit_price = real_time_entry_price * (
                            1 + self.take_profit) if current_signal == 1 else real_time_entry_price * (
                            1 - self.take_profit)
                self.stop_loss_price = round(stop_loss_price, 1)
                self.take_profit_price = round(take_profit_price, 1)
                self.order_manager.place_stop_loss_order(self.stop_loss_price, real_time_position, quantity=self.quantity)
                self.order_manager.place_take_profit_order(self.take_profit_price, real_time_position, quantity=self.quantity)

                # self.submit_trailing_stop(real_time_entry_price, real_time_position, self.stop_loss, self.quantity)

        elif real_time_position != 'none':
            # Active position, monitor the price for favorable movement before placing a trailing stop
            price_change = (current_price - real_time_entry_price) / real_time_entry_price
            if current_signal is not None:
                self.update_existing_order_price(current_price, position_info)

            if (real_time_position == 'long' and current_signal == -1) or (
                    real_time_position == 'short' and current_signal == 1):
                logging.info(f'flipping position')
                self.flip_position(current_signal, current_price)
                self.reverse_signal_count = 0  # Reset reverse signal count after flipping
            elif self.current_signal == 0:
                # Increase neutral signal count if signal is neutral
                if current_signal == 0:
                    self.neutral_signal_count += 1
                limit_price = real_time_entry_price
                # Only act if we have seen consecutive neutral signals for the required tolerance
                if self.neutral_signal_count >= neutral_tolerance:
                    if real_time_position == 'long':
                        if current_price >= limit_price:
                            logging.info('signal 0 and covering trading fees')
                            self.order_manager.close_position_at_market(real_time_position, self.quantity)
                    elif real_time_position == 'short':
                        if current_price <= limit_price:
                            self.order_manager.close_position_at_market(real_time_position, self.quantity)
                            logging.info('signal 0 and covering trading fees')
                elif not self.sent_neutral_signal_flag:
                    message = 'Signal became neutral, but count did not exceed tolerance <@176806410066067456>'
                    utils.send_discord_message(DataConfig.discord_logs_webhook, message)
                    logging.info(
                        f'Signal became neutral, but count did not exceed tolerance, current neutral_signal_count: {self.neutral_signal_count}')
                    self.sent_neutral_signal_flag = True
            else:
                # Reset the neutral signal count if the signal is not neutral
                self.neutral_signal_count = 0
                self.reverse_signal_count = 0
                self.sent_neutral_signal_flag = False
                self.sent_reverse_signal_flag = False

    def update_existing_order_price(self, current_price, position_info):
        """
        Update stop loss and take profit prices only if they change, and log changes to Discord and logs.

        Args:
            current_price (float): The current market price of the asset.
            real_time_position (str): The current position ('long' or 'short').
        """
        # Store the old prices for comparison
        real_time_position = position_info['position']  # 'long', 'short', or 'none'
        position_amount = abs(position_info['positionAmt'])

        old_stop_loss_price = self.stop_loss_price
        old_take_profit_price = self.take_profit_price

        # Update prices based on the position
        if real_time_position == 'long':
            if self.stop_loss_price is np.nan:
                self.stop_loss_price = -np.inf
                self.take_profit_price = -np.inf
            new_stop_loss_price = max(self.stop_loss_price, round(current_price * (1 - self.stop_loss), 1))
            new_take_profit_price = max(self.take_profit_price, round(current_price * (1 + self.take_profit), 1))
        elif real_time_position == 'short':
            if self.stop_loss_price is np.nan:
                self.stop_loss_price = np.inf
                self.take_profit_price = np.inf
            new_stop_loss_price = min(self.stop_loss_price, round(current_price * (1 + self.stop_loss), 1))
            new_take_profit_price = min(self.take_profit_price, round(current_price * (1 - self.take_profit), 1))
        else:
            message = f"Invalid position detected: {real_time_position}. Must be 'long' or 'short'."
            utils.send_discord_message(DataConfig.discord_logs_webhook, message)
            logging.error(message)
            raise ValueError(message)

        # Check if there is a change in prices
        if new_stop_loss_price != old_stop_loss_price or new_take_profit_price != old_take_profit_price or position_amount != self.quantity:
            # Log the changes
            message = (
                f"Prices updated for {real_time_position}: "
                f"Stop Loss: {old_stop_loss_price} -> {new_stop_loss_price}, "
                f"Take Profit: {old_take_profit_price} -> {new_take_profit_price}. "
                f"Canceling existing open orders and placing new ones."
            )
            utils.send_discord_message(DataConfig.discord_logs_webhook, message)
            logging.info(message)

            # Update the prices
            self.stop_loss_price = new_stop_loss_price
            self.take_profit_price = new_take_profit_price

            # Cancel open orders and place new ones
            self.order_manager.cancel_all_orders()
            self.order_manager.place_stop_loss_order(self.stop_loss_price, real_time_position, quantity=position_amount)
            self.order_manager.place_take_profit_order(self.take_profit_price, real_time_position, quantity=position_amount)
            orders = self.order_manager.get_order_sync()
            logging.info(f'Current length of order after placing TP/SL order is: {len(orders)}')
            pprint.pprint(orders)
        else:
            # Log that no updates were made
            message = (
                f"No changes to stop loss or take profit prices for {real_time_position}. "
                f"Existing orders remain unchanged. Stop Loss: {self.stop_loss_price}, Take Profit: {self.take_profit_price}. "
            )
            utils.send_discord_message(DataConfig.discord_logs_webhook, message)
            logging.info(message)

    def flip_position(self, current_signal, current_price):
        """
        Close the current position and open a new one due to a signal flip.
        """
        self.current_position = current_signal
        position_info = check_position(self.order_manager.fetch_current_positions())
        real_time_position = position_info['position']
        order = self.order_manager.close_position_at_market(real_time_position, quantity=self.quantity)

        message = f'Signal flipped. Closed previous position and opened new one with signal: {current_signal} at price: {current_price} <@176806410066067456>'
        logging.info(message)
        utils.send_discord_message(DataConfig.discord_webhook, content=message)

        # Open a new position with the flipped signal
        # if current_signal == 1:
        self.entry_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        order = self.order_manager.open_position_at_market(signal=current_signal, quantity=self.quantity)

        if order:
            current_positions = check_position(self.order_manager.fetch_current_positions())
            avg_fill_price = float(current_positions['entry_price'])
            message = f'Last order (open) average fill price: {avg_fill_price}, Current price: {current_price} <@176806410066067456>'
            utils.send_discord_message(DataConfig.discord_webhook, content=message)
            logging.info(message)

            real_time_position = 'short' if current_signal == -1 else 'long'
            real_time_entry_price = round(avg_fill_price, 1)
            stop_loss_price = real_time_entry_price * (
                    1 - self.stop_loss) if current_signal == 1 else real_time_entry_price * (1 + self.stop_loss)
            take_profit_price = real_time_entry_price * (
                    1 + self.take_profit) if current_signal == 1 else real_time_entry_price * (
                    1 - self.take_profit)
            self.stop_loss_price = round(stop_loss_price, 1)
            self.take_profit_price = round(take_profit_price, 1)
            self.order_manager.cancel_all_orders()
            self.order_manager.place_stop_loss_order(self.stop_loss_price, real_time_position, quantity=self.quantity)
            self.order_manager.place_take_profit_order(self.take_profit_price, real_time_position,
                                                       quantity=self.quantity)


def parse_strategy_args():
    """
    Parse and return command-line arguments for running the signal strategy.

    Returns:
        argparse.Namespace: Parsed arguments including privateKey, quoteSymbolQuantity,
                            take_profit, and stop_loss.
    """
    parser = argparse.ArgumentParser(description='Run the signal strategy.')
    parser.add_argument(
        '--privateKey',
        type=str,
        default='antique interest nerve mask sentence hour radar melt other limb pear flash',
        help='Private key for the API (e.g., the seed phrase)'
    )
    parser.add_argument(
        '--quoteSymbolQuantity',
        type=float,
        default=0.01,
        help='Quote symbol quantity to trade (default: 0.01)'
    )
    parser.add_argument(
        '--take_profit',
        type=float,
        default=0.0075,
        help='Take profit percentage (default: 0.0075)'
    )
    parser.add_argument(
        '--stop_loss',
        type=float,
        default=0.0075,
        help='Stop loss percentage (default: 0.0075)'
    )

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_strategy_args()

    setup_logging(debug=False)

    ticker = 'ETHUSD'
    minutes = 5
    data_ticker = TICKER_TO_DATA_TICKER[ticker]
    binance_ticker = BINANCE_TICKER_TO_BINANCE_TICKER[ticker]
    time_frame = '5m'
    datafile = f'{binance_ticker}_{time_frame}'
    model_path = './models/ETHUSDT_kaggle_features_transformed.joblib'
    features_path = './models/kaggle_features_transformed.joblib'

    feature_processor = data_processor.CryptoDataProcessor(ticker=binance_ticker, existing_filename=datafile,
                                                           db_path='./models/ETHUSDT_prod_features.sqlite', offset=60)
    binance_client = binance_client.BinanceClient(time_interval=minutes, symbol=binance_ticker)
    strategy = SignalStrategy(
        ticker=ticker,
        client_data=binance_client,
        data_processor=feature_processor,
        prob_threshold=0.5,
        smoothing_method='rolling',
        span=8,
        take_profit=args.take_profit,
        stop_loss=args.stop_loss,
        quote_symbol_quantity=args.quoteSymbolQuantity,
        trading_fee=0.0015,
        model_path=model_path,
        api_key=args.privateKey,
        features_path=features_path
    )
    # strategy.main()
    strategy.generate_position_value(df=None, signal_column=None)

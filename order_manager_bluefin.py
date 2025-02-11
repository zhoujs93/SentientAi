import os
import sys

here = os.path.dirname(__file__)
sys.path.append(os.path.join(here, '../'))
import logging, time
from decimal import Decimal
from bluefin_v2_client import (
    BluefinClient,
    Networks,
    MARKET_SYMBOLS,
    ORDER_SIDE,
    ORDER_TYPE,
    ORDER_STATUS,
    OrderSignatureRequest,
    interfaces
)
from pprint import pprint
import asyncio


class BluefinOrderManager:
    def __init__(self, private_key, trading_fee, quantity, symbol=MARKET_SYMBOLS.ETH):
        self.trading_fee = trading_fee
        self.quantity = quantity
        self.private_key = private_key
        self.network = Networks["SUI_PROD"]  # e.g., "SUI_PROD" or "SUI_STAGING"
        self.symbol = symbol
        self.leverage = 20
        self.client = None

        # Create a persistent event loop and set it as the current loop.
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Synchronously run the asynchronous client initialization.
        self._initialize_client_sync()

    def _initialize_client_sync(self):
        """Runs the asynchronous onboarding and initialization for the Bluefin client."""
        self.loop.run_until_complete(self._async_init())

    async def _async_init(self):
        self.client = BluefinClient(
            True,  # Agree to terms and conditions
            self.network,  # Use the provided network
            private_key=self.private_key
        )
        self.auth_token = await self.client.onboard_user(None)
        await self.client.init(True)
        logging.info("Bluefin client successfully initialized.")

    def place_stop_loss_order(self, stop_loss_price, real_time_position, quantity):
        """
        Synchronous wrapper to place a stop loss order using Bluefin's asynchronous API.
        """
        return self.loop.run_until_complete(
            self._async_place_stop_loss_order(stop_loss_price, real_time_position, quantity)
        )

    async def _async_place_stop_loss_order(self, trigger_price, real_time_position, quantity):
        """
        Asynchronously places a stop loss order:
          - Retrieves the current user leverage.
          - Adjusts the leverage.
          - Creates and signs a stop market order.
          - Posts the signed order.
        """
        # Determine the order side: if the position is long, a stop loss is a SELL order; otherwise BUY.
        side = ORDER_SIDE.SELL if real_time_position == 'long' else ORDER_SIDE.BUY

        # Retrieve current leverage (default is 3 on Bluefin)
        user_leverage = await self.client.get_user_leverage(self.symbol)
        logging.info("User Default Leverage: %s", user_leverage)

        # Create an order signature request (price is 0 for market orders).
        signature_request = OrderSignatureRequest(
            symbol=self.symbol,
            price=trigger_price,
            quantity=quantity,
            side=side,
            orderType=ORDER_TYPE.STOP_LIMIT,
            leverage=user_leverage,
            postOnly=True,  # Expires after 10 days.
            triggerPrice=trigger_price+1,
        )

        # Sign and post the order.
        signed_order = self.client.create_signed_order(signature_request)
        resp = await self.client.post_signed_order(signed_order)
        return resp

    def place_take_profit_order(self, take_profit_price, real_time_position, quantity=None):
        """
        Synchronous wrapper to place a take profit order.
        """
        if quantity is None:
            quantity = self.quantity
        return self.loop.run_until_complete(
            self._async_place_take_profit_order(take_profit_price, real_time_position, quantity)
        )

    async def _async_place_take_profit_order(self, take_profit_price, real_time_position, quantity):
        """
        Asynchronously places a take profit order:
          - Retrieves the current user leverage.
          - Adjusts the leverage.
          - Creates and signs a take profit market order.
          - Posts the signed order.
        """
        # For take profit orders: if you're long, you typically exit by selling and vice versa.
        side = ORDER_SIDE.SELL if real_time_position == 'long' else ORDER_SIDE.BUY

        # Retrieve current leverage.
        user_leverage = await self.client.get_user_leverage(self.symbol)
        logging.info("User Default Leverage: %s", user_leverage)

        # Create the order signature request.
        signature_request = OrderSignatureRequest(
            symbol=self.symbol,
            price=take_profit_price,
            quantity=quantity,
            side=side,
            orderType=ORDER_TYPE.LIMIT,
            leverage=user_leverage,
            postOnly=False,  # Expires after 10 days.
        )

        # Sign and post the order.
        signed_order = self.client.create_signed_order(signature_request)
        resp = await self.client.post_signed_order(signed_order)
        return resp

    def open_position_at_market(self, signal, quantity=None):
        """
        Synchronous wrapper to open a market position and wait for fill.
        """
        if quantity is None:
            quantity = self.quantity

        # Submit the market order.
        initial_response = self.loop.run_until_complete(
            self._async_open_position_at_market(signal, quantity)
        )
        if not initial_response:
            return None

        order_hash = initial_response.get("hash")
        if not order_hash:
            logging.error("Order hash missing in response.")
            return initial_response

        # Poll for the order to be filled.
        filled_order = self.loop.run_until_complete(self.wait_for_order_fill(order_hash))
        if filled_order:
            logging.info("Order filled: %s", filled_order)
            return filled_order
        else:
            logging.info("Order did not fill within the expected time frame.")
            return initial_response

    async def _async_open_position_at_market(self, signal, quantity):
        """
        Asynchronously opens a market position based on the signal.
          - Adjusts leverage.
          - Creates a signature request for a market order.
          - Signs and posts the order.
        """
        if signal == 1:
            side = ORDER_SIDE.BUY
        elif signal == -1:
            side = ORDER_SIDE.SELL
        else:
            logging.info('Invalid signal. No position opened.')
            return None

        if quantity <= 0:
            logging.info('Invalid quantity, cannot open position.')
            return None

        user_leverage = await self.client.get_user_leverage(self.symbol)

        signature_request = OrderSignatureRequest(
            symbol=self.symbol,
            price=0,
            quantity=quantity,
            side=side,
            orderType=ORDER_TYPE.MARKET,
            leverage=user_leverage,
            expiration=int((time.time() + 864000) * 1000)
        )

        signed_order = self.client.create_signed_order(signature_request)
        resp = await self.client.post_signed_order(signed_order)
        return resp

    def close_position_at_market(self, real_time_position, quantity=None):
        """
        Synchronous wrapper to close a position at market and wait for fill.
        """
        if quantity is None:
            quantity = self.quantity

        initial_response = self.loop.run_until_complete(
            self._async_close_position_at_market(real_time_position, quantity)
        )
        if not initial_response:
            return None

        order_hash = initial_response.get("hash")
        if not order_hash:
            logging.error("Order hash missing in response.")
            return initial_response

        filled_order = self.loop.run_until_complete(self.wait_for_order_fill(order_hash))
        if filled_order:
            logging.info("Order filled: %s", filled_order)
            return filled_order
        else:
            logging.info("Order did not fill within the expected time frame.")
            return initial_response

    async def _async_close_position_at_market(self, real_time_position, quantity):
        """
        Asynchronously closes a position at market.
        """
        side = ORDER_SIDE.SELL if real_time_position == 'long' else ORDER_SIDE.BUY

        if quantity <= 0:
            logging.info('Invalid quantity, cannot close position.')
            return None

        user_leverage = await self.client.get_user_leverage(self.symbol)

        signature_request = OrderSignatureRequest(
            symbol=self.symbol,
            price=0,
            quantity=quantity,
            side=side,
            orderType=ORDER_TYPE.MARKET,
            leverage=user_leverage,
            expiration=int((time.time() + 864000) * 1000)
        )

        signed_order = self.client.create_signed_order(signature_request)
        resp = await self.client.post_signed_order(signed_order)
        return resp

    def cancel_all_orders(self):
        """
        Synchronous wrapper to cancel all orders for the symbol.
        """
        return self.loop.run_until_complete(self._async_cancel_all_orders())

    async def _async_cancel_all_orders(self):
        orders = await self.client.get_orders({"symbol": self.symbol})
        order_hashes = [order['hash'] for order in orders]

        if not order_hashes:
            logging.info("No orders to cancel for symbol %s.", self.symbol)
            return None

        cancellation_request = self.client.create_signed_cancel_orders(
            self.symbol,
            order_hash=order_hashes
        )
        resp = await self.client.post_cancel_order(cancellation_request)
        logging.info("Cancellation response: %s", resp)
        return resp

    def fetch_current_positions(self):
        """
        Synchronous wrapper to fetch current positions.
        """
        position = self.loop.run_until_complete(self._async_fetch_current_position())
        position = self.parse_position_data(position)
        return position

    def get_order_sync(self):
        orders = self.loop.run_until_complete(self._async_get_orders())
        return orders

    async def _async_get_orders(self):
        orders = await self.client.get_orders(
            {
                "symbol": MARKET_SYMBOLS.ETH,
            },
        )
        return orders

    async def _async_fetch_current_position(self):
        position = await self.client.get_user_position({"symbol": self.symbol})
        return position

    async def wait_for_order_fill(self, order_hash, timeout=30, poll_interval=2):
        """
        Polls the order status until it is filled or a timeout is reached.

        If the order with the specified order_hash is not found, it waits one additional
        poll interval to double-check. If it is still not found, the function assumes that
        the order is filled.

        :param order_hash: The unique identifier of the order to track.
        :param timeout: Maximum time (in seconds) to wait.
        :param poll_interval: Time (in seconds) between checks.
        :return: The final order response if filled; otherwise, None.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            orders = await self.client.get_orders({"symbol": self.symbol})
            matching_order = next((order for order in orders if order.get("hash") == order_hash), None)

            if matching_order is None:
                logging.info("Order %s not found, double-checking...", order_hash)
                await asyncio.sleep(poll_interval)
                orders = await self.client.get_orders({"symbol": self.symbol})
                matching_order = next((order for order in orders if order.get("hash") == order_hash), None)
                if matching_order is None:
                    logging.info("Order %s not found after double-check; assuming it is filled.", order_hash)
                    # Optionally, you can return a constructed order response indicating FILLED status.
                    return {"orderStatus": "FILLED", "hash": order_hash}
            else:
                status = matching_order.get("orderStatus", "")
                logging.info("Polling order status: %s", status)
                if status == "FILLED":
                    return matching_order

            await asyncio.sleep(poll_interval)

        logging.warning("Order %s not filled within %s seconds.", order_hash, timeout)
        return None

    def parse_position_data(self, position: dict) -> dict:
        """
        Parses the position data returned by the Bluefin API, converting numeric
        values (scaled by 10**18, provided as strings) into floats.
        """
        keys_to_scale = [
            "avgEntryPrice", "indexPrice", "leverage", "liquidationPrice", "margin",
            "midMarketPrice", "netMargin", "oraclePrice", "positionSelectedLeverage",
            "positionValue", "quantity", "unrealizedProfit", "unrealizedProfitPercent",
            "fundingDue",
        ]

        parsed = {}
        for key, value in position.items():
            if key in keys_to_scale:
                try:
                    parsed[key] = float(Decimal(value) / Decimal(10 ** 18))
                except Exception as e:
                    logging.error("Error parsing key %s with value %s: %s", key, value, e)
                    parsed[key] = value
            else:
                parsed[key] = value
        return parsed

async def place_orders(client: BluefinClient):
    # Sign and place a limit order at 4x leverage. Order is signed using the account seed phrase set on the client
    adjusted_leverage = 20
    await client.adjust_leverage(MARKET_SYMBOLS.ETH, adjusted_leverage)
    signature_request = OrderSignatureRequest(
        symbol=MARKET_SYMBOLS.ETH,  # market symbol
        price=0,  # price at which you want to place order
        quantity=0.01,  # quantity
        side=ORDER_SIDE.SELL,
        orderType=ORDER_TYPE.MARKET,
        leverage=adjusted_leverage,
        expiration=int(
            (time.time() + 864000) * 1000
        ),  # expiry after 10 days, default expiry is a month
    )
    signed_order = client.create_signed_order(signature_request)
    resp = await client.post_signed_order(signed_order)
    print('MARKET ORDER RESPONSE IS')
    pprint(resp)
    order = await client.get_orders({
        "symbol": MARKET_SYMBOLS.ETH,
        "statuses": [ORDER_STATUS.PENDING]
    })
    pprint(order)
    return

async def place_stop_loss_orders(client: BluefinClient):
    # default leverage of account is set to 3 on Bluefin
    user_leverage = await client.get_user_leverage(MARKET_SYMBOLS.ETH)
    print("User Default Leverage", user_leverage)

    # Sign and place a limit order at 4x leverage. Order is signed using the account seed phrase set on the client
    adjusted_leverage = 20
    await client.adjust_leverage(MARKET_SYMBOLS.BTC, adjusted_leverage)
    signature_request = OrderSignatureRequest(
        symbol=MARKET_SYMBOLS.ETH,  # market symbol
        price=0,  # price at which you want to place order
        quantity=0.01,  # quantity
        side=ORDER_SIDE.SELL,
        orderType=ORDER_TYPE.STOP_MARKET,
        leverage=adjusted_leverage,
        expiration=int(
            (time.time() + 864000) * 1000
        ),  # expiry after 10 days, default expiry is a month
        triggerPrice=3500,
    )
    signed_order = client.create_signed_order(signature_request)
    resp = await client.post_signed_order(signed_order)
    pprint({"msg": "placing stop limit order", "resp": resp})

    # sleeping for 5 seconds
    # time.sleep(5)
    #
    # cancellation_request = client.create_signed_cancel_orders(
    #     MARKET_SYMBOLS.BTC, [resp["hash"]]
    # )
    #
    # cancel_resp = await client.post_cancel_order(cancellation_request)
    #
    # pprint(cancel_resp)
    return

async def cancel_all_orders(client):
    orders = await client.get_orders(
        {
            "symbol": MARKET_SYMBOLS.ETH,
        },
    )
    order_hash = []
    for order in orders:
        hash = order['hash']
        order_hash.append(hash)

    cancellation_request = client.create_signed_cancel_orders(
        MARKET_SYMBOLS.ETH, order_hash=order_hash
    )
    resp = await client.post_cancel_order(cancellation_request)

    pprint(resp)
    return


async def place_limit_order(client: BluefinClient):
    # get default leverage for market
    user_leverage = await client.get_user_leverage(MARKET_SYMBOLS.ETH)

    # creates a LIMIT order to be signed
    signature_request = OrderSignatureRequest(
        symbol=MARKET_SYMBOLS.ETH,  # market symbol
        price=3000,  # price at which you want to place order
        quantity=0.01,  # quantity
        side=ORDER_SIDE.SELL,
        orderType=ORDER_TYPE.LIMIT,
        leverage=user_leverage,
        postOnly=False,
    )
    # create signed order
    signed_order = client.create_signed_order(signature_request)

    print("Placing a limit order")
    # place signed order on orderbook
    resp = await client.post_signed_order(signed_order)

    # returned order with PENDING state
    pprint(resp)

    return


async def place_stop_limit_order(client: BluefinClient):
    # get default leverage for market
    user_leverage = await client.get_user_leverage(MARKET_SYMBOLS.ETH)

    # creates a STOP LIMIT order to be signed
    signature_request = OrderSignatureRequest(
        symbol=MARKET_SYMBOLS.ETH,  # market symbol
        price=1632.8,  # price at which you want to place order
        quantity=0.01,  # quantity
        side=ORDER_SIDE.SELL,
        orderType=ORDER_TYPE.STOP_LIMIT,
        triggerPrice=1633.0,
        leverage=user_leverage,
        postOnly=True,
    )

    # create signed order
    signed_order = client.create_signed_order(signature_request)

    print("Placing a stop limit order")
    # place signed order on orderbook
    resp = await client.post_signed_order(signed_order)

    # returned order with STANDBY_PENDING state
    pprint(resp)

    return

async def main():
    # privateKey = "frozen frame craft weapon happy club news finish orient sponsor flock flame"
    privateKey = 'antique interest nerve mask sentence hour radar melt other limb pear flash'
    client = BluefinClient(
        True,  # agree to terms and conditions
        Networks["SUI_PROD"],  # SUI_STAGING or SUI_PROD
        private_key=privateKey  # seed phrase of the wallet
    )
    auth_token = await client.onboard_user(None)
    await client.init(True)

    print('Account address:', client.get_public_address())
    # gets user account on-chain data
    data = await client.get_user_account_data()
    # check usdc balance deposited to Bluefin Margin Bank
    # checks SUI token balance
    t = await client.get_native_chain_token_balance()
    print("Chain token balance:", await client.get_native_chain_token_balance())

    x = await client.get_usdc_balance()
    print("USDC balance:", await client.get_usdc_balance())

    # x = await client.deposit_margin_to_bank(6)
    bal = await client.get_margin_bank_balance()
    # check usdc balance deposited to Bluefin Margin Bank
    print("Margin bank balance:", await client.get_margin_bank_balance())

    # await place_orders(client)
    # await asyncio.sleep(2)

    position = await client.get_user_position({"symbol":MARKET_SYMBOLS.ETH})
    pprint(position)

    # await place_stop_loss_orders(client)
    # await place_limit_order(client)
    # await place_stop_limit_order(client)

    await asyncio.sleep(2)
    orders = await client.get_orders(
        {
            "symbol": MARKET_SYMBOLS.ETH,
        },
    )
    print(f'Open orders are:')
    pprint(orders)
    #
    await cancel_all_orders(client)
    # await asyncio.sleep(2)
    #
    # orders = await client.get_orders(
    #     {
    #         "symbol": MARKET_SYMBOLS.ETH,
    #     },
    # )
    # print(f'ORDERS AFTER CANCELLING IS:')
    # pprint(orders)

    return await client.close_connections()

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
    loop.close()
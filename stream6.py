import pandas as pd
import requests
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go
import json

# Load the configuration file
with open("config.json") as config_file:
    config = json.load(config_file)

# Use the API key from the configuration file
coinglass_api_key = config["coinglassSecret"]


class CoinGlassAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://open-api.coinglass.com"
        self.headers = self._get_headers()

    def _get_headers(self):
        return {
            "accept": "application/json",
            "coinglassSecret": self.api_key,
        }

    def _request(self, endpoint, params=None):
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = (
                f"HTTP error occurred: {e.response.status_code} {e.response.reason}"
            )
            print(error_msg)
            try:
                error_details = e.response.json()
                print(f"Error details: {error_details}")
            except json.JSONDecodeError:
                print("No detailed error message available from API.")

            raise e

    def get_available_pairs(self, coin):
        endpoint = "/public/v2/instrument"
        params = {"symbol": coin}
        data = self._request(endpoint, params=params)
        pairs = []
        for exchange, instruments in data["data"].items():
            for item in instruments:
                if coin.upper() in [
                    item["baseAsset"].upper(),
                    item["quoteAsset"].upper(),
                ]:
                    pairs.append(
                        {"exchange": exchange, "instrumentId": item["instrumentId"]}
                    )

        return pd.DataFrame(pairs)

    def fetch_ohlc_oi_data(self, exchange, pair):
        endpoint = "/public/v2/indicator/open_interest_ohlc"
        params = {
            "ex": exchange,
            "pair": pair,
            "interval": "h24",
            "limit": 50,
        }
        try:
            request = self._request(endpoint, params=params)
            df = pd.DataFrame(request["data"])
            df["t"] = pd.to_datetime(df["t"], unit="ms").dt.date
            df = df.sort_values("t", ascending=False)
            return df
        except requests.exceptions.HTTPError as err:
            print(f"HTTP error occurred: {err}")
            raise

    def fetch_price_ohlc_data(self, exchange, pair, interval="h24", limit=50):
        endpoint = "/public/v2/indicator/price_ohlc"
        params = {"ex": exchange, "pair": pair, "interval": interval, "limit": limit}
        try:
            request = self._request(endpoint, params=params)
            df = pd.DataFrame(request["data"], columns=["t", "o", "h", "l", "c", "v"])
            df["t"] = pd.to_datetime(df["t"], unit="s").dt.date
            df = df.sort_values("t", ascending=False)
            return df
        except requests.exceptions.HTTPError as err:
            print(f"HTTP error occurred: {err}")
            raise

    def fetch_top_long_short_ratio(self, exchange, pair, interval="h24", limit=50):
        endpoint = "/public/v2/indicator/top_long_short_account_ratio"
        params = {"ex": exchange, "pair": pair, "interval": interval, "limit": limit}
        try:
            request = self._request(endpoint, params=params)
            df = pd.DataFrame(request["data"])
            df["createTime"] = pd.to_datetime(df["createTime"], unit="ms")
            df = df.sort_values("createTime", ascending=False)
        except requests.exceptions.HTTPError as err:
            print(f"HTTP error occured: {err}")
            raise

        return df

    def fetch_top_long_short_position_ratio(
        self, exchange, pair, interval="h24", limit=50
    ):
        endpoint = "/public/v2/indicator/top_long_short_position_ratio"
        params = {"ex": exchange, "pair": pair, "interval": interval, "limit": limit}
        try:
            request = self._request(endpoint, params=params)
            df = pd.DataFrame(request["data"])
            df["createTime"] = pd.to_datetime(df["createTime"], unit="ms")
            df = df.sort_values("createTime", ascending=False)
        except requests.exceptions.HTTPError as err:
            print(f"HTTP error occured: {err}")
            raise

        return df

    def fetch_top_long_short_loser(self, exchange, pair, interval="h24", limit=50):
        endpoint = "/public/v2/indicator/long_short_accounts"
        params = {"ex": exchange, "pair": pair, "interval": interval, "limit": limit}
        try:
            request = self._request(endpoint, params=params)
            df = pd.DataFrame(request["data"])
            df["createTime"] = pd.to_datetime(df["createTime"], unit="ms")
            df = df.sort_values("createTime", ascending=False)
        except requests.exceptions.HTTPError as err:
            print(f"HTTP error occured: {err}")
            raise

        return df


################################################################################################################


class CoinGlassPlotter:
    @staticmethod
    def plot_closing_prices(df, title):
        fig = px.line(
            df, x="t", y="c", title=title, labels={"c": "Closing Price", "t": "Date"}
        )
        return fig

    @staticmethod
    def plot_candlestick_chart(df, title="OHLC Candlestick Chart"):
        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=df["t"], open=df["o"], high=df["h"], low=df["l"], close=df["c"]
                )
            ],
            layout=go.Layout(
                title=title,
                xaxis_title="Date",
                yaxis_title="Price",
                xaxis_rangeslider_visible=False,
            ),
        )
        return fig

    @staticmethod
    def plot_long_short_ratios(df, title="Top Traders Accounts Ratio"):
        fig = px.line(
            df,
            x="createTime",
            y=["longRatio", "shortRatio"],
            title=title,
            labels={
                "createTime": "Date",
                "variable": "Ratio Type",
                "value": "Ratio (%)",
            },
            color_discrete_sequence=["green", "red"],
        )
        fig.update_layout(yaxis=dict(range=[0, 100], dtick=10, title="Percentage"))
        return fig


################################################################################################################


def main():
    st.set_page_config(layout="wide", page_icon="🧊")
    st.title("Coin Advanced Metrics")

    # Load the configuration file
    with open("config.json") as config_file:
        config = json.load(config_file)

    # Create an instance of the CoinGlassAPI with the API key
    coinglass_api = CoinGlassAPI(api_key=config["coinglassSecret"])

    # User input for coin
    coin = st.text_input("Enter the coin symbol (e.g., BTC):").upper()
    if coin:
        # Fetch available pairs
        available_pairs_df = coinglass_api.get_available_pairs(coin)
        if not available_pairs_df.empty:
            # User input for exchange and pair
            selected_exchange = st.selectbox(
                "Select Exchange", available_pairs_df["exchange"].unique()
            )
            selected_pair = st.selectbox(
                "Select Pair",
                available_pairs_df.query("exchange == @selected_exchange")[
                    "instrumentId"
                ],
            )

            # Fetch and display data on button click
            if st.button("Fetch Data"):
                col1, col2, col3, col4, col5 = st.columns(5)
                # Fetch and display data on button click
                with col1:
                    ohlc_oi_data = coinglass_api.fetch_ohlc_oi_data(
                        selected_exchange, selected_pair
                    )
                    latest_oi = ohlc_oi_data.iloc[-1]["c"]
                    st.metric("Open Interest", f"{latest_oi:,} {coin}")
                    fig_oi = CoinGlassPlotter.plot_closing_prices(
                        ohlc_oi_data, "Open Interest"
                    )
                with col2:
                    price_ohlc_data = coinglass_api.fetch_price_ohlc_data(
                        selected_exchange, selected_pair
                    )
                    latest_close = price_ohlc_data.iloc[0]["c"]
                    st.metric("Price", f"${latest_close}")
                    fig_price = CoinGlassPlotter.plot_candlestick_chart(
                        price_ohlc_data, "Price"
                    )
                with col3:
                    long_short_data = coinglass_api.fetch_top_long_short_ratio(
                        selected_exchange, selected_pair
                    )
                    latest_long_ratio = long_short_data.iloc[0]["longRatio"]
                    latest_short_ratio = long_short_data.iloc[0]["shortRatio"]
                    st.metric(
                        "Top Accounts Ratio",
                        f"{latest_long_ratio}/{latest_short_ratio}",
                    )
                    fig_ratio = CoinGlassPlotter.plot_long_short_ratios(long_short_data)
                with col4:
                    top_traders_data = (
                        coinglass_api.fetch_top_long_short_position_ratio(
                            selected_exchange, selected_pair
                        )
                    )
                    latest_long_position_ratio = top_traders_data.iloc[0]["longRatio"]
                    latest_short_position_ratio = top_traders_data.iloc[0]["shortRatio"]
                    st.metric(
                        "Top Traders Position  Ratios",
                        f"{latest_long_position_ratio}/{latest_short_position_ratio}",
                    )
                    fig_top_traders_ratio = CoinGlassPlotter.plot_long_short_ratios(
                        top_traders_data
                    )
                # Create columns for the top row side-by-side display
                top_col1, top_col2 = st.columns(2)
                # Display top row plots
                with top_col1:
                    st.plotly_chart(fig_price)
                with top_col2:
                    st.plotly_chart(fig_oi)
                # Create columns for the bottom row side-by-side display
                bottom_col1, bottom_col2 = st.columns(2)
                # Display bottom row plots
                with bottom_col1:
                    st.plotly_chart(fig_ratio)
                with bottom_col2:
                    st.plotly_chart(fig_top_traders_ratio)
                # Create columns for the bottombottom row side by side
                bot2, bot3 = st.columns(2)
                with bot2:
                    L_data = coinglass_api.fetch_top_long_short_loser(
                        selected_exchange, selected_pair
                    )
                    L_plot = CoinGlassPlotter.plot_long_short_ratios(
                        L_data, "Total Accounts"
                    )
                    st.plotly_chart(L_plot)

                with col5:
                    latest_long_ratio = L_data.iloc[-1]["longRatio"]
                    latest_short_ratio = L_data.iloc[-1]["shortRatio"]
                    st.metric(
                        "All Accounts Ratio",
                        f"{latest_long_ratio}/{latest_short_ratio}",
                    )


if __name__ == "__main__":
    main()

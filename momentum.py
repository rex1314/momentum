import sys
import pandas as pd
import numpy as np
import json 
import os
from datetime import date
from scipy.stats import linregress

pd.set_option('display.max_rows', None)
pd.set_option('display.width', None)
pd.set_option('display.max_columns', None)

# TICKER_DATA_INPUT = "sp500-nasdaq-daily-{}.json".format(date.today())
TICKER_DATA_INPUT = os.path.join("data", "tickers_data.json")
ACCOUNT_VALUE = 5000
RISK_FACTOR = 0.0025

if not os.path.exists('output'):
    os.makedirs('output')

def read_json(json_file):
    with open(json_file, "r") as fp:
        return json.load(fp)

def momentum(closes):
    """Calculates slope of exp. regression normalized by rsquared"""
    returns = np.log(closes)
    indices = np.arange(len(returns))
    slope, _, r, _, _ = linregress(indices, returns)
    # return ((1 + slope) ** 253) * (r**2)
    return (((np.exp(slope) ** 253) - 1) * 100) * (r**2)

def atr_20(candles):
    """Calculates last 20d ATR"""
    daily_atrs = []
    for idx, candle in enumerate(candles):
        high = candle["high"]
        low = candle["low"]
        prev_close = 0
        if idx > 0:
            prev_close = candles[idx - 1]["close"]
        daily_atr = max(high-low, np.abs(high - prev_close), np.abs(low - prev_close))
        daily_atrs.append(daily_atr)
    return pd.Series(daily_atrs).rolling(20).mean().tail(1).item()

def positions():
    """Returns a dataframe doubly sorted by deciles and momentum factor, with atr and position size"""
    json = read_json(TICKER_DATA_INPUT)
    momentums = []
    ranks = []
    for ticker in json:
        closes = []
        for candle in json[ticker]["candles"]:
            closes.append(candle["close"])
        if closes:
            diffs = np.abs(pd.Series(closes).pct_change().diff()).dropna()
            gaps = diffs[diffs > 0.15]
            ma = pd.Series(closes).rolling(100).mean().tail(1).item()
            if ma > closes[-1]:
                print("Ticker %s below 100d moving average." % ticker)
                print(momentum(pd.Series(closes).tail(90)))
            elif len(gaps):
                print("Ticker %s has a gap > 15%%" % ticker)
                print(momentum(pd.Series(closes).tail(90)))
            else:
                momentums.append((0, ticker, momentum(pd.Series(closes).tail(90)), atr_20(json[ticker]["candles"]), closes[-1]))
                ranks.append(len(ranks)+1)
    titleRank = "Rank"
    titleTicker = "Ticker"
    titleMom = "Momentum (%)"
    titleRisk = "ATR20d"
    titlePrice = "Price"
    titleAmount = "Shares"
    titlePosSize = "Position ($)"
    df = pd.DataFrame(momentums, columns=[titleRank, titleTicker, titleMom, titleRisk, titlePrice])
    # df["decile"] = pd.qcut(df["momentum %"], 10, labels=False)
    df[titleAmount] = (np.floor(ACCOUNT_VALUE * RISK_FACTOR / df[titleRisk])).astype(int)
    df[titlePosSize] = np.round(df[titleAmount] * df[titlePrice], 2)
    df = df.sort_values(([titleMom]), ascending=False)
    df[titleRank] = ranks
    df.head(50).to_csv(os.path.join("output", "momentum_positions.csv"), index = False)

    watchlist = open(os.path.join("output", "Momentum.txt"), "w")
    watchlist.write(','.join(df.head(50)[titleTicker]))
    watchlist.close()

    return df
if __name__ == "__main__":
   positions = positions() 
   print(positions)

import os
import yfinance as yf
from datetime import datetime
import pandas as pd
import numpy as np
import pytz
import logging
import plotly.graph_objects as go
from PIL import Image

import matplotlib.pyplot as plt


def init_logging():
    global tz
    tz = pytz.timezone('US/Eastern')
    if not os.path.exists('log'):
        os.makedirs('log')

    date = datetime.now(tz).date().strftime('%Y%m%d')
    logging.basicConfig(filename='log/{}.log'.format(date), level=logging.INFO)

    return None


def dta_to_candlestick(data):
    l = len(data)
    # Make candlestick picture
    layout = go.Layout(xaxis=dict(ticks='',
                                  showgrid=False,
                                  showticklabels=False,
                                  rangeslider=dict(visible=False)),
                       yaxis=dict(ticks='',
                                  showgrid=False,
                                  showticklabels=False),
                       width=256,
                       height=256,
                       paper_bgcolor='rgba(0,0,0,0)',
                       plot_bgcolor='rgba(0,0,0,0)')
    fig = go.Figure(data=[go.Candlestick(x=np.linspace(1,l,l),
                                         open=data.Open,
                                         high=data.High,
                                         low=data.Low,
                                         close=data.Close)],
                    layout=layout)
    fig.write_image("images/fig-1.png")

    # Convert to numpy array
    im = Image.open('images/fig-1.png')

    # im = im.resize((300,300),Image.ANTIALIAS)
    data = np.asarray(im)

    # Return the first channel of the image
    return data[:, :, 0]


def dta_transformation(data, est_h):
    # Make sure data has sufficient columns
    assert 'Open' in data.columns
    assert 'High' in data.columns
    assert 'Low' in data.columns
    assert 'Close' in data.columns

    data['lag_close'] = data['Close'].shift(1)
    data['Indicator'] = np.where(data['Close'] > data['lag_close'], 1, 0)

    x = []
    y = []
    for i in range(est_h, data.shape[0]):
        sub_dta = data.iloc[i - est_h:i]

        y_i = data.iloc[i]['Indicator']
        x_i = dta_to_candlestick(sub_dta)

        y.append(y_i)
        x.append(x_i)

        print("{}/{}".format(i - est_h, data.shape[0] - est_h))

    return x, y


if __name__ == '__main__':

    txt_file = open('ticker_list.txt', 'r')
    sp500_list = [line.rstrip('\n') for line in txt_file]

    START = datetime(1980, 1, 1)
    END = datetime(2020, 4, 23)
    init_logging()

    for ticker in sp500_list[18:100]:
        tic = yf.Ticker(ticker)
        hist = tic.history(start=START, end=END)
        if hist.shape[0] > 1000:
            x, y = dta_transformation(hist, 10)
            x = np.stack(x, axis=2)

            L = x.shape[2] // 1000
            remainder = x.shape[2] % 1000

            for i in range(L):
                sub_x = x[:, :, (1000 * i + remainder):(1000 * (i + 1) + remainder)]
                sub_y = y[(1000 * i + remainder):(1000 * (i + 1) + remainder)]
                if not os.path.exists('images_npy-1/{}'.format(ticker)):
                    os.makedirs('images_npy-1/{}'.format(ticker))
                np.savez_compressed('images_npy-1/{}/{}_{}'.format(ticker, ticker, i), x=sub_x, y=sub_y)

            print("\n")
            status = "Successfully retrieve {}'s data.".format(ticker)
            print(status)
            logging.info(status)
            print("\n")

        else:
            print("\n")
            status = "Insufficient data for {}.".format(ticker)
            print(status)
            logging.info(status)
            print("\n")


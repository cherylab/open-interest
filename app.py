import pandas as pd
import requests
import json
# from pandas.io.json import json_normalize
from functools import reduce
from datetime import datetime, timedelta
import openpyxl
import time
from time import mktime
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objs import *
from plotly.graph_objs.scatter.marker import Line
from plotly.subplots import make_subplots
import xlrd
import openpyxl
import numpy as np
import re
from bs4 import BeautifulSoup
import math
import plotly.io as pio
import plot_settings
from multiapp import MultiApp
import streamlit as st
import yfinance as yf
import plot_functions
# import pkg_resources

st.set_page_config(layout='wide')

GOOD_FRIDAYS = [datetime(2022,4,15), datetime(2023,4,7), datetime(2024,3,29)]
THURS_BEFORE = [x - timedelta(days=1) for x in GOOD_FRIDAYS]

# dictionary of tickers and google drive links 
GOOGLE_DRIVE_URL_DICT = {
    'AAPL':'https://docs.google.com/spreadsheets/d/1RpshZrtU_nAzhBwiiYv5CTGRQPJgjycs/edit?usp=sharing&ouid=109079795382383182623&rtpof=true&sd=true',
    'QQQ':'https://docs.google.com/spreadsheets/d/1ezfvowAhV5wRX7tW_QzFfzv6SJDy8-iS/edit?usp=sharing&ouid=109079795382383182623&rtpof=true&sd=true'
}

#     'QQQ':'https://docs.google.com/spreadsheets/d/1ezfvowAhV5wRX7tW_QzFfzv6SJDy8-iS/edit?usp=sharing&ouid=109079795382383182623&rtpof=true&sd=true'

# function to get excel file from google drive
#@st.cache(allow_output_mutation=True)
@st.cache_data
def pull_google_drive_excel(url, sheet_name=""):
    file_id = url.split('/')[-2]
    dwn_url = "https://drive.google.com/uc?id=" + file_id
    tmp = pd.read_excel(dwn_url, sheet_name=sheet_name)
    return tmp

# function to get file from google drive
@st.cache_data
def pull_google_drive(url):
    file_id = url.split('/')[-2]
    dwn_url = "https://drive.google.com/uc?id=" + file_id
    tmp = pd.read_csv(dwn_url)
    # tmp = pd.read_excel(dwn_url)
    return tmp


def reformat_dfs(d):
#     st.dataframe(d)
    d = d[d.expiration_date.notnull()]

    # reformat date columns
    date_cols = ['expiration_date', 'expiration_date_p']
    for c in date_cols:
#         st.write(c)
        d[c] = pd.to_datetime(d[c])



    d['pulldate'] = pd.to_datetime(d.pulldate)
    d['daywk'] = d.pulldate.dt.strftime('%a')
    d['pulldate_label'] = [f"{x}<br>{y.strftime('%b-%d')}" for (x,y) in zip(d.daywk, d.pulldate)]

    calls = d.filter(['strike', 'open_int', 'expiration_date', 'root_sym', 'pulldate', 'daywk', 'pulldate_label'])
    calls['type'] = 'Call'
    puts = d.filter(['strike', 'open_int_p', 'expiration_date', 'root_sym', 'pulldate', 'daywk', 'pulldate_label'])
    puts['type'] = 'Put'
    puts = puts.rename(columns={'open_int_p': 'open_int'})
    df = pd.concat([calls, puts])

    # filter to only Fridays and Thursdays before Good Friday
    df['expiration_daywk'] = df.expiration_date.dt.strftime('%a')
    df = df[(df.expiration_daywk=='Fri') | (df.expiration_date.isin(THURS_BEFORE))]

    return df

# NOT USED
@st.cache_data
def pull_yahoo(ticker, start, end):
    yahoo = yf.Ticker(ticker)
    yahoohist = yahoo.history(start = start, end = end + timedelta(days=1))

    if len(yahoohist)==0:
        yahoo_failed = True
    else:
        yahoo_failed = False

    return yahoohist, yahoo_failed

# calculate what days have elapsed this week since monday
def calc_dates_this_week():
    # get today's date
    latest_weekday = datetime.today().date()
    # calculate the most recent monday (today if running on a monday)
    last_monday = latest_weekday - timedelta(days=latest_weekday.weekday())
    # calculate previous monday
    last_last_monday = last_monday - timedelta(days=7)

    # if running on a saturday (5) or sunday (6), pull most recent friday
    if latest_weekday.weekday() in [5, 6]:
        latest_weekday = latest_weekday - timedelta(days=latest_weekday.weekday()) + timedelta(days=4)

    # if latest_weekday == Good Friday, change to Thursday before
    if latest_weekday in GOOD_FRIDAYS:
        latest_weekday = latest_weekday - timedelta(days=1)

    dates = pd.date_range(last_monday, latest_weekday, freq='d').strftime('%Y-%m-%d').tolist()

    # current and next Friday (as options in the dropdown for week)
    # change any Good Friday to be Thursday before
    current_friday = last_monday + timedelta(days=4) # treats saturday/sunday as belonging to previous weekdays
    next_friday = current_friday + timedelta(days=7)
    two_fridays = current_friday + timedelta(days=14)
    last_friday = current_friday - timedelta(days=7)

    friday_options = [last_friday, current_friday, next_friday, two_fridays]

    for i in range(len(friday_options)):
        if friday_options[i] in [x.date() for x in GOOD_FRIDAYS]:
            friday_options[i] = friday_options[i] - timedelta(days=1)

    return dates, friday_options, last_last_monday

def sidebar_config(GOOGLE_DRIVE_URL_DICT):
    st.sidebar.write('<br>', unsafe_allow_html=True)
    company = st.sidebar.selectbox('Ticker', options=['QQQ','AAPL'], index=0)

    # return a list of dates that have elapsed since monday to use as sheet names in the google drive imports
    dates, fridays, last_week_monday = calc_dates_this_week()

    week = st.sidebar.selectbox('Contract Expiration Date (Fridays only - use Thursday for week of Good Friday)',
                                options=[pd.to_datetime(str(x)).strftime('%b %d, %Y') for x in fridays],
                                index=1)

    if week == fridays[0].strftime('%b %d, %Y'):
        dates = pd.date_range(last_week_monday, fridays[0], freq='d').strftime('%Y-%m-%d').tolist()

    daily_dfs = []
    missing_dates = []

    for day in dates:
        try:
            df_orig = pull_google_drive_excel(GOOGLE_DRIVE_URL_DICT[company], sheet_name=day)
            # st.write("orig", df_orig)
            df = df_orig.copy()
            df['pulldate'] = day

            # filter and reformat column names so don't have issues when concatenating
            cols_keep = [x for x in df.columns if not x.startswith('Unnamed')]
            df = df[cols_keep]
            df.columns = [
                x.replace('\xa0', '').replace(' ', '_').replace('__', '_').replace('.', '').replace('1', '_p').lower()
                for x in df.columns]
            daily_dfs.append(df)
        except ValueError:
            missing_dates.append(pd.to_datetime(day).strftime('%b %d (%a)'))

#     st.write(daily_dfs)

    if missing_dates != []:
        st.sidebar.write(f"No {company} data pulled for {', '.join(missing_dates)}.<br>", unsafe_allow_html=True)

    if len(daily_dfs) == 0:
        st.warning(f"No data has been pulled from the week of {fridays[1].strftime('%b %d, %Y')}. "
                   "You may either upload data from that week, or choose to view Call & Put volumes from the prior "
                   "week.")
        st.stop()
        dfs = []
    elif len(daily_dfs) == 1:
        dfs = daily_dfs[0]
        dfs = reformat_dfs(dfs)
    else:
        dfs = pd.concat(daily_dfs)
        dfs = reformat_dfs(dfs)

    return dfs, company, week, fridays

def yahoo_pull(company, start, end):
    yahoo = yf.Ticker(company)
    yahoohist = yahoo.history(start=start, end=end+timedelta(days=1))
    yahoohist = yahoohist.reset_index()
    if len(yahoohist)!=0:
        yahoohist = yahoohist.assign(daywk=lambda t: t['Date'].dt.strftime('%a'))
    return yahoohist

def callput_page():
    st.title('Call & Put Volumes')

    url = 'https://drive.google.com/file/d/1pbQacz0l7oAyoDpK8CMrR-4W3ZgmOM7i/view?usp=sharing'
    df = pull_google_drive(url)
    df = reformat_dfs(df)

    company = st.sidebar.selectbox('Ticker', options=['AAPL'], index=0)

    col1, sp, col2, sp2, col3, sp3 = st.columns((.2, .05, .1, .05, .2, .05))
    week = col1.selectbox('Week Ending',
                        options=[pd.to_datetime(str(x)).strftime('%b %d, %Y') for x in df.expiration_date.unique()],
                        index=0)

    rangecalc = col2.radio('Range Calculation', options = ['Default', 'Manual'], index=0)

    week = datetime.strptime(week, '%b %d, %Y')
    start = week - timedelta(days=4)

    dfs = df[df.expiration_date==week]

    yahoohist, yahoo_failed = pull_yahoo(company, start, week)

    if yahoo_failed==False:
        close = yahoohist['Close'][-1]
        range_st = close - close * .08
        range_end = close + close * .08
    else:
        close = dfs[dfs.cvol==dfs.cvol.max()]['strike'].values[0]
        range_st = close - close * .15
        range_end = close + close * .15

    if rangecalc == 'Manual':
        with col3.form("manual_dates"):
            range_st = st.number_input('Min', value=close-close*.08, min_value=0., max_value=close*2.)
            range_end = st.number_input('Max', value=close+close*.08, min_value=0., max_value=close*2.)
            st.form_submit_button('Submit')

    pltdf1 = dfs.filter(['strike', 'cvol', 'expiration_date', 'root_sym'])
    pltdf1['type'] = 'call'
    pltdf2 = dfs.filter(['strike', 'cvol_p', 'expiration_date', 'root_sym'])
    pltdf2['type'] = 'put'
    pltdf2 = pltdf2.rename(columns={'cvol_p': 'cvol'})
    pltdf = pd.concat([pltdf1, pltdf2])

    # get min and max strike prices within the range_st-range_end calculated above based on 8%
    latest = pltdf[(pltdf.strike >= range_st) & (pltdf.strike <= range_end)]
    tru_rangest = latest.strike.min()
    tru_rangeend = latest.strike.max()
    latest = latest[latest.strike == latest.strike.max()]
    latest = latest.reset_index(drop=True)

    fig = px.scatter(pltdf,
                     x='strike',
                     y='cvol',
                     color='type',
                     labels={'strike': 'Strike Price', 'cvol': 'Volume', 'type': 'Type'},
                     color_discrete_sequence=[plot_settings.color_list[4], plot_settings.color_list[1]]).update_traces(
        mode='lines')

    if yahoo_failed==False:
        fig.add_vline(x=yahoohist['Open'][0],
                      line_width=2.,
                      line_dash="dot",
                      line_color="#919191",
                      annotation_text=f" Open: {yahoohist['Open'][0]:,.0f}",
                      annotation_position="top",
                      annotation_textangle=-90,
                      annotation_font_size=10.5,
                      annotation_font_color="#919191")

        fig.add_vline(x=yahoohist['Close'][-1],
                      line_width=2.5,
                      line_dash="dot",
                      line_color="#121212",
                      annotation_text=f" Close: {yahoohist['Close'][-1]:,.0f}",
                      annotation_align='left',
                      annotation_position="top",
                      annotation_textangle=-90,
                      annotation_font_size=10.5,
                      annotation_font_color='#121212')

    fig.update_layout(template=plot_settings.dockstreet_template,
                      margin=dict(t=100),
                      plot_bgcolor='white',
                      legend_title="",
                      title=dict(font_size=22,
                                 x=0.03,
                                 y=.98,
                                 yref='container',
                                 text=f"<b>{company}: Calls & puts for week ending {week.strftime('%b %-d, %Y')}</b>",
                                 font_color="#4c4c4c",
                                 xanchor='left'),
                      legend=dict(
                          font=dict(size=14)
                      ))

    fig.update_xaxes(showgrid=False,
                     range=[tru_rangest - 1, tru_rangeend])

    for ser in fig['data']:
        ser['name'] = ser['name'].title()

    st.write('<br><br>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)

    if yahoo_failed:
        st.write('Yahoo does not yet have price information for the chosen week.')

def animate_page(GOOGLE_DRIVE_URL_DICT):
    st.title('Call & Put Volumes Timelapse')

    # st.title('Installed Packages')
    # installed_packages = [(d.project_name, d.version) for d in pkg_resources.working_set]
    # for package in sorted(installed_packages):
    #     st.text(f'{package[0]}=={package[1]}')

    df, company, week, fridays = sidebar_config(GOOGLE_DRIVE_URL_DICT)

    week = datetime.strptime(week, '%b %d, %Y')
    df = df[df.expiration_date == week]

    # determine if yahoo prices are "past prices" because week chosen hasn't started yet
    future_week_bool = True if week.date() > fridays[1] else False

    yahoohist = yahoo_pull(company, df.pulldate.min(), df.pulldate.max())

    # if there's yahoo data, figure out the mins and maxs for the plot ranges based on strike prices,
    # otherwise, base ranges off all the data collected from CoT for that date range
    if len(yahoohist)!=0:
        # come up with ranges for the plot (typically have a cutoff around 80% of price)
        min_close = yahoohist['Close'].min()
        max_close = yahoohist['Close'].max()
        range_st = min_close - min_close*.08
        range_end = max_close + max_close*.08
        df = df[(df.strike >= range_st) & (df.strike <= range_end)]
    else:
        rangex = df.strike.max() - df.strike.min()
        rangemid = df.strike.min() + (rangex/2)
        range_st = df.strike.min() + rangemid*.2
        range_end = df.strike.max() - rangemid*.2

    df = df[(df.strike>=range_st) & (df.strike<=range_end)]

    x_range_st = df.strike.min()
    x_range_end = df.strike.max()

    y_range_st = df.open_int.min()
    y_range_end = df.open_int.max() + 2

    st.write('<br><br>', unsafe_allow_html=True)
    plot_functions.animation_volume(df,
                                    yahoohist,
                                    x_range_st,
                                    x_range_end,
                                    y_range_st,
                                    y_range_end,
                                    company,
                                    week,
                                    future_week=future_week_bool)

 



def create_app_with_pages():
    # CREATE PAGES IN APP
    app = MultiApp()
    app.add_app("Call & Put Volume Timelapse", animate_page, [GOOGLE_DRIVE_URL_DICT])
    # app.add_app("Call & Put Volumes", callput_page, [])
    app.run(logo_path='logo.png')

if __name__ == '__main__':
    create_app_with_pages()

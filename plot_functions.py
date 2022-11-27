import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objs import *
from plotly.graph_objs.scatter.marker import Line
from plotly.subplots import make_subplots
import numpy as np
import plot_settings
import streamlit as st


def animation_volume(df, yahoohist, x_range_st, x_range_end, y_range_st, y_range_end, company, week, future_week=False):
    contracts = ['Call','Put']

    weekdays = ['Mon','Tue','Wed','Thu','Fri']
    days = [wd for wd in weekdays if wd in df.daywk.values.tolist()]
    day_labels = df.pulldate_label.unique().tolist()

    fig_dict = {'data':[],
                'layout':{},
                'frames':[]}

    fig_dict["layout"]["xaxis"] = {"showgrid": False,
                                   "range": [x_range_st - 1, x_range_end + 1],
                                   "title": "Strike Price"}
    fig_dict["layout"]["yaxis"] = {"range": [y_range_st-10, y_range_end],
                                   "title": "Open Interest"}
    fig_dict["layout"]["hovermode"] = "x"
    fig_dict['layout']['template'] = plot_settings.dockstreet_template
    fig_dict['layout']['plot_bgcolor'] = 'white'
    fig_dict['layout']['height'] = 600
    fig_dict['layout']['margin'] = {'t': 110}
    fig_dict['layout']['legend'] = {'title': '',
                                    'font_size': 14}
    fig_dict['layout']['title'] = {'font_size': 22,
                                   'x': 0.03,
                                   'y': 1,
                                   'yref': 'container',
                                   'text': f"<b>{company}: Calls & puts for contracts expiring {week.strftime('%b %-d, %Y')}</b>",
                                   'font_color': '#4c4c4c',
                                   'xanchor': 'left'}
    if len(days) > 1:
        fig_dict["layout"]["updatemenus"] = [
            {'buttons': [{'args': [None, {'frame': {'duration': 1800, 'redraw': False},
                                          'fromcurrent': True,
                                          'transition': {'duration': 1200, 'easing': 'linear'}}], #'quadratic-in-out'}}],
                          'label': 'Play',
                          'method': 'animate'},
                         {'args': [[None], {'frame': {'duration': 0, 'redraw': False},
                                            'mode': 'immediate',
                                            'transition': {'duration': 0}}],
                          'label': 'Pause',
                          'method': 'animate'}],
             'direction': 'left',
             'pad': {'r': 10, 't': 87},
             'showactive': False,
             'type': 'buttons',
             'x': 0.1,
             'xanchor': 'right',
             'y': 0,
             'yanchor': 'top'
             }]

    sliders_dict = {
        "active": 0,
        "yanchor": "top",
        "xanchor": "left",
        "currentvalue": {
            "font": {"size": 13},
            "prefix": "As of: ",
            "visible": True,
            "xanchor": "right",
        },
        "transition": {"duration": 500, "easing": "cubic-in-out"},
        "pad": {"b": 10, "t": 50},
        "len": 0.9,
        "x": 0.1,
        "y": 0,
        "steps": []
    }

    # keep track of what days there is no yahoo data yet (i.e. if you pull before the market opens on a weekday)
    no_yahoo_yet = []

    # make initial data
    day = days[0]
    data_dict = []
    for contract in contracts:
        dataset_by_day = df[df["daywk"] == day]
        dataset_by_day_and_cont = dataset_by_day[
            dataset_by_day["type"] == contract]

        data_dict = {
            "x": list(dataset_by_day_and_cont["strike"]),
            "y": list(dataset_by_day_and_cont["open_int"]),
            "mode": "lines",
            "name": contract.title()
        }
        fig_dict["data"].append(data_dict)

    if len(yahoohist) != 0:
        try:
            yahoo_day = yahoohist[yahoohist.daywk == day]
            shape_dict = [go.layout.Shape(type='line',
                                          line_width=3,
                                          line_dash='dot', #'dash' if future_week else 'dot',
                                          line_color='#919191',
                                          x0=yahoo_day['Open'].values.tolist()[0],
                                          x1=yahoo_day['Open'].values.tolist()[0],
                                          y0=y_range_st,
                                          y1=y_range_end,
                                          xref='x',
                                          yref='y'
                                          ),
                          go.layout.Shape(type='line',
                                          line_width=3,
                                          line_dash='dot', #'dash' if future_week else 'dot',
                                          line_color='#121212',
                                          x0=yahoo_day['Close'].values.tolist()[0],
                                          x1=yahoo_day['Close'].values.tolist()[0],
                                          y0=y_range_st,
                                          y1=y_range_end,
                                          xref='x',
                                          yref='y'),
                          go.layout.Shape(type='line',
                                          line_width=1.5,
                                          line_dash='dashdot',
                                          line_color='#CE8500',
                                          x0=yahoo_day['Low'].values.tolist()[0],
                                          x1=yahoo_day['Low'].values.tolist()[0],
                                          y0=0,
                                          y1=0.78,
                                          xref='x',
                                          yref='paper'
                                          ),
                          go.layout.Shape(type='line',
                                          line_width=1.5,
                                          line_dash='dashdot',
                                          line_color='#CE8500',
                                          x0=yahoo_day['High'].values.tolist()[0],
                                          x1=yahoo_day['High'].values.tolist()[0],
                                          y0=0,
                                          y1=0.78,
                                          xref='x',
                                          yref='paper')
                          ]

            fig_dict['layout']['shapes'] = shape_dict

            # add annotations for each vertical line
            annotation_dict = [go.layout.Annotation(text=f" Open: {yahoo_day['Open'].values.tolist()[0]:,.1f}",
                                                    font_size=12,
                                                    font_color="#919191",
                                                    showarrow=False,
                                                    x=yahoo_day['Open'].values.tolist()[0],
                                                    y=y_range_end,
                                                    textangle=-90,
                                                    yanchor='bottom'),
                               go.layout.Annotation(text=f" Close: {yahoo_day['Close'].values.tolist()[0]:,.1f}",
                                                    font_size=12,
                                                    font_color="#121212",
                                                    showarrow=False,
                                                    x=yahoo_day['Close'].values.tolist()[0],
                                                    y=y_range_end,
                                                    textangle=-90,
                                                    yanchor='bottom'),
                               go.layout.Annotation(text=f" Low: {yahoo_day['Low'].values.tolist()[0]:,.1f}",
                                                    font_size=11,
                                                    font_color="#CE8500",
                                                    showarrow=False,
                                                    x=yahoo_day['Low'].values.tolist()[0],
                                                    y=0.78,
                                                    yref='paper',
                                                    textangle=-90,
                                                    yanchor='bottom'),
                               go.layout.Annotation(text=f" High: {yahoo_day['High'].values.tolist()[0]:,.1f}",
                                                    font_size=11,
                                                    font_color="#CE8500",
                                                    showarrow=False,
                                                    x=yahoo_day['High'].values.tolist()[0],
                                                    y=0.78,
                                                    yref='paper',
                                                    textangle=-90,
                                                    yanchor='bottom')
                               ]

            fig_dict['layout']['annotations'] = annotation_dict
        except IndexError:
            pass

    # make frames
    for i,day in enumerate(days):
        frame = {"data": [], "name": str(day), "layout": {}}
        for contract in contracts:
            dataset_by_day = df[df["daywk"] == day]
            dataset_by_day_and_cont = dataset_by_day[
                dataset_by_day["type"] == contract]

            data_dict = {
                "x": list(dataset_by_day_and_cont["strike"]),
                "y": list(dataset_by_day_and_cont["open_int"]),
                "mode": "lines",
                "name": contract.title()
            }
            frame["data"].append(data_dict)

        # add the two vertical lines if yahoo has data for that date
        if len(yahoohist)!=0:
            try:
                yahoo_day = yahoohist[yahoohist.daywk == day]
                shape_dict = [go.layout.Shape(type='line',
                                              line_width=3,
                                              line_dash='dot', #'dash' if future_week else 'dot',
                                              line_color='#919191',
                                              x0=yahoo_day['Open'].values.tolist()[0],
                                              x1=yahoo_day['Open'].values.tolist()[0],
                                              y0=y_range_st,
                                              y1=y_range_end,
                                              xref='x',
                                              yref='y'
                                              ),
                              go.layout.Shape(type='line',
                                              line_width=3,
                                              line_dash='dot', #'dash' if future_week else 'dot',
                                              line_color='#121212',
                                              x0=yahoo_day['Close'].values.tolist()[0],
                                              x1=yahoo_day['Close'].values.tolist()[0],
                                              y0=y_range_st,
                                              y1=y_range_end,
                                              xref='x',
                                              yref='y'),
                              go.layout.Shape(type='line',
                                              line_width=1.5,
                                              line_dash='dashdot',
                                              line_color='#CE8500',
                                              x0=yahoo_day['Low'].values.tolist()[0],
                                              x1=yahoo_day['Low'].values.tolist()[0],
                                              y0=0,
                                              y1=0.78,
                                              xref='x',
                                              yref='paper'
                                              ),
                              go.layout.Shape(type='line',
                                              line_width=1.5,
                                              line_dash='dashdot',
                                              line_color='#CE8500',
                                              x0=yahoo_day['High'].values.tolist()[0],
                                              x1=yahoo_day['High'].values.tolist()[0],
                                              y0=0,
                                              y1=0.78,
                                              xref='x',
                                              yref='paper')]

                frame['layout']['shapes'] = shape_dict

                # add annotations for each vertical line
                annotation_dict = [go.layout.Annotation(text=f" Open: {yahoo_day['Open'].values.tolist()[0]:,.1f}",
                                                        font_size=12,
                                                        font_color="#919191",
                                                        showarrow=False,
                                                        x=yahoo_day['Open'].values.tolist()[0],
                                                        y=y_range_end,
                                                        textangle=-90,
                                                        yanchor='bottom'),
                                   go.layout.Annotation(text=f" Close: {yahoo_day['Close'].values.tolist()[0]:,.1f}",
                                                        font_size=12,
                                                        font_color="#121212",
                                                        showarrow=False,
                                                        x=yahoo_day['Close'].values.tolist()[0],
                                                        y=y_range_end,
                                                        textangle=-90,
                                                        yanchor='bottom'),
                                   go.layout.Annotation(text=f" Low: {yahoo_day['Low'].values.tolist()[0]:,.1f}",
                                                        font_size=11,
                                                        font_color="#CE8500",
                                                        showarrow=False,
                                                        x=yahoo_day['Low'].values.tolist()[0],
                                                        y=0.78,
                                                        yref='paper',
                                                        textangle=-90,
                                                        yanchor='bottom'),
                                   go.layout.Annotation(text=f" High: {yahoo_day['High'].values.tolist()[0]:,.1f}",
                                                        font_size=11,
                                                        font_color="#CE8500",
                                                        showarrow=False,
                                                        x=yahoo_day['High'].values.tolist()[0],
                                                        y=0.78,
                                                        yref='paper',
                                                        textangle=-90,
                                                        yanchor='bottom')]

                frame['layout']['annotations'] = annotation_dict
            except IndexError:
                no_yahoo_yet.append(day)

        fig_dict["frames"].append(frame)
        slider_step = {"args": [
            [day],
            {"frame": {"duration": 300, "redraw": False},
             "mode": "immediate",
             "transition": {"duration": 300}}
        ],
            "label": day_labels[i],
            "method": "animate"}
        sliders_dict["steps"].append(slider_step)

    fig_dict["layout"]["sliders"] = [sliders_dict]

    if future_week:
        fig_dict['layout']['annotations'].append(go.layout.Annotation(x=0.0,
                                                                      y=1.0,
                                                                      font_size=15,
                                                                      xref='paper',
                                                                      yref='paper',
                                                                      xanchor='left',
                                                                      yanchor='bottom',
                                                                      align='left',
                                                                      showarrow=False,
                                                                      text='Note: Prices shown are from the most recent<br>'
                                                                           'week, not the contract expiration week.'))

    fig = go.Figure(fig_dict)

    st.plotly_chart(fig, use_container_width=True)

    if no_yahoo_yet != []:
        st.write(f"<br>There is no Yahoo pricing data recorded yet for {', '.join(no_yahoo_yet)}. "
                 f"If you are running this before markets open for the day, please re-run after markets open "
                 f"to see today's Yahoo data.", unsafe_allow_html=True)
    elif len(yahoohist)==0:
        st.write(f"<br>There is no Yahoo pricing data recorded yet for week of {week.strftime('%b %-d, %Y')}. "
                 f"If you are running this before markets open for the week, please re-run after markets open "
                 f"to see Yahoo data.", unsafe_allow_html=True)


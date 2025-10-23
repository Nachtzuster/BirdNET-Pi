import os
import streamlit as st
import pandas as pd
import numpy as np
from numpy import ma
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
from datetime import datetime, timedelta
from dateutil import tz
import sqlite3
from sqlite3 import Connection
import plotly.express as px
from sklearn.preprocessing import normalize
from suntime import Sun
from utils.helpers import get_settings

profile = False
debug = False
if profile:
    try:
        from pyinstrument import Profiler
    except ImportError as e:
        print(e)
        profile = False
    else:
        profiler = Profiler()
        profiler.start()


pio.templates.default = "plotly_white"

userDir = os.path.expanduser('~')
URI_SQLITE_DB = userDir + '/BirdNET-Pi/scripts/birds.db'

st.set_page_config(layout='wide')

# Remove whitespace from the top of the page
st.markdown("""
        <style>
               .css-18e3th9 {
                    padding-top: 2.5rem;
                    padding-bottom: 10rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
               .css-1d391kg {
                    padding-top: 3.5rem;
                    padding-right: 1rem;
                    padding-bottom: 3.5rem;
                    padding-left: 1rem;
                }
        </style>
        """, unsafe_allow_html=True)


def print_now(message):
    if profile or debug:
        print(message, flush=True)


@st.cache_resource()
def get_connection(path: str):
    uri = f"file:{path}?mode=ro"
    return sqlite3.connect(uri, uri=True, check_same_thread=False)


def get_todays_count(conn):
    today = datetime.now().strftime("%Y-%m-%d")
    return pd.read_sql(f"SELECT COUNT(*) FROM detections WHERE Date = DATE('{today}')", con=conn)


@st.cache_data(ttl=300)
def get_data(_conn: Connection, flush_cache):
    print_now('** get_data **')
    df1 = pd.read_sql("SELECT Date, Time, Sci_Name, Com_Name, Confidence, File_Name FROM detections", con=_conn)
    return df1


@st.cache_data(max_entries=1)
def normalise_com_name(df):
    print_now('** normalise_com_name **')
    latest_com_names = df.groupby('Sci_Name').tail(1)
    df.rename(columns={'Com_Name': 'Directory'}, inplace=True)
    df['DateTime'] = pd.to_datetime(df['Date'] + " " + df['Time'])
    return df.merge(latest_com_names[['Sci_Name', 'Com_Name']].set_index('Sci_Name'), how='left', on='Sci_Name').set_index('DateTime')


conn = get_connection(URI_SQLITE_DB)
latest_count = get_todays_count(conn)
df2 = get_data(conn, latest_count)
df2 = normalise_com_name(df2)

if len(df2) == 0:
    st.info('No data yet. Please come back later.')
    exit(0)

daily = st.sidebar.checkbox('Single Day View', help='Select if you want single day view, unselect for multi-day views')

if daily:
    Start_Date = pd.to_datetime(df2.index.min()).date()
    End_Date = pd.to_datetime(df2.index.max()).date()
    end_date = st.sidebar.date_input('Date to View',
                                     min_value=Start_Date,
                                     max_value=End_Date,
                                     value=(End_Date),
                                     help='Select date for single day view')
    start_date = end_date
else:
    Start_Date = pd.to_datetime(df2.index.min()).date()
    End_Date = pd.to_datetime(df2.index.max()).date()
    start_date, end_date = st.sidebar.slider('Date Range',
                                             min_value=Start_Date-timedelta(days=1),
                                             max_value=End_Date,
                                             value=(Start_Date, End_Date),
                                             help='Select start and end date, if same date get a clockplot for a single day')


@st.cache_data()
def date_filter(df, start_date, end_date):
    print_now('** date_filter **')
    filt = (df2.index >= pd.Timestamp(start_date)) & (df2.index <= pd.Timestamp(end_date + timedelta(days=1)))
    df = df[filt]
    return (df)


df2 = date_filter(df2, start_date, end_date)

st.write('<style>div.row-widget.stRadio > div{flex-direction:row;justify-content: left;} </style>',
         unsafe_allow_html=True)
st.write('<style>div.st-bf{flex-direction:column;} div.st-ag{font-weight:bold;padding-left:2px;}</style>',
         unsafe_allow_html=True)


# Select time period buttons
# Disallow "Daily time period" for "Daily Chart"
if start_date == end_date:
    resample_sel = st.sidebar.radio(
        "Resample Resolution",
        ('Raw', '15 minutes', 'Hourly'), index=1, help='Select resolution for single day - larger times run faster')

    resample_times = {'Raw': 'Raw',
                      '1 minute': '1min',
                      '15 minutes': '15min',
                      'Hourly': '1h'
                      }
    resample_time = resample_times[resample_sel]

else:
    resample_sel = st.sidebar.radio(
        "Resample Resolution",
        ('Raw', '15 minutes', 'Hourly', 'DAILY'), index=1, help='Select resolution for species - DAILY provides time series')

    resample_times = {'Raw': 'Raw',
                      '1 minute': '1min',
                      '15 minutes': '15min',
                      'Hourly': '1h',
                      'DAILY': '1D'
                      }
    resample_time = resample_times[resample_sel]


@st.cache_data()
def time_resample(df, resample_time):
    print_now('** time_resample **')
    if resample_time == 'Raw':
        df_resample = df['Com_Name']

    else:
        df_resample = df.resample(resample_time)['Com_Name'].aggregate('unique').explode()

    return (df_resample)


top_bird = df2['Com_Name'].mode()[0]
df5 = time_resample(df2, resample_time)

# Create species count for selected date range

Specie_Count = df5.value_counts()

# Create Hourly Crosstab
hourly = pd.crosstab(df5, df5.index.hour, dropna=True, margins=True)

# Filter on species
species = list(hourly.sort_values("All", ascending=False).index)

if len(Specie_Count) > 1:
    top_N = st.sidebar.slider(
        'Select Number of Birds to Show',
        min_value=1,
        max_value=len(Specie_Count),
        value=min(10, len(Specie_Count))
    )
else:
    top_N = 1

top_N_species = (df5.value_counts()[:top_N])

font_size = 15


def sunrise_sunset_scatter(date_range):
    conf = get_settings()
    latitude = conf.getfloat('LATITUDE')
    longitude = conf.getfloat('LONGITUDE')

    sun = Sun(latitude, longitude)

    sunrise_list = []
    sunset_list = []
    sunrise_text_list = []
    sunset_text_list = []
    daysback_range = []

    local_timezone = tz.tzlocal()

    for current_date in date_range:
        current_datetime = datetime.combine(current_date, datetime.min.time())
        sun_rise = sun.get_sunrise_time(current_datetime, local_timezone)
        sun_dusk = sun.get_sunset_time(current_datetime, local_timezone)

        sun_rise_time = float(sun_rise.hour) + float(sun_rise.minute) / 60.0
        sun_dusk_time = float(sun_dusk.hour) + float(sun_dusk.minute) / 60.0

        temp_time = str(sun_rise)[-14:-9] + " Sunrise"
        sunrise_text_list.append(temp_time)
        temp_time = str(sun_dusk)[-14:-9] + " Sunset"
        sunset_text_list.append(temp_time)
        sunrise_list.append(sun_rise_time)
        sunset_list.append(sun_dusk_time)

        daysback_range.append(current_date.strftime('%d-%m-%Y'))

    sunrise_list.append(None)
    sunrise_text_list.append(None)
    sunrise_list.extend(sunset_list)
    sunrise_text_list.extend(sunset_text_list)
    daysback_range.append(None)
    daysback_range.extend(daysback_range)

    return daysback_range, sunrise_list, sunrise_text_list


def hms_to_dec(t):
    h = t.hour
    m = t.minute / 60
    s = t.second / 3600
    result = h + m + s
    return result


def hms_to_str(t):
    h = t.hour
    m = t.minute
    return "%02d:%02d" % (h, m)


if daily is False:

    if resample_time != '1D':
        specie = st.selectbox(
            'Which bird would you like to explore for the dates '
            + str(start_date) + ' to ' + str(end_date) + '?',
            species,
            index=0)

        if specie == 'All':
            df_counts = int(hourly[hourly.index == specie]['All'].iloc[0])
            fig = make_subplots(
                rows=3, cols=2,
                specs=[[{"type": "xy", "rowspan": 3}, {"type": "polar", "rowspan": 2}],
                       [{"rowspan": 1}, {"rowspan": 1}],
                       [None, {"type": "xy", "rowspan": 1}]],
                subplot_titles=('<b>Top ' + str(top_N) + ' Species in Date Range ' + str(start_date) + ' to ' + str(
                    end_date) + '<br>for ' + str(resample_sel) + ' sampling interval.' + '</b>',
                                'Total Detect:' + str('{:,}'.format(df_counts))
                )
            )
            fig.layout.annotations[1].update(x=0.7, y=0.25, font_size=15)

            # Plot seen species for selected date range and number of species

            fig.add_trace(go.Bar(y=top_N_species.index.tolist(), x=top_N_species.values.tolist(), orientation='h', marker_color='seagreen'), row=1, col=1)

            fig.update_layout(
                margin=dict(l=0, r=0, t=50, b=0),
                yaxis={'categoryorder': 'total ascending'})

            # Set 360 degrees, 24 hours for polar plot
            theta = np.linspace(0.0, 360, 24, endpoint=False).tolist()

            specie_filt = df5 == specie
            df3 = df5[specie_filt]

            detections2 = pd.crosstab(df3, df3.index.hour)

            d = pd.DataFrame(np.zeros((24, 1))).squeeze()
            detections = hourly.loc[specie]
            detections = (d + detections).fillna(0)
            fig.add_trace(go.Barpolar(r=detections.tolist(), theta=theta, marker_color='seagreen'), row=1, col=2)
            fig.update_layout(
                autosize=False,
                width=1000,
                height=500,
                showlegend=False,
                polar=dict(
                    radialaxis=dict(
                        tickfont_size=font_size,
                        showticklabels=False,
                        hoverformat="#%{theta}: <br>Popularity: %{percent} </br> %{r}"
                    ),
                    angularaxis=dict(
                        tickfont_size=font_size,
                        rotation=-90,
                        direction='clockwise',
                        tickmode='array',
                        tickvals=[0, 15, 35, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180, 195, 210,
                                  225, 240, 255, 270, 285, 300, 315, 330, 345],
                        ticktext=['12am', '1am', '2am', '3am', '4am', '5am', '6am', '7am', '8am', '9am',
                                  '10am', '11am', '12pm', '1pm', '2pm', '3pm', '4pm', '5pm', '6pm',
                                  '7pm', '8pm', '9pm', '10pm', '11pm'],
                        hoverformat="#%{theta}: <br>Popularity: %{percent} </br> %{r}"
                    ),
                ),
            )

            daily = pd.crosstab(df5, df5.index.date, dropna=True, margins=True)
            fig.add_trace(go.Bar(x=daily.columns[:-1].tolist(), y=daily.loc[specie][:-1].tolist(), marker_color='seagreen'), row=3, col=2)
            st.plotly_chart(fig, use_container_width=True)  # , config=config)

        else:
            col1, col2 = st.columns(2)
            with col1:
                fig = make_subplots(
                    rows=3, cols=1,
                    specs=[[{"type": "polar", "rowspan": 2}], [{"rowspan": 1}], [{"type": "xy", "rowspan": 1}]]
                )
                # Set 360 degrees, 24 hours for polar plot
                theta = np.linspace(0.0, 360, 24, endpoint=False).tolist()

                specie_filt = df5 == specie
                df3 = df5[specie_filt]

                detections2 = pd.crosstab(df3, df3.index.hour)

                d = pd.DataFrame(np.zeros((24, 1))).squeeze()
                detections = hourly.loc[specie]
                detections = (d + detections).fillna(0)
                fig.add_trace(go.Barpolar(r=detections.tolist(), theta=theta, marker_color='seagreen'), row=1, col=1)
                fig.update_layout(
                    autosize=False,
                    width=1000,
                    height=500,
                    showlegend=False,
                    polar=dict(
                        radialaxis=dict(
                            tickfont_size=font_size,
                            showticklabels=False,
                            hoverformat="#%{theta}: <br>Popularity: %{percent} </br> %{r}"
                        ),
                        angularaxis=dict(
                            tickfont_size=font_size,
                            rotation=-90,
                            direction='clockwise',
                            tickmode='array',
                            tickvals=[0, 15, 35, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180, 195,
                                      210, 225, 240, 255, 270, 285, 300, 315, 330, 345],
                            ticktext=['12am', '1am', '2am', '3am', '4am', '5am', '6am', '7am', '8am',
                                      '9am', '10am', '11am', '12pm', '1pm', '2pm', '3pm', '4pm', '5pm',
                                      '6pm', '7pm', '8pm', '9pm', '10pm', '11pm'],
                            hoverformat="#%{theta}: <br>Popularity: %{percent} </br> %{r}"
                        ),
                    ),
                )

                daily = pd.crosstab(df5, df5.index.date, dropna=True, margins=True)
                fig.add_trace(go.Bar(x=daily.columns[:-1].tolist(), y=daily.loc[specie][:-1].tolist(), marker_color='seagreen'), row=3, col=1)
                st.plotly_chart(fig, use_container_width=True)  # , config=config)
                df_counts = int(hourly[hourly.index == specie]['All'].iloc[0])
                st.subheader('Total Detect:' + str('{:,}'.format(df_counts))
                             + '   Confidence Max:' +
                             str('{:.2f}%'.format(max(df2[df2['Com_Name'] == specie]['Confidence']) * 100))
                             + '   ' + '   Median:' +
                             str('{:.2f}%'.format(np.median(df2[df2['Com_Name'] == specie]['Confidence']) * 100)))

            recordings = df2[df2['Com_Name'] == specie]['File_Name']

            with col2:
                try:
                    recording = st.selectbox('Recordings', recordings.sort_index(ascending=False))
                    date_specie = df2.loc[df2['File_Name'] == recording, ['Date', 'Com_Name', 'Directory']]
                    date_dir = date_specie['Date'].values[0]
                    specie_dir = date_specie['Directory'].values[0].replace(" ", "_").replace("'", "")
                    st.image(userDir + '/BirdSongs/Extracted/By_Date/' + date_dir + '/' + specie_dir + '/' + recording + '.png')
                    st.audio(userDir + '/BirdSongs/Extracted/By_Date/' + date_dir + '/' + specie_dir + '/' + recording)
                except Exception:
                    st.info('Recording not available')

    else:

        specie = st.selectbox('Which bird would you like to explore for the dates '
                              + str(start_date) + ' to ' + str(end_date) + '?',
                              species[1:],
                              index=0)

        df_counts = int(hourly.loc[hourly.index == specie, 'All'].iloc[0])

        fig = make_subplots(rows=1, cols=1)

        df4 = df2['Com_Name'][df2['Com_Name'] == specie].resample('15min').count()
        df4.index = [df4.index.date, df4.index.time]
        day_hour_freq = df4.unstack().fillna(0)

        saved_time_labels = [hms_to_str(h) for h in day_hour_freq.columns.tolist()]
        fig_dec_y = [hms_to_dec(h) for h in day_hour_freq.columns.tolist()]
        fig_x = [d.strftime('%d-%m-%Y') for d in day_hour_freq.index.tolist()]
        fig_y = [h.strftime('%H:%M') for h in day_hour_freq.columns.tolist()]
        day_hour_freq.columns = fig_dec_y
        fig_z = day_hour_freq.values.transpose().tolist()

        color_pals = px.colors.named_colorscales()
        selected_pal = st.sidebar.selectbox('Select Color Pallet for Daily Detections', color_pals)

        heatmap = go.Heatmap(
            x=fig_x,
            y=day_hour_freq.columns.tolist(),
            z=fig_z,  # heat.values,
            showscale=False,
            texttemplate="%{text}", autocolorscale=False, colorscale=selected_pal
        )
        daysback_range, sunrise_list, sunrise_text_list = sunrise_sunset_scatter(day_hour_freq.index.tolist())

        sunrise_sunset = go.Scatter(x=daysback_range,
                                    y=sunrise_list,
                                    mode='lines',
                                    hoverinfo='text',
                                    text=sunrise_text_list,
                                    line_color='orange', line_width=1, name=' ')

        fig = go.Figure(data=[heatmap, sunrise_sunset])
        number_of_y_ticks = 12
        y_downscale_factor = int(len(saved_time_labels) / number_of_y_ticks)
        fig.update_layout(
            yaxis=dict(
                tickmode='array',
                tickvals=day_hour_freq.columns[::y_downscale_factor],
                ticktext=saved_time_labels[::y_downscale_factor],
                nticks=6
            )
        )
        st.plotly_chart(fig, use_container_width=True)  # , config=config)
else:
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "xy", "rowspan": 1}, {"type": "xy", "rowspan": 1}]],
        subplot_titles=('<b>Top ' + str(top_N) + ' Species For ' + str(start_date) + '</b>',
                        '<b>Daily ' + str(start_date) + ' Detections on ' + resample_sel + ' interval</b>'),
        shared_yaxes='all',
        horizontal_spacing=0
    )

    df6 = df5.to_frame(name='Com_Name')
    readings = top_N

    plt_topN_today = (df6['Com_Name'].value_counts()[:readings])
    freq_order = pd.value_counts(df6['Com_Name']).iloc[:readings].index
    fig.add_trace(go.Bar(y=plt_topN_today.index.tolist(), x=plt_topN_today.values.tolist(), marker_color='seagreen', orientation='h'), row=1,
                  col=1)

    df6['Hour of Day'] = [r.hour for r in df6.index.time]
    heat = pd.crosstab(df6['Com_Name'], df6['Hour of Day'])
    # Order heatmap Birds by frequency of occurrance
    heat.index = pd.CategoricalIndex(heat.index, categories=freq_order)
    heat.sort_index(level=0, inplace=True)

    heat.index = heat.index.astype(str)
    heat_plot_values = ma.log(heat.values).filled(0)

    hours_in_day = pd.Series(data=range(0, 24))
    heat_frame = pd.DataFrame(data=0, index=heat.index, columns=hours_in_day)

    heat = (heat + heat_frame).fillna(0)
    heat_values_normalized = normalize(heat.values, axis=1, norm='l1')

    labels = heat.values.astype(int).astype('str')
    labels[labels == '0'] = ""
    fig.add_trace(go.Heatmap(x=heat.columns.tolist(), y=heat.index.tolist(), z=heat_values_normalized,  # heat.values,
                             showscale=False,
                             text=labels, texttemplate="%{text}", colorscale='Blugrn'
                             ), row=1, col=2)
    fig.update_yaxes(visible=True, autorange="reversed", ticks="inside", tickson="boundaries", ticklen=10000,
                     showgrid=True)
    fig.update_layout(xaxis_ticks="inside",
                      margin=dict(l=0, r=0, t=50, b=0))
    st.plotly_chart(fig, use_container_width=True)  # , config=config)

if profile:
    profiler.stop()
    profiler.print()
    print_now('**profiler done**')

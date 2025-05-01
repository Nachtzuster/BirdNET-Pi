import argparse
import os
import sqlite3
import textwrap
from datetime import datetime
from time import sleep

import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import rcParams
from matplotlib.colors import LogNorm

from utils.helpers import DB_PATH, FONT_DIR, get_settings, get_font


def get_data(now=None):
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    if now is None:
        now = datetime.now()
    df = pd.read_sql_query(f"SELECT * from detections WHERE Date = DATE('{now.strftime('%Y-%m-%d')}')",
                           conn)

    # Convert Date and Time Fields to Panda's format
    df['Date'] = pd.to_datetime(df['Date'])
    df['Time'] = pd.to_datetime(df['Time'], unit='ns')

    # Add round hours to dataframe
    df['Hour of Day'] = [r.hour for r in df.Time]

    return df, now


# Function to show value on bars - from https://stackoverflow.com/questions/43214978/seaborn-barplot-displaying-values
def show_values_on_bars(ax, label):
    conf = get_settings()

    for i, p in enumerate(ax.patches):
        x = p.get_x() + p.get_width() * 0.9
        y = p.get_y() + p.get_height() / 2
        # Species confidence
        # value = '{:.0%}'.format(label.iloc[i])
        # Species Count Total
        value = '{:n}'.format(p.get_width())
        bbox = {'facecolor': 'lightgrey', 'edgecolor': 'none', 'pad': 1.0}
        if conf['COLOR_SCHEME'] == "dark":
            color = 'black'
        else:
            color = 'darkgreen'

        ax.text(x, y, value, bbox=bbox, ha='center', va='center', size=9, color=color)


def wrap_width(txt):
    # try to estimate wrap width
    w = 16
    for c in txt:
        if c in ['M', 'm', 'W', 'w']:
            w -= 0.33
        if c in ['I', 'i', 'j', 'l']:
            w += 0.33
    return round(w)


def create_plot(df_plt_today, now, is_top=None):
    if is_top is not None:
        readings = 10
        if is_top:
            plt_selection_today = (df_plt_today['Com_Name'].value_counts()[:readings])
        else:
            plt_selection_today = (df_plt_today['Com_Name'].value_counts()[-readings:])
    else:
        plt_selection_today = df_plt_today['Com_Name'].value_counts()
        readings = len(df_plt_today['Com_Name'].value_counts())

    df_plt_selection_today = df_plt_today[df_plt_today.Com_Name.isin(plt_selection_today.index)]

    conf = get_settings()

    # Set up plot axes and titles
    height = max(readings / 3, 0) + 1.06
    if conf['COLOR_SCHEME'] == "dark":
        facecolor = 'darkgrey'
    else:
        facecolor = '#77C487'

    f, axs = plt.subplots(1, 2, figsize=(10, height), gridspec_kw=dict(width_ratios=[3, 6]), facecolor=facecolor)

    # generate y-axis order for all figures based on frequency
    freq_order = df_plt_selection_today['Com_Name'].value_counts().index

    # make color for max confidence --> this groups by name and calculates max conf
    confmax = df_plt_selection_today.groupby('Com_Name')['Confidence'].max()
    # reorder confmax to detection frequency order
    confmax = confmax.reindex(freq_order)

    # norm values for color palette
    norm = plt.Normalize(confmax.values.min(), confmax.values.max())
    if is_top or is_top is None:
        # Set Palette for graphics
        if conf['COLOR_SCHEME'] == "dark":
            pal = "Greys"
            colors = plt.cm.Greys(norm(confmax)).tolist()
        else:
            pal = "Greens"
            colors = plt.cm.Greens(norm(confmax)).tolist()
        if is_top:
            plot_type = "Top"
        else:
            plot_type = 'All'
        name = "Combo"
    else:
        # Set Palette for graphics
        pal = "Reds"
        colors = plt.cm.Reds(norm(confmax)).tolist()
        plot_type = "Bottom"
        name = "Combo2"

    # Generate frequency plot
    plot = sns.countplot(y='Com_Name', hue='Com_Name', legend=False, data=df_plt_selection_today,
                         palette=dict(zip(confmax.index, colors)), order=freq_order, ax=axs[0], edgecolor='lightgrey')

    # Prints Max Confidence on bars
    show_values_on_bars(axs[0], confmax)

    # Try plot grid lines between bars - problem at the moment plots grid lines on bars - want between bars
    yticklabels = ['\n'.join(textwrap.wrap(ticklabel.get_text(), wrap_width(ticklabel.get_text()))) for ticklabel in plot.get_yticklabels()]
    # Next two lines avoid a UserWarning on set_ticklabels() requesting a fixed number of ticks
    yticks = plot.get_yticks()
    plot.set_yticks(yticks)
    plot.set_yticklabels(yticklabels, fontsize=10)
    plot.set(ylabel=None)
    plot.set(xlabel="Detections")

    # Generate crosstab matrix for heatmap plot
    heat = pd.crosstab(df_plt_selection_today['Com_Name'], df_plt_selection_today['Hour of Day'])

    # Order heatmap Birds by frequency of occurrance
    heat.index = pd.CategoricalIndex(heat.index, categories=freq_order)
    heat.sort_index(level=0, inplace=True)

    hours_in_day = pd.Series(data=range(0, 24))
    heat_frame = pd.DataFrame(data=0, index=heat.index, columns=hours_in_day)
    heat = (heat+heat_frame).fillna(0)
    # mask out zeros, so they do not show up in the final plot. this happens when max count/h is one
    heat[heat == 0] = np.nan

    # Generatie heatmap plot
    plot = sns.heatmap(heat, norm=LogNorm(),  annot=True,  annot_kws={"fontsize": 7}, fmt="g", cmap=pal, square=False,
                       cbar=False, linewidths=0.5, linecolor="Grey", ax=axs[1], yticklabels=False)

    # Set color and weight of tick label for current hour
    for label in plot.get_xticklabels():
        if int(label.get_text()) == now.hour:
            if conf['COLOR_SCHEME'] == "dark":
                label.set_color('white')
            else:
                label.set_color('yellow')

    plot.set_xticklabels(plot.get_xticklabels(), rotation=0, size=8)

    # Set heatmap border
    for _, spine in plot.spines.items():
        spine.set_visible(True)

    plot.set(ylabel=None)
    plot.set(xlabel="Hour of Day")
    # Set combined plot layout and titles
    y = 1 - 8 / (height * 100)
    plt.suptitle(f"{plot_type} {readings} Last Updated: {now.strftime('%Y-%m-%d %H:%M')}", y=y)
    f.tight_layout()
    top = 1 - 40 / (height * 100)
    f.subplots_adjust(left=0.125, right=0.9, top=top, wspace=0)

    # Save combined plot
    save_name = os.path.expanduser(f"~/BirdSongs/Extracted/Charts/{name}-{now.strftime('%Y-%m-%d')}.png")
    plt.savefig(save_name)
    plt.show()
    plt.close()


def load_fonts():
    # Add every font at the specified location
    font_dir = [FONT_DIR]
    for font in font_manager.findSystemFonts(font_dir, fontext='ttf'):
        font_manager.fontManager.addfont(font)
    # Set font family globally
    rcParams['font.family'] = get_font()['font.family']


def main(daemon, sleep_m):
    load_fonts()
    last_run = None
    while True:
        now = datetime.now()
        # now = datetime.strptime('2023-12-13T23:59:59', "%Y-%m-%dT%H:%M:%S")
        # now = datetime.strptime('2024-01-02T23:59:59', "%Y-%m-%dT%H:%M:%S")
        # now = datetime.strptime('2024-02-26T23:59:59', "%Y-%m-%dT%H:%M:%S")
        # now = datetime.strptime('2024-04-03T23:59:59', "%Y-%m-%dT%H:%M:%S")
        # now = datetime.strptime('2024-04-07T23:59:59', "%Y-%m-%dT%H:%M:%S")
        if last_run and now.day != last_run.day:
            print("getting yesterday's dataset")
            yesterday = last_run.replace(hour=23, minute=59)
            data, time = get_data(yesterday)
        else:
            data, time = get_data(now)
        if not data.empty:
            create_plot(data, time)
        else:
            print('empty dataset')
        if daemon:
            last_run = now
            sleep(60 * sleep_m)
        else:
            break


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--daemon', action='store_true')
    parser.add_argument('--sleep', default=2, type=int, help='Time between runs (minutes)')
    args = parser.parse_args()
    main(args.daemon, args.sleep)

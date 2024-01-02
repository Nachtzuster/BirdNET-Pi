import argparse
import os
import sqlite3
import textwrap
from datetime import datetime
from time import sleep

import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib import rcParams
from matplotlib.colors import LogNorm

from utils.helpers import DB_PATH


def get_data():
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now()
    df = pd.read_sql_query("SELECT * from detections WHERE Date = DATE('now', 'localtime')", conn)

    # Convert Date and Time Fields to Panda's format
    df['Date'] = pd.to_datetime(df['Date'])
    df['Time'] = pd.to_datetime(df['Time'], unit='ns')

    # Add round hours to dataframe
    df['Hour of Day'] = [r.hour for r in df.Time]

    return df, now


def create_plot(df_plt_today, now, is_top):
    readings = 10
    if is_top:
        plt_selection_today = (df_plt_today['Com_Name'].value_counts()[:readings])
    else:
        plt_selection_today = (df_plt_today['Com_Name'].value_counts()[-readings:])

    df_plt_selection_today = df_plt_today[df_plt_today.Com_Name.isin(plt_selection_today.index)]

    # Set up plot axes and titles
    f, axs = plt.subplots(1, 2, figsize=(10, 4), gridspec_kw=dict(width_ratios=[3, 6]), facecolor='#77C487')
    plt.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=0, hspace=0)

    # generate y-axis order for all figures based on frequency
    freq_order = pd.value_counts(df_plt_selection_today['Com_Name']).index

    # make color for max confidence --> this groups by name and calculates max conf
    confmax = df_plt_selection_today.groupby('Com_Name')['Confidence'].max()
    # reorder confmax to detection frequency order
    confmax = confmax.reindex(freq_order)

    # norm values for color palette
    norm = plt.Normalize(confmax.values.min(), confmax.values.max())
    if is_top:
        # Set Palette for graphics
        pal = "Greens"
        colors = plt.cm.Greens(norm(confmax))
        plot_type = "Top"
        name = "Combo"
    else:
        # Set Palette for graphics
        pal = "Reds"
        colors = plt.cm.Reds(norm(confmax))
        plot_type = "Bottom"
        name = "Combo2"

    # Generate frequency plot
    plot = sns.countplot(y='Com_Name', data=df_plt_selection_today, palette=colors,  order=freq_order, ax=axs[0])

    # Try plot grid lines between bars - problem at the moment plots grid lines on bars - want between bars
    yticklabels = ['\n'.join(textwrap.wrap(ticklabel.get_text(), 15)) for ticklabel in plot.get_yticklabels()]
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

    # Generatie heatmap plot
    plot = sns.heatmap(heat, norm=LogNorm(),  annot=True,  annot_kws={"fontsize": 7}, fmt="g", cmap=pal, square=False,
                       cbar=False, linewidths=0.5, linecolor="Grey", ax=axs[1], yticklabels=False)

    # Set color and weight of tick label for current hour
    for label in plot.get_xticklabels():
        if int(label.get_text()) == now.hour:
            label.set_color('yellow')

    plot.set_xticklabels(plot.get_xticklabels(), rotation=0, size=7)

    # Set heatmap border
    for _, spine in plot.spines.items():
        spine.set_visible(True)

    plot.set(ylabel=None)
    plot.set(xlabel="Hour of Day")
    # Set combined plot layout and titles
    f.subplots_adjust(top=0.9)
    plt.suptitle(f"{plot_type} {readings} Last Updated: {now.strftime('%Y-%m-%d %H:%M')}")

    # Save combined plot
    save_name = os.path.expanduser(f"~/BirdSongs/Extracted/Charts/{name}-{now.strftime('%Y-%m-%d')}.png")
    plt.savefig(save_name)
    plt.show()
    plt.close()


def load_fonts():
    # Add every font at the specified location
    font_dir = [os.path.expanduser('~/BirdNET-Pi/homepage/static')]
    for font in font_manager.findSystemFonts(font_dir, fontext='ttf'):
        font_manager.fontManager.addfont(font)
    # Set font family globally
    rcParams['font.family'] = 'Roboto Flex'


def main(daemon, sleep_m):
    load_fonts()
    while True:
        data, time = get_data()
        if not data.empty:
            create_plot(data, time, is_top=True)
            create_plot(data, time, is_top=False)
        if daemon:
            sleep(60 * sleep_m)
        else:
            break


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--daemon', action='store_true')
    parser.add_argument('--sleep', default=2, type=int, help='Time between runs (minutes)')
    args = parser.parse_args()
    main(args.daemon, args.sleep)

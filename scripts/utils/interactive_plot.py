"""This module generates a Plotly heatmap visualizing bird detection data, with hourly counts, confidence levels"""
import os
import pandas as pd
import plotly.graph_objects as go
import json
from plotly.subplots import make_subplots
import numpy as np
from utils.helpers import get_settings

conf = get_settings()
color_scheme = conf.get('COLOR_SCHEME', 'light')

if color_scheme == 'dark':
    PLOT_BGCOLOR = '#F0F0F0'
    PAPER_BGCOLOR = 'rgba(170, 170, 170, 0.7)'
    CUSTOM_COLOR_SCALE = [
        [0.0, PLOT_BGCOLOR],
        [0.2, '#BDBDBD'],
        [0.4, '#969696'],
        [0.6, '#737373'],
        [0.8, '#525252'],
        [1.0, '#252525']
    ]
else:
    PLOT_BGCOLOR = '#FFFFFF'
    PAPER_BGCOLOR = 'rgba(123, 197, 138, 0.7)'
    CUSTOM_COLOR_SCALE = [
        [0.0, PLOT_BGCOLOR],
        [0.2, '#A3D8A1'],
        [0.4, '#70BD70'],
        [0.6, '#46A846'],
        [0.8, '#2E7D2E'],
        [1.0, '#004D00']
    ]

ALL_HOURS = list(range(24))


def load_fonts():
    conf = get_settings()
    # Define font families based on language settings
    if conf['DATABASE_LANG'] in ['ja', 'zh']:
        return 'Noto Sans JP'
    elif conf['DATABASE_LANG'] == 'th':
        return 'Noto Sans Thai'
    else:
        return 'Roboto Flex'


def normalize_logarithmic(arr):
    """Applies a logarithmic normalization to the array, mapping values between 0.5 and max(arr) to a normalized scale between 0 and 1."""
    arr = arr.astype(float)
    min_val = 0.5
    arr = np.clip(arr, min_val, None)
    return np.log(arr / min_val) / np.log(np.max(arr) / min_val) if np.max(arr) > min_val else arr - min_val


def determine_text_color(z, threshold=0.8):
    """Determines text color (darkgrey or white) based on normalized value of z."""
    return np.where(z == 0, PLOT_BGCOLOR, np.where(z > threshold, PLOT_BGCOLOR, '#1A1A1A'))


def add_annotations(text_array, text_colors, col, species_list, all_hours, annotations, font_family):
    """Collects annotations for the heatmap without adding them individually, appending them to the provided annotations list."""
    if col in [1, 2]:  # Single-column heatmaps
        for i, species in enumerate(species_list):
            current_text, current_color = text_array[i, 0], text_colors[i, 0]
            if current_text:
                annotations.append(dict(
                    x=0, y=species, text=current_text, showarrow=False,
                    font=dict(family=font_family, color=current_color, size=10),
                    xref=f'x{col}', yref=f'y{col}', xanchor='center', yanchor='middle'
                ))
    elif col == 3:  # Multi-column heatmap
        for i, species in enumerate(species_list):
            for j, hour in enumerate(all_hours):
                current_text, current_color = text_array[i, j], text_colors[i, j]
                if current_text:
                    annotations.append(dict(
                        x=hour, y=species, text=current_text, showarrow=False,
                        font=dict(family=font_family, color=current_color, size=10),
                        xref='x3', yref='y3', xanchor='center', yanchor='middle'
                    ))


def create_plotly_heatmap(df_birds, now):
    """Creates a Plotly heatmap with annotations based on bird detection data."""

    font_family = load_fonts()

    main_title = f"Hourly Overview Updated at {now.strftime('%Y-%m-%d %H:%M:%S')}"
    subtitle = f"({df_birds['Com_Name'].nunique()} species today; {len(df_birds)} detections today)"

    # Ensure 'Time' is datetime
    if not pd.api.types.is_datetime64_any_dtype(df_birds['Time']):
        df_birds['Time'] = pd.to_datetime(df_birds['Time'], unit='ns')

    df_birds['Hour'] = df_birds['Time'].dt.hour

    plot_dataframe = df_birds.groupby(['Hour', 'Com_Name']).agg(
        Count=('Com_Name', 'count'),
        Conf=('Confidence', 'max')
    ).reset_index().fillna({'Conf': 0, 'Count': 0})

    df_birds_summary = plot_dataframe.groupby('Com_Name').agg(
        Count=('Count', 'sum'),
        Conf=('Conf', 'max')
    ).reset_index()
    df_birds_summary = df_birds_summary[df_birds_summary['Count'] > 0]
    df_birds_summary.sort_values(by=['Count', 'Conf'], ascending=[False, False], inplace=True)
    species_list = df_birds_summary['Com_Name'].tolist()

    z_confidence = normalize_logarithmic(df_birds_summary['Conf'].values.reshape(-1, 1)) * 100
    text_confidence = np.char.add((df_birds_summary['Conf'].values * 100).round().astype(int).astype(str), ' %')

    z_detections = normalize_logarithmic(df_birds_summary['Count'].values.reshape(-1, 1))
    text_detections = df_birds_summary['Count'].astype(str).values
    text_color_detections = determine_text_color(z_detections, threshold=0.5)

    df_hourly_counts = plot_dataframe.pivot_table(index='Com_Name', columns='Hour', values='Count', aggfunc='sum').fillna(0)
    df_hourly_conf = plot_dataframe.pivot_table(index='Com_Name', columns='Hour', values='Conf', aggfunc='max').fillna(0)
    df_hourly_counts = df_hourly_counts.reindex(species_list).fillna(0).reindex(columns=ALL_HOURS, fill_value=0)
    df_hourly_conf = df_hourly_conf.reindex(species_list).fillna(0).reindex(columns=ALL_HOURS, fill_value=0)

    z_hourly = normalize_logarithmic(df_hourly_counts.values)
    text_hourly = df_hourly_counts.astype(int).astype(str).values
    text_color_hourly = determine_text_color(z_hourly, threshold=0.5)

    custom_data_hourly = np.dstack((df_hourly_counts.values, (df_hourly_conf.values * 100).astype(int)))

    fig = make_subplots(rows=1, cols=3, shared_yaxes=True, column_widths=[0.1, 0.1, 0.7], horizontal_spacing=0.002)

    custom_data_confidence = np.array([{'confidence': conf * 100} for conf in df_birds_summary['Conf'].values]).reshape(-1, 1)
    custom_data_count = np.array([{'count': count} for count in df_birds_summary['Count'].values]).reshape(-1, 1)

    fig.add_trace(go.Heatmap(
        z=z_confidence, customdata=custom_data_confidence, x=['Confidence'], y=species_list,
        colorscale=CUSTOM_COLOR_SCALE, showscale=False,
        hovertemplate='Species: %{y}<br>Max Confidence: %{customdata.confidence:.0f}%<extra></extra>',
        xgap=1, ygap=1, zmin=0, zmax=100
    ), row=1, col=1)

    fig.add_trace(go.Heatmap(
        z=z_detections, customdata=custom_data_count, x=['Count'], y=species_list,
        colorscale=CUSTOM_COLOR_SCALE, showscale=False,
        hovertemplate='Species: %{y}<br>Total Counts: %{customdata.count}<extra></extra>',
        xgap=1, ygap=1, zmin=0, zmax=1
    ), row=1, col=2)

    fig.add_trace(go.Heatmap(
        z=z_hourly,
        customdata=custom_data_hourly,
        x=ALL_HOURS,
        y=species_list,
        colorscale=CUSTOM_COLOR_SCALE,
        showscale=False,
        text=text_hourly,
        hovertemplate='Species: %{y}<br>Hour: %{x}<br>Detections: %{customdata[0]}<br>Max Confidence: %{customdata[1]}%<extra></extra>',
        xgap=1,
        ygap=1,
        zmin=0,
        zmax=1
    ), row=1, col=3)

    annotations = []
    add_annotations(text_confidence.reshape(-1, 1), determine_text_color(z_confidence, threshold=0.5),
                    col=1, species_list=species_list, all_hours=ALL_HOURS, annotations=annotations, font_family=font_family)
    add_annotations(text_detections.reshape(-1, 1), text_color_detections,
                    col=2, species_list=species_list, all_hours=ALL_HOURS, annotations=annotations, font_family=font_family)
    add_annotations(text_hourly, text_color_hourly,
                    col=3, species_list=species_list, all_hours=ALL_HOURS, annotations=annotations, font_family=font_family)
    fig.update_layout(annotations=annotations)
    annotations_json = json.dumps(annotations)

    fig.update_layout(
        title=dict(
            text=f"<b>{main_title}</b><br><span style='font-size:12px;'>{subtitle}</span>",
            x=0.5, y=0.97, xanchor='center', yanchor='top',
            font=dict(family=font_family, size=20)
        ),
        autosize=True,
        height=max(600, len(species_list) * 25 + 100),
        yaxis=dict(
            autorange='reversed',
            tickfont=dict(family=font_family, size=10),
            showticklabels=True,
            ticklabelstandoff=15,
            fixedrange=True
        ),
        xaxis1=dict(
            title='Max Confidence',
            showticklabels=False,
            title_font=dict(family=font_family, size=10),
            fixedrange=True
        ),
        xaxis2=dict(
            title='Total Counts',
            showticklabels=False,
            title_font=dict(family=font_family, size=10),
            fixedrange=True
        ),
        xaxis3=dict(
            title='Hour',
            tickfont=dict(family=font_family, size=10),
            tickmode='linear',
            dtick=1,
            fixedrange=True
        ),
        margin=dict(l=20, r=20, t=80, b=80),
        clickmode='event+select',
        plot_bgcolor=PAPER_BGCOLOR,
        paper_bgcolor=PAPER_BGCOLOR,
        font=dict(family=font_family, size=10, color='#000000'),  # Global font color set to black
        dragmode=False
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)

    html_str = (
        "<div class='chart-container' style='width: 80%; margin: 0 auto;'>"
        + fig.to_html(
            include_plotlyjs='cdn',
            full_html=False,
            default_height='80%',
            default_width='100%',
            config=dict(
                scrollZoom=False,
                doubleClick=False,
                displaylogo=False,
                displayModeBar=False,
                modeBarButtonsToRemove=[
                    'zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'resetScale2d'
                ]
            )
        )
        + "</div>"
    )

    # Correct `custom_data_confidence` in the create_plotly_heatmap function:
    custom_data_confidence = np.array([
        {'confidence': conf * 100, 'count': count}
        for conf, count in zip(df_birds_summary['Conf'].values, df_birds_summary['Count'].values)
    ]).reshape(-1, 1)

    # In HTML string:
    html_str = f"""
    <style>.modebar-container {{ display: none !important; }}</style>
    <div class='chart-container' style='position: relative; max-width: 1000px; width: 98%; margin: 0 auto;'>
        <div style='position: absolute; bottom: 10px; left: 10px; z-index: 10;'>
            <input type='text' id='birdSearch' placeholder='Search...'
            style='padding: 5px; font-size: 12px; background-color: rgba(255, 255, 255, 0.5); color: #7F7F7F; border: none;
            border-radius: 3px; width: 150px;' />
            <button id='filterButton' style='padding: 5px; font-size: 12px; background-color: rgba(255, 255, 255, 0.5);
            color: #7F7F7F; border: none; border-radius: 3px; font-weight: normal;'>OK</button>
            <select id='sortOptions' style='padding: 5px; font-size: 12px; background-color: rgba(255, 255, 255, 0.5);
            color: #7F7F7F; border: none; border-radius: 3px;'>
                <option value="count" style="color: #7F7F7F;" selected>Count</option>
                <option value="confidence" style="color: #7F7F7F;">Max Confidence</option>
                <option value="species" style="color: #7F7F7F;">Species Name</option>
            </select>
        </div>
        {fig.to_html(
            include_plotlyjs='cdn',
            full_html=False,
            default_height='80%',
            default_width='100%',
            config=dict(
                scrollZoom=False,
                doubleClick=False,
                displaylogo=False,
                displayModeBar=False,
                modeBarButtonsToRemove=[
                    'zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'resetScale2d'
                ]
            )
        )}
    </div>

    <script>
        // Store the serialized annotations from Python
        var allAnnotations = {annotations_json};

        var plot = document.getElementsByClassName('plotly-graph-div')[0];
        var originalData = JSON.parse(JSON.stringify(plot.data));  // Deep copy of original data

        function applyFilter() {{
            var searchTerm = document.getElementById('birdSearch').value.toLowerCase();
            var sortOption = document.getElementById('sortOptions').value;
            var indicesToShow = [];
            var speciesList = originalData[0].y;

            // Filter species list based on search term
            speciesList.forEach(function(species, index) {{
                if (species.toLowerCase().includes(searchTerm)) {{
                    indicesToShow.push(index);
                }}
            }});

            // Sort indices based on selected sort option
            if (sortOption === 'confidence') {{
                indicesToShow.sort(function(a, b) {{
                    return originalData[0].customdata[b][0].confidence - originalData[0].customdata[a][0].confidence;
                }});
            }} else if (sortOption === 'species') {{
                indicesToShow.sort(function(a, b) {{
                    return speciesList[a].localeCompare(speciesList[b]);
                }});
            }} else if (sortOption === 'count') {{
                indicesToShow.sort(function(a, b) {{
                    return originalData[0].customdata[b][0].count - originalData[0].customdata[a][0].count;
                }});
            }}

            // Prepare new data based on sorted and filtered indices
            var newData = [];
            originalData.forEach(function(trace) {{
                var newTrace = JSON.parse(JSON.stringify(trace));
                if (trace.type === 'heatmap') {{
                    newTrace.y = indicesToShow.map(i => speciesList[i]);
                    newTrace.z = indicesToShow.map(i => trace.z[i]);
                    if (trace.customdata) {{
                        newTrace.customdata = indicesToShow.map(i => trace.customdata[i]);
                    }}
                    if (trace.text) {{
                        newTrace.text = indicesToShow.map(i => trace.text[i]);
                    }}
                }}
                newData.push(newTrace);
            }});

            // Filter annotations based on visible species
            var filteredAnnotations = allAnnotations.filter(function(annotation) {{
                var species = annotation.y.toLowerCase();
                return species.includes(searchTerm);
            }});

            // Update the plot with new data and annotations
            Plotly.react(plot, newData, plot.layout);
            Plotly.relayout(plot, {{ annotations: filteredAnnotations }});
        }}

        document.getElementById('filterButton').addEventListener('click', applyFilter);
        document.getElementById('birdSearch').addEventListener('keyup', function(event) {{
            if (event.key === 'Enter') {{
                applyFilter();
            }}
        }});
        document.getElementById('sortOptions').addEventListener('change', applyFilter);

        plot.on('plotly_click', function(data) {{
            if (data.points && data.points[0] && data.points[0].y) {{
                var species = data.points[0].y.replace(/ /g, '+');
                var url = '/views.php?view=Recordings&species=' + species;
                window.location.href = url;
            }}
        }});
    </script>
    """

    output_dir = os.path.expanduser('~/BirdSongs/Extracted/Charts/')
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'interactive_daily_plot.html'), 'w', encoding='utf-8') as f:
        f.write(html_str)

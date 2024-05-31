import seaborn as sns
import numpy as np
import dash
from dash import dcc
from dash import html
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go

def plot_generator(data):
    # plot = px.line(
    #     data_frame=data.rolling(window=1000).mean()[::6000],
    #     y='Fp1-M2',
    #
    #     title="EGG",
    #     width=1000,
    #     height=400,
    # )

    data = data[['Airflow', 'Chest', 'Abdomen', 'Gipno']].copy()
    data['Gipno'] = data['Gipno']/900

    n_records = len(data)
    time_range = pd.date_range(start='00:00:00', periods=n_records, freq='30s').strftime('%H:%M:%S')

    i = 0

    fig = go.Figure()
    for column in data.columns:
        data[column] = data[column]
        fig.add_trace(go.Scatter(x=time_range, y=data[column] + 0.02 * i, name=column))
        fig.update_xaxes(
            tickformat="%H"
        )
        i += 1
    fig.update_xaxes(rangeslider_visible=True)  # ranges slider

    return fig

def plot_to_html(app, data):
   div = html.Div(
        children=dcc.Graph(figure=plot_generator(data)),
        style={"display": "flex", "justify-content": "center"},
   )
   app.layout = html.Div(div)

if __name__ == "__main__":
    sample_data = pd.read_csv('to_lesha_test_csv.csv', sep=';')
    sample_data = sample_data.drop('Unnamed: 0', axis=1)
    gipno = pd.read_csv('111.csv', sep=';')
    sample_data['Gipno'] = gipno['1']

    app = dash.Dash(__name__)

    plot_to_html(app, sample_data)

    app.run_server(debug=True)


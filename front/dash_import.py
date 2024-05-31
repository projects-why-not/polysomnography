import seaborn as sns
import numpy as np
import dash
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, callback
from dash.exceptions import PreventUpdate



def div_maker(fig):
    return html.Div(
        children=dcc.Graph(figure=fig),
        style={"display": "flex", "justify-content": "center"},
    )

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
    data['Gipno'] = data['Gipno'] / 900

    n_records = len(data)
    time_range = pd.date_range(start='00:00:00', periods=n_records, freq='30s').strftime('%H:%M:%S')

    i = 0


    fig = go.Figure()
    for column in data.columns:
        data[column] = data[column]
        fig.add_trace(go.Scatter(x=time_range, y=data[column] + 0.02 * i, name=column))
        # fig.layout.width = 1400
        # fig.layout.height = 600
        fig.update_yaxes(showticklabels=False)
        fig.update_xaxes(
            tickformat="%H"
        )
        i += 1
    fig.update_xaxes(rangeslider_visible=True)  # ranges slider

    # return fig

    return div_maker(fig)


def input_plot_generator(data):
    data_slice = pd.DataFrame()
    for column in data.columns:
        if column in ['Fp1-M2', 'C3-M2', 'O1-M2', 'Fp2-M1', 'C4-M1', 'O2-M1']:
            data_slice[column] = data[column]

    i = 0

    n_records = len(data_slice)
    time_range = pd.date_range(start='00:00:00', periods=n_records, freq='30s').strftime('%H:%M:%S')
    data_slice['Time'] = time_range

    fig = go.Figure()
    for column in data_slice.drop('Time', axis=1).columns:
        # new[column] = new[column] + 0.01*i
        fig.add_trace(go.Scatter(x=data_slice['Time'], y=data_slice[column] + 0.0025 * i, name=column))
        # fig.layout.width = 1400
        # fig.layout.height = 900
        fig.update_yaxes(showticklabels=False)
        fig.update_xaxes(
            tickformat="%H"
        )
        i += 1

    fig.update_xaxes(rangeslider_visible=True)  # ranges slider

    # return fig

    return div_maker(fig)

# preloader = html.Div(className='preloader')

title_page = html.H1(children = 'Результаты анализа сна по ЭЭГ', className = 'title')

link_1 = html.A(children='Загрузить отчёт Word', href='link/to/your/download/file', download='output_report.docx')
link_2 = html.A(children='Загрузить отчёт PDF', href='link/to/your/download/file', download='output_report.pdf')


# external_stylesheets = [
#     {
#         "rel": "stylesheet",
#     },
# ]


if __name__ == "__main__":
    sample_data = pd.read_csv('to_lesha_test_csv.csv', sep=';')
    sample_data = sample_data.drop('Unnamed: 0', axis=1)
    gipno = pd.read_csv('111.csv', sep=';')
    sample_data['Gipno'] = gipno['1']

    app = dash.Dash(__name__)
    app._favicon = "images\\icon3.png"
    app.title = "Результат анализа"

    app.layout = html.Div(children=[
        title_page, 
        plot_generator(sample_data),  
        input_plot_generator(sample_data), 
        link_1, 
        link_2], 
        className='page')
    
   
    app.run_server(debug=True)

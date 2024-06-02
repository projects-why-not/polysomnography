import random
from dash import Dash, dcc, html, callback, Input, Output, clientside_callback
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import os

def auto_shablon_generator_pdf(episodes_df, duration, processing_time):
    # Получение текущего времени и форматирование в строку
    dir_path = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

    # Создание директории с именем текущего времени
    os.makedirs(dir_path)

    # Paths for output files
    output_pdf_path = os.path.join(dir_path, 'polysomnography_report.pdf')

    # Create a canvas object
    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 40, "Отчет для врача ... по полисомнографической записи ...")

    # Technical report section
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 80, "Технический отчет")
    c.setFont("Helvetica", 12)
    c.drawString(40, height - 100, f'Проведен анализ ПСГ длительностью {duration} минут')
    c.drawString(40, height - 120, f'Оценивались сигналы типа ЭЭГ')
    c.drawString(40, height - 140, f'Время обработки составило {processing_time} секунд')

    # Clinical report section
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 180, "Клинический отчет")

    y_position = height - 200
    if episodes_df.empty:
        c.setFont("Helvetica", 12)
        c.drawString(40, y_position, f'По результатам анализа выявлено отсутствие признаков нарушений дыхания во сне')
    else:
        c.setFont("Helvetica", 12)
        c.drawString(40, y_position, f'По результатам анализа выявлено наличие признаков нарушений дыхания во сне')
        y_position -= 20
        c.drawString(40, y_position, f'За время ПСГ выявлено {len(episodes_df)} эпизодов нарушения дыхания (НРД)')

        # Add table
        y_position -= 40
        c.setFont("Helvetica-Bold", 10)
        headers = ['№ эпизода НРД', 'Время начала регистрации эпизода НРД, с', 'Время завершения регистрации НРД, с',
                   'Длительность эпизода НРД, с', 'Тип эпизода НРД']
        for i, header in enumerate(headers):
            c.drawString(40 + i * 90, y_position, header)

        y_position -= 20
        c.setFont("Helvetica", 10)
        for index, row in episodes_df.iterrows():
            c.drawString(40, y_position, str(row["number"]))
            c.drawString(130, y_position, str(row["start_time"]))
            c.drawString(220, y_position, str(row["end_time"]))
            c.drawString(310, y_position, str(row["duration"]))
            c.drawString(400, y_position, row["type"])
            y_position -= 20

        # Длительность эпизода НРД, с
        fig = go.Figure()
        fig.add_trace(go.Box(y=episodes_df['duration']))
        fig.update_xaxes(showticklabels=False)
        fig.update_layout(template='plotly', title={
            'text': "Длительность эпизода НРД, с",
            'y': 0.9,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
        }, )
        image_path = os.path.join(dir_path, 'image_graf.png')
        fig.write_image(image_path)

        c.drawImage(image_path, 40, y_position - 200, width=6 * inch, preserveAspectRatio=True, mask='auto')
        y_position -= 220

        # Средняя длительность – […] секунд
        c.drawString(40, y_position, f'Средняя длительность – {round(episodes_df["duration"].mean(), 2)} секунд')
        y_position -= 20
        # Медиана длительности НРД -- […] секунд
        c.drawString(40, y_position, f'Медиана длительности НРД – {round(episodes_df["duration"].median(), 2)} секунд')
        y_position -= 20
        # Разброс длительности НРД -- от […] секунд до […] секунд
        c.drawString(40, y_position,
                     f'Разброс длительности НРД - от {round(episodes_df["duration"].quantile(0.25), 2)} секунд до {round(episodes_df["duration"].quantile(0.75), 2)} секунд')
        y_position -= 40

        # Количество разных типов апноэ за всю ночь
        fig = go.Figure()
        fig.add_trace(go.Bar(x=episodes_df[episodes_df["type"].str.contains("апноэ")]['type'].unique(),
                             y=episodes_df[episodes_df["type"].str.contains("апноэ")]['type'].value_counts()))
        fig.update_layout(template='plotly', title={
            'text': "Количество разных типов апноэ за всю ночь",
            'y': 0.9,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
        }, )
        image_path = os.path.join(dir_path, 'image_graf1.png')
        fig.write_image(image_path)

        c.drawImage(image_path, 40, y_position - 200, width=6 * inch, preserveAspectRatio=True, mask='auto')
        y_position -= 220

        # Количество разных типов нарушений дыхания
        values_of_different_types_of_respiratory_disorders = episodes_df["type"].replace({
            "центральное апноэ": "апноэ",
            "обструктивное апноэ": "апноэ",
            "апноэ": "апноэ",
            "апноэ неопределенного типа": "апноэ"
        })
        fig = go.Figure()
        fig.add_trace(go.Bar(x=values_of_different_types_of_respiratory_disorders.unique(),
                             y=values_of_different_types_of_respiratory_disorders.value_counts()))
        fig.update_layout(template='plotly', title={
            'text': "Количество разных типов нарушений дыхания",
            'y': 0.9,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
        }, )
        image_path = os.path.join(dir_path, 'image_graf2.png')
        fig.write_image(image_path)

        c.drawImage(image_path, 40, y_position - 200, width=6 * inch, preserveAspectRatio=True, mask='auto')
        y_position -= 220

        # Распределение эпизодов НРД по первой, второй и последней третях ночного сна
        fig = go.Figure()
        fig.add_trace(go.Bar(x=['первая треть', 'вторая треть', 'последняя треть'],
                             y=[len(episodes_df[episodes_df['start_time'] < duration / 3]),
                                len(episodes_df[(episodes_df['start_time'] > duration / 3) & (
                                        episodes_df['start_time'] < duration * 2 / 3)]),
                                len(episodes_df[episodes_df['start_time'] > duration * 2 / 3])]))
        fig.update_layout(template='plotly', title={
            'text': "Распределение эпизодов НРД по третям ночного сна",
            'y': 0.9,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
        }, )
        image_path = os.path.join(dir_path, 'image_graf3.png')
        fig.write_image(image_path)

        c.drawImage(image_path, 40, y_position - 200, width=6 * inch, preserveAspectRatio=True, mask='auto')
        y_position -= 220

    # Save the PDF document
    c.save()

    return output_pdf_path

def div_maker(fig):
    return html.Div(
        children=dcc.Graph(figure=fig),
        style={"display": "flex", "justify-content": "center"},
    )

def upper_plot_generator(data_poly, data_gipno):

    i = 0

    fig = go.Figure()
    for column in data_poly.columns[:-1]:
        if column in ['Airflow', 'Chest', 'Abdomen']:
            fig.add_trace(go.Scatter(x=data_poly['Time'], y=data_poly[column] - 0.005 * i, name=column))
            i += 1

    if data_gipno is not None:
        fig.add_trace(go.Scatter(x=data_gipno['Time'], y=data_gipno['stage'] / 900 - 0.0075 * i, name='gipno'))

    fig.update_yaxes(showticklabels=False)
    fig.update_xaxes(
        tickformat="%H:%M:%S"
    )
    fig.update_xaxes(rangeslider_visible=True)  # ranges slider

    return div_maker(fig)

def lower_plot_generator(data):
    i = 0

    fig = go.Figure()
    for column in data.columns[:-1]:
        if column in ['Fp1-M2', 'C3-M2', 'O1-M2', 'Fp2-M1', 'C4-M1', 'O2-M1']:
            fig.add_trace(go.Scatter(x=data['Time'], y=data[column] - 0.0005 * i, name=column))
            i += 1
    fig.update_yaxes(showticklabels=False)
    fig.update_xaxes(
        tickformat="%H:%M:%S"
    )
    fig.update_xaxes(rangeslider_visible=True)  # ranges slider

    return div_maker(fig)

def start_dash(data_poly, data_gipno, episodes, hertz, processing_time):
    data_poly, data_gipno, duration = data_preprocessing(data_poly, data_gipno, hertz)

    path_pdf = auto_shablon_generator_pdf(episodes, duration, processing_time)
    path_word = ''

    app = Dash(__name__)
    app._favicon = "images/icon3.png"
    app.title = "Результат анализа"

    title_page = html.H1(children='Результаты анализа сна по ЭЭГ', className='title')

    link_1 = html.A(children=html.Div(children=html.P('Загрузить отчёт .docx', className='download_button_lable'), className='link__button'), href='link/to/your/download/file', download=path_word)
    link_2 = html.A(children=html.Div(children=html.P('Загрузить отчёт .pdf', className='download_button_lable'), className='link__button'), href='link/to/your/download/file', download=path_pdf)
    link_place = html.Div(children=[link_1, link_2], className='link__place')

    report_message = html.H3('Загрузить полный отчёт на компьютер', className='report_message')
    report_place = html.Div(children=[report_message, link_place], className='report_place')

    app.layout = html.Div(children=[
        title_page,
        html.Div(children=upper_plot_generator(data_poly, data_gipno), className='upper_plot'),
        html.Div(children='Показать ЭЭГ',className="lower-plot__button", id="test"),
        html.Div(children=lower_plot_generator(data_poly), className='lower_plot', id='lowerplot'),
        report_place],
        className='page')
    
    clientside_callback(
    """
    function(id) {
        const el = document.getElementById("test");
        const tosee = document.getElementById("lowerplot");
        el.addEventListener('click', () => {
        tosee.classList.toggle("lower_plot_visible")
        if (el.textContent === "Показать ЭЭГ"){
        el.textContent = "Скрыть ЭЭГ"
        el.style.marginBottom ='0'
        } else {
        el.textContent = "Показать ЭЭГ"
        el.style.marginBottom = '32px'
        }
        })
        
        
        
        return window.dash_clientside.no_update
    }
    """,
    Output("test","id"),
    Input("test","id"),
    )

    app.run_server(port=9857, debug=True)

def data_preprocessing(data_poly, data_gipno, hertz):
    poly = pd.DataFrame()
    for column in data_poly.columns:
        poly[column] = data_poly[column].rolling(window=hertz).mean()[::hertz]
    poly.loc[0, poly.columns] = data_poly.loc[0, poly.columns]
    poly['Time'] = pd.date_range(start='00:00:00', periods=len(poly), freq='1s')


    data_gipno['Time'] = pd.date_range(start='00:00:00', periods=len(data_gipno), freq='30s')
    data_gipno = data_gipno[['Time', 'stage']].copy()

    duration = int((poly['Time'].iloc[-1] - poly['Time'].iloc[0]).total_seconds())

    return poly, data_gipno, duration

if __name__ == "__main__":
    #input
    data1 = pd.read_csv('../../full_data.csv')
    data2 = pd.read_csv('../../hypno.csv')
    hertz = 200
    processing_time = random.randrange(5,15)
    episodes_data = pd.read_csv('../../episodes.csv')
    #func
    start_dash(data1, data2, episodes_data, hertz, processing_time)


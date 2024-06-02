import pandas as pd
import numpy as np
import mne
import json
import os

from DataProcessor import DataProcessor

from catboost import CatBoostRegressor

from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error as mse
from sklearn.metrics import mean_absolute_error as mae
from sklearn.metrics import mean_squared_error as rmse
from sklearn.metrics import mean_absolute_percentage_error as mape

from scipy import signal
from scipy.fft import fft, ifft
from scipy.signal import butter
from scipy.signal import argrelextrema
from statistics import mean, median


class Analyser:
    # Class attributes for storing paths, dataframes, and model-related information
    dir_path = None
    system = None
    model_path = None
    scaler = None

    df_poly = None
    df_hypno = None

    XX = None
    yy = None
    X = None
    y = None

    X_train = None
    X_test = None
    y_train = None
    y_test = None
    y_train_pred = None
    y_test_pred = None

    def __init__(
        self,
        path: str,
        pretrained_model_path: str,
        system: str = None,
        default_scaler=MinMaxScaler(),
    ):
        """
        Инициализация анализатора.

        :param path: Путь к данным.
        :param pretrained_model_path: Путь к предобученной модели.
        :param system: Операционная система ('win' или 'mac').
        :param default_scaler: Масштабировщик по умолчанию (MinMaxScaler).
        """
        self.dir_path = path
        self.system = system
        self.model_path = pretrained_model_path
        self.scaler = default_scaler
        self.dp = DataProcessor(path)

    def get_record(self, patient_id, record_id, addname="", columns=[]):
        """
        Получение записей полиграфии и гипнограммы пациента.

        :param patient_id: ID пациента.
        :param record_id: ID записи.
        :param addname: Дополнительное имя для файла.
        :param columns: Список столбцов для извлечения.
        """
        if self.dir_path is None:
            if self.system == "win":
                file_path = "C:\\Users\\TereschenkoAV3\\VSCodeProjects\\DFOHack\\Data"
            else:
                file_path = "/Users/fffgson/vscode/Python/MHDWork/DFOHack/Data"
        else:
            file_path = self.dir_path

        result = []
        for type in ["poly", "hypno"]:
            raw = self.dp.fix_load_specific(file_path, patient_id, record_id)
            data = self.dp.get_data(raw, patient_id, record_id, type)
            df = self.dp.make_df(data)
            result.append(df)

        self.df_poly, self.df_hypno = result[0], result[1]

    def prep_XX_yy(
        self,
        df,
        used_columns,
        target,
        window=200,
        step=200,
        shifts=[-30, -15, -5, 5, 15, 30],
    ):
        """
        Подготовка признаков и целевой переменной для модели.

        :param df: DataFrame с данными.
        :param used_columns: Используемые столбцы.
        :param target: Целевая переменная.
        :param window: Размер окна для скользящего среднего и медианы.
        :param step: Шаг окна.
        :param shifts: Список сдвигов для признаков.
        """
        feat = df[used_columns][window::step]
        targ = df[target][window::step].reset_index().drop(columns="index")
        mean_feat = (
            df[used_columns]
            .rolling(window=window)
            .mean()[window::step]
            .reset_index()
            .drop(columns="index")
        )
        median_feat = (
            df[used_columns]
            .rolling(window=window)
            .median()[window::step]
            .reset_index()
            .drop(columns="index")
        )
        for col in mean_feat.columns:
            feat[col + "_mean"] = mean_feat[col]
        for col in median_feat.columns:
            feat[col + "_median"] = median_feat[col]
        shifts_cols = feat.columns
        for sh in shifts:
            for col in shifts_cols:
                feat[col + f"_shifted{sh}"] = feat[col].shift(sh)
        for col in mean_feat.columns:
            feat["ratio"] = feat[col] / feat[col + "_median"]
            feat["diff"] = feat[col] - feat[col + "_median"]
        tail = max(shifts)
        XX = feat[tail:]
        XX = XX[:-tail].reset_index().drop(columns="index")
        yy = targ[tail:]
        yy = yy[:-tail].reset_index().drop(columns="index")
        self.XX, self.yy = XX, yy

    def prep_X_y(
        self,
        used_columns,
        target,
        window=200,
        step=200,
        shifts=[-30, -15, -5, 5, 15, 30],
    ):
        """
        Подготовка данных для обучения и тестирования модели.

        :param used_columns: Используемые столбцы.
        :param target: Целевая переменная.
        :param window: Размер окна для скользящего среднего и медианы.
        :param step: Шаг окна.
        :param shifts: Список сдвигов для признаков.
        """
        feat = self.df_poly[used_columns][window::step]
        targ = self.df_poly[target][window::step].reset_index().drop(columns="index")
        mean_feat = (
            self.df_poly[used_columns]
            .rolling(window=window)
            .mean()[window::step]
            .reset_index()
            .drop(columns="index")
        )
        median_feat = (
            self.df_poly[used_columns]
            .rolling(window=window)
            .median()[window::step]
            .reset_index()
            .drop(columns="index")
        )
        for col in mean_feat.columns:
            feat[col + "_mean"] = mean_feat[col]
        for col in median_feat.columns:
            feat[col + "_median"] = median_feat[col]
        shifts_cols = feat.columns
        for sh in shifts:
            for col in shifts_cols:
                feat[col + f"_shifted{sh}"] = feat[col].shift(sh)
        for col in mean_feat.columns:
            feat["ratio"] = feat[col] / feat[col + "_median"]
            feat["diff"] = feat[col] - feat[col + "_median"]
        tail = max(shifts)
        XX = feat[tail:]
        XX = XX[:-tail].reset_index().drop(columns="index")
        yy = targ[tail:]
        yy = yy[:-tail].reset_index().drop(columns="index")
        self.X, self.y = XX.values, yy.values

    def split_scale(self, test_size=0.2):
        """
        Разделение данных на обучающую и тестовую выборки, и их масштабирование.

        :param test_size: Размер тестовой выборки (доля).
        """
        l = len(self.X)
        X_train, X_test, y_train, y_test = (
            self.X[: round(l * test_size)],
            self.X[round(l * test_size) :],
            self.y[: round(l * test_size)],
            self.y[round(l * test_size) :],
        )
        sc = self.scaler
        X_train_scaled = sc.fit_transform(X_train)
        X_test_scaled = sc.transform(X_test)
        y_train_scaled = sc.fit_transform(y_train)
        y_test_scaled = sc.transform(y_test)
        self.X_train, self.X_test, self.y_train, self.y_test = (
            X_train_scaled,
            X_test_scaled,
            y_train_scaled,
            y_test_scaled,
        )

    def get_predictions(self):
        """
        Получение предсказаний модели на обучающей и тестовой выборках.
        """
        m = CatBoostRegressor()
        m.load_model()
        self.y_train_pred = m.predict(self.X_train)
        self.y_test_pred = m.predict(self.X_test)

    def wake_coords(self, hyp):
        """
        Функция отрезает начальную и конечную части записи, где пациент ещё не спит.

        :param hyp: Гипнограмма.
        :return: Начало и конец фаз сна.
        """
        i, j = 0, len(hyp)
        while (hyp[i] == 0) & (i != len(hyp) - 1):
            i += 1
        while (hyp[j - 1] == 0) & (j != 0):
            j -= 1
        if j <= i:
            i, j = j, i
        return i, j

    def count_amplitudes(self, i, df, window_big, window_small, num_parts):
        """
        Расчёт амплитуд в окрестности заданной точки.

        :param i: Точка на графике.
        :param df: DataFrame с данными.
        :param window_big: Размер большого окна.
        :param window_small: Размер маленького окна.
        :param num_parts: Количество частей для большого окна.
        :return: Маленькая и большая амплитуды.
        """
        small_max = max(df.Airflow[(i - window_small // 2) : (i + window_small // 2)])
        small_min = min(df.Airflow[(i - window_small // 2) : (i + window_small // 2)])
        small_amplitude = abs(small_max - small_min)

        part_big_max = []
        part_big_min = []
        for j in range(num_parts // 2):
            part_size = (window_big - window_small) // num_parts

            part_big_max_left = max(
                df.Airflow[
                    (i - window_big // 2 + j * part_size) : (
                        i - window_big // 2 + (j + 1) * part_size
                    )
                ]
            )
            part_big_max_right = max(
                df.Airflow[
                    (i + window_big // 2 - (j + 1) * part_size) : (
                        i + window_big // 2 - j * part_size
                    )
                ]
            )
            part_big_max.append(part_big_max_left)
            part_big_max.append(part_big_max_right)

            part_big_min_left = min(
                df.Airflow[
                    (i - window_big // 2 + j * part_size) : (
                        i - window_big // 2 + (j + 1) * part_size
                    )
                ]
            )
            part_big_min_right = min(
                df.Airflow[
                    (i + window_big // 2 - (j + 1) * part_size) : (
                        i + window_big // 2 - j * part_size
                    )
                ]
            )
            part_big_min.append(part_big_min_left)
            part_big_min.append(part_big_min_right)

        big_max = median(part_big_max)
        big_min = median(part_big_min)
        big_amplitude = abs(big_max - big_min)

        return small_amplitude, big_amplitude

    def mark_episodes(self, df, hyp, big_window=60, small_window=4, num_parts=8):
        """
        Основная функция для разметки эпизодов НДС в выбранном фрагменте.

        :param df: DataFrame с данными.
        :param hyp: Гипнограмма.
        :param big_window: Размер большого окна оценки амплитуды.
        :param small_window: Размер маленького окна оценки амплитуды.
        :param num_parts: Количество кусочков большого окна.
        :return: Словарь с эпизодами апноэ и гипопноэ.
        """
        window_big = 200 * big_window
        window_small = 200 * small_window
        start, end = self.wake_coords(hyp)

        episode_s_e = {"apnoe": [], "hypapnoe": []}
        episode_idx = {"apnoe": [], "hypapnoe": []}

        apnoe = []
        hypapnoe = []
        for i in range(
            start + window_big // 2, end - window_big // 2, window_small // 2
        ):
            small_amplitude, big_amplitude = self.count_amplitudes(
                i, df, window_big, window_small, num_parts
            )

            max_sat = max(
                df.SaO2[
                    (i - window_big // 2 + small_window) : (
                        i + window_big // 2 + small_window
                    )
                ]
            )
            min_sat = min(
                df.SaO2[
                    (i - window_big // 2 + small_window) : (
                        i + window_big // 2 + small_window
                    )
                ]
            )

            if small_amplitude < big_amplitude * 0.1:
                apnoe += range(i - window_small // 2, i + window_small // 2)
                episode_idx["apnoe"].append(i)
            elif (small_amplitude < big_amplitude * 0.5) & (max_sat - min_sat >= 4):
                hypapnoe += range(i - window_small // 2, i + window_small // 2)
                episode_idx["hypapnoe"].append(i)
            else:
                if apnoe:
                    episode_s_e["apnoe"].append((apnoe[0], apnoe[-1]))
                elif hypapnoe:
                    episode_s_e["hypapnoe"].append((hypapnoe[0], hypapnoe[-1]))
                apnoe = []
                hypapnoe = []

        return episode_s_e

    def automark(
        self, patient_id, record_id, df, hyp, big_window=60, small_window=4, num_parts=8
    ):
        """
        Автоматическая разметка эпизодов для заданного пациента и записи.

        :param patient_id: ID пациента.
        :param record_id: ID записи.
        :param df: DataFrame с данными.
        :param hyp: Гипнограмма.
        :param big_window: Размер большого окна оценки амплитуды.
        :param small_window: Размер маленького окна оценки амплитуды.
        :param num_parts: Количество кусочков большого окна.
        :return: Размеченные эпизоды.
        """
        raw = self.dp.fix_load_specific(patient_id, record_id)
        return

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
from sklearn.metrics import root_mean_squared_error as rmse
from sklearn.metrics import mean_absolute_percentage_error as mape

from scipy import signal
from scipy.fft import fft, ifft
from scipy.signal import butter
from scipy.signal import argrelextrema
from statistics import mean, median


class Analyser:
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
        self.dir_path = path
        self.system = system
        self.model_path = pretrained_model_path
        self.scaler = default_scaler
        self.dp = DataProcessor(path)

    def get_record(self, patient_id, record_id, addname="", columns=[]):
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

        self.df_polu, self.df_hypno = result[0], result[1]

    def prep_XX_yy(
        self,
        df,
        used_columns,
        target,
        window=200,
        step=200,
        shifts=[-30, -15, -5, 5, 15, 30],
    ):
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
        m = CatBoostRegressor()
        m.load_model()
        self.y_train_pred = m.predict(self.X_train)
        self.y_test_pred = m.predict(self.X_test)

    # Эта функция отрезает начальную и конечную части записи, где пациент ещё не спит
    def wake_coords(self, hyp):
        i, j = 0, len(hyp)
        # Цикл, по которому мы ищем начало первой фазы сна
        while (hyp[i] == 0) & (i != len(hyp) - 1):
            i += 1

        # Цикл, по которому мы ищем конец последней фазы сна
        while (hyp[j - 1] == 0) & (j != 0):
            j -= 1
        # Условие, нужное при проверке эпизодов среди сна (если вдруг пациент проснулся ночью, счётчик может сбиться)
        if j <= i:
            i, j = j, i
        return i, j

    # Функция для расчёта амплитуд в окрестности заданной точки i
    def count_amplitudes(self, i, df, window_big, window_small, num_parts):

        # Считаем максимальные и минимальные значения внутри маленького окошка
        small_max = max(df.Airflow[(i - window_small // 2) : (i + window_small // 2)])
        small_min = min(df.Airflow[(i - window_small // 2) : (i + window_small // 2)])
        small_amplitude = abs(
            small_max - small_min
        )  # Считаем максимальную амплитуду внутри маленького окна

        # Инициализируем списки максимумов и минимумов большого окна
        part_big_max = []
        part_big_min = []
        # Итерируемся по кусочкам большого окна слева и справа от маленького окна
        for j in range(num_parts // 2):
            # Считаем размер кусочка большого окна
            part_size = (window_big - window_small) // num_parts

            # Считаем максимальное значение внутри кусочка слева и справа (j-ого слева и j-ого справа)
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

            # Считаем минимальное значение внутри кусочка слева и справа (j-ого слева и j-ого справа)
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

        # Берём медианные значения по максимума и минимума по кусочкам
        big_max = median(part_big_max)
        big_min = median(part_big_min)
        big_amplitude = abs(
            big_max - big_min
        )  # Считаем медианную амплитуду по большому окну

        return small_amplitude, big_amplitude

    # Основная большая функция для разметки эпизодов НДС в выбранном фрагменте
    def mark_episodes(self, df, hyp, big_window=60, small_window=4, num_parts=8):
        """
        На вход подаётся:

        - df = датафрейм(или его срез),
        - hyp = гипнограмма(или такой же её срез, как в датафрейме),
        - big_window = размер большого окна оценки амплитуды,
        - small_window = размер маленького окна оценки амплитуды,
        - num_parts = количество кусочков большого окна, в которых мы будем считать амплитуды

        В этой функции нам нужны каналы Airflow и SaO2
        """
        # Переводим секунды в точки на графике
        window_big = 200 * big_window
        window_small = 200 * small_window
        start, end = self.wake_coords(hyp)  # Вычисляем начало и конец отсчёта

        # Сохраняем для каждого эпизода начало и конец
        episode_s_e = {"apnoe": [], "hypapnoe": []}

        episode_idx = {
            "apnoe": [],
            "hypapnoe": [],
        }  # Сохраняем координаты эпизодов НДС (на всякий случай, если допрём до нового варианта модели)

        # Инициализируем списки точек, в которых найдено апноэ или гипопноэ
        apnoe = []
        hypapnoe = []
        # Движемся в цикле большим окном по списку (в середине большого окна маленькое окно)
        for i in range(
            start + window_big // 2, end - window_big // 2, window_small // 2
        ):

            # Считаем амплитуды большого и маленького окна в координате i
            small_amplitude, big_amplitude = self.count_amplitudes(
                i, df, window_big, window_small, num_parts
            )

            # Считаем максимальное и минимальное значение сатурации со сдвигом вперёд по времени
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

            # Задаём условия отнесения НДС к тому или иному типу
            if small_amplitude < big_amplitude * 0.1:
                apnoe += range(i - window_small // 2, i + window_small // 2)
                episode_idx["apnoe"].append(i)
            elif (small_amplitude < big_amplitude * 0.5) & (max_sat - min_sat >= 4):
                hypapnoe += range(i - window_small // 2, i + window_small // 2)
                episode_idx["hypapnoe"].append(i)
            else:
                # Если в точке i НДС не обнаружен, сохраняем в словарь координаты последнего НДС и обнуляем списки точек апноэ и гипопноэ
                if apnoe:
                    episode_s_e["apnoe"].append((apnoe[0], apnoe[-1]))
                elif hypapnoe:
                    episode_s_e["hypapnoe"].append((hypapnoe[0], hypapnoe[-1]))
                apnoe = []
                hypapnoe = []

        return episode_s_e

    def automark(self, patient_id, record_id, df, hyp, big_window=60, small_window=4, num_parts=8):
        raw = self.dp.fix_load_specific(patient_id, record_id)
        return 
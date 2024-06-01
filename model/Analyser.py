import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import mne
import json
import os
import warnings
warnings.filterwarnings('ignore')
from pyspark.sql import SparkSession
from DataProcessor import DataProcessor

from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor
import lightgbm as lgb

from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error as mse
from sklearn.metrics import mean_absolute_error as mae
from sklearn.metrics import root_mean_squared_error as rmse
from sklearn.metrics import mean_absolute_percentage_error as mape
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression, Lasso, Ridge

from sklearn.svm import SVR
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline

class Analyser():

    @staticmethod
    def get_record(patient_id, record_id, pathh=None, syst="win", addname="", columns=[]):
        if pathh is None:
            if syst == "win":
                path = "C:\\Users\\TereschenkoAV3\\VSCodeProjects\\DFOHack\\Data"
            else:
                path = "/Users/fffgson/vscode/Python/MHDWork/DFOHack/Data"
        else:
            path = pathh

        result = []
        for type in ["poly", "hypno"]:

            raw = DataProcessor.fix_load_specific(path, patient_id, record_id)

            data = DataProcessor.get_data(raw, patient_id, record_id, type)

            df = DataProcessor.make_df(data)
            
            result.append(df)
            
        return result[0], result[1]

    @staticmethod
    def prep(df, used_columns, target, window=200, step=200, shifts=[-30, -15, -5, 5,15,30]):
        feat = df[used_columns][window::step]
        targ = df[target][window::step].reset_index().drop(columns="index")
        mean_feat = df[used_columns].rolling(window=window).mean()[window::step].reset_index().drop(columns="index")
        median_feat = df[used_columns].rolling(window=window).median()[window::step].reset_index().drop(columns="index")
        for col in mean_feat.columns:
            feat[col+"_mean"] = mean_feat[col]
        for col in median_feat.columns:
            feat[col+"_median"] = median_feat[col]
        shifts_cols = feat.columns
        for sh in shifts:
            for col in shifts_cols:
                feat[col+f"_shifted{sh}"] = feat[col].shift(sh)
        for col in mean_feat.columns:
            feat["ratio"] = feat[col]/feat[col+"_median"]
            feat["diff"] = feat[col]-feat[col+"_median"]
        tail = max(shifts)
        XX = feat[tail:]
        XX = XX[:-tail].reset_index().drop(columns="index")
        yy = targ[tail:]
        yy = yy[:-tail].reset_index().drop(columns="index")
        return XX, yy
    
    @staticmethod
    def split_scale(X, y, scaler, test_size=0.2):
        l = len(X)
        X_train, X_test, y_train, y_test = X[:round(l*test_size)], X[round(l*test_size):], y[:round(l*test_size)], y[round(l*test_size):]
        sc=scaler
        X_train_scaled = sc.fit_transform(X_train)
        X_test_scaled = sc.transform(X_test)
        y_train_scaled = sc.fit_transform(y_train)
        y_test_scaled = sc.transform(y_test)
        return X_train_scaled, X_test_scaled, y_train_scaled, y_test_scaled
    
    @staticmethod
    def get_predictions(X, y, model_path):
        m = CatBoostRegressor()
        m.load_model()
        m.predict
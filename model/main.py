import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import mne
import os
import string
import random
import codecs

sns.set_theme(style="darkgrid", palette="muted", font_scale=1)


# Функция подготовки датасета к использованию
def fix_file(dirpath: str, file):
    file_name = file.split(".")[0]
    file_format = file.split(".")[1]

    if file_format == "EDF":
        return os.path.join(dirpath, file)

    elif file_format == "REC":
        # Исправляем формат времени в файле
        with codecs.open(os.path.join(dirpath, file), "r+", encoding="cp1251") as f:
            row = f.readline(200)
            row = row.replace(":", ".")
            f.seek(0)
            f.write(row)
        # Переименовываем файл в формат EDF
        new_file = os.path.join(dirpath, file_name + "_poly" + ".EDF")
        os.rename(os.path.join(dirpath, file), new_file)
        return new_file

    else:
        # Переименовываем файл в формат EDF
        new_file = os.path.join(dirpath, file_name + "_hypno" + ".EDF")
        os.rename(os.path.join(dirpath, file), new_file)
        return new_file


# Функция загрузки данных из датасета
def load_raw_file(file, format, verbose=0):
    raw_file = mne.io.read_raw_edf(file, preload=True, verbose=verbose)
    print("File loaded!")
    # Здесь пропишем, что именно хотим получить из файла, а пока возвращаю полностью данные
    return raw_file


# Функция обработки и загрузки данных в программу:
def files_ready(path: str, syst="win") -> list:
    """
    Возвращает тип raw_data, из которого можно вытащить все данные срезами и парой функций
    data = res_list[N_patient][0 - гипнография]['poly' - код для получания данных из тапла].get_data()
    channels = res_list[0][1 - полисомнография]['poly'].ch_names
    """
    # В этой переменной лежат все открытые файлы, чтобы не возвращать глобальные переменные без явного объявления
    result = []
    # Выбор сепаратора в зависимости от OS
    if syst == "win":
        separator = "\\"
    else:
        separator = "/"
    # Вводим директорию с НД:
    os.chdir(path)
    # Печатаем все файлы и папки рекурсивно
    for dirpath, dirnames, filenames in os.walk("."):
        # Перебираем файлы
        # В этой переменной лежит пара hypno/poly
        pre_result = {}
        for file in filenames:
            # Заглушка для MacOS
            if file == ".DS_Store":
                continue
            else:
                print("File:", os.path.join(dirpath, file))
                new_file = fix_file(dirpath, file)
                # print(new_file)
                patient = new_file.split(separator)[1][3:]
                research = new_file.split(separator)[2][3:]

                pre_result["patient"] = int(patient)
                pre_result["record"] = int(research)

                # Запись в переменную либо поли, либо гипно, возможность сохранения в глобальные переменные закомментирована
                if new_file[-8:-4] == "poly":
                    # globals()[
                    #     "df" + "_p" + str(patient) + "_r" + str(research) + "_poly"
                    # ] = load_raw_file(new_file, format="poly")
                    pre_result["poly"] = load_raw_file(new_file, format="poly")
                    # print("==========> Poly successfull! <==========")
                elif new_file[-9:-4] == "hypno":
                    # globals()[
                    #     "df" + "_p" + str(patient) + "_r" + str(research) + "_hypno"
                    # ] = load_raw_file(new_file, format="hypno")
                    pre_result["hypno"] = load_raw_file(new_file, format="hypno")
                    # print("==========> Hypno successfull! <==========")
        if len(pre_result) > 0:
            result.append(pre_result)
    return result


# Возврат частоту дискретизации из информации о raw файле
def get_freq(raw_data: list, N_patient: int, N_record: int, research_type: str):
    for i in raw_data:
        if i["patient"] == N_patient and i["record"] == N_record:
            freq = dict(i[research_type].info)["sfreq"]
    return freq


# Функция которая возвращает словарь
def get_data(raw_data: list, N_patient: int, N_record: int, research_type: str):
    for i in raw_data:
        if i["patient"] == N_patient and i["record"] == N_record:
            if research_type == "poly":
                data = i[research_type].get_data()
                channels = i[research_type].ch_names

                res = dict()
                res["research_type"] = research_type
                for idx, col in enumerate(channels):
                    res[col] = data[idx]

                return res

            if research_type == "hypno":
                res = dict()
                res["research_type"] = research_type

                hypno_data = i[research_type][0][0].flatten()
                hypno_timestamps = i[research_type][0][1].flatten()
                res["timestamps"] = hypno_timestamps
                res["stage"] = hypno_data

                return res


def make_df(data):
    if data["research_type"] == "poly":
        return pd.DataFrame(data).drop(columns="research_type")
    else:
        df = pd.DataFrame(data).drop(columns="research_type")
        return df


if __name__ == "__main__":
    # path = "C:\\Users\\TereschenkoAV3\\VSCodeProjects\\DFOHack\\Data"
    # general = loadData(path)
    # if len(general) > 0:
    #     choice_type = input("CHOOSE TYPE (poly/gipno): ")
    #     choice_number = int(input("CHOOSE FILE NUMBER (1-8): "))
    #     choice_frame = input("CHOOSE FRAME (info/data): ")

    #     res = choose_file(general, choice_type, choice_number, choice_frame)

    #     printout(res)
    mac_path = "/Users/fffgson/vscode/Python/MHDWork/DFOHack/Data"
    win_path = "C:\\Users\\TereschenkoAV3\\VSCodeProjects\\DFOHack\\Data"
    res_list = files_ready(win_path)

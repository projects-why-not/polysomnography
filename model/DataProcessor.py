import pandas as pd
import mne
import os
import codecs


class DataProcessor:
    def __init__(self, dir_path: str, system: str = None):
        if not isinstance(dir_path, str):
            raise ValueError("The path must be a string.")
        self.dir_path = dir_path
        self.system = system

    def fix_file(self, dirpath: str, file: str) -> str:
        """
        Исправляет формат и переименовывает файл в формате REC или гипнограмму в формат EDF.

        Parameters:
        dirpath (str): Путь к директории, содержащей файл.
        file (str): Имя файла для обработки.

        Returns:
        str: Новый путь к файлу.
        """
        file_name, file_format = file.split(".")
        full_path = os.path.join(dirpath, file)
        if file_format == "EDF":
            return full_path
        elif file_format == "REC" or file_format == "rec":
            with codecs.open(full_path, "r+", encoding="cp1251") as f:
                row = f.readline(200).replace(":", ".")
                f.seek(0)
                f.write(row)
            new_file = os.path.join(dirpath, f"{file_name}_poly.EDF")
        elif file_format in [
            "cm1",
            "cp1",
            "ch3",
            "cc1",
            "cn1",
            "cc3",
            "cu4",
            "cn4",
            "cn3",
            "cc2",
            "cs1",
        ]:
            new_file = os.path.join(self.dir_path, f"{file_name}_hypno.EDF")
        else:
            return file
        os.rename(full_path, new_file)
        return new_file

    def load_raw_file(self, dirpath: str, file: str, verbose: int = 0):
        """
        Загружает и возвращает файл данных в формате EDF.

        Parameters:
        file (str): Путь к файлу.
        verbose (int): Уровень детализации сообщений (0 для отключения).

        Returns:
        mne.io.Raw: Загруженный файл данных.
        """
        raw_file = mne.io.read_raw_edf(
            os.path.join(dirpath, file), preload=True, verbose=verbose
        )
        return raw_file

    def fix_load_all(self) -> list:
        """
        Обрабатывает и загружает все файлы в директории.

        Parameters:
        path (str): Путь к директории с файлами.
        system (str): Операционная система (win или другой).

        Returns:
        list: Список обработанных данных.
        """
        result = []
        separator = "\\" if self.system == "win" else "/"
        os.chdir(self.dir_path)

        for dirpath, _, filenames in os.walk("."):
            pre_result = {}
            for file in filenames:
                if file == ".DS_Store":
                    continue
                new_file = DataProcessor.fix_file(dirpath, file)

                patient = int(new_file.split(separator)[-2][3:])
                record = int(new_file.split(separator)[-1][3:])

                pre_result["patient"] = patient
                pre_result["record"] = record

                if new_file.endswith("poly.EDF"):
                    pre_result["poly"] = DataProcessor.load_raw_file(new_file)
                elif new_file.endswith("hypno.EDF"):
                    pre_result["hypno"] = DataProcessor.load_raw_file(new_file)

            if pre_result:
                result.append(pre_result)
        return result

    def get_freq(
        self, raw_data: list, N_patient: int, N_record: int, record_type: str
    ) -> float:
        """
        Возвращает частоту дискретизации для указанного пациента и исследования.

        Parameters:
        raw_data (list): Список загруженных данных.
        N_patient (int): Номер пациента.
        N_record (int): Номер исследования.
        record_type (str): Тип исследования (poly или hypno).

        Returns:
        float: Частота дискретизации.
        """
        for i in raw_data:
            if i["patient"] == N_patient and i["record"] == N_record:
                return i[record_type].info["sfreq"]
        return -1.0

    def get_info(
        self, raw_data: list, patient_id: int, record_id: int, record_type: str
    ) -> dict:
        """
        Возвращает частоту дискретизации для указанного пациента и исследования.

        Parameters:
        raw_data (list): Список загруженных данных.
        N_patient (int): Номер пациента.
        N_record (int): Номер исследования.
        record_type (str): Тип исследования (poly или hypno).

        Returns:
        dict: Информация об исследовании
        """
        for i in raw_data:
            if i["patient"] == patient_id and i["record"] == record_id:
                return dict(i[record_type].info)
        return dict()

    def get_data(
        self, raw_data: list, patient_id: int, record_id: int, record_type: str
    ) -> dict:
        """
        Возвращает данные исследования для указанного пациента и исследования.

        Parameters:
        raw_data (list): Список загруженных данных.
        patient_id (int): Номер пациента.
        record_id (int): Номер исследования.
        record_type (str): Тип исследования (poly или hypno).

        Returns:
        dict: Данные исследования.
        """
        for i in raw_data:
            if i["patient"] == patient_id and i["record"] == record_id:
                if record_type == "poly":
                    data = i[record_type].get_data()
                    channels = i[record_type].ch_names
                    return {"record_type": record_type, **dict(zip(channels, data))}
                elif record_type == "hypno":
                    hypno_data = i[record_type][0][0].flatten()
                    hypno_timestamps = i[record_type][0][1].flatten()
                    return {
                        "record_type": record_type,
                        "timestamps": hypno_timestamps,
                        "stage": hypno_data,
                    }
        return {}

    def make_df(self, data: dict) -> pd.DataFrame:
        """
        Преобразует данные исследования в DataFrame.

        Parameters:
        data (dict): Данные исследования.

        Returns:
        pd.DataFrame: DataFrame с данными исследования.
        """
        return pd.DataFrame(data).drop(columns="record_type")

    def fix_load_specific(self, patient_id: int, record_id: int) -> list:
        """
        Загружает данные для указанного пациента и исследования.

        Parameters:
        path (str): Путь к директории с файлами.
        patient_id (int): Номер пациента.
        record_id (int): Номер исследования.
        system (str): Операционная система (win или другой).

        Returns:
        dict: Данные исследования для указанного пациента.
        """
        if self.dir_path is None:
            raise ValueError("The directory path is not set.")

        separator = "\\" if self.system == "win" else "/"

        dirpath = os.path.join(self.dir_path, f"Np {patient_id}", f"Nr {record_id}")

        os.chdir(dirpath)

        result = []
        pre_result = {}

        for file in os.listdir(dirpath):
            if file == ".DS_Store":
                continue
            else:
                new_file = self.fix_file(dirpath, file)

                pre_result["patient"] = patient_id
                pre_result["record"] = record_id

                if new_file.endswith("poly.EDF"):
                    pre_result["poly"] = self.load_raw_file(dirpath, new_file)
                elif new_file.endswith("hypno.EDF"):
                    pre_result["hypno"] = self.load_raw_file(dirpath, new_file)

        if len(pre_result):
            result.append(pre_result)
            return result
        else:
            return []

    # ФИКСИТ ТОЛЬКО ФАЙЛЫ ВЫБРАННОГО ПАЦИЕНТА И ИССЛЕДОВАНИЯ
    def fix_specific(self, patient_id: int, record_id: int):
        """
        Фиксит данные для указанного пациента и исследования.

        Parameters:
        path (str): Путь к директории с файлами.
        patient_id (int): Номер пациента.
        record_id (int): Номер исследования.
        system (str): Операционная система (win или другой).
        """
        separator = "\\" if self.system == "win" else "/"

        dirpath = os.path.join(self.dir_path, f"Np {patient_id}", f"Nr {record_id}")

        os.chdir(dirpath)

        for file in os.listdir(dirpath):
            if file == ".DS_Store":
                continue
            else:
                new_file = DataProcessor.fix_file(dirpath, file)

    def fix_all(self):
        """
        Исправляет все файлы в указанной директории.

        Parameters:
        path (str): Путь к директории с файлами.
        system (str): Операционная система (win или другой).
        """
        os.chdir(self.dir_path)
        for dirpath, _, filenames in os.walk("."):
            for file in filenames:
                if file == ".DS_Store":
                    continue
                DataProcessor.fix_file(dirpath, file)

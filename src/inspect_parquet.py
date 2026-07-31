from pathlib import Path

import pandas as pd


PROCESSED_DATA_DIRECTORY = Path("data/processed")

PARQUET_FILE_NAMES = [
    "questions.parquet",
    "answers.parquet",
    "question_answer_metrics.parquet",
    "user_questions.parquet",
]


for file_name in PARQUET_FILE_NAMES:
    file_path = PROCESSED_DATA_DIRECTORY / file_name

    print("\n" + "=" * 70)
    print(f"Файл: {file_path}")

    if not file_path.exists():
        print("Файл не найден")
        continue

    dataframe = pd.read_parquet(file_path)

    print(f"Количество строк: {len(dataframe)}")
    print("\nКолонки и типы данных:")

    for column_name, data_type in dataframe.dtypes.items():
        print(f"{column_name}: {data_type}")
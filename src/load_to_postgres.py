import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import psycopg
from dotenv import load_dotenv
from psycopg import sql
from psycopg.types.json import Jsonb


PROCESSED_DATA_DIRECTORY = Path("data/processed")

TABLES = [
    (
        "staging.questions",
        PROCESSED_DATA_DIRECTORY / "questions.parquet",
    ),
    (
        "staging.answers",
        PROCESSED_DATA_DIRECTORY / "answers.parquet",
    ),
    (
        "staging.question_answer_metrics",
        PROCESSED_DATA_DIRECTORY / "question_answer_metrics.parquet",
    ),
    (
        "staging.user_questions",
        PROCESSED_DATA_DIRECTORY / "user_questions.parquet",
    ),
]


def normalize_value(value: Any) -> Any:
    """
    Преобразует значения Pandas и NumPy
    в значения, которые PostgreSQL может записать.
    """

    if value is None or value is pd.NA or value is pd.NaT:
        return None

    # Списки тегов из Parquet могут читаться как массивы NumPy.
    if isinstance(value, np.ndarray):
        return Jsonb(value.tolist())

    if isinstance(value, (list, tuple, dict)):
        return Jsonb(value)

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if isinstance(value, np.generic):
        value = value.item()

    if pd.isna(value):
        return None

    return value


def create_table_identifier(table_name: str) -> sql.Composed:
    schema_name, short_table_name = table_name.split(".")

    return sql.SQL(".").join(
        [
            sql.Identifier(schema_name),
            sql.Identifier(short_table_name),
        ]
    )


def load_dataframe(
    cursor: psycopg.Cursor,
    table_name: str,
    dataframe: pd.DataFrame,
) -> None:
    columns = dataframe.columns.tolist()

    insert_query = sql.SQL(
        """
        INSERT INTO {} ({})
        VALUES ({})
        """
    ).format(
        create_table_identifier(table_name),
        sql.SQL(", ").join(
            sql.Identifier(column_name)
            for column_name in columns
        ),
        sql.SQL(", ").join(
            sql.Placeholder()
            for _ in columns
        ),
    )

    rows = [
        tuple(
            normalize_value(value)
            for value in row
        )
        for row in dataframe.itertuples(
            index=False,
            name=None,
        )
    ]

    cursor.executemany(
        insert_query,
        rows,
    )

    print(
        f"Загружено в {table_name}: "
        f"{len(rows)} строк"
    )


def main() -> None:
    load_dotenv()

    connection_parameters = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
    }

    missing_parameters = [
        parameter_name
        for parameter_name, parameter_value
        in connection_parameters.items()
        if not parameter_value
    ]

    if missing_parameters:
        raise ValueError(
            "В .env отсутствуют параметры: "
            + ", ".join(missing_parameters)
        )

    for table_name, file_path in TABLES:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Не найден файл: {file_path}"
            )

    print(
        "Подключение к базе: "
        f"{connection_parameters['dbname']}"
    )

    with psycopg.connect(
        **connection_parameters
    ) as connection:
        with connection.cursor() as cursor:
            # Удаляем старые строки перед повторной загрузкой.
            # Сами таблицы при этом остаются.
            cursor.execute(
                """
                TRUNCATE TABLE
                    staging.answers,
                    staging.question_answer_metrics,
                    staging.user_questions,
                    staging.questions;
                """
            )

            print("Старые строки из staging удалены.")

            for table_name, file_path in TABLES:
                dataframe = pd.read_parquet(file_path)

                load_dataframe(
                    cursor=cursor,
                    table_name=table_name,
                    dataframe=dataframe,
                )

            print("\nПроверка количества строк:")

            for table_name, file_path in TABLES:
                expected_rows = len(
                    pd.read_parquet(file_path)
                )

                count_query = sql.SQL(
                    "SELECT COUNT(*) FROM {}"
                ).format(
                    create_table_identifier(table_name)
                )

                cursor.execute(count_query)
                actual_rows = cursor.fetchone()[0]

                print(
                    f"{table_name}: "
                    f"{actual_rows} строк "
                    f"(ожидалось {expected_rows})"
                )

                if actual_rows != expected_rows:
                    raise ValueError(
                        f"Количество строк в {table_name} "
                        "не совпало с Parquet-файлом."
                    )

    print("\nВсе таблицы успешно загружены.")


if __name__ == "__main__":
    main()
import json
from pathlib import Path

import pandas as pd


ANSWERS_INPUT_PATH = Path(
    "data/raw/answers_2026-01-01_page_1.json"
)

QUESTIONS_INPUT_PATH = Path(
    "data/processed/questions.parquet"
)

OUTPUT_DIRECTORY = Path("data/processed")


# Читаем сырой JSON с ответами
with ANSWERS_INPUT_PATH.open(
    mode="r",
    encoding="utf-8",
) as file:
    data = json.load(file)

answers = data["items"]

# Превращаем вложенный JSON в DataFrame
answers_df = pd.json_normalize(
    answers,
    sep="_",
)


# Оставляем только нужные поля
selected_columns = [
    "answer_id",
    "question_id",
    "owner_user_id",
    "owner_reputation",
    "owner_user_type",
    "creation_date",
    "last_activity_date",
    "last_edit_date",
    "score",
    "is_accepted",
    "content_license",
]

answers_df = answers_df.reindex(
    columns=selected_columns
)


# Делаем названия колонок понятнее
answers_df = answers_df.rename(
    columns={
        "owner_user_id": "answer_author_id",
        "owner_reputation": "answer_author_reputation",
        "owner_user_type": "answer_author_type",
        "creation_date": "answer_created_at",
        "last_activity_date": "answer_last_activity_at",
        "last_edit_date": "answer_last_edit_at",
        "score": "answer_score",
    }
)


# Преобразуем Unix timestamp в даты
date_columns = [
    "answer_created_at",
    "answer_last_activity_at",
    "answer_last_edit_at",
]

for column in date_columns:
    answers_df[column] = pd.to_datetime(
        answers_df[column],
        unit="s",
        utc=True,
        errors="coerce",
    )


# Исправляем типы идентификаторов
id_columns = [
    "answer_id",
    "question_id",
    "answer_author_id",
]

for column in id_columns:
    answers_df[column] = (
        pd.to_numeric(
            answers_df[column],
            errors="coerce",
        )
        .astype("Int64")
    )


# Исправляем числовые поля
numeric_columns = [
    "answer_author_reputation",
    "answer_score",
]

for column in numeric_columns:
    answers_df[column] = (
        pd.to_numeric(
            answers_df[column],
            errors="coerce",
        )
        .astype("Int64")
    )


answers_df["is_accepted"] = (
    answers_df["is_accepted"]
    .astype("boolean")
)


# Проверяем и удаляем дубли по answer_id
duplicate_count = answers_df.duplicated(
    subset="answer_id"
).sum()

answers_df = (
    answers_df
    .drop_duplicates(subset="answer_id")
    .sort_values(
        [
            "question_id",
            "answer_created_at",
            "answer_id",
        ]
    )
    .reset_index(drop=True)
)


# Загружаем авторов и даты вопросов
questions_df = pd.read_parquet(
    QUESTIONS_INPUT_PATH,
    columns=[
        "question_id",
        "author_id",
        "creation_date",
    ],
)

questions_df = questions_df.rename(
    columns={
        "author_id": "question_author_id",
        "creation_date": "question_created_at",
    }
)


# Добавляем к каждому ответу автора вопроса
answers_df = answers_df.merge(
    questions_df,
    on="question_id",
    how="left",
    validate="many_to_one",
)


# Определяем, ответил ли человек на свой вопрос
answers_df["is_self_answer"] = (
    answers_df["answer_author_id"]
    .eq(answers_df["question_author_id"])
    .astype("boolean")
)


# Находим первый любой ответ
first_any_answers_df = (
    answers_df
    .sort_values(
        [
            "question_id",
            "answer_created_at",
            "answer_id",
        ]
    )
    .drop_duplicates(
        subset="question_id",
        keep="first",
    )
    [
        [
            "question_id",
            "answer_id",
            "answer_created_at",
        ]
    ]
    .rename(
        columns={
            "answer_id": "first_any_answer_id",
            "answer_created_at": "first_any_answer_at",
        }
    )
)


# Оставляем ответы других пользователей
external_answers_df = answers_df[
    answers_df["is_self_answer"].eq(False)
]


# Находим первый внешний ответ
first_external_answers_df = (
    external_answers_df
    .sort_values(
        [
            "question_id",
            "answer_created_at",
            "answer_id",
        ]
    )
    .drop_duplicates(
        subset="question_id",
        keep="first",
    )
    [
        [
            "question_id",
            "answer_id",
            "answer_created_at",
        ]
    ]
    .rename(
        columns={
            "answer_id": "first_external_answer_id",
            "answer_created_at": "first_external_answer_at",
        }
    )
)


# Создаём одну строку на каждый вопрос
question_answer_metrics_df = (
    questions_df
    .merge(
        first_any_answers_df,
        on="question_id",
        how="left",
    )
    .merge(
        first_external_answers_df,
        on="question_id",
        how="left",
    )
)


# Считаем время до первого любого ответа
question_answer_metrics_df[
    "hours_to_first_any_answer"
] = (
    question_answer_metrics_df["first_any_answer_at"]
    - question_answer_metrics_df["question_created_at"]
).dt.total_seconds() / 3600


# Считаем время до первого внешнего ответа
question_answer_metrics_df[
    "hours_to_first_external_answer"
] = (
    question_answer_metrics_df["first_external_answer_at"]
    - question_answer_metrics_df["question_created_at"]
).dt.total_seconds() / 3600


# Создаём продуктовые признаки
question_answer_metrics_df["received_any_answer_24h"] = (
    question_answer_metrics_df[
        "hours_to_first_any_answer"
    ].le(24)
    & question_answer_metrics_df[
        "hours_to_first_any_answer"
    ].notna()
)

question_answer_metrics_df["received_external_answer_24h"] = (
    question_answer_metrics_df[
        "hours_to_first_external_answer"
    ].le(24)
    & question_answer_metrics_df[
        "hours_to_first_external_answer"
    ].notna()
)


# Создаём папку и сохраняем таблицы
OUTPUT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)

answers_output_path = (
    OUTPUT_DIRECTORY / "answers.parquet"
)

metrics_output_path = (
    OUTPUT_DIRECTORY / "question_answer_metrics.parquet"
)

answers_df.to_parquet(
    answers_output_path,
    index=False,
)

question_answer_metrics_df.to_parquet(
    metrics_output_path,
    index=False,
)


# Выводим результаты проверки
print(f"Исходных ответов: {len(answers)}")
print(f"Дубликатов answer_id: {duplicate_count}")
print(f"Строк после очистки: {len(answers_df)}")

print(
    "Ответов без известного автора: "
    f"{answers_df['answer_author_id'].isna().sum()}"
)

print(
    "Самоответов: "
    f"{answers_df['is_self_answer'].eq(True).sum()}"
)

print(
    "Внешних ответов: "
    f"{answers_df['is_self_answer'].eq(False).sum()}"
)

print(
    "Вопросов с любым ответом: "
    f"{question_answer_metrics_df['first_any_answer_at'].notna().sum()}"
)

print(
    "Вопросов с внешним ответом: "
    f"{question_answer_metrics_df['first_external_answer_at'].notna().sum()}"
)

print(
    "Вопросов с внешним ответом за 24 часа: "
    f"{question_answer_metrics_df['received_external_answer_24h'].sum()}"
)

print(f"Сохранено: {answers_output_path}")
print(f"Сохранено: {metrics_output_path}")

print("\nПервые строки метрик:")

print(
    question_answer_metrics_df[
        [
            "question_id",
            "question_created_at",
            "first_any_answer_at",
            "first_external_answer_at",
            "hours_to_first_external_answer",
            "received_external_answer_24h",
        ]
    ]
    .head(10)
    .to_string(index=False)
)
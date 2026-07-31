import json
from html import unescape
from pathlib import Path

import pandas as pd


USER_QUESTIONS_INPUT_DIRECTORY = Path(
    "data/raw/user_questions"
)

COHORT_QUESTIONS_INPUT_PATH = Path(
    "data/processed/questions.parquet"
)

OUTPUT_PATH = Path(
    "data/processed/user_questions.parquet"
)


COHORT_START_DATE = pd.Timestamp(
    "2026-01-01",
    tz="UTC",
)

COHORT_END_DATE_EXCLUSIVE = pd.Timestamp(
    "2026-01-08",
    tz="UTC",
)


# Ищем все JSON-файлы истории авторов
input_paths = sorted(
    USER_QUESTIONS_INPUT_DIRECTORY.glob(
        "user_questions_batch_*.json"
    )
)


if not input_paths:
    raise FileNotFoundError(
        "В папке "
        f"{USER_QUESTIONS_INPUT_DIRECTORY} "
        "не найдены JSON-файлы"
    )


# Собираем вопросы из всех файлов
user_questions = []

for input_path in input_paths:
    with input_path.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    user_questions.extend(
        data.get("items", [])
    )


source_row_count = len(user_questions)


# Превращаем список словарей в DataFrame
user_questions_df = pd.json_normalize(
    user_questions,
    sep="_",
)


selected_columns = [
    "question_id",
    "owner_user_id",
    "creation_date",
    "post_state",
    "title",
    "tags",
    "score",
    "answer_count",
    "is_answered",
    "link",
]


user_questions_df = (
    user_questions_df
    .reindex(columns=selected_columns)
    .rename(
        columns={
            "owner_user_id": "author_id",
        }
    )
)


# Преобразуем Unix timestamp в дату UTC
user_questions_df["creation_date"] = (
    pd.to_datetime(
        user_questions_df["creation_date"],
        unit="s",
        utc=True,
        errors="coerce",
    )
)


# Приводим идентификаторы к Int64
for column in [
    "question_id",
    "author_id",
]:
    user_questions_df[column] = (
        pd.to_numeric(
            user_questions_df[column],
            errors="coerce",
        )
        .astype("Int64")
    )


# Приводим числовые колонки к Int64
for column in [
    "score",
    "answer_count",
]:
    user_questions_df[column] = (
        pd.to_numeric(
            user_questions_df[column],
            errors="coerce",
        )
        .astype("Int64")
    )


user_questions_df["is_answered"] = (
    user_questions_df["is_answered"]
    .astype("boolean")
)


# Исправляем HTML-коды в заголовках
user_questions_df["title"] = (
    user_questions_df["title"]
    .map(
        lambda title: (
            unescape(title)
            if isinstance(title, str)
            else title
        )
    )
)


missing_question_id_count = (
    user_questions_df["question_id"]
    .isna()
    .sum()
)

missing_author_id_count = (
    user_questions_df["author_id"]
    .isna()
    .sum()
)

missing_post_state_count = (
    user_questions_df["post_state"]
    .isna()
    .sum()
)

duplicate_question_count = (
    user_questions_df
    .duplicated(
        subset=["question_id"],
    )
    .sum()
)


if missing_question_id_count > 0:
    raise ValueError(
        "В истории авторов найдены строки "
        "без question_id"
    )


if missing_post_state_count > 0:
    raise ValueError(
        "В истории авторов найдены строки "
        "без post_state"
    )


# Считаем количество записей каждого состояния
post_state_counts = (
    user_questions_df["post_state"]
    .value_counts(dropna=False)
    .sort_index()
)


# Оставляем только обычные публичные вопросы
public_user_questions_df = (
    user_questions_df[
        user_questions_df["post_state"]
        .eq("Published")
    ]
    .copy()
)


excluded_staging_count = (
    len(user_questions_df)
    - len(public_user_questions_df)
)


# Удаляем возможные дубликаты
public_user_questions_df = (
    public_user_questions_df
    .drop_duplicates(
        subset=["question_id"],
        keep="first",
    )
    .sort_values(
        by=[
            "author_id",
            "creation_date",
            "question_id",
        ]
    )
    .reset_index(drop=True)
)


# Загружаем исходную публичную когорту
cohort_questions_df = pd.read_parquet(
    COHORT_QUESTIONS_INPUT_PATH,
    columns=[
        "question_id",
        "author_id",
        "creation_date",
    ],
)


for column in [
    "question_id",
    "author_id",
]:
    cohort_questions_df[column] = (
        pd.to_numeric(
            cohort_questions_df[column],
            errors="coerce",
        )
        .astype("Int64")
    )


cohort_questions_df["creation_date"] = (
    pd.to_datetime(
        cohort_questions_df["creation_date"],
        utc=True,
        errors="coerce",
    )
)


known_cohort_questions_df = (
    cohort_questions_df[
        cohort_questions_df["author_id"]
        .notna()
    ]
    .copy()
)


# Проверяем, что все публичные вопросы когорты
# присутствуют в опубликованной истории
missing_cohort_question_count = (
    ~known_cohort_questions_df[
        "question_id"
    ].isin(
        public_user_questions_df[
            "question_id"
        ]
    )
).sum()


# Публичные вопросы истории за 1–7 января
public_questions_in_cohort_period_df = (
    public_user_questions_df[
        public_user_questions_df[
            "creation_date"
        ].ge(COHORT_START_DATE)
        &
        public_user_questions_df[
            "creation_date"
        ].lt(COHORT_END_DATE_EXCLUSIVE)
    ]
    .copy()
)


# Проверяем, остались ли дополнительные
# публичные вопросы за 1–7 января
extra_public_questions_df = (
    public_questions_in_cohort_period_df[
        ~public_questions_in_cohort_period_df[
            "question_id"
        ].isin(
            cohort_questions_df[
                "question_id"
            ]
        )
    ]
    .copy()
)


# Считаем Staging Ground-записи
# внутри и после когортного периода
staging_questions_df = (
    user_questions_df[
        user_questions_df["post_state"]
        .ne("Published")
    ]
    .copy()
)


staging_in_cohort_period_count = (
    staging_questions_df[
        staging_questions_df[
            "creation_date"
        ].ge(COHORT_START_DATE)
        &
        staging_questions_df[
            "creation_date"
        ].lt(COHORT_END_DATE_EXCLUSIVE)
    ]
    .shape[0]
)


staging_after_cohort_period_count = (
    len(staging_questions_df)
    - staging_in_cohort_period_count
)


OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)


# Сохраняем только публичную историю
public_user_questions_df.to_parquet(
    OUTPUT_PATH,
    index=False,
)


print(
    "Найдено JSON-файлов: "
    f"{len(input_paths)}"
)

print(
    "Всего записей из API: "
    f"{source_row_count}"
)

print(
    "Дубликатов question_id: "
    f"{duplicate_question_count}"
)

print(
    "Записей без question_id: "
    f"{missing_question_id_count}"
)

print(
    "Записей без author_id: "
    f"{missing_author_id_count}"
)

print(
    "Записей без post_state: "
    f"{missing_post_state_count}"
)


print("\nКоличество записей по post_state:")

for post_state, count in post_state_counts.items():
    print(
        f"{post_state}: {count}"
    )


print(
    "\nПубличных вопросов Published: "
    f"{len(public_user_questions_df)}"
)

print(
    "Исключено записей Staging Ground: "
    f"{excluded_staging_count}"
)

print(
    "Staging Ground за 1–7 января: "
    f"{staging_in_cohort_period_count}"
)

print(
    "Staging Ground после 7 января: "
    f"{staging_after_cohort_period_count}"
)

print(
    "Уникальных авторов публичных вопросов: "
    f"{public_user_questions_df['author_id'].nunique()}"
)

print(
    "Вопросов когорты с известным автором: "
    f"{len(known_cohort_questions_df)}"
)

print(
    "Вопросов когорты, отсутствующих "
    "в публичной истории: "
    f"{missing_cohort_question_count}"
)

print(
    "Публичных вопросов в истории "
    "за 1–7 января: "
    f"{len(public_questions_in_cohort_period_df)}"
)

print(
    "Дополнительных публичных вопросов "
    "за 1–7 января: "
    f"{len(extra_public_questions_df)}"
)

print(
    "Минимальная дата публичной истории: "
    f"{public_user_questions_df['creation_date'].min()}"
)

print(
    "Максимальная дата публичной истории: "
    f"{public_user_questions_df['creation_date'].max()}"
)

print(
    f"\nСохранено: {OUTPUT_PATH}"
)
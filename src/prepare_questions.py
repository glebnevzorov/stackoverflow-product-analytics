import json
from pathlib import Path

import pandas as pd


INPUT_PATH = Path(
    "data/raw/questions_2026-01-01_page_1.json"
)

OUTPUT_DIRECTORY = Path("data/processed")


with INPUT_PATH.open(
    mode="r",
    encoding="utf-8",
) as file:
    data = json.load(file)


questions = data["items"]

questions_df = pd.json_normalize(
    questions,
    sep="_",
)


selected_columns = [
    "question_id",
    "owner_user_id",
    "owner_reputation",
    "owner_user_type",
    "creation_date",
    "last_activity_date",
    "last_edit_date",
    "score",
    "view_count",
    "answer_count",
    "is_answered",
    "accepted_answer_id",
    "title",
    "tags",
    "link",
    "content_license",
]

questions_df = questions_df.reindex(
    columns=selected_columns
)


questions_df = questions_df.rename(
    columns={
        "owner_user_id": "author_id",
        "owner_reputation": "author_reputation",
        "owner_user_type": "author_type",
    }
)





date_columns = [
    "creation_date",
    "last_activity_date",
    "last_edit_date",
]

for column in date_columns:
    questions_df[column] = pd.to_datetime(
        questions_df[column],
        unit="s",
        utc=True,
        errors="coerce",
    )







id_columns = [
    "question_id",
    "author_id",
    "accepted_answer_id",
]

for column in id_columns:
    questions_df[column] = (
        pd.to_numeric(
            questions_df[column],
            errors="coerce",
        )
        .astype("Int64")
    )

numeric_columns = [
    "author_reputation",
    "score",
    "view_count",
    "answer_count",
]

for column in numeric_columns:
    questions_df[column] = (
        pd.to_numeric(
            questions_df[column],
            errors="coerce",
        )
        .astype("Int64")
    )

questions_df["is_answered"] = (
    questions_df["is_answered"]
    .astype("boolean")
)

questions_df["has_any_answer"] = (
    questions_df["answer_count"]
    .fillna(0)
    .gt(0)
)

questions_df["has_accepted_answer"] = (
    questions_df["accepted_answer_id"]
    .notna()
)




duplicate_count = questions_df.duplicated(
    subset="question_id"
).sum()

print(f"Дубликатов question_id: {duplicate_count}")

questions_df = (
    questions_df
    .drop_duplicates(subset="question_id")
    .sort_values("creation_date")
    .reset_index(drop=True)
)


question_tags_df = (
    questions_df[
        [
            "question_id",
            "tags",
        ]
    ]
    .explode("tags")
    .rename(columns={"tags": "tag"})
    .dropna(subset=["tag"])
    .drop_duplicates()
    .reset_index(drop=True)
)

OUTPUT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)

questions_table = questions_df.drop(
    columns=["tags"]
)

questions_output_path = (
    OUTPUT_DIRECTORY / "questions.parquet"
)

tags_output_path = (
    OUTPUT_DIRECTORY / "question_tags.parquet"
)

questions_table.to_parquet(
    questions_output_path,
    index=False,
)

question_tags_df.to_parquet(
    tags_output_path,
    index=False,
)


print(f"Исходных вопросов: {len(questions)}")
print(f"Строк после очистки: {len(questions_table)}")
print(f"Уникальных авторов: {questions_table['author_id'].nunique()}")
print(f"Вопросов без author_id: {questions_table['author_id'].isna().sum()}")
print(f"Вопросов с любым ответом: {questions_table['has_any_answer'].sum()}")
print(
    "Вопросов с принятым ответом: "
    f"{questions_table['has_accepted_answer'].sum()}"
)
print(f"Строк в таблице тегов: {len(question_tags_df)}")

print("\nПервые пять очищенных вопросов:")

print(
    questions_table
    .head()
    .to_string(index=False)
)

print("\nТипы данных:")

questions_table.info()








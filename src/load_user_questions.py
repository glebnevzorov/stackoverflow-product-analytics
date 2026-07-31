import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests


QUESTIONS_INPUT_PATH = Path(
    "data/processed/questions.parquet"
)

OUTPUT_DIRECTORY = Path(
    "data/raw/user_questions"
)

API_VERSION = "2.4"

API_BASE_URL = (
    f"https://api.stackexchange.com/"
    f"{API_VERSION}/users"
)

BATCH_SIZE = 100
PAGE_SIZE = 100


HISTORY_START_DATE = datetime(
    2026,
    1,
    1,
    tzinfo=timezone.utc,
)

HISTORY_END_EXCLUSIVE = datetime(
    2026,
    2,
    7,
    tzinfo=timezone.utc,
)

HISTORY_END_DATE = (
    HISTORY_END_EXCLUSIVE
    - timedelta(seconds=1)
)


# Загружаем авторов вопросов нашей когорты
questions_df = pd.read_parquet(
    QUESTIONS_INPUT_PATH,
    columns=[
        "author_id",
    ],
)


questions_without_author = (
    questions_df["author_id"]
    .isna()
    .sum()
)


# Получаем уникальные известные user_id
author_ids = (
    questions_df["author_id"]
    .dropna()
    .drop_duplicates()
    .sort_values()
    .astype("int64")
    .astype(str)
    .tolist()
)


if not author_ids:
    raise ValueError(
        "Не найдено ни одного известного автора"
    )


OUTPUT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)


# Удаляем файлы предыдущего запуска,
# чтобы данные API 2.3 не смешались
# с новыми данными API 2.4
old_output_paths = list(
    OUTPUT_DIRECTORY.glob(
        "user_questions_batch_*.json"
    )
)

for old_output_path in old_output_paths:
    old_output_path.unlink()


print(
    "Удалено старых файлов: "
    f"{len(old_output_paths)}"
)

print(
    "Используемая версия API: "
    f"{API_VERSION}"
)


total_batches = (
    len(author_ids) + BATCH_SIZE - 1
) // BATCH_SIZE

total_user_questions = 0
request_count = 0
quota_remaining = None

missing_post_state_count = 0

post_state_counts = {}


# Делим авторов на пачки максимум по 100 user_id
for batch_number, start_index in enumerate(
    range(
        0,
        len(author_ids),
        BATCH_SIZE,
    ),
    start=1,
):
    batch_author_ids = author_ids[
        start_index:start_index + BATCH_SIZE
    ]

    author_ids_string = ";".join(
        batch_author_ids
    )

    api_url = (
        f"{API_BASE_URL}/"
        f"{author_ids_string}/questions"
    )

    page = 1

    # Загружаем все страницы текущей пачки
    while True:
        params = {
            "site": "stackoverflow",
            "page": page,
            "pagesize": PAGE_SIZE,
            "sort": "creation",
            "order": "asc",
            "fromdate": int(
                HISTORY_START_DATE.timestamp()
            ),
            "todate": int(
                HISTORY_END_DATE.timestamp()
            ),
        }

        response = requests.get(
            api_url,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        user_questions = data.get(
            "items",
            [],
        )

        quota_remaining = data.get(
            "quota_remaining"
        )


        # Считаем состояния вопросов:
        # Published, StagingGround_... и другие
        for user_question in user_questions:
            post_state = user_question.get(
                "post_state"
            )

            if post_state is None:
                missing_post_state_count += 1
                continue

            post_state_counts[post_state] = (
                post_state_counts.get(
                    post_state,
                    0,
                )
                + 1
            )


        output_path = (
            OUTPUT_DIRECTORY
            / (
                f"user_questions_batch_"
                f"{batch_number:03d}"
                f"_page_{page:03d}.json"
            )
        )

        with output_path.open(
            mode="w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
            )

        total_user_questions += len(
            user_questions
        )

        request_count += 1

        print(
            f"Пачка {batch_number}/"
            f"{total_batches}, "
            f"страница {page}: "
            f"получено вопросов "
            f"{len(user_questions)}"
        )

        print(
            f"Файл сохранён: {output_path}"
        )

        backoff = data.get("backoff")

        if backoff is not None:
            print(
                "API попросил подождать "
                f"{backoff} секунд"
            )

            time.sleep(backoff)

        if not data.get(
            "has_more",
            False,
        ):
            break

        page += 1


print("\nЗагрузка завершена")

print(
    "Версия API: "
    f"{API_VERSION}"
)

print(
    "Вопросов когорты без author_id: "
    f"{questions_without_author}"
)

print(
    "Уникальных известных авторов: "
    f"{len(author_ids)}"
)

print(
    "Количество пачек: "
    f"{total_batches}"
)

print(
    "Всего запросов: "
    f"{request_count}"
)

print(
    "Получено вопросов авторов: "
    f"{total_user_questions}"
)

print(
    "Вопросов без post_state: "
    f"{missing_post_state_count}"
)

print("\nКоличество вопросов по post_state:")

for post_state, question_count in sorted(
    post_state_counts.items()
):
    print(
        f"{post_state}: "
        f"{question_count}"
    )

print(
    "\nОсталось запросов: "
    f"{quota_remaining}"
)


if missing_post_state_count > 0:
    raise ValueError(
        "В ответах API 2.4 найдены вопросы "
        "без поля post_state"
    )
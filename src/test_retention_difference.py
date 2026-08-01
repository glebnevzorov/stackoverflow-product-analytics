import math
import os

import psycopg
from dotenv import load_dotenv
from statsmodels.stats.proportion import proportions_ztest


load_dotenv()

connection_parameters = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

query = """
SELECT
    received_external_answer_24h,
    COUNT(*) AS authors_count,
    COUNT(*) FILTER (
        WHERE returned_30d
    ) AS returned_authors
FROM analytics.author_retention
GROUP BY received_external_answer_24h;
"""

with psycopg.connect(**connection_parameters) as connection:
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

groups = {
    received_answer: {
        "authors": authors_count,
        "returned": returned_authors,
    }
    for received_answer, authors_count, returned_authors in rows
}

if True not in groups or False not in groups:
    raise ValueError(
        "PostgreSQL не вернул обе группы авторов."
    )

answered_authors = groups[True]["authors"]
answered_returned = groups[True]["returned"]

not_answered_authors = groups[False]["authors"]
not_answered_returned = groups[False]["returned"]

answered_rate = answered_returned / answered_authors

not_answered_rate = (
    not_answered_returned
    / not_answered_authors
)

difference = answered_rate - not_answered_rate

z_statistic, p_value = proportions_ztest(
    count=[
        answered_returned,
        not_answered_returned,
    ],
    nobs=[
        answered_authors,
        not_answered_authors,
    ],
    alternative="two-sided",
)

standard_error = math.sqrt(
    answered_rate
    * (1 - answered_rate)
    / answered_authors
    +
    not_answered_rate
    * (1 - not_answered_rate)
    / not_answered_authors
)

confidence_interval_lower = (
    difference - 1.96 * standard_error
)

confidence_interval_upper = (
    difference + 1.96 * standard_error
)

print(
    "Получили внешний ответ за 24 часа: "
    f"{answered_returned}/{answered_authors} "
    f"({answered_rate:.2%})"
)

print(
    "Не получили внешний ответ за 24 часа: "
    f"{not_answered_returned}/{not_answered_authors} "
    f"({not_answered_rate:.2%})"
)

print(
    "Разница в доле возврата: "
    f"{difference * 100:.2f} п.п."
)

print(f"Z-статистика: {z_statistic:.3f}")
print(f"P-value: {p_value:.4f}")

print(
    "95% доверительный интервал разницы: "
    f"от {confidence_interval_lower * 100:.2f} "
    f"до {confidence_interval_upper * 100:.2f} п.п."
)

if p_value < 0.05:
    print(
        "Разница статистически значима "
        "на уровне 5%."
    )
else:
    print(
        "Статистически значимая разница "
        "на уровне 5% не обнаружена."
    )
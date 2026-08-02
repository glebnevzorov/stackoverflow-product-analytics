DROP VIEW IF EXISTS analytics.retention_summary;
DROP VIEW IF EXISTS analytics.retention_dashboard;


CREATE VIEW analytics.retention_dashboard AS

SELECT
    author_id,
    index_question_id,
    index_question_at,

    received_external_answer_24h,

    CASE
        WHEN received_external_answer_24h
        THEN 'Получили ответ за 24 часа'
        ELSE 'Не получили ответ за 24 часа'
    END AS answer_group,

    returned_30d,

    CASE
        WHEN returned_30d
        THEN 'Вернулся'
        ELSE 'Не вернулся'
    END AS return_status,

    next_question_id,
    next_question_at,

    CASE
        WHEN next_question_at IS NOT NULL
        THEN ROUND(
            EXTRACT(
                EPOCH FROM (
                    next_question_at - index_question_at
                )
            )::numeric / 86400,
            2
        )
        ELSE NULL
    END AS days_to_next_question

FROM analytics.author_retention;


CREATE VIEW analytics.retention_summary AS

SELECT
    CASE
        WHEN received_external_answer_24h
        THEN 1
        ELSE 2
    END AS group_order,

    CASE
        WHEN received_external_answer_24h
        THEN 'Получили ответ за 24 часа'
        ELSE 'Не получили ответ за 24 часа'
    END AS answer_group,

    COUNT(*) AS authors_count,

    COUNT(*) FILTER (
        WHERE returned_30d
    ) AS returned_authors,

    COUNT(*) FILTER (
        WHERE NOT returned_30d
    ) AS not_returned_authors,

    ROUND(
        COUNT(*) FILTER (
            WHERE returned_30d
        )::numeric
        / COUNT(*),
        4
    ) AS return_rate

FROM analytics.author_retention

GROUP BY received_external_answer_24h;
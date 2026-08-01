DROP TABLE IF EXISTS analytics.author_retention;

CREATE TABLE analytics.author_retention AS

WITH ranked_cohort_questions AS (
    SELECT
        question_id,
        author_id,
        creation_date,

        ROW_NUMBER() OVER (
            PARTITION BY author_id
            ORDER BY creation_date, question_id
        ) AS question_number

    FROM staging.questions

    WHERE author_id IS NOT NULL
),

index_questions AS (
    SELECT
        question_id,
        author_id,
        creation_date

    FROM ranked_cohort_questions

    WHERE question_number = 1
),

ordered_user_questions AS (
    SELECT
        question_id,
        author_id,
        creation_date,

        LEAD(question_id) OVER (
            PARTITION BY author_id
            ORDER BY creation_date, question_id
        ) AS next_question_id,

        LEAD(creation_date) OVER (
            PARTITION BY author_id
            ORDER BY creation_date, question_id
        ) AS next_question_at

    FROM staging.user_questions
)

SELECT
    iq.author_id,

    iq.question_id AS index_question_id,
    iq.creation_date AS index_question_at,

    metrics.received_external_answer_24h,

    history.next_question_id,
    history.next_question_at,

    CASE
        WHEN history.next_question_at
            <= iq.creation_date + INTERVAL '30 days'
        THEN TRUE
        ELSE FALSE
    END AS returned_30d

FROM index_questions AS iq

INNER JOIN staging.question_answer_metrics AS metrics
    ON metrics.question_id = iq.question_id

INNER JOIN ordered_user_questions AS history
    ON history.question_id = iq.question_id
   AND history.author_id = iq.author_id;
SELECT
    received_external_answer_24h,
    COUNT(*) AS authors_count,

    COUNT(*) FILTER (
        WHERE returned_30d
    ) AS returned_authors,

    ROUND(
        100.0
        * COUNT(*) FILTER (WHERE returned_30d)
        / COUNT(*),
        2
    ) AS return_rate_percent

FROM analytics.author_retention

GROUP BY received_external_answer_24h

ORDER BY received_external_answer_24h DESC;
-- Chuẩn hoá tin tức từ raw layer
SELECT
    source,
    TRIM(title)                           AS title,
    url,
    CAST(published_at AS TIMESTAMP)       AS published_at,
    CAST(date_trunc('day', CAST(published_at AS TIMESTAMP)) AS DATE)
                                          AS published_date,
    TRIM(description)                     AS description,
    LOWER(TRIM(sentiment))                AS sentiment,
    CASE LOWER(TRIM(sentiment))
        WHEN 'positive' THEN  1.0
        WHEN 'negative' THEN -1.0
        ELSE 0.0
    END                                   AS sentiment_score
FROM {{ source('raw', 'news') }}
WHERE title IS NOT NULL
  AND published_at IS NOT NULL

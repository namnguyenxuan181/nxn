-- Bảng tổng hợp sentiment theo ngày và nguồn
{{
  config(
    materialized = 'incremental',
    unique_key   = "published_date || '|' || source",
    on_schema_change = 'sync_all_columns'
  )
}}

SELECT
    published_date,
    source,
    COUNT(*)                                              AS total_articles,
    SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) AS positive_count,
    SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) AS negative_count,
    SUM(CASE WHEN sentiment = 'neutral'  THEN 1 ELSE 0 END) AS neutral_count,
    ROUND(AVG(sentiment_score), 4)                        AS avg_sentiment_score,
    CURRENT_TIMESTAMP                                     AS updated_at
FROM {{ ref('stg_news') }}
{% if is_incremental() %}
WHERE published_date >= CURRENT_DATE - INTERVAL '7' DAY
{% endif %}
GROUP BY 1, 2

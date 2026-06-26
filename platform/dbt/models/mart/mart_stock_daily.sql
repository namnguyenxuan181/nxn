-- Bảng phân tích cổ phiếu hàng ngày — join giá + tin tức + sentiment
{{
  config(
    materialized = 'incremental',
    unique_key   = "trade_date || '|' || symbol",
    on_schema_change = 'sync_all_columns'
  )
}}

WITH prices AS (
    SELECT *
    FROM {{ ref('stg_stock_prices') }}
    {% if is_incremental() %}
    WHERE trade_date >= CURRENT_DATE - INTERVAL '5' DAY
    {% endif %}
),

prices_with_lag AS (
    SELECT
        trade_date,
        symbol,
        open_price,
        high_price,
        low_price,
        close_price,
        volume,
        LAG(close_price) OVER (
            PARTITION BY symbol ORDER BY trade_date
        ) AS prev_close
    FROM prices
),

news_agg AS (
    SELECT
        published_date,
        -- Lấy symbols từ title (đơn giản: tìm chuỗi 3 ký tự HOA)
        AVG(sentiment_score)  AS avg_sentiment,
        COUNT(*)              AS news_count
    FROM {{ ref('stg_news') }}
    GROUP BY 1
)

SELECT
    p.trade_date,
    p.symbol,
    p.open_price,
    p.high_price,
    p.low_price,
    p.close_price,
    p.volume,
    p.prev_close,
    CASE
        WHEN p.prev_close IS NOT NULL AND p.prev_close > 0
        THEN ROUND((p.close_price - p.prev_close) * 100.0 / p.prev_close, 2)
        ELSE NULL
    END AS change_pct,
    COALESCE(n.avg_sentiment, 0.0)  AS market_sentiment,
    COALESCE(n.news_count, 0)       AS market_news_count,
    CURRENT_TIMESTAMP               AS updated_at
FROM prices_with_lag p
LEFT JOIN news_agg n ON n.published_date = p.trade_date

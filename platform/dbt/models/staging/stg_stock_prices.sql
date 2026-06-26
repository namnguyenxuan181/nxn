-- Chuẩn hoá bảng giá cổ phiếu từ raw layer
SELECT
    CAST(date AS DATE)                    AS trade_date,
    UPPER(TRIM(symbol))                   AS symbol,
    CAST(open   AS BIGINT)                AS open_price,
    CAST(high   AS BIGINT)                AS high_price,
    CAST(low    AS BIGINT)                AS low_price,
    CAST(close  AS BIGINT)                AS close_price,
    CAST(volume AS BIGINT)                AS volume,
    -- Giá tham chiếu sàn (VND đã nhân 1000)
    CASE
        WHEN close IS NOT NULL AND close > 0 THEN 'valid'
        ELSE 'invalid'
    END                                   AS data_quality
FROM {{ source('raw', 'stock_prices') }}
WHERE date IS NOT NULL
  AND symbol IS NOT NULL
  AND close IS NOT NULL
  AND CAST(close AS BIGINT) > 0

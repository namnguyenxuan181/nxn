-- Chuẩn hoá lãi suất ngân hàng từ raw layer
SELECT
    TRIM(bank)                            AS bank,
    TRIM(channel)                         AS channel,
    TRY_CAST(rate_3m  AS DOUBLE)          AS rate_3m,
    TRY_CAST(rate_6m  AS DOUBLE)          AS rate_6m,
    TRY_CAST(rate_12m AS DOUBLE)          AS rate_12m,
    TRY_CAST(rate_24m AS DOUBLE)          AS rate_24m,
    CAST(fetched_at AS DATE)              AS fetched_date
FROM {{ source('raw', 'interest_rates') }}
WHERE bank IS NOT NULL

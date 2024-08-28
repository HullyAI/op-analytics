SELECT *
    , num_blocks * block_time_sec as active_secs_per_day
    , l2_num_txs_per_day / num_blocks AS l2_num_txs_per_day_per_block
    , l2_num_txs_per_day / (num_blocks*block_time_sec) AS num_user_txs_per_second
    , l2_gas_used / num_blocks AS l2_gas_used_per_block
    , l2_gas_used / (num_blocks*block_time_sec) AS l2_gas_used_per_second
    , l2_eth_fees_per_day / num_blocks AS l2_eth_fees_per_block
    , l2_eth_fees_per_day / (num_blocks*block_time_sec) AS l2_eth_fees_per_second
    , chain as chain_name

FROM (
    SELECT
        DATE_TRUNC('day', toDateTime(t.block_timestamp)) AS dt,
        chain, network, chain_id, cast(2.0 as Float64) AS block_time_sec,

        COUNT(*) AS num_raw_txs,
        1+ (MAX(t.block_number) - MIN(t.block_number)) AS num_blocks,

        SUM(IF(gas_price = 0 AND to_address = '0x4200000000000000000000000000000000000015', 1, 0)) AS l2_num_attr_deposit_txs_per_day,
        SUM(IF(gas_price = 0 AND to_address = '0x4200000000000000000000000000000000000007', 1, 0)) AS l2_num_user_deposit_txs_per_day,
        SUM(IF(gas_price > 0, 1, 0)) AS l2_num_txs_per_day,
        SUM(IF(receipt_status = 1 AND gas_price > 0, 1, 0)) AS l2_num_success_txs_per_day,

        COUNT(DISTINCT from_address) AS num_senders_per_day,

        SUM(t.receipt_gas_used) AS l2_gas_used,
        SUM(cast(receipt_l1_gas_used as Nullable(Int64))) AS l1_gas_used_on_l2,
        SUM(cast(receipt_l1_gas_used as Nullable(Float64)) * COALESCE(receipt_l1_base_fee_scalar,receipt_l1_fee_scalar)) AS l1_gas_paid,
        SUM(cast(receipt_l1_gas_used as Nullable(Float64)) * receipt_l1_blob_base_fee_scalar) AS blob_gas_paid,
        SUM(((length(unhex(input)) - 1))) AS calldata_bytes_l2_per_day,

        SUM(IF(gas_price > 0, (receipt_l1_fee /
(
 16*COALESCE(receipt_l1_fee_scalar,receipt_l1_base_fee_scalar)*cast(receipt_l1_gas_price AS Nullable(Float64))/1e6
 + COALESCE( receipt_l1_blob_base_fee_scalar*cast(receipt_l1_blob_base_fee AS Nullable(Float64))/1e6 , 0)
)), 0)) AS estimated_size_user_txs,

        SUM((receipt_l1_fee /
(
 16*COALESCE(receipt_l1_fee_scalar,receipt_l1_base_fee_scalar)*cast(receipt_l1_gas_price AS Nullable(Float64))/1e6
 + COALESCE( receipt_l1_blob_base_fee_scalar*cast(receipt_l1_blob_base_fee AS Nullable(Float64))/1e6 , 0)
)) * COALESCE(receipt_l1_base_fee_scalar,receipt_l1_fee_scalar)) AS l1_gas_paid_fjord,
        SUM((receipt_l1_fee /
(
 16*COALESCE(receipt_l1_fee_scalar,receipt_l1_base_fee_scalar)*cast(receipt_l1_gas_price AS Nullable(Float64))/1e6
 + COALESCE( receipt_l1_blob_base_fee_scalar*cast(receipt_l1_blob_base_fee AS Nullable(Float64))/1e6 , 0)
)) * receipt_l1_blob_base_fee_scalar) AS blob_gas_paid_fjord,

        SUM(IF(gas_price > 0, cast(receipt_l1_gas_used as Nullable(Float64)) * receipt_l1_fee_scalar, 0)) AS l1_gas_paid_user_txs,
        SUM(IF(gas_price > 0, cast(receipt_l1_gas_used as Nullable(Float64)) * receipt_l1_blob_base_fee_scalar, 0)) AS blob_gas_paid_user_txs,

        SUM(IF(gas_price > 0, receipt_l1_gas_used, 0)) AS l1_gas_used_user_txs_l2_per_day,
        SUM(IF(gas_price > 0, ((length(unhex(input)) - 1)), 0)) AS calldata_bytes_user_txs_l2_per_day,
        SUM(IF(gas_price > 0, t.receipt_gas_used, 0)) AS l2_gas_used_user_txs_per_day,

        SUM((cast((gas_price * t.receipt_gas_used) + receipt_l1_fee AS Nullable(Float64))) / 1e18) AS l2_eth_fees_per_day,
        median(IF(gas_price > 0, (cast((gas_price * t.receipt_gas_used) + receipt_l1_fee AS Nullable(Float64))) / 1e18, NULL)) AS median_l2_eth_fees_per_tx,

        SUM(IF(gas_price > 0, CAST(receipt_l1_fee AS Nullable(Float64)) / 1e18, 0)) AS l1_contrib_l2_eth_fees_per_day,
        SUM(IF(gas_price > 0, CAST(gas_price * t.receipt_gas_used AS Nullable(Float64)) / 1e18, 0)) AS l2_contrib_l2_eth_fees_per_day,

        SUM(IF(gas_price > 0, 
            (cast((receipt_l1_fee /
(
 16*COALESCE(receipt_l1_fee_scalar,receipt_l1_base_fee_scalar)*cast(receipt_l1_gas_price AS Nullable(Float64))/1e6
 + COALESCE( receipt_l1_blob_base_fee_scalar*cast(receipt_l1_blob_base_fee AS Nullable(Float64))/1e6 , 0)
)) as Nullable(Float64)) * COALESCE(16*receipt_l1_base_fee_scalar/1e6,receipt_l1_fee_scalar) * cast(receipt_l1_gas_price AS Nullable(Float64))) / 1e18, 
            0)) AS l1_l1gas_contrib_l2_eth_fees_per_day,
        SUM(IF(gas_price > 0, 
            coalesce((cast((receipt_l1_fee /
(
 16*COALESCE(receipt_l1_fee_scalar,receipt_l1_base_fee_scalar)*cast(receipt_l1_gas_price AS Nullable(Float64))/1e6
 + COALESCE( receipt_l1_blob_base_fee_scalar*cast(receipt_l1_blob_base_fee AS Nullable(Float64))/1e6 , 0)
)) as Nullable(Float64)) * receipt_l1_blob_base_fee_scalar/1e6 * cast(receipt_l1_blob_base_fee AS Nullable(Float64))) / 1e18, 0), 
            0)) AS l1_blobgas_contrib_l2_eth_fees_per_day,

        SUM(IF(gas_price > 0, CAST((base_fee_per_gas) * t.receipt_gas_used AS Nullable(Float64)) / 1e18, 0)) AS l2_contrib_l2_eth_fees_base_fee_per_day,
        SUM(IF(gas_price > 0, CAST((gas_price - base_fee_per_gas) * t.receipt_gas_used AS Nullable(Float64)) / 1e18, 0)) AS l2_contrib_l2_eth_fees_priority_fee_per_day,

        SUM((16 * (length(replace(toString(unhex(input)), ' ', '')) - 1)
            + 4 * ((length(unhex(input)) - 1) - (length(replace(toString(unhex(input)), ' ', '')) - 1)))) AS input_calldata_gas_l2_per_day,
        SUM(IF(gas_price > 0, (16 * (length(replace(toString(unhex(input)), ' ', '')) - 1)
            + 4 * ((length(unhex(input)) - 1) - (length(replace(toString(unhex(input)), ' ', '')) - 1))), 0)) AS input_calldata_gas_user_txs_l2_per_day,

        SUM(receipt_l1_gas_used / 16) AS compressedtxsize_approx_l2_per_day_ecotone,
        SUM(IF(gas_price > 0, receipt_l1_gas_used / 16, 0)) AS compressedtxsize_approx_user_txs_l2_per_day_ecotone,

        SUM((CAST(receipt_l1_gas_price AS Nullable(Float64)) / CAST(1e9 AS Nullable(Float64))) * CAST(receipt_l1_gas_used AS Nullable(Float64))) / SUM(CAST(receipt_l1_gas_used AS Nullable(Float64))) AS avg_l1_gas_price_on_l2,
        SUM((CAST(receipt_l1_blob_base_fee AS Nullable(Float64)) / CAST(1e9 AS Nullable(Float64))) * CAST(receipt_l1_gas_used AS Nullable(Float64))) / SUM(CAST(receipt_l1_gas_used AS Nullable(Float64))) AS avg_blob_base_fee_on_l2,
        
        SUM(IF(gas_price > 0, CAST(t.receipt_gas_used * gas_price AS Nullable(Float64)) / 1e9, NULL))
        / SUM(IF(gas_price > 0, t.receipt_gas_used, NULL)) AS avg_l2_gas_price,
        
        SUM(IF(gas_price > 0, CAST(t.receipt_gas_used AS Nullable(Float64)) * CAST((base_fee_per_gas) AS Nullable(Float64)) / 1e9, NULL))
        / SUM(IF(gas_price > 0, t.receipt_gas_used, NULL)) AS base_fee_gwei,
        
        SUM(IF(gas_price = 0, 0, CAST(t.receipt_gas_used*receipt_l1_gas_price as Nullable(Float64))) / 1e18) AS equivalent_l1_tx_fee,
        
        AVG(IF(gas_price > 0, COALESCE(receipt_l1_base_fee_scalar,receipt_l1_fee_scalar), NULL)) AS avg_l1_fee_scalar,
        coalesce(AVG(IF(gas_price > 0, receipt_l1_blob_base_fee_scalar, NULL)), 0) AS avg_l1_blob_fee_scalar
        
    FROM mode_transactions t final
        INNER JOIN mode_blocks b final
            ON t.block_number = b.number 
            AND t.block_timestamp = b.timestamp
    
    WHERE t.block_timestamp >= toDate(now() - interval '3 days')
        AND t.block_timestamp < toDate(now())
        AND b.timestamp >= toDate(now() - interval '3 days')
        AND b.timestamp < toDate(now())
        AND t.is_deleted = 0
        AND b.is_deleted = 0
    
    GROUP BY 1,2,3,4
    ) a

SETTINGS
    max_memory_usage = 200000000000,
    max_execution_time = 5000
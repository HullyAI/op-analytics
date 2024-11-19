SELECT
  dt,
  chain,
  chain_id,
  from_address AS address,
  -- Aggregates

  count(*) AS tx_cnt,

  count(if(success, 1, NULL)) AS success_tx_cnt,

  count(DISTINCT block_number) AS block_cnt,

  count(DISTINCT if(success, block_number, NULL)) AS success_block_cnt,

  min(block_number) AS block_number_min,

  max(block_number) AS block_number_max,

  max(block_number) - min(block_number) + 1 AS active_block_range,

  min(nonce) AS nonce_min,

  max(nonce) AS nonce_max,

  max(nonce) - min(nonce) + 1 AS active_nonce_range,

  min(block_timestamp) AS block_timestamp_min,

  max(block_timestamp) AS block_timestamp_max,

  max(block_timestamp) - min(block_timestamp) AS active_time_range,

  count(DISTINCT block_hour) AS active_hours_ucnt,

  count(DISTINCT to_address) AS to_address_ucnt,

  count(DISTINCT if(success, to_address, NULL)) AS success_to_address_ucnt,

  count(DISTINCT method_id) AS method_id_ucnt,

  sum(receipt_gas_used) AS l2_gas_used_sum,

  sum(if(success, receipt_gas_used, 0)) AS success_l2_gas_used_sum,

  sum(l1_gas_used) AS l1_gas_used_sum,

  sum(if(success, l1_gas_used, 0)) AS success_l1_gas_used_sum,

  wei_to_eth(sum(tx_fee)) AS tx_fee_sum_eth,

  wei_to_eth(sum(if(success, tx_fee, 0))) AS success_tx_fee_sum_eth,

  -- L2 Fee and breakdown into BASE + PRIORITY
  wei_to_eth(sum(l2_fee)) AS l2_fee_sum_eth,

  wei_to_eth(sum(l2_base_fee)) AS l2_base_fee_sum_eth,

  wei_to_eth(sum(l2_priority_fee)) AS l2_priority_fee_sum_eth,

  wei_to_eth(sum(l2_base_legacy)) AS l2_base_legacy_fee_sum_eth,

  -- L1 Fee and breakdown into BASE + BLOB
  wei_to_eth(sum(l1_fee)) AS l1_fee_sum_eth,

  wei_to_eth(sum(l1_base_fee)) AS l1_base_fee_sum_eth,

  wei_to_eth(sum(l1_blob_fee)) AS l1_blob_fee_sum_eth,

  -- L2 Price and breakdown into BASE + PRIORITY
  wei_to_gwei(safe_div(sum(l2_fee), sum(receipt_gas_used)))
    AS l2_gas_price_avg_gwei,

  wei_to_gwei(safe_div(sum(l2_base_fee), sum(receipt_gas_used)))
    AS l2_base_price_avg_gwei,

  wei_to_gwei(safe_div(sum(l2_priority_fee), sum(receipt_gas_used)))
    AS l2_priority_price_avg_gwei,

  -- L1 Price breakdown into BASE + BLOB
  wei_to_gwei(safe_div(sum(l1_base_fee), sum(l1_base_scaled_size))
  ) AS l1_base_price_avg_gwei,

  wei_to_gwei(safe_div(sum(l1_blob_fee), sum(l1_blob_scaled_size)))
    AS l1_blob_fee_avg_gwei
FROM
  transaction_fees
GROUP BY
  1,
  2,
  3,
  4

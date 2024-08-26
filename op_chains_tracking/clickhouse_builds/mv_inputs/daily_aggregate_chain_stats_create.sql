CREATE TABLE {view_name}
(
    dt Date,
    chain String,
    network String,
    chain_id UInt64,
    block_time_sec Float64,
    
    num_raw_txs AggregateFunction(count),
    num_blocks AggregateFunction(uniqExact, UInt64),
    l2_num_attr_deposit_txs_per_day AggregateFunction(sum, UInt8),
    l2_num_user_deposit_txs_per_day AggregateFunction(sum, UInt8),
    l2_num_txs_per_day AggregateFunction(sum, UInt8),
    l2_num_success_txs_per_day AggregateFunction(sum, UInt8),
    num_senders_per_day AggregateFunction(uniqExact, FixedString(42)),
    l2_gas_used AggregateFunction(sum, UInt128),
    l1_gas_used_on_l2 AggregateFunction(sum, Nullable(Int64)),
    l1_gas_paid AggregateFunction(sum, Nullable(Float64)),
    blob_gas_paid AggregateFunction(sum, Nullable(Float64)),
    calldata_bytes_l2_per_day AggregateFunction(sum, Int64),
    estimated_size_user_txs AggregateFunction(sum, Nullable(Float64)),
    l1_gas_paid_fjord AggregateFunction(sum, Nullable(Float64)),
    blob_gas_paid_fjord AggregateFunction(sum, Nullable(Float64)),
    l1_gas_paid_user_txs AggregateFunction(sum, Nullable(Float64)),
    blob_gas_paid_user_txs AggregateFunction(sum, Nullable(Float64)),
    l1_gas_used_user_txs_l2_per_day AggregateFunction(sum, Nullable(UInt128)),
    calldata_bytes_user_txs_l2_per_day AggregateFunction(sum, Int64),
    l2_gas_used_user_txs_per_day AggregateFunction(sum, UInt128),
    l2_eth_fees_per_day AggregateFunction(sum, Float64),
    median_l2_eth_fees_per_tx AggregateFunction(median, Nullable(Float64)),
    l1_contrib_l2_eth_fees_per_day AggregateFunction(sum, Nullable(Float64)),
    l2_contrib_l2_eth_fees_per_day AggregateFunction(sum, Nullable(Float64)),
    l1_l1gas_contrib_l2_eth_fees_per_day AggregateFunction(sum, Nullable(Float64)),
    l1_blobgas_contrib_l2_eth_fees_per_day AggregateFunction(sum, Nullable(Float64)),
    l2_contrib_l2_eth_fees_base_fee_per_day AggregateFunction(sum, Nullable(Float64)),
    l2_contrib_l2_eth_fees_priority_fee_per_day AggregateFunction(sum, Nullable(Float64)),
    input_calldata_gas_l2_per_day AggregateFunction(sum, Int64),
    input_calldata_gas_user_txs_l2_per_day AggregateFunction(sum, Int64),
    compressedtxsize_approx_l2_per_day_ecotone AggregateFunction(sum, Nullable(Float64)),
    compressedtxsize_approx_user_txs_l2_per_day_ecotone AggregateFunction(sum, Nullable(Float64)),
    avg_l1_gas_price_on_l2_state AggregateFunction(avgWeighted, Nullable(Float64), Nullable(Float64)),
    avg_blob_base_fee_on_l2_state AggregateFunction(avgWeighted, Nullable(Float64), Nullable(Float64)),
    avg_l2_gas_price_state AggregateFunction(avgWeighted, Nullable(Float64), Nullable(UInt128)),
    base_fee_gwei_state AggregateFunction(avgWeighted, Nullable(Float64), Nullable(UInt128)),
    equivalent_l1_tx_fee AggregateFunction(sum, Nullable(Float64)),
    avg_l1_fee_scalar_state AggregateFunction(avg, Nullable(Float64)),
    avg_l1_blob_fee_scalar_state AggregateFunction(avg, Nullable(Float64))
)
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(dt)
ORDER BY (dt, chain, network, chain_id);
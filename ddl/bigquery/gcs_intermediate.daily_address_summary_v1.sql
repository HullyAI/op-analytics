CREATE EXTERNAL TABLE `oplabs-tools-data.gcs_intermediate.daily_address_summary_v1`
WITH PARTITION COLUMNS (chain STRING, dt DATE) 
OPTIONS (
    format = 'PARQUET',
    uris = ['gs://oplabs-tools-data-sink/intermediate/daily_address_summary/summary_v1/*'],
    hive_partition_uri_prefix = 'gs://oplabs-tools-data-sink/intermediate/daily_address_summary/summary_v1',
    require_hive_partition_filter = true,
    decimal_target_types = ["NUMERIC", "BIGNUMERIC"]
)

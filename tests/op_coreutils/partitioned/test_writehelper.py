import polars as pl
import pyarrow as pa
import datetime
from unittest.mock import patch


from op_coreutils.duckdb_local import run_query
from op_coreutils.partitioned.location import DataLocation
from op_coreutils.partitioned.writehelper import ParqueWriteManager
from op_coreutils.partitioned.output import ExpectedOutput, OutputData
from op_coreutils.partitioned.types import SinkOutputRootPath, SinkMarkerPath


def test_parquet_writer():
    run_query("TRUNCATE TABLE etl_monitor_dev.intermediate_model_markers")

    df = pl.DataFrame(
        {
            "dt": [
                datetime.date.fromisoformat("2024-01-01"),
                datetime.date.fromisoformat("2024-01-01"),
                datetime.date.fromisoformat("2024-01-01"),
                datetime.date.fromisoformat("2024-01-01"),
                datetime.date.fromisoformat("2024-01-02"),
                datetime.date.fromisoformat("2024-01-02"),
                datetime.date.fromisoformat("2024-01-03"),
            ],
            "chain": [
                "DUMMYOP",
                "DUMMYOP",
                "DUMMYBASE",
                "DUMMYBASE",
                "DUMMYBASE",
                "DUMMYBASE",
                "DUMMYOP",
            ],
            "c": ["some", "words", "here", "and", "few", "more", "blah"],
        }
    )

    manager = ParqueWriteManager(
        location=DataLocation.LOCAL,
        expected_output=ExpectedOutput(
            dataset_name="daily_address_summary/daily_address_summary_v1",
            root_path=SinkOutputRootPath(
                "intermediate/daily_address_summary/daily_address_summary_v1"
            ),
            file_name="out.parquet",
            marker_path=SinkMarkerPath("BLAH"),
            process_name="default",
            additional_columns={"model_name": "MYMODEL"},
            additional_columns_schema=[
                pa.field("chain", pa.string()),
                pa.field("dt", pa.date32()),
                pa.field("model_name", pa.string()),
            ],
        ),
        markers_table="intermediate_model_markers",
        force=False,
    )

    with patch("op_coreutils.partitioned.dataaccess.local_upload_parquet") as mock:
        manager.write(
            OutputData(
                dataframe=df,
                dataset_name="daily_address_summary/daily_address_summary_v1",
                default_partition=None,
            )
        )

    calls = []
    for mock_call in mock.call_args_list:
        calls.append(
            dict(
                path=mock_call.kwargs["path"],
                num_rows=len(mock_call.kwargs["df"]),
            )
        )

    calls.sort(key=lambda x: x["path"])

    assert calls == [
        {
            "path": "ozone/warehouse/intermediate/daily_address_summary/daily_address_summary_v1/chain=DUMMYBASE/dt=2024-01-01/out.parquet",
            "num_rows": 2,
        },
        {
            "path": "ozone/warehouse/intermediate/daily_address_summary/daily_address_summary_v1/chain=DUMMYBASE/dt=2024-01-02/out.parquet",
            "num_rows": 2,
        },
        {
            "path": "ozone/warehouse/intermediate/daily_address_summary/daily_address_summary_v1/chain=DUMMYOP/dt=2024-01-01/out.parquet",
            "num_rows": 2,
        },
        {
            "path": "ozone/warehouse/intermediate/daily_address_summary/daily_address_summary_v1/chain=DUMMYOP/dt=2024-01-03/out.parquet",
            "num_rows": 1,
        },
    ]

    markers = (
        run_query(
            "SELECT * FROM etl_monitor_dev.intermediate_model_markers WHERE chain IN ('DUMMYOP', 'DUMMYBASE')"
        )
        .pl()
        .sort("dt", "chain")
        .to_dicts()
    )

    for marker in markers:
        # Remove keys that change depending on machine or time.
        del marker["writer_name"]
        del marker["updated_at"]

    assert markers == [
        {
            "marker_path": "BLAH",
            "dataset_name": "daily_address_summary/daily_address_summary_v1",
            "root_path": "intermediate/daily_address_summary/daily_address_summary_v1",
            "num_parts": 4,
            "data_path": "intermediate/daily_address_summary/daily_address_summary_v1/chain=DUMMYBASE/dt=2024-01-01/out.parquet",
            "row_count": 2,
            "process_name": "default",
            "chain": "DUMMYBASE",
            "dt": datetime.date(2024, 1, 1),
            "model_name": "MYMODEL",
        },
        {
            "marker_path": "BLAH",
            "dataset_name": "daily_address_summary/daily_address_summary_v1",
            "root_path": "intermediate/daily_address_summary/daily_address_summary_v1",
            "num_parts": 4,
            "data_path": "intermediate/daily_address_summary/daily_address_summary_v1/chain=DUMMYOP/dt=2024-01-01/out.parquet",
            "row_count": 2,
            "process_name": "default",
            "chain": "DUMMYOP",
            "dt": datetime.date(2024, 1, 1),
            "model_name": "MYMODEL",
        },
        {
            "marker_path": "BLAH",
            "dataset_name": "daily_address_summary/daily_address_summary_v1",
            "root_path": "intermediate/daily_address_summary/daily_address_summary_v1",
            "num_parts": 4,
            "data_path": "intermediate/daily_address_summary/daily_address_summary_v1/chain=DUMMYBASE/dt=2024-01-02/out.parquet",
            "row_count": 2,
            "process_name": "default",
            "chain": "DUMMYBASE",
            "dt": datetime.date(2024, 1, 2),
            "model_name": "MYMODEL",
        },
        {
            "marker_path": "BLAH",
            "dataset_name": "daily_address_summary/daily_address_summary_v1",
            "root_path": "intermediate/daily_address_summary/daily_address_summary_v1",
            "num_parts": 4,
            "data_path": "intermediate/daily_address_summary/daily_address_summary_v1/chain=DUMMYOP/dt=2024-01-03/out.parquet",
            "row_count": 1,
            "process_name": "default",
            "chain": "DUMMYOP",
            "dt": datetime.date(2024, 1, 3),
            "model_name": "MYMODEL",
        },
    ]
from dataclasses import dataclass

import polars as pl
import pyarrow as pa

from op_coreutils import clickhouse, duckdb_local
from op_coreutils.logger import structlog, bound_contextvars
from op_coreutils.storage.gcs_parquet import (
    gcs_upload_parquet,
    local_upload_parquet,
)

from .breakout import breakout_partitions
from .location import DataLocation
from .marker import MARKERS_DB, marker_exists, Marker
from .output import OutputData, ExpectedOutput
from .status import all_outputs_complete

log = structlog.get_logger()


@dataclass
class DataWriter:
    """Manages writing data and markers consistently."""

    # Sinks
    write_to: list[DataLocation]

    # Markers Table
    markers_table: str

    # Expected Outputs
    expected_outputs: dict[str, ExpectedOutput]

    # Is set to true if all markers already exist.
    is_complete: bool

    # If true, writes data even if markers already exist.
    force: bool

    def all_complete(self) -> bool:
        """Check if all expected markers are complete."""
        return all_outputs_complete(
            sinks=self.write_to,
            markers=[_.marker_path for _ in self.expected_outputs.values()],
            markers_table=self.markers_table,
        )

    def write_all(self, outputs: list[OutputData]):
        """Write data and markers to all the specified locations.

        The data is provided as a list of functions that return a dataframe. This lets us generalize
        the way in which different tasks produce OutputDataFrame.
        """
        for location in self.write_to:
            for output_data in outputs:
                self.write(location, output_data)

    def write(self, location: DataLocation, output_data: OutputData):
        expected_output = self.expected_outputs[output_data.dataset_name]

        # The default partition value is included in logs because it includes
        # the dt value, which helps keep track of where we are when we run a
        # backfill.
        with bound_contextvars(**(output_data.default_partition or {})):
            is_complete = marker_exists(
                data_location=location,
                marker_path=expected_output.marker_path,
                markers_table=self.markers_table,
            )

            if is_complete and not self.force:
                log.info(
                    f"[{location.name}] Skipping already complete output at {expected_output.marker_path}"
                )
                return

            parts = breakout_partitions(
                df=output_data.dataframe,
                partition_cols=["chain", "dt"],
                default_partition=output_data.default_partition,
            )

            parts_meta = []
            for part in parts:
                write_single_part(
                    location=location,
                    dataframe=part.df,
                    full_path=part.meta.full_path(
                        expected_output.root_path, expected_output.file_name
                    ),
                )
                parts_meta.append(part.meta)

            marker = Marker(
                expected_output=expected_output,
                written_parts=parts_meta,
            )

            write_marker(
                data_location=location,
                arrow_table=marker.to_pyarrow_table(),
                markers_table=self.markers_table,
            )
            log.info(f"Wrote {output_data.dataset_name} to {location.name}")


def write_single_part(
    location: DataLocation,
    dataframe: pl.DataFrame,
    full_path: str,
):
    """Write a single parquet output file for a partitioned output."""
    if location == DataLocation.GCS:
        gcs_upload_parquet(full_path, dataframe)
        return

    elif location == DataLocation.LOCAL:
        local_upload_parquet(
            path=location.with_prefix(full_path),
            df=dataframe,
        )

        return

    raise NotImplementedError()


def write_marker(
    data_location: DataLocation,
    arrow_table: pa.Table,
    markers_table: str,
):
    """Write marker.

    Having markers allows us to quickly check completion and perform analytics
    over previous iterations of the ingestion process.

    Markers for GCS output are written to Clickhouse.
    Markers for local output are written to DuckDB

    """
    if data_location == DataLocation.GCS:
        clickhouse.insert_arrow("OPLABS", MARKERS_DB, markers_table, arrow_table)
        return

    elif data_location == DataLocation.LOCAL:
        duckdb_local.insert_arrow(MARKERS_DB, markers_table, arrow_table)
        return

    raise NotImplementedError()

import pyarrow as pa

from op_analytics.coreutils.logger import structlog
from op_analytics.coreutils.partitioned import (
    DataLocation,
    DataReader,
    PartitionedMarkerPath,
    PartitionedRootPath,
    DataWriter,
    ExpectedOutput,
)

from op_analytics.datapipeline.etl.ingestion.reader import construct_readers
from op_analytics.datapipeline.etl.ingestion.markers import (
    INGESTION_DATASETS,
    INGESTION_MARKERS_TABLE,
)

from .markers import INTERMEDIATE_MODELS_MARKERS_TABLE
from .registry import REGISTERED_INTERMEDIATE_MODELS
from .task import IntermediateModelsTask

log = structlog.get_logger()


def construct_data_readers(
    chains: list[str],
    range_spec: str,
    read_from: DataLocation,
) -> list[DataReader]:
    return construct_readers(
        chains=chains,
        range_spec=range_spec,
        read_from=read_from,
        markers_table=INGESTION_MARKERS_TABLE,
        dataset_names=INGESTION_DATASETS,
    )


def construct_tasks(
    chains: list[str],
    models: list[str],
    range_spec: str,
    read_from: DataLocation,
    write_to: DataLocation,
) -> list[IntermediateModelsTask]:
    """Construct a collection of tasks to compute intermediate models.

    While constructing tasks we also go ahead and load the model definitions and create the
    shared duckdb macros that are used across models.
    """

    readers: list[DataReader] = construct_data_readers(
        chains=chains,
        range_spec=range_spec,
        read_from=read_from,
    )

    tasks = []
    for reader in readers:
        # Each model can have one or more outputs. There is 1 marker per output.
        expected_outputs = []
        for model in models:
            for dataset in REGISTERED_INTERMEDIATE_MODELS[model].expected_output_datasets:
                full_model_name = f"{model}/{dataset}"

                datestr = reader.partition_value("dt")
                chain = reader.partition_value("chain")

                marker_path = PartitionedMarkerPath(f"{datestr}/{chain}/{model}/{dataset}")

                expected_outputs.append(
                    ExpectedOutput(
                        dataset_name=full_model_name,
                        root_path=PartitionedRootPath(f"intermediate/{full_model_name}"),
                        file_name="out.parquet",
                        marker_path=marker_path,
                        process_name="default",
                        additional_columns=dict(
                            model_name=model,
                        ),
                        additional_columns_schema=[
                            pa.field("chain", pa.string()),
                            pa.field("dt", pa.date32()),
                            pa.field("model_name", pa.string()),
                        ],
                    )
                )

        tasks.append(
            IntermediateModelsTask(
                data_reader=reader,
                models=models,
                output_duckdb_relations={},
                data_writer=DataWriter(
                    partition_cols=["chain", "dt"],
                    write_to=write_to,
                    markers_table=INTERMEDIATE_MODELS_MARKERS_TABLE,
                    expected_outputs=expected_outputs,
                    force=False,
                ),
            )
        )

    log.info(f"constructed {len(tasks)} tasks.")
    return tasks

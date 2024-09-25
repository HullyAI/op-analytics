import json
import typer
from op_indexer.schemas.blocks import BLOCKS_SCHEMA

from op_analytics.cli.subcommands.dbt.sources import to_dbt_table
from op_analytics.cli.subcommands.dbt.yamlwriter import write_sources_yaml

from op_coreutils.logger import LOGGER
from op_coreutils.path import repo_path

log = LOGGER.get_logger()

app = typer.Typer()


@app.command()
def generate_sources():
    """Generate dbt source YAML files for our core tables."""

    dbt_sources = {
        "version": "2.0",
        "sources": [
            {
                "name": "indexed",
                "description": "Tables for indexed onchain data.",
                "tables": [to_dbt_table(_) for _ in [BLOCKS_SCHEMA]],
            }
        ],
    }

    path = repo_path("dbt/sources/indexed.yml")

    with open(path, "w") as fobj:
        fobj.write(
            "### AUTO-GENERATED FILE. DO NOT CHANGE. This file was autogenerated by the generate_sources command."
        )
        write_sources_yaml(fobj, dbt_sources)

    log.info(f"Saved sources to {path}")


@app.command()
def docs_custom():
    """Customize html dbt docs.

    Splice in the optimism.css stylesheet on the generated dbt docs index.html
    """

    html_path = repo_path("dbt/target/index.html")
    manifest_path = repo_path("dbt/target/manifest.json")
    catalog_path = repo_path("dbt/target/catalog.json")
    stylesheet_path = repo_path("dbt/docssite/optimism.css")
    html_new_path = repo_path("dbt/docssite/index.html")

    with open(html_path, "r") as f:
        html_content = f.read()

    with open(stylesheet_path, "r") as f:
        stylesheet_content = f.read()

    with open(manifest_path, "r") as f:
        json_manifest = json.loads(f.read())

    with open(catalog_path, "r") as f:
        json_catalog = json.loads(f.read())

    with open(html_new_path, "w") as f:
        search_str = 'n=[o("manifest","manifest.json"+t),o("catalog","catalog.json"+t)]'

        new_str = (
            "n=[{label: 'manifest', data: "
            + json.dumps(json_manifest)
            + "},{label: 'catalog', data: "
            + json.dumps(json_catalog)
            + "}]"
        )

        new_content = html_content.replace(search_str, new_str).replace(
            "<head>", f"<head><style>{stylesheet_content}</style>"
        )
        f.write(new_content)

    log.info(f"Set optimism.css stylesheet at {html_new_path}")

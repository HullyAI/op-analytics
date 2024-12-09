from dataclasses import dataclass
from typing import Any, List
import os
import requests
import polars as pl
from datetime import datetime

from op_analytics.cli.subcommands.pulls.agora.dataacess import Agora
from op_analytics.coreutils.logger import structlog
from op_analytics.coreutils.request import get_data
from op_analytics.coreutils.threads import run_concurrently_store_failures

log = structlog.get_logger()

BASE_URL = "https://vote.optimism.io/api/v1"
API_KEY = os.environ["AGORA_API_KEY"]


@dataclass
class AgoraDelegateVotes:
    votes_df: pl.DataFrame


@dataclass
class PaginatedResponse:
    has_next: bool
    next_offset: int
    data: Any


@dataclass
class SimplePaginator:
    url: str
    limit: int = 50

    def request(self, offset: int) -> PaginatedResponse:
        session = requests.Session()
        result = get_data(
            session,
            url=self.url,
            headers={"Authorization": f"Bearer {API_KEY}"},
            params={"offset": offset, "limit": self.limit},
        )

        assert "meta" in result
        assert "data" in result

        return PaginatedResponse(
            has_next=result["meta"]["has_next"],
            next_offset=result["meta"]["next_offset"],
            data=result["data"],
        )

    def fetch_all(self) -> List[Any]:
        offset = 0
        all_data = []
        while True:
            response = self.request(offset)
            all_data.extend(response.data)
            if not response.has_next:
                break
            offset = response.next_offset
        return all_data


def fetch_event_data(delegates: List[str], endpoint: str, workers: int) -> List[Any]:
    def fetch_delegate_data(address: str, endpoint: str) -> List[Any]:
        paginator = SimplePaginator(url=f"{BASE_URL}/delegates/{address}/{endpoint}", limit=50)
        return paginator.fetch_all()

    run_results = run_concurrently_store_failures(
        function=fetch_delegate_data,
        targets=delegates,
        max_workers=workers,
        function_args=(endpoint,),
    )

    if run_results.failures:
        log.error(f"Failed to fetch data for {len(run_results.failures)} addresses")

    return list(run_results.results.values())


def parse_datetime(value: str) -> datetime:
    """Parse datetime strings in ISO format with 'Z'."""
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def _flatten_vote_data(data: List[Any]) -> List[dict]:
    return [
        {
            "transaction_hash": value["transactionHash"],
            "address": value["address"],
            "proposal_id": value["proposalId"],
            "support": value["support"],
            "weight": value["weight"],
            "reason": value["reason"],
            "params": value["params"],
            "proposal_value": value["proposalValue"],
            "proposal_title": value["proposalTitle"],
            "proposal_type": value["proposalType"],
            "dt": parse_datetime(value["timestamp"]),
        }
        for record in data
        for value in record
    ]


def fetch_delegate_votes(delegates: List[str], workers: int = 12) -> AgoraDelegateVotes:
    votes_data = fetch_event_data(delegates, endpoint="votes", workers=workers)
    flattened = _flatten_vote_data(votes_data)
    df = pl.DataFrame(flattened).sort("dt")
    Agora.DELEGATE_VOTES.write(dataframe=df, sort_by=["dt"])
    return AgoraDelegateVotes(votes_df=df)


def fetch_proposals() -> None:
    paginator = SimplePaginator(url=f"{BASE_URL}/proposals", limit=50)
    proposals = paginator.fetch_all()

    def parse_optional_time(time_str: str) -> Any:
        return parse_datetime(time_str) if time_str else None

    def extract_proposal_data(proposal: dict) -> dict:
        return {
            "id": proposal["id"],
            "proposer": proposal["proposer"],
            "snapshot_block_number": proposal["snapshotBlockNumber"],
            "created_time": parse_datetime(proposal["createdTime"]),
            "start_time": parse_datetime(proposal["startTime"]),
            "end_time": parse_optional_time(proposal.get("endTime")),
            "cancelled_time": parse_optional_time(proposal.get("cancelledTime")),
            "executed_time": parse_optional_time(proposal.get("executedTime")),
            "queued_time": parse_optional_time(proposal.get("queuedTime")),
            "markdowntitle": proposal["markdowntitle"],
            "description": proposal["description"],
            "quorum": proposal["quorum"],
            "approval_threshold": proposal["approvalThreshold"],
            "proposal_type": proposal["proposalType"],
            "status": proposal["status"],
            "created_transaction_hash": proposal["createdTransactionHash"],
            "cancelled_transaction_hash": proposal["cancelledTransactionHash"],
            "executed_transaction_hash": proposal["executedTransactionHash"],
            "proposal_results_for": proposal["proposalResults"]["for"],
            "proposal_results_against": proposal["proposalResults"]["against"],
            "proposal_results_abstain": proposal["proposalResults"]["abstain"],
        }

    cleaned_rows = [extract_proposal_data(p) for p in proposals]
    df = pl.DataFrame(cleaned_rows).sort("start_time")
    Agora.PROPOSALS.write(dataframe=df, sort_by=["start_time"])


def _fetch_single_address_data(address: str, endpoint: str) -> List[dict]:
    session = requests.Session()
    url = f"{BASE_URL}/delegates/{address}/{endpoint}"
    result = get_data(
        session,
        url=url,
        headers={"Authorization": f"Bearer {API_KEY}"},
        params={},
    )
    return result.get("votes", []) if endpoint == "delegators" else [result]


def fetch_delegate_data(delegates: List[str], endpoint: str, workers: int) -> pl.DataFrame:
    def fetch_data(address: str) -> List[dict]:
        return _fetch_single_address_data(address, endpoint=endpoint)

    run_results = run_concurrently_store_failures(
        function=fetch_data,
        targets=delegates,
        max_workers=workers,
    )

    all_data = [record for v in run_results.results.values() for record in v]
    rows = [
        {
            "from_address": record["from"],
            "to_address": record["to"],
            "allowance": record["allowance"],
            "dt": parse_datetime(record["timestamp"]),
            "type": record["type"],
            "amount": record["amount"],
            "transaction_hash": record["transaction_hash"],
        }
        for record in all_data
    ]

    return pl.DataFrame(rows)


def fetch_delegate_delegators(delegates: List[str], workers: int = 12) -> pl.DataFrame:
    return fetch_delegate_data(delegates, endpoint="delegators", workers=workers)


def fetch_delegate_delegatees(delegates: List[str], workers: int = 12) -> pl.DataFrame:
    return fetch_delegate_data(delegates, endpoint="delegatees", workers=workers)

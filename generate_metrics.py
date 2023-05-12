import json
import requests
import datetime
from typing import Dict, Iterable, Tuple, Union
from bs4 import BeautifulSoup


def query_mtrain_by_id(uri: str, _id: str) -> Dict:
    """Attempts to query mtrain for an object with a specific id.
    """
    response = requests.get(
        uri,
        params={
            # api requires queries to serialized json...:/
            "q": json.dumps({
                "filters": [
                    {
                        "name": "id",
                        "val": _id,
                        "op": "eq",
                    }
                ]
            })
        }
    )
    if response.status_code not in (200, ):
        response.raise_for_status()

    objects = response.json()["objects"]

    if len(objects) < 1:
        raise Exception("No objects returned from query.")

    if len(objects) > 1:
        raise Exception(
            "More than one object returned from query, expected to only return one.")

    return objects[0]


def get_stage_name_from_session_id(api_base: str, session_id: str) -> str:
    """Attempts to query mtrain for a "Stage" name from a "BehaviorSession" id.
    """
    session = query_mtrain_by_id(
        f"{api_base}/api/v1/behavior_sessions",
        session_id,
    )

    state = query_mtrain_by_id(
        f"{api_base}/api/v1/states",
        session["state_id"],
    )

    return query_mtrain_by_id(
        f"{api_base}/api/v1/stages",
        state["id"],
    )["name"]


def session_metrics_summary_to_training_summary(api_base: str, session_metrics: Dict) -> \
        Tuple[str, str, Union[str, None], Union[str, None], Union[str, None]]:  # TODO: use typevar
    return (
        session_metrics["session_datetime"].strftime("%m-%d-%y"),
        get_stage_name_from_session_id(
            api_base, session_metrics["session_id"]),
        session_metrics.get("hitCount"),
        session_metrics.get("dprimeSameModal"),
        session_metrics.get("dprimeOtherModalGo"),
    )


def get_mtrain_training_history(api_base: str, subject_id: str, session_id: str) -> \
        Iterable[Tuple[str, str, Union[str, None], Union[str, None], Union[str, None]]]:  # TODO: use typevar
    """Gets a subject's mtrain training history up to and including `session_id`.

    Returns
    -------
    iterable of training history, each tuple represents:
        - session date (represented as a string in format: month-day-year)
        - stage_name
        - hitCount or None
        - dprimeSameModal or None
        - dprimeOtherModalGo or None

    Notes
    -----
    - sorted in behavior session datetime ascending
    - if any of: hitCount, dprimeSameModal, dprimeOtherModalGo is equal to 
    'None', this metric was found on mtrain but it's value was None
    - if any of: hitCount, dprimeSameModal, dprimeOtherModalGo is equal to 
    None, this metric was not found on mtrain
    """
    resolved_uri = f"{api_base}/df/session_metrics"
    response = requests.get(resolved_uri)
    if response.status_code not in [200]:
        response.raise_for_status()

    soup = BeautifulSoup(response.text, features="html.parser")

    table = soup.find("table")
    if table is None:
        raise Exception(
            "No table detected in content returned from mtrain uri. uri=%s" % resolved_uri)

    table_body = table.find("tbody")
    if table_body is None:
        raise Exception("No table body detected in table.")

    table_data = []
    for row in table_body.find_all("tr"):
        cols = row.find_all('td')
        cols = [ele.text.strip() for ele in cols]
        table_data.append([ele for ele in cols if ele])

    session_metrics_map = {}  # dict is convenient, constant
    for item in table_data:
        if len(item) != 6:
            raise Exception(
                "A critical assumption we made about the table is wrong...")

        # we only want metrics from a specific subject
        if item[2] != subject_id:
            continue

        # we only want to display some metrics
        metric_name = item[4]
        if metric_name not in ["hitCount", "dprimeSameModal", "dprimeOtherModalGo"]:
            continue

        _session_id = item[1]
        if _session_id not in session_metrics_map:
            session_metrics_map[_session_id] = {
                "session_datetime": datetime.datetime.strptime(
                    item[3],
                    '%Y-%m-%d',
                ),
                "session_id": _session_id,
            }

        session_metrics_map[_session_id][metric_name] = item[5].lstrip(
            "[").rstrip("]")  # metric value, remove brackets

    # sort datetime asc
    sorted_session_metrics = sorted(
        session_metrics_map.values(),
        key=lambda item: item["session_datetime"],
    )

    filtered_training_history = []
    for session_summary in sorted_session_metrics:
        if session_summary["session_id"] == session_id:
            filtered_training_history.append(
                session_metrics_summary_to_training_summary(
                    api_base,
                    session_summary,
                )
            )
            break  # stop after including session with target session_id
        filtered_training_history.append(
            session_metrics_summary_to_training_summary(
                api_base,
                session_summary,
            )
        )
    else:
        raise Exception(
            "Session id not present in returned table. session_id=%s" % session_id)

    return filtered_training_history


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("api_base", type=str)
    parser.add_argument("subject_id", type=str)
    parser.add_argument("session_id", type=str)

    args = parser.parse_args()

    training_history = get_mtrain_training_history(
        args.api_base, args.subject_id, args.session_id)

    print(training_history)

    def generate_html(training_history):
        header = "<tr><th>Session datetime</th><th>Stage name</th><th>hitCount</th><th>dprimeSameModal</th><th>dprimeOtherModalGo</th></tr>"
        rows = [
            f"<tr><td>{summary[0]}</td><td>{summary[1]}</td><td>{summary[2]}</td><td>{summary[3]}</td><td>{summary[4]}</td></tr>"
            for summary in training_history
        ]
        table = f"<table>\n{header}\n\n{''.join(rows)}\n</table>"
        return f"<html>\n{table}\n</html>"

    with open("table_example.html", "w") as f:
        f.write(generate_html(training_history))

import requests
import datetime
from typing import Iterable, Tuple, Union
from bs4 import BeautifulSoup


def get_mtrain_training_history(api_base: str, subject_id: str, session_id: str) -> \
        Iterable[Tuple[datetime.datetime, str, Union[str, None], Union[str, None], Union[str, None]]]:
    """Gets a subject's mtrain training history up to and including `session_id`.

    Returns
    -------
    iterable of training history, each tuple represents:
        - session datetime
        - session_id
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

    # convert to tuples
    all_training_history = map(
        lambda session_metrics: (
            session_metrics["session_datetime"],
            session_metrics["session_id"],
            session_metrics.get("hitCount"),
            session_metrics.get("dprimeSameModal"),
            session_metrics.get("dprimeOtherModalGo"),
        ),
        session_metrics_map.values(),
    )

    # sort datetime asc
    sorted_all_training_history = sorted(
        all_training_history,
        key=lambda item: item[0],
    )

    filtered_training_history = []
    for session_summary in sorted_all_training_history:
        if session_summary[1] == session_id:
            filtered_training_history.append(session_summary)
            break  # break after including target session_id
        filtered_training_history.append(session_summary)
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

    assert training_history[-1][1] == args.session_id, \
        f"Last session in training history should have target session id: {args.session_id}"

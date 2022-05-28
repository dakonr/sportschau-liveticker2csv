# file: liveticker2csv.py
import argparse
import json
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Union

import httpx  # Documentation: https://www.python-httpx.org/quickstart/
import pandas as pd
from bs4 import (  # Documentation: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
    BeautifulSoup, Tag)
from pytz import utc

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

def get_livetickerpage(url: str) -> httpx.Response.text:
    page = httpx.get(url)
    assert page.status_code == 200
    return page.text

def match_details(parsed_content: BeautifulSoup) -> dict:
    team_shortname_mapping = dict()
    metadata = parsed_content.select("div.first.last.odd.finished.active.match")[0]
    for team_shortname in metadata.select("div.team-shortname"):
        for team in team_shortname.find_all("a"):
            team_slug_name = Path(team.get('href')).parts[-2]
            team_shortname_mapping[team.get_text().lower()] = team_slug_name
            team_shortname_mapping[team_slug_name.replace("-", " ")] = team_slug_name
            team_shortname_mapping[team_slug_name] = team_slug_name
    return {
        "start_datetime": pd.to_datetime(metadata.attrs.get("data-datetime")),
        "end_datetime": pd.to_datetime(metadata.attrs.get("data-datetime_end")),
        "team_shortname_mapping": team_shortname_mapping
    }

def corresponding_team(liveticker_event: Tag) -> Union[str, None]:
    for tag in liveticker_event.select("div.team-shortname"):
        for a_tag in tag.select("a"):
            return Path(a_tag.attrs.get("href")).parts[-2]

def liveticker_content(liveticker_event: Tag) -> Union[str, None]:
    for tag in liveticker_event.select("div.liveticker-content"):
        return str(tag.get_text()).replace('\n', ' ').replace('\r', '').strip()

def liveticker_event_parser(liveticker_event: Tag, match_details: dict) -> dict:
    event_minute = int(liveticker_event.select("div.liveticker-minute")[0].get_text())
    event_action = liveticker_event.attrs.get("data-event_action")
    is_goal = event_action == "goal"
    is_card = event_action == "card"
    relevant_team = corresponding_team(liveticker_event)
    text = liveticker_content(liveticker_event)
    halftime = 0
    event_timestamp = liveticker_event.select("div.liveticker-datetime")[0].get_text()

    if event_minute <= 45:
        halftime = 1
    if event_minute > 45:
        halftime = 2

    return {
        "minute": event_minute,
        "action": event_action,
        "is_goal": is_goal,
        "is_card": is_card,
        "relevant_team": relevant_team,
        "halftime": halftime,
        "datetime": event_timestamp,
        "text": text
    }

def relevant_liveticker_events(liveticker_events: BeautifulSoup) -> Iterable[Tag]:
    for element in liveticker_events.select("div.module-liveticker")[0].select("div.liveticker"):
        if element.select("div.liveticker-minute")[0].get_text():
            yield element

def workflow(url: str, data_dir: str):
    data_path = Path(data_dir)

    # Get and Parse Liveticker
    content = get_livetickerpage(url)
    with open(data_path.joinpath("raw_liveticker.html"), "w") as file:
        file.write(content)
    parsed_content = BeautifulSoup(content, "html.parser")

    # Retrive Metadata
    meta_data = match_details(parsed_content)
    meta_data["url"] = url

    # Retrive Play Data
    data = [liveticker_event_parser(element, meta_data) for element in relevant_liveticker_events(parsed_content)]
    df = pd.DataFrame(data)

    # Revert Dataframe
    df = df.loc[::-1].reset_index(drop=True)
    # Create UTC Timestamp
    play_start = meta_data["start_datetime"]
    utc_timedelta = pd.to_datetime(
        f'{play_start.strftime("%m/%d/%Y-")}{df["datetime"][0]}',
        format="%m/%d/%Y-%H:%M",
        utc=True
        ) - play_start #"%m/%d/%Y-%H:%M"

    corrected_timestamps = []
    for row in df.itertuples():
        corrected_timestamps.append(
            pd.to_datetime(
        f'{play_start.strftime("%m/%d/%Y-")}{row.datetime}',
        format="%m/%d/%Y-%H:%M",
        utc=True
        ) - utc_timedelta
        )
    df["timestamp"] = corrected_timestamps
    
    # Get Pause Data
    meta_data["break_start"] = df[df["minute"] == 45].iloc[0]["timestamp"]
    meta_data["break_end"] = df[df["minute"] == 46].iloc[0]["timestamp"]

    # Clean DataFrame
    df.drop(columns=["datetime"])
    
    # Save to csv
    df.to_csv(data_path.joinpath(Path("./liveticker.csv")) ,index=False)
    # Save Metadata
    with open(data_path.joinpath("metadata.json"), "w") as file:
        json.dump(meta_data, file, default=json_serial)

def main():
    parser = argparse.ArgumentParser(description="Process Sportschau Liveticker.")
    parser.add_argument("--url", type=str, required=True, help="URL to Liveticker")
    parser.add_argument("--data-dir", type=str, default="./", help="Path to folder to store data")
    args = parser.parse_args()
    print(f"Downloading Liveticker {args.url} \nand extract data to {args.data_dir}")
    workflow(args.url, args.data_dir)

if __name__ == "__main__":
    main()

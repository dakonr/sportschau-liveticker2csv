# file: liveticker2csv.py
import httpx #Documentation: https://www.python-httpx.org/quickstart/
from bs4 import BeautifulSoup #Documentation: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
from pathlib import Path
from pprint import pprint

def get_livetickerpage(url: str) -> httpx.Response.text:
    page = httpx.get(url)
    assert page.status_code == 200
    return page.text

def match_details(content: httpx.Response.text) -> dict:
    team_shortname_mapping = dict()
    parsed_content = BeautifulSoup(content, "html.parser")
    metadata = parsed_content.select("div.first.last.odd.finished.active.match")[0]
    for team_shortname in metadata.select("div.team-shortname"):
        for team in team_shortname.find_all("a"):
            team_slug_name = Path(team.get('href')).parts[-2]
            team_shortname_mapping[team.get_text().lower()] = team_slug_name
            team_shortname_mapping[team_slug_name.replace("-", " ")] = team_slug_name
            team_shortname_mapping[team_slug_name] = team_slug_name
    return {
        "start_datetime": metadata.attrs.get("data-competition_type"),
        "team_shortname_mapping": team_shortname_mapping
    }

if __name__ == "__main__":
    page = get_livetickerpage("https://livecenter.sportschau.de/fussball/deutschland-bundesliga/ma9242973/vfb-stuttgart_borussia-dortmund/liveticker/")
    pprint(
        match_details(page)
    )
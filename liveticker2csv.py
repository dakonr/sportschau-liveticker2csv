# file: liveticker2csv.py
import httpx

def get_livetickerpage(url: str):
    page = httpx.get(url)
    return page.text


if __name__ == "__main__":
    print(get_livetickerpage("https://livecenter.sportschau.de/fussball/deutschland-bundesliga/ma9242973/vfb-stuttgart_borussia-dortmund/liveticker/"))
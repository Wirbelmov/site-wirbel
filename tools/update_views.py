"""Atualiza as views do projects.json pela YouTube Data API (chave no ambiente: YT_API_KEY).

- Cada vídeo do portfólio recebe as views atuais (e o texto "78 mil views" nos três idiomas).
- O contador do site ("views" no topo do projects.json) soma:
    * todos os vídeos LONGOS dos canais listados em counter.channels (o canal inteiro, inclusive os
      vídeos publicados depois; "longo" = mais de 3 minutos, para deixar Shorts de fora, já que o
      site diz "views em vídeos longos");
    * os vídeos do portfólio;
    * os vídeos avulsos de counter.videos (trabalhos que não estão no portfólio).
  Cada vídeo conta uma vez só, mesmo que apareça em mais de uma lista.

Se o YouTube não responder, o arquivo fica como estava e o site segue com os números anteriores.
Uso: YT_API_KEY=... python tools/update_views.py (na pasta do site).
"""

import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://www.googleapis.com/youtube/v3/"
SHORT_MAX_SECONDS = 180  # YouTube Shorts go up to 3 minutes

FMT = {
    "facts": lambda v: f"{round(v / 1000)} mil views" if v >= 1000 else f"{v} views",
    "facts_en": lambda v: f"{round(v / 1000)}K views" if v >= 1000 else f"{v} views",
    "facts_es": lambda v: f"{round(v / 1000)} mil vistas" if v >= 1000 else f"{v} vistas",
}


def get(endpoint, key, **params):
    url = API + endpoint + "?" + urllib.parse.urlencode({**params, "key": key})
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def yt_id(url):
    m = re.search(r"(?:youtu\.be/|[?&]v=|shorts/)([\w-]{11})", url or "")
    return m.group(1) if m else ""


def seconds(iso):
    m = re.fullmatch(r"P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mi, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + s


def channel_videos(channel_id, key):
    """Every upload of a channel, through its uploads playlist (UC... -> UU...)."""
    playlist = "UU" + channel_id[2:]
    ids, token = [], None
    while True:
        params = {"part": "contentDetails", "playlistId": playlist, "maxResults": 50}
        if token:
            params["pageToken"] = token
        page = get("playlistItems", key, **params)
        ids += [i["contentDetails"]["videoId"] for i in page.get("items", [])]
        token = page.get("nextPageToken")
        if not token:
            return ids


def video_stats(ids, key):
    out = {}
    for i in range(0, len(ids), 50):
        page = get("videos", key, part="statistics,contentDetails", id=",".join(ids[i:i + 50]))
        for v in page.get("items", []):
            out[v["id"]] = (int(v["statistics"].get("viewCount", 0)), seconds(v["contentDetails"].get("duration")))
    return out


def main():
    key = os.environ.get("YT_API_KEY")
    if not key:
        print("::warning::Segredo YT_API_KEY não configurado; as views não foram atualizadas.")
        return
    path = ROOT / "projects.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    counter = d.get("counter") or {}

    portfolio = [yt_id(p.get("url")) for p in d.get("projects", [])]
    extra = [v for v in counter.get("videos", []) if v]
    try:
        from_channels = [v for ch in counter.get("channels", []) for v in channel_videos(ch, key)]
        stats = video_stats(list(dict.fromkeys([*portfolio, *extra, *from_channels])), key)
    except Exception as e:  # network or quota: keep the previous numbers rather than publish a wrong total
        print(f"::warning::O YouTube não respondeu ({e}); o site segue com os números anteriores.")
        return

    for p in d.get("projects", []):
        vid = yt_id(p.get("url"))
        if vid not in stats:
            print(f"::warning::Vídeo {vid} do portfólio não encontrado no YouTube; mantido o número anterior.")
            continue
        p["views"] = stats[vid][0]
        for k, f in FMT.items():
            if isinstance(p.get(k), list) and len(p[k]) > 1:
                p[k][1] = f(p["views"])

    counted = {}
    for vid in [*portfolio, *extra]:
        if vid in stats:
            counted[vid] = stats[vid][0]
    for vid in from_channels:
        if vid in stats and stats[vid][1] > SHORT_MAX_SECONDS:
            counted[vid] = stats[vid][0]
    for vid in extra:
        if vid not in stats:
            print(f"::warning::Vídeo avulso {vid} não encontrado no YouTube.")

    d["views"] = sum(counted.values())
    if counter:
        counter["counted"] = len(counted)  # how many videos the site's total adds up
    path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Total de views: {d['views']} em {len(counted)} vídeos "
          f"({len(from_channels)} vídeos nos canais, {len(extra)} avulsos, {len(portfolio)} no portfólio)")


if __name__ == "__main__":
    main()

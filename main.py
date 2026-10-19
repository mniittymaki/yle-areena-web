from nicegui import ui, app
import subprocess
import os
import re
import threading
from pathlib import Path

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "/downloads"))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Plex-kansiot (oletuksena DOWNLOAD_DIR:n alle, voidaan ylikirjoittaa ympäristömuuttujilla tai asetuksilla)
PLEX_MOVIES = Path(os.getenv("PLEX_MOVIES", DOWNLOAD_DIR / "Movies"))
PLEX_TV = Path(os.getenv("PLEX_TV", DOWNLOAD_DIR / "TV Shows"))

settings = {
    "movies": str(PLEX_MOVIES),
    "tv": str(PLEX_TV),
}

download_status = {"running": False, "message": "", "progress": ""}


def sanitize_filename(name: str) -> str:
    """Keep original title readable but remove filesystem-problematic characters."""
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = re.sub(r"[\s_]+", " ", name).strip()
    return name or "video"


def get_metadata(url: str) -> dict:
    """Fetch useful metadata from yt-dlp."""
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--print",
                "%(title)s|%(series)s|%(season_number)s|%(episode_number)s|%(release_year)s|%(upload_date)s",
                "--no-warnings",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split("|")
            return {
                "title": parts[0] if len(parts) > 0 else "video",
                "series": parts[1] if len(parts) > 1 and parts[1] != "NA" else None,
                "season": int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None,
                "episode": int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else None,
                "year": parts[4] if len(parts) > 4 and parts[4] != "NA" else (
                    parts[5][:4] if len(parts) > 5 and len(parts[5]) >= 4 else None
                ),
            }
    except Exception:
        pass
    return {"title": "video"}


def build_plex_path(meta: dict, content_type: str) -> Path:
    """Build a Plex-friendly path using configured base directories."""
    title = sanitize_filename(meta.get("title") or "video")
    year = meta.get("year") or ""
    series = sanitize_filename(meta.get("series") or title)
    season = meta.get("season")
    episode = meta.get("episode")

    movies_base = Path(settings["movies"])
    tv_base = Path(settings["tv"])

    if content_type == "movie" or (content_type == "auto" and not season and not episode):
        folder = f"{title} ({year})" if year else title
        filename = f"{folder}.%(ext)s"
        return movies_base / folder / filename

    season_num = f"{season:02d}" if season else "01"
    episode_num = f"{episode:02d}" if episode else "01"
    show_folder = f"{series} ({year})" if year else series
    season_folder = f"Season {season_num}"
    filename = f"{show_folder} - S{season_num}E{episode_num} - {title}.%(ext)s"
    return tv_base / show_folder / season_folder / filename


def run_download(url: str, quality: str, sub_langs: str, embed: bool, content_type: str = "auto"):
    download_status["running"] = True
    download_status["message"] = "Haetaan metatietoja..."
    download_status["progress"] = ""

    meta = get_metadata(url)
    safe_title = sanitize_filename(meta.get("title") or "video")

    if content_type == "none":
        out_path = DOWNLOAD_DIR / f"{safe_title}.%(ext)s"
    else:
        out_path = build_plex_path(meta, content_type)
        out_path.parent.mkdir(parents=True, exist_ok=True)

    download_status["message"] = f"Ladataan: {safe_title}"

    cmd = [
        "yt-dlp",
        "--newline",
        "--progress",
        "--no-part",
        "--merge-output-format", "mkv",
        "-o", str(out_path),
        "--paths", f"temp:{DOWNLOAD_DIR}",
        "--paths", f"home:{DOWNLOAD_DIR}",
    ]

    if quality == "best":
        cmd.extend(["-f", "bv*+ba/b"])
    elif quality == "1080":
        cmd.extend(["-f", "bv*[height<=1080]+ba/b"])
    elif quality == "720":
        cmd.extend(["-f", "bv*[height<=720]+ba/b"])

    if sub_langs and sub_langs != "none":
        cmd.extend(["--write-subs", "--sub-langs", sub_langs])
        if embed:
            cmd.append("--embed-subs")

    cmd.append(url)

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        for line in process.stdout:
            line = line.strip()
            if line:
                download_status["progress"] = line
                if "%" in line or "ETA" in line:
                    download_status["message"] = line
        process.wait()
        if process.returncode == 0:
            download_status["message"] = f"Valmis: {safe_title}"
        else:
            download_status["message"] = f"Virhe (exit {process.returncode})"
    except Exception as e:
        download_status["message"] = f"Virhe: {e}"
    finally:
        download_status["running"] = False

@ui.page("/")
def main_page():
    ui.markdown("# Yle Areena -lataaja")
    ui.markdown("Liitä Areena-osoite ja lataa video palvelimelle.")

    url_input = ui.input("Areena-URL", placeholder="https://areena.yle.fi/...").classes("w-full")

    with ui.row().classes("w-full gap-4"):
        quality = ui.select(
            {"best": "Paras laatu", "1080": "1080p", "720": "720p"},
            value="best",
            label="Laatu",
        )
        subs = ui.select(
            {"fi,sv,all": "Kaikki (fi+sv)", "fi": "Suomi", "sv": "Ruotsi", "none": "Ei tekstityksiä"},
            value="fi,sv,all",
            label="Tekstitykset",
        )
        content_type = ui.select(
            {"auto": "Automaattinen (Plex)", "movie": "Elokuva (Plex)", "tv": "TV-sarja (Plex)", "none": "Tavallinen"},
            value="auto",
            label="Tallennustapa",
        )
        embed = ui.checkbox("Upota tekstitykset MKV:hen", value=True)

    status_label = ui.label("Valmis").classes("text-lg")
    progress_label = ui.label("").classes("text-sm text-gray-500")

    def update_status():
        status_label.text = download_status["message"] or "Valmis"
        progress_label.text = download_status["progress"]
        if download_status["running"]:
            status_label.classes(replace="text-lg text-blue-600")
        else:
            status_label.classes(replace="text-lg")

    ui.timer(0.5, update_status)

    def start():
        url = url_input.value.strip()
        if not url or "areena.yle.fi" not in url:
            ui.notify("Anna kelvollinen Areena-URL", type="warning")
            return
        if download_status["running"]:
            ui.notify("Lataus on jo käynnissä", type="info")
            return
        threading.Thread(
            target=run_download,
            args=(url, quality.value, subs.value, embed.value, content_type.value),
            daemon=True,
        ).start()
        ui.notify("Lataus aloitettu")

    ui.button("Lataa", on_click=start).classes("bg-blue-600 text-white")

    ui.separator()
    ui.markdown("### Plex-kansiot")
    with ui.row().classes("w-full gap-4"):
        movies_input = ui.input("Elokuvakansio", value=settings["movies"]).classes("w-1/2")
        tv_input = ui.input("TV-sarjakansio", value=settings["tv"]).classes("w-1/2")

    def save_settings():
        settings["movies"] = movies_input.value.strip() or str(PLEX_MOVIES)
        settings["tv"] = tv_input.value.strip() or str(PLEX_TV)
        Path(settings["movies"]).mkdir(parents=True, exist_ok=True)
        Path(settings["tv"]).mkdir(parents=True, exist_ok=True)
        ui.notify("Asetukset tallennettu")

    ui.button("Tallenna kansiot", on_click=save_settings).props("outline")

    ui.separator()
    ui.markdown("### Ladatut tiedostot")
    files_container = ui.column()

    def refresh_files():
        files_container.clear()
        files = sorted(DOWNLOAD_DIR.rglob("*"), key=lambda p: p.stat().st_mtime if p.is_file() else 0, reverse=True)
        files = [f for f in files if f.is_file()][:30]
        if not files:
            with files_container:
                ui.label("Ei ladattuja tiedostoja.")
            return
        with files_container:
            for f in files:
                with ui.row().classes("items-center gap-2"):
                    ui.label(str(f.relative_to(DOWNLOAD_DIR)) if f.is_relative_to(DOWNLOAD_DIR) else f.name)
                    ui.button(
                        "Lataa",
                        on_click=lambda path=f: ui.download(path),
                    ).props("flat")

    ui.timer(2.0, refresh_files)
    refresh_files()

ui.run(title="Yle Areena", host="0.0.0.0", port=8080, reload=False)

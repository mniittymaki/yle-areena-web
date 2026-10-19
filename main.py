from nicegui import ui, app
import subprocess
import os
import re
import threading
from pathlib import Path

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "/downloads"))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

download_status = {"running": False, "message": "", "progress": ""}


def sanitize_filename(name: str) -> str:
    """Keep original title readable but remove filesystem-problematic characters."""
    name = name.strip()
    # Replace characters that are illegal on most filesystems
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    # Collapse multiple spaces/underscores
    name = re.sub(r"[\s_]+", " ", name).strip()
    return name or "video"


def get_title(url: str) -> str:
    try:
        result = subprocess.run(
            ["yt-dlp", "--print", "title", "--no-warnings", url],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return "video"


def run_download(url: str, quality: str, sub_langs: str, embed: bool):
    download_status["running"] = True
    download_status["message"] = "Haetaan otsikkoa..."
    download_status["progress"] = ""

    raw_title = get_title(url)
    safe_title = sanitize_filename(raw_title)
    download_status["message"] = f"Ladataan: {safe_title}"

    cmd = [
        "yt-dlp",
        "--newline",
        "--progress",
        "--no-part",
        "--merge-output-format", "mkv",
        "-o", str(DOWNLOAD_DIR / f"{safe_title}.%(ext)s"),
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
            args=(url, quality.value, subs.value, embed.value),
            daemon=True,
        ).start()
        ui.notify("Lataus aloitettu")

    ui.button("Lataa", on_click=start).classes("bg-blue-600 text-white")

    ui.separator()
    ui.markdown("### Ladatut tiedostot")
    files_container = ui.column()

    def refresh_files():
        files_container.clear()
        files = sorted(DOWNLOAD_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            with files_container:
                ui.label("Ei ladattuja tiedostoja.")
            return
        with files_container:
            for f in files[:30]:
                with ui.row().classes("items-center gap-2"):
                    ui.label(f.name)
                    ui.button(
                        "Lataa",
                        on_click=lambda path=f: ui.download(path),
                    ).props("flat")

    ui.timer(2.0, refresh_files)
    refresh_files()

ui.run(title="Yle Areena", host="0.0.0.0", port=8080, reload=False)

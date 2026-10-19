# Yle Areena -lataaja (NiceGUI)

Selainpohjainen käyttöliittymä Yle Areena -videoiden lataamiseen. Käyttää taustalla yt-dlp:tä.

## Käyttö Dockerilla

```bash
cd yle-areena-web
docker compose up -d --build
```

Avaa selaimessa: http://localhost:8080

Ladatut tiedostot tallentuvat `./downloads`-kansioon.

## Ominaisuudet

- Areena-URL
- Laatuvalinta (paras / 1080p / 720p)
- Tekstitykset (kaikki, suomi, ruotsi tai ei)
- Upota tekstitykset MKV-tiedostoon
- Ladattujen tiedostojen lista ja latauslinkit

## Huomiot

- Vaatii toimivan verkkoyhteyden palvelimelta Yle Areenaan.
- Tekstitykset ja korkea laatu edellyttävät ffmpeg:ää (sisältyy Docker-imageen).
- Käyttö vain omaan käyttöön. Noudata tekijänoikeuksia.

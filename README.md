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
- **Plex-yhteensopiva tallennus** (Automaattinen / Elokuva / TV-sarja)
- Ladattujen tiedostojen lista ja latauslinkit

### Plex-kansiorakenne

Kun valitset Plex-tilan, tiedostot tallentuvat esimerkiksi:

```
downloads/
  Movies/
    Elokuvan nimi (2024)/
      Elokuvan nimi (2024).mkv
  TV Shows/
    Sarjan nimi (2023)/
      Season 01/
        Sarjan nimi (2023) - S01E03 - Jakson nimi.mkv
```

Osoita Plex-kirjastosi näihin kansioihin (`Movies` ja `TV Shows`).

## Huomiot

- Vaatii toimivan verkkoyhteyden palvelimelta Yle Areenaan.
- Tekstitykset ja korkea laatu edellyttävät ffmpeg:ää (sisältyy Docker-imageen).
- Käyttö vain omaan käyttöön. Noudata tekijänoikeuksia.

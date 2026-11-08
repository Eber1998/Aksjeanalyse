# Aksjeanalyse (gratis, selvgående)

## Oppsett (ca. 10 minutter, én gang)
1. Lag en konto på github.com og et nytt **offentlig** repo (f.eks. `aksjeanalyse`).
2. Last opp alle filene fra denne mappen (husk mappen `.github/workflows`).
3. Gå til **Settings → Pages → Source: GitHub Actions**.
4. Gå til **Actions → Oppdater aksjedata → Run workflow** (første kjøring).
5. Appen ligger på `https://BRUKERNAVN.github.io/aksjeanalyse/`. Åpne den på telefonen og velg «Legg til på Hjem-skjerm».

Oppdateres automatisk hver time, hele døgnet (krypto handles 24/7).

## Legge til flere aksjer
Rediger `watchlist.json` på GitHub (blyant-ikonet). Format: `"TICKER": "Navn"`.
Oslo Børs ender på `.OL` (f.eks. `NHY.OL`), USA uten endelse (f.eks. `TSLA`).
Etter lagring kjører oppdateringen, og aksjen kan søkes opp og legges til i appen.

## Krypto
- Ligger i fanen **Krypto**. Rediger `"crypto"` i `watchlist.json` for å legge til mynter (format `SOL-USD`).
- **Risikonivå:** krypto har egne grenser og måles bare mot andre kryptovalutaer. Daglig svingning under 2,5 % = Lav, 2,5–4 % = Middels, over 4 % = Høy. Aksjer bruker strengere grenser (1,5 % og 2,5 %).
- **Score:** teknisk 40 %, trend siste 30 dager 30 %, nyheter 30 %.
- **Trender:** Frykt og grådighet-indeksen (alternative.me), mest søkte mynter på CoinGecko, og temaer som går igjen i nyhetene (ETF, regulering, hack, stablecoins m.m.).
- **Nyheter fra hele verden:** Google Nyheter i USA, Storbritannia, Norge, Tyskland, Japan, Sør-Korea, Brasil og India. Overskriftene vises på originalspråk og blir ikke oversatt.
- Stemning (positiv/negativ) vurderes bare for engelske og norske overskrifter.

## Slik beregnes signalene
- **Teknisk (40 %):** RSI(14), MACD(12/26/9), kurs mot 200-dagers snitt.
- **Fundamental (30 %):** P/E og utbytte. Mangler P/E, brukes 20 (nøytral).
- **Nyheter (30 %):** enkel nøkkelordscore på overskrifter fra Yahoo Finance og Google Nyheter. Grov metode, les alltid selve artikkelen.
- **Daglig risiko:** årlig volatilitet delt på √252. «Dårlig dag» = 1,65 × daglig svingning (95 %).

## Begrensninger
- Gratis kurser er ca. 15 min forsinket, og Yahoo kan av og til svikte (aksjen hoppes da over).
- GitHub stopper planlagte kjøringer hvis repoet er helt inaktivt i 60 dager. Trykk «Run workflow» for å starte igjen.
- Dette er statistikk, ikke investeringsråd.
.

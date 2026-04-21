# Dupe Scraper

A local web app and CLI for finding Dupe marketplace listings that are priced below configured or learned typical prices.

## Features

- Scans Dupe marketplace listings for buy-now deals.
- Learns baseline prices from the marketplace summary endpoint.
- Supports configured typical prices for items you care about.
- Runs as a browser UI or a command-line tool.
- Keeps API keys out of source control.

## Setup

Copy the example config and adjust values if needed:

```bash
cp config.example.json config.json
```

Set your API key in the environment:

```bash
export DUPE_API_KEY="your_api_key_here"
```

The default API base URL is:

```text
https://dupe.fi
```

## Web App

Start the local web app:

```bash
python3 -m dupe_deal_tracker web --host 127.0.0.1 --port 8787
```

Open:

```text
http://127.0.0.1:8787
```

You can also enter the API base URL and API key directly in the browser UI. Those values are stored in that browser's local storage and are not written to repo files.

## CLI

Update learned baseline prices:

```bash
python3 -m dupe_deal_tracker collect-baseline
```

Scan once:

```bash
python3 -m dupe_deal_tracker scan
```

Run continuously:

```bash
python3 -m dupe_deal_tracker daemon
```

## Configuration

Important fields in `config.json`:

- `deal_threshold`: maximum listing-to-typical price ratio. `0.82` means 18% off or better.
- `min_profit_usdc`: minimum expected profit before a listing is shown.
- `item_filters`: marketplace search terms to scan.
- `typical_prices`: manually configured baseline prices.
- `state_path`: local learned-price cache path.

Local config and learned state are ignored by git.

## Tests

Run:

```bash
PYTHONPYCACHEPREFIX=/tmp/dupe-scraper-pycache python3 -m unittest discover -s tests
```

## License

This project is licensed under the GNU Affero General Public License v3.0. See `LICENSE.txt`.

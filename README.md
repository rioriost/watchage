# WatchAGE

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.13%2B-blue)

## Obsoleted

Integrated into [AGEFreighter](https://github.com/rioriost/agefreighter).
watchage is no longer maintained.

## Overview

WatchAGE is a visualizer for Apache AGE.

## Table of Contents

- [Installation](#installation)
- [Prerequisites](#prerequisites)
- [Usage](#usage)
- [Release Notes](#release-notes)
- [License](#license)

## Installation

### Git based installation

On macOS / Linux
```bash
git clone https://github.com/rioriost/watchage.git
cd watchage
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export PG_CONNECTION_STRING="host=localhost port=5432 dbname=yourdb user=youruser password=yourpassword"

python app.py
```

On Windows
```bash
git clone https://github.com/rioriost/watchage.git
cd watchage
python3 -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

set PG_CONNECTION_STRING="host=localhost port=5432 dbname=yourdb user=youruser password=yourpassword"

python app.py
```

If you're using uv,

```bash
git clone https://github.com/rioriost/watchage.git
cd watchage
uv venv
source .venv/bin/activate
uv sync

export PG_CONNECTION_STRING="host=localhost port=5432 dbname=yourdb user=youruser password=yourpassword"

uv run app.py
```

### Docker based installation

[https://hub.docker.com/repository/docker/rioriost/watchage/](https://hub.docker.com/repository/docker/rioriost/watchage/)

```bash
docker pull rioriost/watchage:latest
docker run -d -p 5050:5000 \
  -e PG_CONNECTION_STRING="host=localhost port=5432 dbname=yourdb user=youruser password=yourpassword" \
  rioriost/watchage:latest
```

## Usage

Open your browser and navigate to [URL](http://127.0.0.1:5000) or [URL with specified port number](http://127.0.0.1:5050) when running the container.

![Connect](https://raw.githubusercontent.com/rioriost/watchage/main/images/01_connect.png)
![Connected](https://raw.githubusercontent.com/rioriost/watchage/main/images/02_connected.png)
![Query](https://raw.githubusercontent.com/rioriost/watchage/main/images/03_queried.png)
![Select a node](https://raw.githubusercontent.com/rioriost/watchage/main/images/04_selected.png)
![Table view](https://raw.githubusercontent.com/rioriost/watchage/main/images/05_table.png)
![JSON view](https://raw.githubusercontent.com/rioriost/watchage/main/images/06_json.png)

## Release Notes

### 0.1.0 Release
* Initial release.
* Still using Werkzeug.

## License
MIT License

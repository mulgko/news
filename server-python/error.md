internal
load build definition from Dockerfile
0ms

internal
load metadata for ghcr.io/railwayapp/nixpacks:ubuntu-1745885067
793ms

internal
load .dockerignore
0ms

stage-0
FROM ghcr.io/railwayapp/nixpacks:ubuntu-1745885067@sha256:d45c89d80e13d7ad0fd555b5130f22a866d9dd10e861f589932303ef2314c7de
8ms

internal
load build context
0ms

stage-0
WORKDIR /app/
192ms

stage-0
COPY .nixpacks/nixpkgs-bc8f8d1be58e8c8383e683a06e1e1e57893fff87.nix .nixpacks/nixpkgs-bc8f8d1be58e8c8383e683a06e1e1e57893fff87.nix
10ms

# [Region: us-west1]

# Using Nixpacks

context: 2pcq-T4SA
╔══════════════════════════════ Nixpacks v1.38.0 ══════════════════════════════╗
║ setup │ python3, postgresql_16.dev, gcc ║
║──────────────────────────────────────────────────────────────────────────────║
║ install │ python -m venv --copies /opt/venv && . /opt/venv/bin/activate ║
║ │ && pip install -r requirements.txt ║
║──────────────────────────────────────────────────────────────────────────────║
║ build │ npm run build ║
║──────────────────────────────────────────────────────────────────────────────║
║ start │ cd server-python && python main.py ║
╚══════════════════════════════════════════════════════════════════════════════╝

internal
load build definition from Dockerfile
0ms

internal
load .dockerignore
0ms

internal
load build context
0ms

stage-0
COPY .nixpacks/nixpkgs-bc8f8d1be58e8c8383e683a06e1e1e57893fff87.nix .nixpacks/nixpkgs-bc8f8d1be58e8c8383e683a06e1e1e57893fff87.nix
97ms

stage-0
RUN nix-env -if .nixpacks/nixpkgs-bc8f8d1be58e8c8383e683a06e1e1e57893fff87.nix && nix-collect-garbage -d
35s

22 store paths deleted, 242.42 MiB freed

stage-0
COPY . /app/.
771ms

stage-0
RUN python -m venv --copies /opt/venv && . /opt/venv/bin/activate && pip install -r requirements.txt
20s

Successfully installed Mako-1.3.10 MarkupSafe-3.0.3 aiofiles-25.1.0 alembic-1.17.2 annotated-doc-0.0.4 annotated-types-0.7.0 anyio-4.12.0 babel-2.17.0 beautifulsoup4-4.14.3 cachetools-6.2.4 certifi-2025.11.12 charset_normalizer-3.4.4 click-8.3.1 courlan-1.3.2 dateparser-1.2.2 fastapi-0.128.0 feedparser-6.0.12 google-ai-generativelanguage-0.6.15 google-api-core-2.28.1 google-api-python-client-2.187.0 google-auth-2.45.0 google-auth-httplib2-0.3.0 google-generativeai-0.8.6 googleapis-common-protos-1.72.0 googlenewsdecoder-0.1.7 greenlet-3.3.0 grpcio-1.76.0 grpcio-status-1.71.2 h11-0.16.0 htmldate-1.9.4 httpcore-1.0.9 httplib2-0.31.0 httptools-0.7.1 httpx-0.28.1 idna-3.11 justext-3.0.2 lxml-6.0.2 lxml_html_clean-0.4.3 proto-plus-1.27.0 protobuf-5.29.5 psycopg2-binary-2.9.11 pyasn1-0.6.1 pyasn1-modules-0.4.2 pydantic-2.12.5 pydantic-core-2.41.5 pyparsing-3.3.1 pysocks-1.7.1 python-dateutil-2.9.0.post0 python-dotenv-1.2.1 python-multipart-0.0.21 pytz-2025.2 pyyaml-6.0.3 regex-2025.11.3 requests-2.32.5 rsa-4.9.1 selectolax-0.4.6 sgmllib3k-1.0.0 six-1.17.0 soupsieve-2.8.1 sqlalchemy-2.0.45 starlette-0.50.0 tld-0.13.1 tqdm-4.67.1 trafilatura-2.0.0 typing-extensions-4.15.0 typing-inspection-0.4.2 tzlocal-5.3.1 uritemplate-4.2.0 urllib3-2.6.2 uvicorn-0.40.0 uvloop-0.22.1 watchfiles-1.1.1 websockets-15.0.1

stage-0
COPY . /app/.
879ms

stage-0
RUN npm run build
122ms
/bin/bash: line 1: npm: command not found

## Dockerfile:24

22 | # build phase
23 | COPY . /app/.
24 | >>> RUN npm run build
25 |
26 |

---

ERROR: failed to build: failed to solve: process "/bin/bash -ol pipefail -c npm run build" did not complete successfully: exit code: 127
Error: Docker build failed

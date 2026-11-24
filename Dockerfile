FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY AGENTS.md CLAUDE.md GEMINI.md DATA_CONTRACT.md README.md ./
COPY config/ ./config/
COPY data/raw_docs/ ./data/raw_docs/
COPY data/sample/ ./data/sample/
COPY output/ ./output/
COPY scripts/ ./scripts/
COPY skills/ ./skills/
COPY src/ ./src/

RUN groupadd --system verigreen \
    && useradd --system --gid verigreen --create-home verigreen \
    && chown -R verigreen:verigreen /app

USER verigreen

CMD ["python", "src/dashboard.py"]

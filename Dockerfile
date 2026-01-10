FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        libmariadb-dev-compat \
        libmariadb-dev \
        libssl-dev \
        libffi-dev \
        python3-dev \
        pkg-config \
        netcat-openbsd \
        curl \
        # --- ปรับปรุงแพ็กเกจสำหรับ WeasyPrint ใน Debian Trixie/Testing ---
        shared-mime-info \
        libpango-1.0-0 \
        libharfbuzz0b \
        libpangoft2-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        fontconfig \
        fonts-thai-tlwg \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /code/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Build Tailwind CSS inside the image (theme static_src)
RUN if [ -d /code/theme/static_src ]; then \
            cd /code/theme/static_src && npm install --no-audit --no-fund && npm run build || true; \
        fi

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]

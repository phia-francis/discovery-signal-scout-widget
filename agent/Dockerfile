FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt && pip install .
COPY . /app
ENTRYPOINT ["signal-scout"]
CMD ["run","--config","/app/config.yaml"]

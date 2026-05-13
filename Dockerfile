ARG PYTHON_BASE_IMAGE=python:3.12-slim
FROM ${PYTHON_BASE_IMAGE}

WORKDIR /app

COPY pyproject.toml ./
COPY collectarr_sync ./collectarr_sync

RUN pip install --no-cache-dir .

EXPOSE 8020

CMD ["uvicorn", "collectarr_sync.main:app", "--host", "0.0.0.0", "--port", "8020"]

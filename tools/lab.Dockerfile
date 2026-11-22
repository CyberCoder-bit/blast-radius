# Lab image: a copy of the labeling environment (same base digest plus
# requirements.lock) for running sqlglot's tests and building maps. This is
# not the submission image. Build with `make lab`.
FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90

COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock

# The labels were made with executor tests enabled and sqlglot on PYTHONPATH
# (not pip-installed). The repo is mounted at /work by the Makefile.
ENV SKIP_INTEGRATION=0 \
    PYTHONPATH=/work/vendor/sqlglot \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/tmp
WORKDIR /work/vendor/sqlglot

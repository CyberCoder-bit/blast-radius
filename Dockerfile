# Submission image. The scorer builds this on linux/amd64 and runs it with no
# network, read-only, as user nobody. The digest is the image the organisers
# labeled every commit in: its Python and SQLite decide which sqlglot tests
# run, so keep it if this image ever runs sqlglot tests.
FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90

# The disk is read-only at run time: precompile here, never write .pyc later.
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY selector /app/selector
COPY maps /app/maps
RUN python -m compileall -q /app && chmod -R a+rX /app

# Keep in sync with SELECTOR_CMD in the Makefile.
CMD ["python", "-m", "selector"]

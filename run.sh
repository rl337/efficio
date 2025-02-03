
poetry run mypy . && \
    poetry run pytest  && \
    poetry run python -m efficio "$@"

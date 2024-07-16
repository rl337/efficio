
python3 -m poetry run mypy . && \
    python3 -m poetry run pytest  && \
    python3 -m poetry run python -m efficio "$@"

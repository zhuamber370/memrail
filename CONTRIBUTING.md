# Contributing

Thanks for contributing to `memrail`.

## Before opening a PR

1. Open an issue first for non-trivial changes.
2. Keep diffs small and focused.
3. Do not include secrets (`.env`, tokens, private keys).
4. Keep behavior docs in sync with code.
5. If tests insert data, clean test data before merge.

## Local checks

### Backend

```bash
python3 -m pytest -q
python3 backend/scripts/cleanup_test_data.py
```

### Frontend

```bash
cd frontend
npm run build
```

## PR expectations

1. Explain what changed and why.
2. List verification commands and actual results.
3. Include screenshots for UI changes.
4. Mention updated docs when behavior changed.

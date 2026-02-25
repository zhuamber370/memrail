# Contributing

Thanks for contributing to `memrail`.

## Before opening a PR

1. Open an issue first for non-trivial changes.
2. Keep diffs small and focused.
3. Do not include secrets (`.env`, tokens, private keys).
4. Keep docs in sync with behavior changes.

## Local checks

### Backend

```bash
python3 -m pytest backend/tests/test_changes_api.py -q
```

### Frontend

```bash
cd frontend
npm run build
```

## PR expectations

1. Explain what changed and why.
2. List verification commands and results.
3. Include screenshots for UI changes.

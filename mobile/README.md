# Telomy mobile (Expo SDK 57)

One app, three roles (member · doctor · centre owner). See the root [README](../README.md) and [docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md).

```bash
npm install
npx expo start          # press i for the iOS Simulator
npx tsc --noEmit        # type-check
```

- Routes: `src/app` (expo-router). Member tabs in `(tabs)/`, doctor in `doctor/`, centre in `centre/`.
- Components: `src/ui`; tokens and fonts: `src/lib/theme.ts`; API client: `src/lib/api.ts`.
- API base URL: `EXPO_PUBLIC_API_URL`, else the Metro host IP on port 8787.
- Expo APIs change every SDK — read `AGENTS.md` and the versioned docs before using one.

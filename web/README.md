# Web Client

The P5.4b product frontend is a React and TypeScript client for the local Capability Runner demo
composition. It renders only backend-owned capability, run, evidence, and intervention state.

```powershell
npm install
npm run dev
```

Vite proxies `/api` to the local product server on port 5000. See
`docs/ui/frontend-implementation.md` for the data boundary and route contract.
/**
 * P26 Gateway Server — OpenClaw API Bridge
 * Listens on :18789, routes POST /api/search to Smart Classroom :8000
 */

import { createServer } from 'node:http';
import { handleSearch } from './routes/search.js';

const PORT = Number(process.env.GATEWAY_PORT) || 18789;

const server = createServer(async (req, res) => {
  const url = req.url || '/';

  if (url === '/health' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', service: 'namo-gateway', port: PORT }));
    return;
  }

  if (url === '/api/search' && req.method === 'POST') {
    await handleSearch(req, res);
    return;
  }

  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not found', path: url }));
});

server.listen(PORT, () => {
  console.log(`[namo-gateway] Listening on http://localhost:${PORT}`);
  console.log(`[namo-gateway] POST /api/search → Smart Classroom :8000`);
});

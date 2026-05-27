// api/proxy.js — Vercel Serverless Function
// Proxies IPTV API requests to bypass browser CORS restrictions
// Deploy to Vercel: vercel deploy

export default async function handler(req, res) {
  // Allow all origins (CORS headers)
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Cookie');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  // Get the target URL from query param
  const targetUrl = req.query.url;
  if (!targetUrl) {
    return res.status(400).json({ error: 'Missing ?url= parameter' });
  }

  // Security: only allow http/https
  try {
    const parsed = new URL(targetUrl);
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      return res.status(400).json({ error: 'Only http/https URLs allowed' });
    }
  } catch (e) {
    return res.status(400).json({ error: 'Invalid URL' });
  }

  // Forward headers from client (MAC portal needs Cookie/UA)
  const forwardHeaders = {
    'User-Agent': req.headers['x-forward-ua'] || 
      'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3',
    'Accept': '*/*',
  };
  if (req.headers['x-forward-cookie']) {
    forwardHeaders['Cookie'] = req.headers['x-forward-cookie'];
  }
  if (req.headers['x-forward-auth']) {
    forwardHeaders['Authorization'] = req.headers['x-forward-auth'];
  }
  if (req.headers['x-requested-with']) {
    forwardHeaders['X-Requested-With'] = req.headers['x-requested-with'];
  }

  try {
    const response = await fetch(targetUrl, {
      method: req.method === 'POST' ? 'POST' : 'GET',
      headers: forwardHeaders,
      body: req.method === 'POST' ? req.body : undefined,
      // 30 second timeout
      signal: AbortSignal.timeout(30000),
    });

    const contentType = response.headers.get('content-type') || 'application/octet-stream';
    
    // Stream the response back
    const body = await response.arrayBuffer();
    
    res.status(response.status);
    res.setHeader('Content-Type', contentType);
    res.setHeader('X-Proxied-Status', response.status);
    
    return res.send(Buffer.from(body));

  } catch (err) {
    console.error('Proxy error:', err);
    if (err.name === 'TimeoutError') {
      return res.status(504).json({ error: 'Target server timed out' });
    }
    return res.status(502).json({ error: 'Failed to fetch: ' + err.message });
  }
}

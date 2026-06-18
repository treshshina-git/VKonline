import express from 'express';
import morgan from 'morgan';

const app = express();
app.use(morgan('dev'));

app.get('/play', (req, res) => {
  const urik = String(req.query.urik || '');
  const safeUrik = urik.replace(/[^a-zA-Z0-9_\-\.]/g, '');
  const url = safeUrik ? `https://live.vkvideo.ru/${safeUrik}` : 'https://live.vkvideo.ru/';

  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.end(`<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>VK Live</title>
  <style>
    body { margin: 0; background: #000; font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; }
    .wrap { width: 100vw; height: 100vh; }
    iframe { width: 100%; height: 100%; border: 0; }
    .fallback { color: #fff; padding: 16px; }
  </style>
</head>
<body>
  <div class="wrap">
    <iframe 
      src="${url}" 
      allow="autoplay; fullscreen; picture-in-picture" 
      allowfullscreen>
    </iframe>
  </div>
  <div class="fallback" style="display:none">
    Видео: <a href="${url}" target="_blank" rel="noopener noreferrer" style="color:#4da3ff">${url}</a>
  </div>
</body>
</html>`);
});

app.listen(3000, () => {
  // eslint-disable-next-line no-console
  console.log('webapp listening on http://localhost:3000');
});


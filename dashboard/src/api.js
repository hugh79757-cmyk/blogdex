import axios from 'axios';

const apiKey = import.meta.env.VITE_BLOGDEX_API_KEY;

if (!apiKey) {
  console.warn(
    'VITE_BLOGDEX_API_KEY is not set. Create dashboard/.env with:\n' +
    'VITE_BLOGDEX_API_KEY=your_key_here'
  );
}

const api = axios.create({
  baseURL: 'https://blogdex-api.hugh79757.workers.dev',
  headers: { 'X-API-Key': apiKey }
});

export default api;


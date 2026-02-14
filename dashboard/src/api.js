import axios from 'axios';

const api = axios.create({
  baseURL: 'https://blogdex-api.hugh79757.workers.dev',
  headers: { 'X-API-Key': 'blogdex-secret-key' }
});

export default api;


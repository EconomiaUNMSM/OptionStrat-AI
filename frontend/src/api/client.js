import axios from 'axios';

// Instancia global pre-configurada hacia nuestro FastAPI
const api = axios.create({
    baseURL: 'http://127.0.0.1:8000/api',
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
});

export default api;

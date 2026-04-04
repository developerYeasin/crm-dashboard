import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// Global error handler
window.addEventListener('error', (event) => {
  console.error(event.error || event.message);
});

window.addEventListener('unhandledrejection', (event) => {
  console.error(event.reason);
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

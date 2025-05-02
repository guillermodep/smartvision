const express = require('express');
const path = require('path');
const app = express();
const PORT = process.env.PORT || 5000;

// Servir archivos estáticos
app.use(express.static(path.join(__dirname, 'templates')));

// Ruta principal
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'templates', 'index.html'));
});

// API endpoint para simular la extracción de texto
app.post('/extract-text', express.json(), (req, res) => {
  // En un entorno real, aquí se conectaría con la API de Azure
  // Para el despliegue en Netlify, devolvemos una respuesta simulada
  res.json({
    status: 'succeeded',
    results: [
      {
        text: "Este es un texto de ejemplo extraído de la imagen.",
        confidence: 0.95
      },
      {
        text: "Smart Vision ha detectado este contenido.",
        confidence: 0.92
      }
    ]
  });
});

// Iniciar el servidor
app.listen(PORT, () => {
  console.log(`Servidor ejecutándose en http://localhost:${PORT}`);
});

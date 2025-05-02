// Función serverless para manejar la extracción de texto en Netlify
const serverless = require('serverless-http');
const express = require('express');
const cors = require('cors');
const multer = require('multer');
const app = express();

// Configurar CORS
app.use(cors());

// Configurar multer para manejar la carga de archivos
const storage = multer.memoryStorage();
const upload = multer({ storage: storage });

// Endpoint para extraer texto de imágenes
app.post('/extract-text', upload.single('image'), (req, res) => {
  // En un entorno real, aquí se conectaría con la API de Azure
  // Para el despliegue en Netlify, devolvemos una respuesta simulada
  
  // Simular un pequeño retraso para que parezca que está procesando
  setTimeout(() => {
    // Devolver resultados de ejemplo
    res.json({
      status: 'succeeded',
      results: [
        {
          text: "JUCAY",
          confidence: 0.95
        },
        {
          text: "RESJUCAY CIA. LTDA.",
          confidence: 0.92
        },
        {
          text: "RUC: 1792996015001",
          confidence: 0.98
        },
        {
          text: "AMAZONAS N33B-147 Y ARIZAGA",
          confidence: 0.94
        },
        {
          text: "Teléfono: 2244177",
          confidence: 0.93
        },
        {
          text: "CONTRIBUYENTE REGIMEN MICROEMPRESAS",
          confidence: 0.91
        },
        {
          text: "CLAVE DE ACCESO",
          confidence: 0.97
        },
        {
          text: "30042025011792996015001200100100005862912345678",
          confidence: 0.89
        },
        {
          text: "COMPROBANTE DE FACTURA:001-001-000058629",
          confidence: 0.96
        },
        {
          text: "MESERO: ERIKA       MESA: 14",
          confidence: 0.93
        },
        {
          text: "FECHA: 30/4/2025    HORA: 13:57:42",
          confidence: 0.95
        },
        {
          text: "CLIENTE: JOSE MIGUEL GRANDA",
          confidence: 0.94
        }
      ]
    });
  }, 1500);
});

// Ruta por defecto
app.get('/', (req, res) => {
  res.json({ message: 'API de Smart Vision funcionando correctamente' });
});

// Exportar la aplicación envuelta en serverless
module.exports.handler = serverless(app);

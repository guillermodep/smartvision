// Función serverless para manejar la extracción de texto en Netlify
const serverless = require('serverless-http');
const express = require('express');
const cors = require('cors');
const multer = require('multer');
const axios = require('axios');
const FormData = require('form-data');
const app = express();

// Configurar CORS
app.use(cors());

// Configurar multer para manejar la carga de archivos
const storage = multer.memoryStorage();
const upload = multer({ storage: storage });

// Endpoint para verificar el estado de inicialización
app.get('/check-init', (req, res) => {
  // Verificar si las variables de entorno están configuradas
  const endpoint = process.env.AZURE_COMPUTER_VISION_ENDPOINT;
  const key = process.env.AZURE_COMPUTER_VISION_KEY;
  
  res.json({
    initialized: !!(endpoint && key),
    endpoint: endpoint ? endpoint.substring(0, 10) + '...' : 'No configurado',
    key: key ? key.substring(0, 5) + '...' : 'No configurado'
  });
});

// Endpoint para extraer texto de imágenes
app.post('/extract-text', upload.single('image'), async (req, res) => {
  try {
    // Verificar si tenemos las credenciales necesarias
    const endpoint = process.env.AZURE_COMPUTER_VISION_ENDPOINT;
    const key = process.env.AZURE_COMPUTER_VISION_KEY;
    
    if (!endpoint || !key) {
      return res.status(400).json({
        error: "Cliente de Smart Vision no está inicializado. Verifica las credenciales en las variables de entorno."
      });
    }
    
    // Verificar si tenemos una imagen
    if (!req.file) {
      return res.status(400).json({
        error: "No se ha subido ninguna imagen"
      });
    }
    
    console.log("Procesando imagen...");
    
    // Preparar la URL para la API de Azure
    const url = `${endpoint}vision/v3.2/read/analyze`;
    
    // Hacer la solicitud a la API de Azure
    const response = await axios.post(url, req.file.buffer, {
      headers: {
        'Ocp-Apim-Subscription-Key': key,
        'Content-Type': 'application/octet-stream'
      }
    });
    
    // Verificar si la solicitud fue exitosa
    if (response.status !== 202) {
      console.error("Error al iniciar el análisis:", response.status, response.data);
      return res.status(response.status).json({
        error: `Error al iniciar el análisis: ${response.statusText}`
      });
    }
    
    // Obtener la URL de operación del encabezado de respuesta
    const operationLocation = response.headers['operation-location'];
    console.log("Operation Location:", operationLocation);
    
    // Esperar a que se complete el procesamiento
    let result = null;
    let retries = 0;
    const maxRetries = 10;
    
    while (retries < maxRetries) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Consultar el estado de la operación
      const statusResponse = await axios.get(operationLocation, {
        headers: {
          'Ocp-Apim-Subscription-Key': key
        }
      });
      
      if (statusResponse.status !== 200) {
        console.error("Error al obtener resultados:", statusResponse.status, statusResponse.data);
        return res.status(statusResponse.status).json({
          error: `Error al obtener resultados: ${statusResponse.statusText}`
        });
      }
      
      result = statusResponse.data;
      
      // Verificar si el procesamiento ha terminado
      if (result.status !== "notStarted" && result.status !== "running") {
        break;
      }
      
      retries++;
      console.log(`Análisis en progreso... Intento ${retries}/${maxRetries}`);
    }
    
    // Extraer texto de los resultados
    const textResults = [];
    
    if (result.status === "succeeded") {
      if (result.analyzeResult && result.analyzeResult.readResults) {
        for (const page of result.analyzeResult.readResults) {
          for (const line of page.lines) {
            textResults.push({
              text: line.text,
              bounding_box: line.boundingBox,
              confidence: 0.9 // La API v3.2 no proporciona confianza por línea
            });
          }
        }
      }
    }
    
    // Devolver los resultados
    res.json({
      status: result.status,
      results: textResults
    });
  } catch (error) {
    console.error("Error al procesar la imagen:", error);
    res.status(500).json({
      error: error.message || "Error al procesar la imagen"
    });
  }
});

// Ruta por defecto
app.get('/', (req, res) => {
  res.json({ message: 'API de Smart Vision funcionando correctamente' });
});

// Exportar la aplicación envuelta en serverless
module.exports.handler = serverless(app);

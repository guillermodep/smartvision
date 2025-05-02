// Función serverless para manejar la autenticación en Netlify
const serverless = require('serverless-http');
const express = require('express');
const cors = require('cors');
const app = express();

// Configurar CORS
app.use(cors());
app.use(express.json());

// Credenciales válidas
const VALID_USERNAME = "admin";
const VALID_PASSWORD = "smartsolutions";

// Endpoint para verificar las credenciales
app.post('/login', (req, res) => {
  console.log("Recibida solicitud de login:", req.body);
  const { username, password } = req.body;
  
  if (username === VALID_USERNAME && password === VALID_PASSWORD) {
    console.log("Autenticación exitosa para:", username);
    res.json({
      success: true,
      message: 'Autenticación exitosa',
      user: {
        username: username
      }
    });
  } else {
    console.log("Autenticación fallida para:", username);
    res.status(401).json({
      success: false,
      message: 'Credenciales inválidas. Por favor, inténtalo de nuevo.'
    });
  }
});

// Endpoint para verificar el token
app.post('/verify', (req, res) => {
  const { token } = req.body;
  
  // En una implementación real, verificaríamos el token
  // Para este ejemplo, simplemente verificamos que exista
  if (token) {
    res.json({
      success: true,
      message: 'Token válido'
    });
  } else {
    res.status(401).json({
      success: false,
      message: 'Token inválido o expirado'
    });
  }
});

// Ruta por defecto para pruebas
app.get('/', (req, res) => {
  res.json({
    message: 'Servicio de autenticación funcionando correctamente'
  });
});

// Exportar la aplicación envuelta en serverless
module.exports.handler = serverless(app);

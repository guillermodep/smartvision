// Este archivo es necesario para desplegar la aplicación en Netlify
// Netlify Functions para redirigir las solicitudes a nuestra API Flask

const serverless = require('serverless-http');
const express = require('express');
const app = express();

// Configurar Express para manejar las solicitudes
app.all('*', (req, res) => {
  res.status(200).send('API funcionando correctamente');
});

// Exportar la aplicación envuelta en serverless
module.exports.handler = serverless(app);

// Función serverless para manejar la extracción de texto en Netlify usando Azure OpenAI
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
  const endpoint = process.env.AZURE_OPENAI_ENDPOINT;
  const key = process.env.AZURE_OPENAI_API_KEY;
  
  res.json({
    initialized: !!(endpoint && key),
    message: "Sistema listo para procesar imágenes con Azure OpenAI"
  });
});

// Endpoint para extraer texto de imágenes usando Azure OpenAI
app.post('/extract-text', upload.single('file'), async (req, res) => {
  try {
    // Verificar si tenemos las credenciales necesarias
    const endpoint = process.env.AZURE_OPENAI_ENDPOINT;
    const key = process.env.AZURE_OPENAI_API_KEY;
    const deployment = process.env.AZURE_OPENAI_DEPLOYMENT || 'gpt-4o-mini';
    const apiVersion = process.env.AZURE_OPENAI_API_VERSION || '2025-01-01-preview';
    
    if (!endpoint || !key) {
      return res.status(400).json({
        error: "Cliente de Azure OpenAI no está inicializado. Verifica las credenciales en las variables de entorno."
      });
    }
    
    // Verificar si tenemos una imagen
    if (!req.file) {
      return res.status(400).json({
        error: "No se ha subido ninguna imagen"
      });
    }
    
    console.log("Procesando imagen con Azure OpenAI...");
    
    // Convertir la imagen a base64
    const imageBase64 = req.file.buffer.toString('base64');
    
    // Preparar la URL para la API de Azure OpenAI
    const url = `${endpoint}openai/deployments/${deployment}/chat/completions?api-version=${apiVersion}`;
    
    // Construir el mensaje con la imagen
    const payload = {
      "messages": [
        {
          "role": "system", 
          "content": "Eres un asistente especializado en extraer texto de imágenes. Extrae todo el texto visible en la imagen, incluyendo números de factura, fechas, importes y cualquier otra información relevante. Organiza la información de manera clara y estructurada."
        },
        {
          "role": "user", 
          "content": [
            {"type": "text", "text": "Extrae todo el texto de esta imagen, prestando especial atención a los números de factura, recibos o tickets."},
            {"type": "image_url", "image_url": {"url": `data:image/jpeg;base64,${imageBase64}`}}
          ]
        }
      ],
      "temperature": 0.0,
      "max_tokens": 4000
    };
    
    // Hacer la solicitud a la API de Azure OpenAI
    const response = await axios.post(url, payload, {
      headers: {
        'Content-Type': 'application/json',
        'api-key': key
      }
    });
    
    // Verificar si la solicitud fue exitosa
    if (response.status !== 200) {
      console.error("Error al procesar la imagen con OpenAI:", response.status, response.data);
      return res.status(response.status).json({
        error: `Error al procesar la imagen: ${response.statusText}`
      });
    }
    
    // Extraer la respuesta del modelo
    const responseData = response.data;
    
    if ('choices' in responseData && responseData.choices.length > 0) {
      const extractedText = responseData.choices[0].message.content;
      console.log("Texto extraído correctamente");
      
      // Extraer números de factura del texto
      const invoiceNumbers = extractInvoiceNumbers(extractedText);
      
      // Devolver los resultados
      return res.json({
        success: true,
        full_text: extractedText,
        invoice_numbers: invoiceNumbers
      });
    } else {
      console.error("No se pudo extraer texto de la respuesta");
      return res.status(500).json({
        success: false,
        error: "No se pudo extraer texto de la respuesta",
        raw_response: responseData
      });
    }
  } catch (error) {
    console.error("Error al procesar la imagen:", error);
    res.status(500).json({
      success: false,
      error: error.message || "Error al procesar la imagen"
    });
  }
});

// Función para extraer números de factura del texto
function extractInvoiceNumbers(text) {
  const invoiceNumbers = [];
  
  // Patrones para buscar números de factura o recibo
  const patterns = [
    /(?:factura|fra|ticket|recibo)[\s:.#-]*(?:n[o°º]?[.:]*)?(\s*[A-Z0-9][-A-Z0-9-]{2,20})/i,
    /(?:n[o°º][.:]*|numero|número)\s*(?:de)?\s*(?:factura|fra|ticket|recibo)[\s:.#-]*([A-Z0-9][-A-Z0-9-]{2,20})/i,
    /invoice\s*(?:no\.?|number|num|#)[\s:.#-]*([A-Z0-9][-A-Z0-9-]{2,20})/i,
    /receipt\s*#[\s:]*([0-9]+)/i,
    /receipt[\s:]*#?[\s:]*([0-9]+)/i,
    /receipt[\s:#]*([0-9]+)/i,
    /#[\s:]*([0-9]+)/i
  ];
  
  // Buscar todos los patrones en el texto
  for (const pattern of patterns) {
    const matches = text.matchAll(new RegExp(pattern, 'g'));
    for (const match of matches) {
      const invoiceNumber = match[1].trim();
      // Verificar si es un número de factura válido
      if (isValidInvoiceNumber(invoiceNumber)) {
        // Añadir a la lista si no está ya
        if (!invoiceNumbers.some(inv => inv.invoice_number === invoiceNumber)) {
          invoiceNumbers.push({
            invoice_number: invoiceNumber,
            confidence: 0.9  // Alta confianza ya que viene de GPT-4o
          });
        }
      }
    }
  }
  
  // Buscar también en líneas que contienen palabras clave
  const keywords = ['factura', 'invoice', 'receipt', 'ticket', 'recibo', 'número', 'number'];
  const lines = text.split('\n');
  
  for (const line of lines) {
    const lowerLine = line.toLowerCase().trim();
    if (keywords.some(keyword => lowerLine.includes(keyword))) {
      // Buscar números en la línea
      const numberMatches = lowerLine.match(/\b([A-Z0-9][-A-Z0-9]{2,20})\b|\b(\d{4,10})\b/gi);
      if (numberMatches) {
        for (const match of numberMatches) {
          const invoiceNumber = match.trim();
          if (isValidInvoiceNumber(invoiceNumber)) {
            if (!invoiceNumbers.some(inv => inv.invoice_number === invoiceNumber)) {
              invoiceNumbers.push({
                invoice_number: invoiceNumber,
                confidence: 0.85
              });
            }
          }
        }
      }
    }
  }
  
  return invoiceNumbers;
}

// Función para verificar si un texto es un número de factura válido
function isValidInvoiceNumber(text) {
  // Debe tener al menos un dígito
  if (!/\d/.test(text)) {
    return false;
  }
  
  // Debe tener una longitud razonable (ni muy corta ni muy larga)
  if (text.length < 2 || text.length > 30) {
    return false;
  }
  
  // Evitar palabras comunes que no son números de factura
  const commonWords = ['total', 'subtotal', 'iva', 'tax', 'amount', 'precio', 'date', 'fecha', 
                    'customer', 'cliente', 'address', 'direccion', 'telefono', 'phone',
                    'email', 'web', 'http', 'www', 'com', 'net', 'org', 'es'];
  
  if (commonWords.includes(text.toLowerCase())) {
    return false;
  }
  
  return true;
}

// Ruta por defecto
app.get('/', (req, res) => {
  res.json({ message: 'API de Smart Vision funcionando correctamente' });
});

// Exportar la aplicación envuelta en serverless
module.exports.handler = serverless(app);

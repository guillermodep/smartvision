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
    
    console.log("Variables de entorno:", {
      endpoint: endpoint ? "Configurado" : "No configurado",
      key: key ? "Configurado" : "No configurado",
      deployment,
      apiVersion
    });
    
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
    console.log("Tamaño de la imagen:", req.file.size, "bytes");
    
    // Comprobar si la imagen es demasiado grande (más de 20MB)
    if (req.file.size > 20 * 1024 * 1024) {
      return res.status(400).json({
        success: false,
        error: "La imagen es demasiado grande. El tamaño máximo permitido es 20MB."
      });
    }
    
    // Convertir la imagen a base64
    const imageBase64 = req.file.buffer.toString('base64');
    
    // Verificar el tamaño de la imagen en base64
    console.log("Tamaño de la imagen en base64:", imageBase64.length, "caracteres");
    
    // Si la imagen es muy grande, intentar comprimirla o rechazarla
    if (imageBase64.length > 10000000) { // Más de 10MB en base64
      return res.status(400).json({
        success: false,
        error: "La imagen es demasiado grande para ser procesada. Por favor, utiliza una imagen más pequeña o de menor resolución."
      });
    }
    
    // Preparar la URL para la API de Azure OpenAI
    const url = `${endpoint}openai/deployments/${deployment}/chat/completions?api-version=${apiVersion}`;
    
    // Determinar si la imagen es un ticket o una factura basado en el nombre del archivo o tamaño
    const isTicket = req.file.originalname ? 
                    (req.file.originalname.toLowerCase().includes('ticket') || 
                     req.file.originalname.toLowerCase().includes('recibo') ||
                     req.file.size < 500000) : // Menos de 500KB probablemente es un ticket
                    false;
    
    // Construir el mensaje con la imagen - optimizado según el tipo de documento
    const payload = {
      "messages": [
        {
          "role": "system", 
          "content": isTicket ?
            "Eres un asistente especializado en extraer texto de tickets y recibos simples. Extrae solo el texto visible, especialmente números de recibo, fechas e importes. Sé muy conciso." :
            "Eres un asistente especializado en extraer texto de facturas. Extrae todo el texto visible, especialmente números de factura, fechas e importes. Responde de forma clara y estructurada."
        },
        {
          "role": "user", 
          "content": [
            {"type": "text", "text": isTicket ?
              "Extrae el texto básico de este ticket o recibo. Busca especialmente el número de recibo o ticket." :
              "Extrae el texto de esta factura. Presta especial atención a los números de factura."
            },
            {"type": "image_url", "image_url": {"url": `data:image/jpeg;base64,${imageBase64}`}}
          ]
        }
      ],
      "temperature": 0.0,
      "max_tokens": isTicket ? 1000 : 2000  // Reducido aún más para tickets
    };
    
    console.log("Tipo de documento detectado:", isTicket ? "Ticket/Recibo" : "Factura");
    
    console.log("Enviando solicitud a Azure OpenAI...");
    
    // Hacer la solicitud a la API de Azure OpenAI con timeout
    const response = await axios.post(url, payload, {
      headers: {
        'Content-Type': 'application/json',
        'api-key': key
      },
      timeout: 25000  // 25 segundos de timeout
    });
    
    console.log("Respuesta recibida de Azure OpenAI");
    
    // Verificar si la solicitud fue exitosa
    if (response.status !== 200) {
      console.error("Error al procesar la imagen con OpenAI:", response.status, response.data);
      return res.status(response.status).json({
        success: false,
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
      console.log("Números de factura encontrados:", invoiceNumbers.length);
      
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
    console.error("Error al procesar la imagen:", error.message);
    console.error("Stack trace:", error.stack);
    
    // Mensaje de error más amigable y detallado
    let errorMessage = "Error al procesar la imagen";
    let errorDetails = {};
    
    // Capturar información sobre el archivo
    if (req.file) {
      errorDetails.fileName = req.file.originalname || 'unknown';
      errorDetails.fileSize = req.file.size || 'unknown';
      errorDetails.mimeType = req.file.mimetype || 'unknown';
    }
    
    // Determinar el tipo de error
    if (error.code === 'ECONNABORTED') {
      errorMessage = "La solicitud ha tardado demasiado tiempo. Intenta con una imagen más pequeña o de menor resolución.";
      errorDetails.timeoutError = true;
    } else if (error.response) {
      errorMessage = `Error del servidor: ${error.response.status} - ${error.response.statusText}`;
      errorDetails.serverResponse = {
        status: error.response.status,
        statusText: error.response.statusText,
        data: error.response.data
      };
    } else if (error.request) {
      errorMessage = "No se pudo conectar con el servidor de Azure OpenAI. Verifica la configuración y tu conexión a internet.";
      errorDetails.noResponse = true;
    } else if (error.message.includes('getaddrinfo')) {
      errorMessage = "No se pudo resolver el nombre del servidor de Azure OpenAI. Verifica que las variables de entorno estén configuradas correctamente.";
      errorDetails.dnsError = true;
    } else if (error.message.includes('413')) {
      errorMessage = "La imagen es demasiado grande para ser procesada. Utiliza una imagen más pequeña.";
      errorDetails.payloadTooLarge = true;
    }
    
    // Incluir sugerencias para resolver el problema
    errorDetails.suggestions = [
      "Utiliza una imagen más pequeña o de menor resolución",
      "Asegúrate de que la imagen sea clara y legible",
      "Verifica que las credenciales de Azure OpenAI estén configuradas correctamente",
      "Intenta con un ticket o factura más simple"
    ];
    
    // Enviar respuesta de error detallada
    res.status(500).json({
      success: false,
      error: errorMessage,
      details: errorDetails,
      message: error.message
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

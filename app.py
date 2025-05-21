import os
import io
import time
import requests
import json
import re
import uuid
import base64
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file
from dotenv import load_dotenv
from PIL import Image

# Cargar variables de entorno
load_dotenv()

# Obtener la ruta del directorio actual
current_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, 
            static_folder=os.path.join(current_dir, 'static'),  # Carpeta de archivos estáticos
            static_url_path='/static')         # URL path para archivos estáticos
app.secret_key = os.urandom(24)  # Clave secreta para las sesiones

# Configuración de Azure OpenAI desde variables de entorno
OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
OPENAI_DEPLOYMENT = os.getenv('AZURE_OPENAI_DEPLOYMENT')
OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION')

# Credenciales de usuario
VALID_USERNAME = "admin"
VALID_PASSWORD = "smartsolutions"

# Imprimir información de depuración
print("OpenAI Endpoint:", OPENAI_ENDPOINT)
print("OpenAI Key (primeros 5 caracteres):", OPENAI_API_KEY[:5] if OPENAI_API_KEY else "None")

def process_image_with_openai(image_bytes):
    """Procesa una imagen directamente con Azure OpenAI GPT-4o-mini"""
    try:
        # Convertir la imagen a base64
        image_base64 = base64.b64encode(image_bytes.getvalue()).decode('utf-8')
        
        # Configurar la solicitud a la API de Azure OpenAI
        url = f"{OPENAI_ENDPOINT}openai/deployments/{OPENAI_DEPLOYMENT}/chat/completions?api-version={OPENAI_API_VERSION}"
        headers = {
            "Content-Type": "application/json",
            "api-key": OPENAI_API_KEY
        }
        
        # Construir el mensaje con la imagen
        payload = {
            "messages": [
                {
                    "role": "system", 
                    "content": "Eres un asistente especializado en extraer texto de imágenes. Extrae todo el texto visible en la imagen, incluyendo números de factura, fechas, importes y cualquier otra información relevante. Organiza la información de manera clara y estructurada."
                },
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": "Extrae todo el texto de esta imagen, prestando especial atención a los números de factura, recibos o tickets."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                }
            ],
            "temperature": 0.0,
            "max_tokens": 4000
        }
        
        # Realizar la solicitud a la API
        print("Enviando imagen a Azure OpenAI...")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Lanzar excepción si hay error HTTP
        
        response_data = response.json()
        
        # Extraer la respuesta del modelo
        if 'choices' in response_data and len(response_data['choices']) > 0:
            extracted_text = response_data['choices'][0]['message']['content']
            print("Texto extraído correctamente")
            return {
                "success": True,
                "extracted_text": extracted_text,
                "raw_response": response_data
            }
        else:
            print("No se pudo extraer texto de la respuesta")
            return {
                "success": False,
                "error": "No se pudo extraer texto de la respuesta",
                "raw_response": response_data
            }
            
    except Exception as e:
        print(f"Error al procesar la imagen: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def extract_invoice_numbers_from_text(text):
    """Extrae números de factura del texto procesado por Azure OpenAI"""
    invoice_numbers = []
    
    # Patrones para buscar números de factura o recibo
    patterns = [
        r'(?i)(?:factura|fra|ticket|recibo)[\s:.#-]*(?:n[o°º]?[.:]*)?\s*([A-Z0-9][-A-Z0-9-]{2,20})',
        r'(?i)(?:n[o°º][.:]*|numero|número)\s*(?:de)?\s*(?:factura|fra|ticket|recibo)[\s:.#-]*([A-Z0-9][-A-Z0-9-]{2,20})',
        r'(?i)invoice\s*(?:no\.?|number|num|#)[\s:.#-]*([A-Z0-9][-A-Z0-9-]{2,20})',
        r'(?i)receipt\s*#[\s:]*([0-9]+)',
        r'(?i)receipt[\s:]*#?[\s:]*([0-9]+)',
        r'(?i)receipt[\s:#]*([0-9]+)',
        r'(?i)#[\s:]*([0-9]+)'
    ]
    
    import re
    
    # Buscar todos los patrones en el texto
    for pattern in patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            invoice_number = match.group(1).strip()
            # Verificar si es un número de factura válido
            if is_valid_invoice_number(invoice_number):
                # Añadir a la lista si no está ya
                if not any(inv['invoice_number'] == invoice_number for inv in invoice_numbers):
                    invoice_numbers.append({
                        'invoice_number': invoice_number,
                        'confidence': 0.9  # Alta confianza ya que viene de GPT-4o
                    })
    
    # Buscar también en líneas que contienen palabras clave
    keywords = ['factura', 'invoice', 'receipt', 'ticket', 'recibo', 'número', 'number']
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip().lower()
        if any(keyword in line for keyword in keywords):
            # Buscar números en la línea
            number_matches = re.finditer(r'\b([A-Z0-9][-A-Z0-9]{2,20})\b|\b(\d{4,10})\b', line, re.IGNORECASE)
            for match in number_matches:
                invoice_number = match.group(0).strip()
                if is_valid_invoice_number(invoice_number):
                    if not any(inv['invoice_number'] == invoice_number for inv in invoice_numbers):
                        invoice_numbers.append({
                            'invoice_number': invoice_number,
                            'confidence': 0.85
                        })
    
    return invoice_numbers

def is_valid_invoice_number(text):
    """Verifica si un texto es un número de factura válido"""
    # Debe tener al menos un dígito
    if not re.search(r'\d', text):
        return False
    
    # Debe tener una longitud razonable (ni muy corta ni muy larga)
    if len(text) < 2 or len(text) > 30:
        return False
    
    # Evitar palabras comunes que no son números de factura
    common_words = ['total', 'subtotal', 'iva', 'tax', 'amount', 'precio', 'date', 'fecha', 
                    'customer', 'cliente', 'address', 'direccion', 'telefono', 'phone',
                    'email', 'web', 'http', 'www', 'com', 'net', 'org', 'es', 'ber', 'ncisco', 'relates']
    
    if text.lower() in common_words:
        return False
    
    return True

print("Sistema configurado para usar Azure OpenAI GPT-4o-mini para procesar imágenes")

# Decorador para requerir autenticación
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def interpret_ticket_data(text_results):
    """Interpreta y clasifica los datos extraídos de un ticket o factura,
    enfocándose en identificar el número de factura"""
    interpreted_results = []
    invoice_number_results = []
    
    import re
    
    # Patrones específicos para números de factura con validación más estricta
    invoice_patterns = [
        # Patrones para facturas en español
        r"(?i)(?:factura|fra|ticket|recibo)[\s:.#-]*(?:n[o°º]?[.:]*)?\s*([A-Z0-9][-A-Z0-9-]{2,20})",  # Factura: A12345 o Factura Nº: F12345
        r"(?i)(?:n[o°º][.:]*|numero|número)\s*(?:de)?\s*(?:factura|fra|ticket|recibo)[\s:.#-]*([A-Z0-9][-A-Z0-9-]{2,20})",  # Nº Factura: F-12345
        
        # Patrones específicos para 'Invoice', 'Invoice number', 'Invoice #'
        r"(?i)\binvoice\b[\s:.#-]*([A-Z0-9][-A-Z0-9-]{2,20})",  # Invoice: 12345
        r"(?i)\binvoice\s+(?:no\.?|number|num|#)[\s:.#-]*([A-Z0-9][-A-Z0-9-]{2,20})",  # Invoice No: 12345
        r"(?i)\binvoice\s+(?:date|fecha).*?\binvoice\s+(?:no\.?|number|#)[\s:.#-]*([A-Z0-9][-A-Z0-9-]{2,20})",  # Invoice Date: ... Invoice Number: 12345
        r"(?i)\binvoice\s+id[\s:.#-]*([A-Z0-9][-A-Z0-9-]{2,20})",  # Invoice ID: 12345
        
        # Patrones específicos para 'Receipt #', 'Receipt Number'
        r"(?i)\breceipt\s+#[\s:.]*([\d]{5,7})",  # Receipt #: 214860
        r"(?i)\breceipt\s+(?:no\.?|number|num)[\s:.#-]*([\d]{5,7})",  # Receipt Number: 214860
        r"(?i)\breceipt\s+(?:no\.?|number|num|#)[\s:.#-]*([A-Z0-9][-A-Z0-9\/.]{2,20})",  # Receipt No: ABC-12345
        r"(?i)receipt\s*#:\s*(\d+)",  # Exactamente 'Receipt #: 214860'
        
        # Patrones para facturas en inglés (generales)
        r"(?i)(?:invoice|receipt)[\s:.#-]*(?:no|number|#)?[\s:.#-]*([A-Z0-9][-A-Z0-9-]{2,20})",  # Invoice: INV-12345
        r"(?i)(?:no|number|#)[\s:.#-]*(?:invoice|receipt)[\s:.#-]*([A-Z0-9][-A-Z0-9-]{2,20})",  # No. Invoice: INV-12345
        
        # Patrones para referencias y otros formatos
        r"(?i)(?:ref|reference|referencia)[\s:.#-]*([A-Z0-9][-A-Z0-9-]{2,20})",  # Ref: REF-12345
        r"(?i)(?:order|pedido)[\s:.#-]*(?:no|number|#)?[\s:.#-]*([A-Z0-9][-A-Z0-9-]{2,20})",  # Order: ORD-12345
        
        # Formato especial como en la imagen de ejemplo (40006-s-1015)
        r"(\d{4,5})[-\s]?[a-zA-Z][-\s]?(\d{1,5})",  # 40006-s-1015
        
        # Patrón para capturar números de factura que aparecen solos en una línea con formato específico
        r"^\s*([A-Z]{1,3}[-\d]{4,15})\s*$",  # INV-12345 (solo en una línea)
        r"^\s*(\d{4,6}-\d{1,10})\s*$",  # 123456-789 (solo en una línea)
        
        # Patrones para capturar números de factura en formatos comunes
        r"(?i)\b(?:inv|invoice|bill|receipt)[-#]?(\d{4,10})\b",  # INV12345 o Invoice#12345
        r"(?i)\b([A-Z]{1,3}-\d{3,10})\b"  # AB-12345 (en cualquier contexto)
    ]
    
    # Función para validar si una cadena parece un número de factura válido
    def is_valid_invoice_number(text):
        # Debe tener al menos un dígito
        if not re.search(r'\d', text):
            return False
        
        # Debe tener una longitud razonable (ni muy corta ni muy larga)
        if len(text) < 2 or len(text) > 30:
            return False
        
        # Evitar palabras comunes que no son números de factura
        common_words = ['total', 'subtotal', 'iva', 'tax', 'amount', 'precio', 'date', 'fecha', 
                        'customer', 'cliente', 'address', 'direccion', 'telefono', 'phone',
                        'email', 'web', 'http', 'www', 'com', 'net', 'org', 'es', 'ber', 'ncisco', 'relates',
                        'payment', 'pago', 'card', 'tarjeta', 'cash', 'efectivo', 'change', 'cambio',
                        'discount', 'descuento', 'quantity', 'cantidad', 'unit', 'unidad', 'price', 'precio',
                        'item', 'articulo', 'product', 'producto', 'service', 'servicio', 'description', 'descripcion']
        
        if text.lower() in common_words:
            return False
            
        # Verificar si es solo un número (sin letras ni separadores)
        if re.match(r'^\d+$', text):
            # Si es un número de 5 a 7 dígitos, es muy probable que sea un número de factura/recibo
            if 5 <= len(text) <= 7:
                return True
            # Si tiene 4 o más dígitos, podría ser un número de factura
            elif len(text) >= 4:
                return True
            
        # Verificar formatos comunes de números de factura
        common_formats = [
            r'^[A-Za-z]\d{3,}$',                # A12345
            r'^\d{3,}-\d+$',                    # 123-456789
            r'^[A-Za-z]{1,3}-\d{3,}$',          # INV-12345
            r'^[A-Za-z]{1,3}\d{3,}$',           # INV12345
            r'^\d{2,4}-[A-Za-z]{1,2}-\d{3,}$'  # 2023-S-123
        ]
        
        for pattern in common_formats:
            if re.match(pattern, text):
                return True
        
        # Preferir formatos que combinan letras y números o que tienen separadores
        has_good_format = bool(re.search(r'[A-Za-z].*\d|\d.*[A-Za-z]|[-\/]', text))
        
        return has_good_format
    
    # Patrones comunes en tickets y facturas (para otros datos)
    patterns = {
        "nombre_comercio": ["el corte inglés", "corte inglés", "mercadona", "carrefour", "lidl", "dia", "alcampo", "tienda de la esquina"],
        "nif": ["nif", "cif", "n.i.f", "c.i.f", "a-", "b-", "e-"],
        "fecha": ["fecha", "date", "dt", "/", "-"],
        "hora": ["hora", "time", "h:", ":"],
        "total": ["total", "importe", "suma", "€", "eur"],
        "iva": ["iva", "i.v.a", "impuesto", "%"],
        "direccion": ["calle", "c/", "avda", "plaza", "paseo", "p.º", "domicilio"],
        "codigo_postal": ["cp", "c.p", "código postal"],
        "telefono": ["tel", "telf", "teléfono", "tlf"],
        "articulo": ["ud", "unidad", "kg", "gr", "litro", "l", "ml", "piezas", "pzas"],
        "precio": ["precio", "€", "eur", "pvp"],
        "descuento": ["descuento", "dto", "oferta", "ahorro", "-%"],
        "metodo_pago": ["efectivo", "tarjeta", "visa", "mastercard", "transferencia", "bizum"],
        "registro_mercantil": ["registro mercantil", "reg. mercantil", "r.m."],
        "cliente": ["cliente", "consumidor", "comprador", "titular"]
    }
    
    # Descripciones para cada categoría
    descriptions = {
        "nombre_comercio": "Nombre de la tienda o establecimiento",
        "nif": "Número de Identificación Fiscal del comercio",
        "fecha": "Fecha de emisión del ticket o factura",
        "hora": "Hora de emisión del ticket o factura",
        "total": "Importe total de la compra",
        "iva": "Impuesto sobre el Valor Añadido aplicado",
        "direccion": "Dirección del establecimiento",
        "codigo_postal": "Código Postal del establecimiento",
        "telefono": "Número de teléfono del establecimiento",
        "articulo": "Producto o servicio adquirido",
        "precio": "Precio del producto o servicio",
        "descuento": "Descuento aplicado a la compra",
        "metodo_pago": "Forma de pago utilizada",
        "numero_factura": "Número identificativo del ticket o factura",
        "registro_mercantil": "Información del Registro Mercantil",
        "cliente": "Datos del cliente o comprador"
    }
    
    # Primero, buscar específicamente números de factura
    for item in text_results:
        text = item["text"]
        
        # Imprimir para depuración
        print(f"Analizando texto: {text}")
        
        # Buscar patrones de número de factura
        for pattern in invoice_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                # Determinar qué grupo capturado usar
                if len(match.groups()) > 1 and match.group(2):  # Para patrones con múltiples grupos
                    invoice_number = f"{match.group(1)}-{match.group(2)}".strip()
                else:
                    invoice_number = match.group(1).strip()
                
                # Imprimir para depuración
                print(f"Patrón coincidente: {pattern}")
                print(f"Número de factura encontrado: {invoice_number}")
                
                # Validar el número de factura
                if is_valid_invoice_number(invoice_number):
                    print(f"Número de factura válido: {invoice_number}")
                    # Crear un nuevo item solo con el número de factura
                    invoice_item = item.copy()
                    invoice_item["categories"] = ["numero_factura"]
                    invoice_item["description"] = "Número identificativo del ticket o factura"
                    invoice_item["invoice_number"] = invoice_number
                    invoice_number_results.append(invoice_item)
                else:
                    print(f"Número de factura rechazado: {invoice_number}")
                    
        # Imprimir todo el texto para depuración
        print(f"Texto completo: {text}")
        
        # Buscar específicamente el formato "Receipt #: 214860"
        receipt_patterns = [
            r'(?i)receipt\s*#[\s:]*([0-9]{5,7})',
            r'(?i)receipt\s*#[\s:]*([0-9]+)',
            r'(?i)receipt[\s:]*#?[\s:]*([0-9]+)',
            r'(?i)receipt[\s:#]*([0-9]+)',
            r'(?i)#[\s:]*([0-9]+)'
        ]
        
        for pattern in receipt_patterns:
            receipt_match = re.search(pattern, text)
            if receipt_match:
                receipt_number = receipt_match.group(1).strip()
                print(f"Número de recibo encontrado: {receipt_number} con patrón: {pattern}")
                invoice_item = item.copy()
                invoice_item["categories"] = ["numero_factura"]
                invoice_item["description"] = "Número identificativo del ticket o factura"
                invoice_item["invoice_number"] = receipt_number
                invoice_number_results.append(invoice_item)
                break
    
    # Si encontramos números de factura, solo devolvemos esos resultados
    if invoice_number_results:
        return invoice_number_results
    
    # Si no encontramos números de factura, procesamos todos los datos
    for item in text_results:
        text = item["text"].lower()
        categories = []
        
        # Buscar coincidencias con patrones
        for category, keywords in patterns.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    categories.append(category)
                    break
        
        # Si no se encontró ninguna categoría, asignar "otro"
        if not categories:
            categories = ["otro"]
            description = "Información adicional del ticket"
        else:
            # Usar la descripción de la primera categoría encontrada
            description = descriptions[categories[0]]
        
        # Añadir la interpretación al resultado
        interpreted_item = item.copy()
        interpreted_item["categories"] = categories
        interpreted_item["description"] = description
        interpreted_results.append(interpreted_item)
    
    return interpreted_results

def extract_invoice_number_only(extracted_data):
    """Extrae solo el número de factura de los datos procesados"""
    invoice_numbers = []
    all_texts = []
    
    # Recopilar todos los textos para búsqueda adicional
    for item in extracted_data:
        if 'text' in item:
            all_texts.append({
                'text': item.get('text', ''),
                'confidence': float(item.get('confidence', 0))
            })
    
    # Buscar elementos que sean números de factura
    for item in extracted_data:
        if 'categories' in item and 'numero_factura' in item.get('categories', []):
            invoice_number = item.get('invoice_number', item.get('text', ''))
            confidence = float(item.get('confidence', 0))
            invoice_numbers.append({
                'invoice_number': invoice_number,
                'confidence': confidence
            })
    
    # Si no se encontraron números de factura, buscar patrones adicionales en todos los textos
    if not invoice_numbers:
        import re
        # Patrones para buscar números de factura o recibo
        patterns = [
            r'(?i)receipt\s*#[\s:]*([0-9]{5,7})',
            r'(?i)receipt\s*#[\s:]*([0-9]+)',
            r'(?i)receipt[\s:]*#?[\s:]*([0-9]+)',
            r'(?i)receipt[\s:#]*([0-9]+)',
            r'(?i)#[\s:]*([0-9]+)',
            r'(?i)(?:invoice|receipt)[\s:#]*([0-9]+)',
            r'(?i)(?:factura|fra|ticket|recibo)[\s:#]*([0-9]+)'
        ]
        
        for text_item in all_texts:
            text = text_item['text']
            confidence = text_item['confidence']
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    invoice_number = match.group(1).strip()
                    print(f"Número encontrado en segunda búsqueda: {invoice_number}")
                    invoice_numbers.append({
                        'invoice_number': invoice_number,
                        'confidence': confidence
                    })
                    break
    
    # Si aún no se encontraron números de factura, devolver un mensaje
    if not invoice_numbers:
        return {
            "success": True,
            "message": "No se encontraron números de factura",
            "invoice_numbers": []
        }
    
    # Eliminar duplicados
    unique_invoice_numbers = []
    seen = set()
    for item in invoice_numbers:
        if item['invoice_number'] not in seen:
            seen.add(item['invoice_number'])
            unique_invoice_numbers.append(item)
    
    # Ordenar por confianza (mayor primero)
    unique_invoice_numbers.sort(key=lambda x: x['confidence'], reverse=True)
    
    return {
        "success": True,
        "message": "Números de factura encontrados",
        "invoice_numbers": unique_invoice_numbers
    }

def extract_text_from_image(image_bytes):
    """Extraer texto de una imagen usando Azure Computer Vision"""
    global computervision_client
    
    # Verificar si el cliente está inicializado, si no, intentar inicializarlo
    if not computervision_client:
        if not initialize_client():
            return {"error": "Cliente de Smart Vision no está inicializado. Verifica las credenciales en el archivo .env"}
    
    try:
        # Imprimir información de depuración
        print(f"Usando endpoint: {ENDPOINT}")
        print(f"Usando clave: {KEY[:5]}...{KEY[-5:]}"  if KEY else "Clave no disponible")  # Solo mostrar parte de la clave por seguridad
        
        # Usar directamente la API REST en lugar del SDK para mayor control
        url = f"{ENDPOINT}vision/v3.2/read/analyze"
        
        headers = {
            'Ocp-Apim-Subscription-Key': KEY,
            'Content-Type': 'application/octet-stream'
        }
        
        # Enviar la solicitud para iniciar el análisis
        response = requests.post(url, headers=headers, data=image_bytes.getvalue())
        
        if response.status_code != 202:
            print(f"Error al iniciar el análisis: {response.status_code} - {response.text}")
            return {"error": f"Error al iniciar el análisis: {response.text}"}
        
        # Obtener la URL de operación del encabezado de respuesta
        operation_location = response.headers["Operation-Location"]
        print(f"Operation Location: {operation_location}")
        
        # Esperar a que se complete el procesamiento
        max_retries = 10
        retry_delay = 1  # segundos
        
        for i in range(max_retries):
            # Consultar el estado de la operación
            read_result_response = requests.get(operation_location, headers={
                'Ocp-Apim-Subscription-Key': KEY
            })
            
            if read_result_response.status_code != 200:
                print(f"Error al obtener resultados: {read_result_response.status_code} - {read_result_response.text}")
                return {"error": f"Error al obtener resultados: {read_result_response.text}"}
            
            read_result = read_result_response.json()
            
            # Verificar si el procesamiento ha terminado
            if read_result["status"] not in ["notStarted", "running"]:
                break
                
            print(f"Análisis en progreso... Intento {i+1}/{max_retries}")
            time.sleep(retry_delay)
        
        # Extraer texto de los resultados
        text_results = []
        
        if read_result["status"] == "succeeded":
            if "analyzeResult" in read_result and "readResults" in read_result["analyzeResult"]:
                for page in read_result["analyzeResult"]["readResults"]:
                    for line in page["lines"]:
                        text_results.append({
                            "text": line["text"],
                            "bounding_box": line["boundingBox"],
                            "confidence": 0.9  # La API v3.2 no proporciona confianza por línea
                        })
        
        # Interpretar los datos del ticket
        interpreted_results = interpret_ticket_data(text_results)
        
        return {
            "status": read_result["status"],
            "results": interpreted_results
        }
    
    except Exception as e:
        print(f"Error al procesar la imagen: {str(e)}")
        return {"error": str(e)}

@app.route('/login')
def login():
    """Página de inicio de sesión"""
    # Servir el archivo login.html desde la carpeta static
    return app.send_static_file('login.html')

@app.route('/logout')
def logout():
    """Cerrar sesión"""
    # Redirigir a la página principal en lugar de login
    return redirect(url_for('index'))

@app.route('/')
def index():
    """Página principal"""
    # Servir el archivo index.html desde la carpeta static
    return app.send_static_file('index.html')

@app.route('/check-init', methods=['GET'])
def check_init():
    """Endpoint para verificar si el sistema está listo"""
    return jsonify({
        "initialized": True,
        "message": "Sistema listo para procesar imágenes con Azure OpenAI"
    })

@app.route('/extract-text', methods=['POST'])
def extract_text():
    """Endpoint para extraer texto de una imagen usando Azure OpenAI"""
    # Verificar si hay un archivo en la solicitud
    if 'file' not in request.files and 'image' not in request.files:
        return jsonify({"error": "No se ha proporcionado una imagen"}), 400
    
    # Obtener el archivo de la solicitud (puede venir como 'file' o 'image')
    image_file = request.files.get('file') or request.files.get('image')
    
    if not image_file or image_file.filename == '':
        return jsonify({"error": "Archivo no válido"}), 400
    
    # Leer el contenido del archivo
    image_bytes = io.BytesIO(image_file.read())
    
    # Procesar la imagen con Azure OpenAI
    result = process_image_with_openai(image_bytes)
    
    if not result["success"]:
        return jsonify({"error": result.get("error", "Error al procesar la imagen")}), 500
    
    # Extraer el texto procesado
    extracted_text = result["extracted_text"]
    
    # Buscar números de factura en el texto extraído
    invoice_numbers = extract_invoice_numbers_from_text(extracted_text)
    
    # Verificar si se ha solicitado análisis con IA
    use_ai_analysis = request.form.get('use_ai_analysis', 'false').lower() == 'true'
    
    if use_ai_analysis:
        # Si se solicita análisis con IA, devolver solo los números de factura
        return jsonify({
            "success": True,
            "message": "Números de factura encontrados" if invoice_numbers else "No se encontraron números de factura",
            "invoice_numbers": invoice_numbers,
            "full_text": extracted_text
        })
    else:
        # Si no se solicita análisis con IA, devolver todo el texto extraído
        return jsonify({
            "success": True,
            "extracted_text": extracted_text,
            "invoice_numbers": invoice_numbers
        })

if __name__ == '__main__':
    app.run(debug=True, port=5005)

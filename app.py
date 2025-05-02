import os
import io
import time
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials
from dotenv import load_dotenv
from PIL import Image
from functools import wraps

# Cargar variables de entorno
load_dotenv()

# Obtener la ruta del directorio actual
current_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, 
            static_folder=os.path.join(current_dir, 'static'),  # Carpeta de archivos estáticos
            static_url_path='/static')         # URL path para archivos estáticos
app.secret_key = os.urandom(24)  # Clave secreta para las sesiones

# Configuración de Azure Computer Vision
ENDPOINT = os.getenv('AZURE_COMPUTER_VISION_ENDPOINT')
KEY = os.getenv('AZURE_COMPUTER_VISION_KEY')
API_VERSION = os.getenv('AZURE_COMPUTER_VISION_API_VERSION', '2023-04-01-preview')

# Credenciales de usuario
VALID_USERNAME = "admin"
VALID_PASSWORD = "smartsolutions"

# Imprimir información de depuración
print("Endpoint:", ENDPOINT)
print("Key (primeros 5 caracteres):", KEY[:5] if KEY else "None")

# Crear cliente de Computer Vision
computervision_client = None

def initialize_client():
    global computervision_client
    if ENDPOINT and KEY:
        try:
            print("Intentando inicializar el cliente de Computer Vision...")
            computervision_client = ComputerVisionClient(
                ENDPOINT, CognitiveServicesCredentials(KEY))
            print("Cliente inicializado correctamente")
            return True
        except Exception as e:
            print(f"Error al inicializar el cliente: {str(e)}")
            return False
    else:
        print("Endpoint o KEY no están definidos")
        return False

# Inicializar el cliente al arrancar la aplicación
client_initialized = initialize_client()
print(f"Estado de inicialización del cliente: {client_initialized}")

# Decorador para requerir autenticación
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

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
        print(f"Usando clave: {KEY[:5]}...{KEY[-5:]}")  # Solo mostrar parte de la clave por seguridad
        
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
        
        return {
            "status": read_result["status"],
            "results": text_results
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

@app.route('/check-init')
def check_init():
    """Endpoint para verificar si el cliente está inicializado"""
    client_initialized = initialize_client()
    return jsonify({
        'initialized': client_initialized,
        'endpoint': ENDPOINT[:10] + '...' if ENDPOINT else 'No configurado',
        'key': KEY[:5] + '...' if KEY else 'No configurado'
    })

@app.route('/extract-text', methods=['POST'])
def extract_text():
    """Endpoint para extraer texto de una imagen"""
    if 'image' not in request.files:
        return jsonify({"error": "No se ha subido ninguna imagen"}), 400
    
    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({"error": "Nombre de archivo vacío"}), 400
    
    # Leer la imagen
    image_bytes = io.BytesIO(image_file.read())
    
    # Procesar la imagen con Azure Computer Vision
    result = extract_text_from_image(image_bytes)
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5006)

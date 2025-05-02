import os
import requests
import json
from dotenv import load_dotenv
from PIL import Image
import io

# Cargar variables de entorno
load_dotenv()

# Obtener credenciales desde variables de entorno
endpoint = os.getenv('AZURE_COMPUTER_VISION_ENDPOINT')
key = os.getenv('AZURE_COMPUTER_VISION_KEY')
api_version = os.getenv('AZURE_COMPUTER_VISION_API_VERSION', '2023-04-01-preview')

print("=== Verificación de Azure Computer Vision OCR API ===")
print(f"Endpoint: {endpoint}")
print(f"Key (primeros 5 caracteres): {key[:5]}...")
print(f"API Version: {api_version}")

# Ruta de la imagen de prueba (reemplaza con tu ruta de imagen)
image_path = input("Ingresa la ruta de la imagen para OCR (o presiona Enter para usar una imagen de ejemplo): ")

if not image_path:
    # Si no se proporciona una ruta, usar una imagen de ejemplo
    print("Usando imagen de ejemplo...")
    # Puedes reemplazar esto con la ruta a una imagen de ejemplo en tu sistema
    image_path = "test_image.jpg"  # Reemplaza con una imagen real

# Verificar si la imagen existe
if not os.path.exists(image_path):
    print(f"Error: La imagen {image_path} no existe.")
    exit(1)

# Construir la URL correcta para la API de OCR
# Asegurarse de incluir 'computervision' en la ruta como se menciona en el post
url = f"{endpoint}computervision/vision/v3.1/read/analyze"
if "?" not in url:
    url += f"?api-version={api_version}"
else:
    url += f"&api-version={api_version}"

print(f"\nURL de la API: {url}")

# Configurar los encabezados con la clave de suscripción
headers = {
    'Ocp-Apim-Subscription-Key': key,
    'Content-Type': 'application/octet-stream'
}

try:
    # Leer la imagen
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()
    
    # Realizar la solicitud HTTP para iniciar el análisis
    print("\nEnviando solicitud para analizar la imagen...")
    response = requests.post(url, headers=headers, data=image_data)
    
    # Verificar la respuesta inicial
    if response.status_code == 202:  # Accepted
        print("Solicitud aceptada. Obteniendo resultados...")
        
        # Obtener la URL de la operación desde los encabezados
        operation_location = response.headers['Operation-Location']
        print(f"Operation Location: {operation_location}")
        
        # Esperar y obtener los resultados
        headers = {'Ocp-Apim-Subscription-Key': key}
        
        # Polling hasta que el procesamiento esté completo
        import time
        max_retries = 10
        retry_delay = 1  # segundos
        
        for i in range(max_retries):
            print(f"Intento {i+1}/{max_retries} para obtener resultados...")
            result_response = requests.get(operation_location, headers=headers)
            result = result_response.json()
            
            if "status" in result and result["status"] == "succeeded":
                print("Procesamiento completado con éxito.")
                break
                
            if "status" in result and result["status"] == "failed":
                print(f"Error en el procesamiento: {result}")
                exit(1)
                
            print(f"Estado: {result.get('status', 'desconocido')}. Esperando {retry_delay} segundos...")
            time.sleep(retry_delay)
        
        # Mostrar los resultados
        if "analyzeResult" in result and "readResults" in result["analyzeResult"]:
            print("\n=== Texto extraído de la imagen ===")
            for read_result in result["analyzeResult"]["readResults"]:
                for line in read_result["lines"]:
                    print(f"Texto: {line['text']}")
            print("\n¡La extracción de texto funcionó correctamente!")
        else:
            print(f"\nNo se encontraron resultados de lectura en la respuesta: {result}")
    else:
        print(f"\n❌ ERROR: Código de estado {response.status_code}")
        print("Respuesta:", response.text)
        
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    print("\nPosibles soluciones:")
    print("1. Verifica que el endpoint incluya 'computervision' en la ruta")
    print("2. Asegúrate de que la clave API sea válida")
    print("3. Verifica que la imagen sea válida y accesible")

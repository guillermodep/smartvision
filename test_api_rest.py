import os
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener credenciales desde variables de entorno
endpoint = os.getenv('AZURE_COMPUTER_VISION_ENDPOINT')
key = os.getenv('AZURE_COMPUTER_VISION_KEY')

print("=== Verificación de Credenciales de Azure Computer Vision (REST API) ===")
print(f"Endpoint: {endpoint}")
print(f"Key (primeros 5 caracteres): {key[:5]}...")

# Construir la URL para la API de listado de dominios
url = f"{endpoint}vision/v3.1/models"

# Configurar los encabezados con la clave de suscripción
headers = {
    'Ocp-Apim-Subscription-Key': key,
    'Content-Type': 'application/json'
}

try:
    # Realizar la solicitud HTTP
    print("\nIntentando conectar a la API REST...")
    response = requests.get(url, headers=headers)
    
    # Verificar la respuesta
    if response.status_code == 200:
        print("¡Conexión exitosa! Código de estado:", response.status_code)
        print("\nRespuesta de la API:")
        print(response.json())
        print("\n¡Las credenciales son válidas y funcionan correctamente!")
    else:
        print(f"\n❌ ERROR: Código de estado {response.status_code}")
        print("Respuesta:", response.text)
        
        if response.status_code == 401:
            print("\nError de autenticación (401). Posibles causas:")
            print("1. La clave API no es válida o está mal formateada")
            print("2. La clave API ha expirado o está desactivada")
            print("3. El recurso de Azure Computer Vision no está activo")
        elif response.status_code == 404:
            print("\nError de recurso no encontrado (404). Posibles causas:")
            print("1. El endpoint no es correcto")
            print("2. La ruta de la API no es correcta")
            print("3. El recurso de Azure Computer Vision no existe")
        
except Exception as e:
    print(f"\n❌ ERROR de conexión: {str(e)}")
    print("\nPosibles soluciones:")
    print("1. Verifica tu conexión a Internet")
    print("2. Comprueba que el endpoint sea accesible")
    print("3. Asegúrate de que no haya problemas con el servicio de Azure")

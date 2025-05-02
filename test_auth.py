import os
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener credenciales desde variables de entorno
endpoint = os.getenv('AZURE_COMPUTER_VISION_ENDPOINT')
key = os.getenv('AZURE_COMPUTER_VISION_KEY')

print("=== Prueba de Autenticación de Azure Computer Vision ===")
print(f"Endpoint: {endpoint}")
print(f"Key (primeros 5 caracteres): {key[:5]}...")

# Construir la URL para la API de listado de dominios (una operación simple)
# Incluir 'computervision' en la ruta como se mencionó en el post
url = f"{endpoint}computervision/vision/v3.1/models"

# Configurar los encabezados con la clave de suscripción
headers = {
    'Ocp-Apim-Subscription-Key': key
}

try:
    # Realizar la solicitud HTTP
    print("\nIntentando conectar a la API REST...")
    response = requests.get(url, headers=headers)
    
    # Verificar la respuesta
    print(f"Código de estado: {response.status_code}")
    
    if response.status_code == 200:
        print("¡Autenticación exitosa!")
        print("\nRespuesta de la API:")
        print(response.json())
    else:
        print(f"Error en la autenticación. Respuesta: {response.text}")
        
        # Sugerencias basadas en el código de error
        if response.status_code == 401:
            print("\nError 401 - No autorizado. Posibles causas:")
            print("1. La clave API no es válida")
            print("2. La clave API ha expirado")
        elif response.status_code == 404:
            print("\nError 404 - No encontrado. Posibles causas:")
            print("1. El endpoint no es correcto")
            print("2. Falta 'computervision' en la ruta")
            print("3. La versión de la API no es correcta")
            
            # Probar con un endpoint alternativo
            alt_url = f"{endpoint}vision/v3.1/models"
            print(f"\nProbando con endpoint alternativo: {alt_url}")
            alt_response = requests.get(alt_url, headers=headers)
            print(f"Código de estado alternativo: {alt_response.status_code}")
            
            if alt_response.status_code == 200:
                print("¡El endpoint alternativo funcionó!")
                print("Deberías actualizar tu código para usar este endpoint")
            else:
                print(f"El endpoint alternativo también falló: {alt_response.text}")
                
                # Probar con otro endpoint alternativo
                alt_url2 = f"{endpoint}computervision/imageanalysis:analyze?api-version=2023-02-01-preview"
                print(f"\nProbando con otro endpoint alternativo: {alt_url2}")
                alt_response2 = requests.get(alt_url2, headers=headers)
                print(f"Código de estado alternativo 2: {alt_response2.status_code}")
                
                if alt_response2.status_code != 404:
                    print("Este endpoint parece ser válido, aunque puede requerir un método POST")
        
except Exception as e:
    print(f"\nError de conexión: {str(e)}")
    print("Posibles causas:")
    print("1. Problemas de red")
    print("2. El endpoint no es accesible")
    print("3. El formato del endpoint es incorrecto")

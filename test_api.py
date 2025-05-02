import os
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener credenciales desde variables de entorno
endpoint = os.getenv('AZURE_COMPUTER_VISION_ENDPOINT')
key = os.getenv('AZURE_COMPUTER_VISION_KEY')

print("=== Verificación de Credenciales de Azure Computer Vision ===")
print(f"Endpoint: {endpoint}")
print(f"Key (primeros 5 caracteres): {key[:5]}...")

try:
    # Intentar crear el cliente
    print("\nIntentando crear el cliente de Computer Vision...")
    client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(key))
    
    # Intentar una operación simple para verificar la autenticación
    print("Intentando listar los modelos disponibles...")
    models = client.list_models()
    print("¡Conexión exitosa! Se pudieron listar los modelos.")
    
    # Mostrar algunos modelos disponibles
    print("\nModelos disponibles:")
    for model in models.models_property:
        print(f" - {model.name} ({model.category})")
    
    print("\n¡Las credenciales son válidas y funcionan correctamente!")
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    print("\nPosibles soluciones:")
    print("1. Verifica que el endpoint sea correcto y esté completo (debe terminar en .com/)")
    print("2. Asegúrate de que la clave API sea válida y esté activa")
    print("3. Comprueba que el recurso de Azure Computer Vision esté activo y no tenga restricciones")
    print("4. Verifica que la región del recurso coincida con el endpoint")

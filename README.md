# Extractor de Texto con Azure Computer Vision

Esta aplicación web permite cargar imágenes (tickets, facturas, documentos, etc.) y extraer el texto contenido en ellas utilizando Azure Computer Vision.

## Características

- Interfaz web sencilla para cargar imágenes
- Extracción de texto utilizando Azure Computer Vision API
- Visualización de resultados con nivel de confianza
- Configuración de credenciales de Azure desde la interfaz

## Requisitos

- Python 3.6 o superior
- Cuenta de Azure con servicio Computer Vision activo
- Claves de API de Azure Computer Vision

## Instalación

1. Clona o descarga este repositorio

2. Instala las dependencias:
   ```
   pip install -r requirements.txt
   ```

3. Configura las variables de entorno:
   - Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido:
   ```
   AZURE_COMPUTER_VISION_ENDPOINT=https://your-resource-name.cognitiveservices.azure.com/
   AZURE_COMPUTER_VISION_KEY=your_key_here
   ```
   - Reemplaza los valores con tus propias credenciales de Azure Computer Vision

## Uso

1. Inicia la aplicación:
   ```
   python app.py
   ```

2. Abre tu navegador y ve a `http://localhost:5000`

3. Si no has configurado las credenciales en el archivo `.env`, puedes hacerlo directamente desde la interfaz web en la sección de Configuración.

4. Carga una imagen y haz clic en "Extraer Texto" para procesar la imagen.

## Obtener credenciales de Azure Computer Vision

1. Inicia sesión en el [Portal de Azure](https://portal.azure.com)
2. Crea un recurso de Computer Vision o utiliza uno existente
3. Ve a la sección "Claves y punto de conexión"
4. Copia el "Punto de conexión" y una de las claves (Key 1 o Key 2)
5. Utiliza estos valores en la configuración de la aplicación

## Tecnologías utilizadas

- Flask: Framework web para Python
- Azure Computer Vision API: Servicio de reconocimiento óptico de caracteres (OCR)
- Bootstrap: Framework CSS para la interfaz de usuario
- JavaScript: Para la interactividad en el lado del cliente

## Limitaciones

- El tamaño máximo de imagen puede estar limitado por la configuración de Flask y Azure
- La precisión de la extracción de texto depende de la calidad de la imagen y del servicio de Azure

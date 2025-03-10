# Discord Music Bot

Este es un bot de Discord para reproducir música en canales de voz. Utiliza **yt-dlp** para buscar y reproducir canciones desde YouTube y otros servicios. Puedes controlar la reproducción de la música con comandos como **play**, **pause**, **skip**, **stop**, entre otros.

## Requisitos

- Python 3.8 o superior.
- **FFMPEG** (ya está incluido en el proyecto en la carpeta `bin/ffmpeg`).
- Un **token de bot de Discord**.

## Instalación

1. Instala las dependencias necesarias:

   ```bash
   pip install discord.py
   pip install yt-dlp
   pip install python-dotenv
   pip install -r requirements.txt

2. Crea un archivo .env en la raíz del proyecto con el siguiente contenido:
  ```bash
   DISCORD_TOKEN=tu_token_aqui




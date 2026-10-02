#!/usr/bin/env python3
"""
Convierte PNG a ICO con múltiples resoluciones
"""
from PIL import Image
import os

def convert_png_to_ico(png_path, ico_path):
    """Convierte PNG a ICO con resoluciones estándar para Windows"""
    try:
        img = Image.open(png_path).convert("RGBA")
        
        # Resoluciones estándar para iconos Windows
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        icon_images = [img.resize(size, Image.Resampling.LANCZOS) for size in icon_sizes]
        
        # Guardar como ICO
        icon_images[0].save(ico_path, format='ICO', sizes=icon_sizes)
        print(f"✅ Icono creado exitosamente: {ico_path}")
        print(f"   Tamaño: {os.path.getsize(ico_path)} bytes")
        print(f"   Resoluciones: {icon_sizes}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    return True

if __name__ == "__main__":
    png_file = "schedule-board.png"
    ico_file = "assets/sorth.ico"
    
    if not os.path.exists(png_file):
        print(f"❌ No se encontró: {png_file}")
        exit(1)
    
    print(f"Convirtiendo {png_file} → {ico_file}")
    if convert_png_to_ico(png_file, ico_file):
        print("\n✅ Listo para compilar: .\build_exe.ps1")

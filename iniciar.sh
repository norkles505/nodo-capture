#!/usr/bin/env bash
# Inicia Nodo Capture en Linux (equivalente al compilar.bat de Windows).
# La primera vez crea un entorno virtual (.venv) e instala PySide6.
cd "$(dirname "$0")" || exit 1

echo "Iniciando Nodo Capture..."

if ! command -v python3 >/dev/null 2>&1; then
  echo "No encontré python3. Instálalo con el gestor de paquetes de tu distro."
  read -rp "Presiona Enter para salir..." _
  exit 1
fi

# Entorno virtual (evita el error "externally-managed-environment" de pip)
if [ ! -x ".venv/bin/python" ]; then
  echo "Creando entorno virtual (.venv)..."
  if ! python3 -m venv .venv; then
    rm -rf .venv
    echo
    echo "No se pudo crear el entorno virtual."
    echo "En Debian/Ubuntu/Mint instala el módulo con: sudo apt install python3-venv"
    read -rp "Presiona Enter para salir..." _
    exit 1
  fi
fi

# Instala PySide6 solo si falta
if ! .venv/bin/python -c "import PySide6" >/dev/null 2>&1; then
  echo "Instalando PySide6 (solo la primera vez, puede tardar)..."
  if ! .venv/bin/python -m pip install PySide6; then
    echo
    echo "Falló la instalación de PySide6. Revisa tu conexión a internet."
    read -rp "Presiona Enter para salir..." _
    exit 1
  fi
fi

.venv/bin/python main.py
codigo=$?

if [ $codigo -ne 0 ]; then
  echo
  echo "La app terminó con un error. Revisa el mensaje de arriba."
  read -rp "Presiona Enter para cerrar..." _
fi
exit $codigo

Proyecto migrado a Python con una GUI mejorada para interactuar con dispositivos CP2112.

Requisitos:
- Colocar `SLABHIDtoSMBus.dll` en el PATH o en la misma carpeta que el ejecutable en Windows.
- Instalar dependencias:

```
pip install -r requirements.txt
```

Usar la versión de Python del sistema (recomendada >= 3.11). En Windows se puede usar el lanzador `py`:

```
py -3 -m pip install -r requirements.txt
```

Ejecutar GUI de ejemplo con el lanzador de Windows:

```
py -3 -m pyreader
```

Funcionalidades incluidas:
- Detección de dispositivos CP2112 y apertura/cierre del dispositivo.
- Lectura y escritura de transferencias SMBus con direcciones de esclavo y datos hexadecimales.
- Lectura/escritura de latch y cancelación de transferencias/I/O.
- Lectura de registros de batería tipo Smart Battery (dirección configurable, registros predefinidos, resumen de batería y exportación de reportes).
- Registro visible en la GUI con exportación a archivo de texto para logs y reportes.

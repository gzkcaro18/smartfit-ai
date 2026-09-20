# SmartFit AI

Prototipo local para un hackatón. No usa APIs, cuentas externas ni modelos de pago: todos los cálculos y ajustes se realizan con reglas deterministas en Python.

## Requisitos

- Python 3.10 o posterior
- Una terminal (PowerShell en Windows)

## Puesta en marcha

Desde esta carpeta, ejecuta:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Streamlit abrirá la aplicación en `http://localhost:8501`. Para detenerla, vuelve a la terminal y pulsa `Ctrl+C`.

Si PowerShell bloquea la activación del entorno, ejecuta una vez en esa misma terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Después vuelve a ejecutar `.\.venv\Scripts\Activate.ps1`.

## Lógica del prototipo

- Estimación basal: ecuación Mifflin-St Jeor.
- Calorías diarias: basal multiplicado por el nivel de actividad, con ajuste por objetivo.
- Ajuste anti-fatiga: sueño, energía y molestias generan una puntuación de recuperación que reduce las series de la sesión. Las molestias intensas recomiendan parar y consultar a un profesional.

Los resultados nutricionales son orientativos y no sustituyen la atención de profesionales sanitarios.

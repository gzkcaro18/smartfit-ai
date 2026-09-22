"""SmartFit AI - prototipo local sin APIs de pago."""

from __future__ import annotations

import hmac
from datetime import datetime
from html import escape
from io import BytesIO
from itertools import combinations, permutations
from math import ceil
from random import choice, shuffle
import re
import time
import unicodedata

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import streamlit as st
import streamlit.components.v1 as components


# Candado local solicitado para este prototipo.
APP_PASSWORD = "SmartFit2026"


ACTIVITY_FACTORS = {
    "Sedentario (poco o ningún ejercicio)": 1.2,
    "Ligero (1-3 entrenamientos/semana)": 1.375,
    "Moderado (3-5 entrenamientos/semana)": 1.55,
    "Alto (6-7 entrenamientos/semana)": 1.725,
}

GOAL_ADJUSTMENTS = {
    "Volumen": 400,
    "Hipertrofia": 150,
    "Definición": -500,
}

GOAL_EXPLANATIONS = {
    "Volumen": "subir peso y masa muscular de forma controlada con un superávit moderado.",
    "Hipertrofia": "favorecer la ganancia muscular con un pequeño margen extra de energía.",
    "Definición": "bajar grasa con déficit calórico y proteína alta para proteger la masa muscular.",
}

WEEKDAYS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")

# Megacatálogo local: nombre, músculo, bloque, series base, equipo guiado e ID visual.
# Las imágenes pertenecen al dataset público free-exercise-db y se fijan a una revisión concreta.
_EXERCISE_ROWS = [
    # Empuje: pecho, hombro y tríceps.
    ("Press de banca plano", "Pecho", "Empuje", 4, False, "Barbell_Bench_Press_-_Medium_Grip"),
    ("Press inclinado con mancuernas", "Pecho", "Empuje", 3, False, "Incline_Dumbbell_Press"),
    ("Press militar sentado con barra", "Hombros", "Empuje", 3, False, "Seated_Barbell_Military_Press"),
    ("Fondos para tríceps", "Tríceps", "Empuje", 3, False, "Dips_-_Triceps_Version"),
    ("Aperturas con mancuernas", "Pecho", "Empuje", 3, False, "Dumbbell_Flyes"),
    ("Extensión unilateral de tríceps con mancuerna", "Tríceps", "Empuje", 3, False, "Dumbbell_One-Arm_Triceps_Extension"),
    ("Press de pecho en máquina sentada (Chest Press)", "Pecho", "Empuje", 3, True, "Machine_Bench_Press"),
    ("Press de hombro guiado (Shoulder Press)", "Hombros", "Empuje", 3, True, "Leverage_Shoulder_Press"),
    ("Aperturas en máquina (Pec Deck)", "Pecho", "Empuje", 3, True, "Butterfly"),
    ("Extensión de tríceps en polea alta con barra", "Tríceps", "Empuje", 3, True, "Triceps_Pushdown"),
    ("Press inclinado con barra", "Pecho", "Empuje", 3, False, "Barbell_Incline_Bench_Press_-_Medium_Grip"),
    ("Press declinado con barra", "Pecho", "Empuje", 3, False, "Decline_Barbell_Bench_Press"),
    ("Press plano con mancuernas", "Pecho", "Empuje", 3, False, "Dumbbell_Bench_Press"),
    ("Press de pecho en polea", "Pecho", "Empuje", 3, True, "Cable_Chest_Press"),
    ("Cruce de poleas medio", "Pecho", "Empuje", 3, True, "Cable_Crossover"),
    ("Cruce de poleas bajo", "Pecho", "Empuje", 3, True, "Low_Cable_Crossover"),
    ("Elevaciones laterales con mancuernas", "Hombros", "Empuje", 3, False, "Side_Lateral_Raise"),
    ("Elevación lateral en polea sentado", "Hombros", "Empuje", 3, True, "Cable_Seated_Lateral_Raise"),
    ("Press Arnold", "Hombros", "Empuje", 3, False, "Arnold_Dumbbell_Press"),
    ("Extensión de tríceps con cuerda", "Tríceps", "Empuje", 3, True, "Triceps_Pushdown_-_Rope_Attachment"),
    ("Fondos en máquina asistida", "Tríceps", "Empuje", 3, True, "Dip_Machine"),
    ("Press de banca en máquina Smith", "Pecho", "Empuje", 3, True, "Smith_Machine_Bench_Press"),
    ("Press de hombro en máquina Smith", "Hombros", "Empuje", 3, True, "Smith_Machine_Overhead_Shoulder_Press"),
    ("Extensión de tríceps sobre cabeza con polea", "Tríceps", "Empuje", 3, True, "Cable_Rope_Overhead_Triceps_Extension"),
    ("Press de pecho convergente de discos (Hammer de pecho)", "Pecho", "Empuje", 3, True, "Leverage_Chest_Press"),
    ("Press inclinado de discos", "Pecho", "Empuje", 3, True, "Leverage_Incline_Chest_Press"),
    ("Press de hombros de discos", "Hombros", "Empuje", 3, True, "Leverage_Shoulder_Press"),
    # Tirón: espalda, deltoide posterior, trapecio y bíceps.
    ("Dominadas", "Espalda", "Tirón", 4, False, "Pullups"),
    ("Remo con barra", "Espalda", "Tirón", 4, False, "Bent_Over_Barbell_Row"),
    ("Jalón al pecho con agarre ancho", "Espalda", "Tirón", 3, True, "Wide-Grip_Lat_Pulldown"),
    ("Remo en polea baja con agarre neutro", "Espalda", "Tirón", 3, True, "Seated_Cable_Rows"),
    ("Curl de bíceps con barra", "Bíceps", "Tirón", 3, False, "Barbell_Curl"),
    ("Curl martillo", "Bíceps", "Tirón", 3, False, "Hammer_Curls"),
    ("Remo en máquina de placas con soporte al pecho", "Espalda", "Tirón", 3, True, "Leverage_High_Row"),
    ("Jalón al pecho en máquina convergente", "Espalda", "Tirón", 3, True, "Close-Grip_Front_Lat_Pulldown"),
    ("Extensión de espalda en máquina (Lumbar)", "Espalda", "Tirón", 3, True, "Hyperextensions_Back_Extensions"),
    ("Curl de bíceps en banco Scott en máquina", "Bíceps", "Tirón", 3, True, "Machine_Preacher_Curls"),
    ("Remo a una mano con mancuerna", "Espalda", "Tirón", 3, False, "One-Arm_Dumbbell_Row"),
    ("Remo en barra T con agarre neutro", "Espalda", "Tirón", 3, False, "T-Bar_Row_with_Handle"),
    ("Remo con mancuernas apoyado en banco inclinado", "Espalda", "Tirón", 3, False, "Dumbbell_Incline_Row"),
    ("Jalón supino en polea", "Espalda", "Tirón", 3, True, "Underhand_Cable_Pulldowns"),
    ("Jalón de brazos rectos en polea", "Espalda", "Tirón", 3, True, "Straight-Arm_Pulldown"),
    ("Face pull con cuerda", "Hombros", "Tirón", 3, True, "Face_Pull"),
    ("Pájaros en máquina inversa", "Hombros", "Tirón", 3, True, "Reverse_Machine_Flyes"),
    ("Remo alto en polea con cuerda", "Hombros", "Tirón", 3, True, "Cable_Rope_Rear-Delt_Rows"),
    ("Curl inclinado alterno con mancuernas", "Bíceps", "Tirón", 3, False, "Alternate_Incline_Dumbbell_Curl"),
    ("Curl martillo con cuerda en polea", "Bíceps", "Tirón", 3, True, "Cable_Hammer_Curls_-_Rope_Attachment"),
    ("Curl predicador con barra Z", "Bíceps", "Tirón", 3, False, "Preacher_Curl"),
    ("Curl de concentración", "Bíceps", "Tirón", 3, False, "Concentration_Curls"),
    ("Encogimientos con mancuernas", "Trapecio", "Tirón", 3, False, "Dumbbell_Shrug"),
    ("Remo iso-lateral en máquina", "Espalda", "Tirón", 3, True, "Leverage_Iso_Row"),
    ("Jalón con agarre V", "Espalda", "Tirón", 3, True, "V-Bar_Pulldown"),
    ("Remo bajo de discos (Low Row)", "Espalda", "Tirón", 3, True, "Leverage_Iso_Row"),
    ("Remo alto convergente de discos", "Espalda", "Tirón", 3, True, "Leverage_High_Row"),
    # Tren inferior: cuádriceps, femoral, glúteo, aductores y gemelos.
    ("Sentadilla trasera con barra", "Pierna", "Tren Inferior", 4, False, "Barbell_Squat"),
    ("Peso muerto rumano", "Pierna", "Tren Inferior", 3, False, "Romanian_Deadlift"),
    ("Prensa de piernas horizontal", "Pierna", "Tren Inferior", 3, True, "Leg_Press"),
    ("Extensión de cuádriceps en máquina", "Pierna", "Tren Inferior", 3, True, "Leg_Extensions"),
    ("Curl femoral sentado", "Pierna", "Tren Inferior", 3, True, "Seated_Leg_Curl"),
    ("Máquina de abductores", "Pierna", "Tren Inferior", 3, True, "Thigh_Abductor"),
    ("Prensa de gemelos", "Pierna", "Tren Inferior", 3, True, "Calf_Press_On_The_Leg_Press_Machine"),
    ("Zancada búlgara con mancuernas", "Pierna", "Tren Inferior", 3, False, "Split_Squat_with_Dumbbells"),
    ("Zancada con barra", "Pierna", "Tren Inferior", 3, False, "Barbell_Lunge"),
    ("Zancadas con mancuernas", "Pierna", "Tren Inferior", 3, False, "Dumbbell_Lunges"),
    ("Zancadas caminando con barra", "Pierna", "Tren Inferior", 3, False, "Barbell_Walking_Lunge"),
    ("Sentadilla goblet", "Pierna", "Tren Inferior", 3, False, "Goblet_Squat"),
    ("Sentadilla frontal con barra", "Pierna", "Tren Inferior", 3, False, "Front_Barbell_Squat"),
    ("Sentadilla Jaca (Hack Squat)", "Pierna", "Tren Inferior", 3, True, "Hack_Squat"),
    ("Sentadilla en máquina Smith", "Pierna", "Tren Inferior", 3, True, "Smith_Machine_Squat"),
    ("Prensa inclinada con pies estrechos", "Pierna", "Tren Inferior", 3, True, "Narrow_Stance_Leg_Press"),
    ("Extensión unilateral de cuádriceps", "Pierna", "Tren Inferior", 3, True, "Single-Leg_Leg_Extension"),
    ("Curl femoral tumbado", "Pierna", "Tren Inferior", 3, True, "Lying_Leg_Curls"),
    ("Curl femoral de pie unilateral", "Pierna", "Tren Inferior", 3, True, "Standing_Leg_Curl"),
    ("Hip thrust con barra", "Pierna", "Tren Inferior", 3, False, "Barbell_Glute_Bridge"),
    ("Patada de glúteo en polea", "Pierna", "Tren Inferior", 3, True, "Glute_Kickback"),
    ("Máquina de aductores", "Pierna", "Tren Inferior", 3, True, "Thigh_Adductor"),
    ("Elevación de gemelos sentado", "Pierna", "Tren Inferior", 3, True, "Seated_Calf_Raise"),
    ("Elevación de gemelos de pie", "Pierna", "Tren Inferior", 3, True, "Standing_Calf_Raises"),
    ("Peso muerto rumano con mancuernas", "Pierna", "Tren Inferior", 3, False, "Stiff-Legged_Dumbbell_Deadlift"),
    ("Peso muerto sumo", "Pierna", "Tren Inferior", 3, False, "Sumo_Deadlift"),
    ("Zancada búlgara en máquina Smith", "Pierna", "Tren Inferior", 3, True, "Smith_Single-Leg_Split_Squat"),
    ("Peso muerto en polea baja", "Pierna", "Tren Inferior", 3, True, "Cable_Deadlifts"),
    ("Press de piernas inclinado a 45 grados (Prensa de discos)", "Pierna", "Tren Inferior", 3, True, "Leg_Press"),
    ("Prensa pendular de discos", "Pierna", "Tren Inferior", 3, True, "Narrow_Stance_Hack_Squats"),
]

EXERCISE_DATABASE = [
    {
        "name": name,
        "muscle": muscle,
        "block": block,
        "sets": sets,
        "reps": 10,
        "guided": guided,
        "image_id": image_id,
    }
    for name, muscle, block, sets, guided, image_id in _EXERCISE_ROWS
]

UPPER_BODY = ["Pecho", "Hombros", "Tríceps", "Espalda", "Bíceps"]
LOWER_BODY = ["Pierna"]
MUSCLE_OPTIONS = UPPER_BODY + LOWER_BODY

BLOCK_DESCRIPTIONS = {
    "Empuje": "Pecho + hombros + tríceps: se agrupan porque comparten el patrón de empujar y actúan como sinergistas en los presses.",
    "Tirón": "Espalda + bíceps: se agrupan porque comparten el patrón de tracción y la flexión del codo acompaña remos y jalones.",
    "Tren Inferior": "Pierna: combina un patrón dominante de rodilla con una bisagra de cadera.",
}

MOVEMENT_EXPLANATIONS = {
    "Empuje": (
        "**Empuje (Push):** ejercicios en los que alejas el peso de tu cuerpo. "
        "Trabajan principalmente pecho, hombros y tríceps."
    ),
    "Tirón": (
        "**Tirón (Pull):** ejercicios en los que acercas el peso hacia tu cuerpo. "
        "Trabajan principalmente espalda y bíceps."
    ),
}

CARDIO_RECOMMENDATIONS = {
    "Volumen": {
        "duration": "15-20 minutos",
        "title": "Caminata ligera en cinta",
        "detail": (
            "Velocidad: 5.0-5.5 km/h · Inclinación fija: 0%. Enfoque de salud cardiovascular "
            "sin degradar masa muscular ni añadir fatiga innecesaria."
        ),
    },
    "Hipertrofia": {
        "duration": "20-25 minutos",
        "title": "Caminata moderada en cinta",
        "detail": (
            "Usa un ritmo cómodo-moderado que te permita hablar. Complementa el trabajo de fuerza "
            "sin convertir el cardio en otra sesión exigente."
        ),
    },
    "Definición": {
        "duration": "30-40 minutos",
        "title": "Caminata en cinta con inclinación",
        "detail": (
            "Velocidad: 5.5-6.0 km/h · Inclinación obligatoria: 4%-6%. Enfoque de máxima "
            "oxidación de grasa protegiendo las articulaciones y conservando el trabajo de fuerza."
        ),
    },
}

REST_BY_GOAL = {
    "Volumen": (
        "Descanso: 2 a 3 minutos entre series (Recuperación completa para maximizar la fuerza "
        "y el movimiento de cargas pesadas en máquinas de discos)"
    ),
    "Hipertrofia": (
        "Descanso: 90 segundos a 2 minutos entre series (Punto óptimo para disipar la fatiga "
        "acumulada manteniendo la congestión muscular)"
    ),
    "Definición": (
        "Descanso: 60 a 90 segundos entre series (Enfoque metabólico dinámico para mantener "
        "pulsaciones elevadas y optimizar la sesión)"
    ),
}

CORE_BY_WEEKDAY = {
    "Lunes": ("Plancha isométrica", "3 x 45 s", "Aprieta glúteos y abdomen; mantén cabeza, cadera y talones alineados."),
    "Martes": ("Dead bug controlado", "3 x 10 por lado", "Pega la zona lumbar al suelo y extiende brazo y pierna contrarios sin arquearla."),
    "Miércoles": ("Crunch abdominal en suelo", "3 x 15", "Eleva solo las escápulas y exhala; evita tirar del cuello."),
    "Jueves": ("Pallof press en polea", "3 x 12 por lado", "Resiste la rotación con el tronco firme y los brazos extendidos."),
    "Viernes": ("Elevaciones de piernas colgado", "3 x 12", "Eleva las rodillas sin balanceo y controla por completo la bajada."),
    "Sábado": ("Plancha lateral", "3 x 35 s por lado", "Mantén hombro, cadera y tobillo en línea sin dejar caer la pelvis."),
    "Domingo": ("Bird dog", "2 x 10 por lado", "Extiende extremidades contrarias lentamente manteniendo la pelvis estable."),
}

# URLs directas de imágenes JPG, fijadas a una revisión inmutable del dataset.
EXERCISE_IMAGE_REVISION = "a859101d633a01c4a1a920d6a8ce41dabba0705f"
EXERCISE_IMAGE_BASE = (
    f"https://raw.githubusercontent.com/yuhonas/free-exercise-db/"
    f"{EXERCISE_IMAGE_REVISION}/exercises"
)
EXERCISE_MEDIA = {
    str(exercise["name"]): f"{EXERCISE_IMAGE_BASE}/{exercise['image_id']}/0.jpg"
    for exercise in EXERCISE_DATABASE
}

# Valores por 100 g de porción comestible. Referencia: USDA FoodData Central (FDC).
# Los FDC ID permiten revisar el alimento de referencia; los valores pueden variar por marca y cocción.
FOOD_DATABASE = {
    "Pechuga de pollo cocida": {
        "protein": 31.02,
        "carbs": 0.0,
        "fat": 3.57,
        "fdc_id": 5746,
    },
    "Arroz blanco cocido": {
        "protein": 2.69,
        "carbs": 28.17,
        "fat": 0.28,
        "fdc_id": 20045,
    },
    "Ternera magra cocida": {
        "protein": 26.1,
        "carbs": 0.0,
        "fat": 8.9,
        "fdc_id": 23562,
        "category": "protein",
    },
    "Salmón cocido": {
        "protein": 25.4,
        "carbs": 0.0,
        "fat": 13.4,
        "fdc_id": 15236,
        "category": "protein",
    },
    "Atún al natural escurrido": {
        "protein": 25.5,
        "carbs": 0.0,
        "fat": 0.8,
        "fdc_id": 15121,
        "category": "protein",
    },
    "Pavo cocido": {
        "protein": 29.5,
        "carbs": 0.0,
        "fat": 2.1,
        "fdc_id": 5696,
        "category": "protein",
    },
    "Pasta integral cocida": {
        "protein": 5.3,
        "carbs": 26.5,
        "fat": 0.9,
        "fdc_id": 20125,
        "category": "carb",
    },
    "Patata cocida": {
        "protein": 1.87,
        "carbs": 20.13,
        "fat": 0.1,
        "fdc_id": 11367,
        "category": "carb",
    },
    "Boniato al horno": {
        "protein": 2.01,
        "carbs": 20.71,
        "fat": 0.15,
        "fdc_id": 11510,
        "category": "carb",
    },
    "Avena seca": {
        "protein": 16.9,
        "carbs": 66.3,
        "fat": 6.9,
        "fdc_id": 20132,
        "category": "carb",
    },
    "Copos de maíz sin azúcar": {
        "protein": 7.5,
        "carbs": 84.1,
        "fat": 0.4,
        "fdc_id": 8020,
        "category": "snack_carb",
    },
    "Huevo entero": {
        "protein": 12.6,
        "carbs": 1.1,
        "fat": 10.6,
        "fdc_id": 171287,
        "category": "breakfast",
    },
    "Claras de huevo": {
        "protein": 10.9,
        "carbs": 0.7,
        "fat": 0.2,
        "fdc_id": 172183,
        "category": "breakfast",
    },
    "Plátano": {
        "protein": 1.1,
        "carbs": 22.8,
        "fat": 0.3,
        "fdc_id": 173944,
        "category": "breakfast",
    },
    "Leche semidesnatada": {
        "protein": 3.4,
        "carbs": 5.0,
        "fat": 1.5,
        "fdc_id": 746782,
        "category": "breakfast",
    },
    "Aceite de oliva": {
        "protein": 0.0,
        "carbs": 0.0,
        "fat": 100.0,
        "fdc_id": 4053,
        "category": "fat",
    },
    "Miel": {
        "protein": 0.3,
        "carbs": 82.4,
        "fat": 0.0,
        "fdc_id": 169640,
        "category": "breakfast",
    },
    "Tortitas de arroz": {
        "protein": 8.2,
        "carbs": 81.5,
        "fat": 2.8,
        "fdc_id": 170250,
        "category": "snack_carb",
    },
    "Pan integral": {
        "protein": 12.4,
        "carbs": 42.7,
        "fat": 3.5,
        "fdc_id": 172688,
        "category": "snack_carb",
    },
    "Yogur griego natural 0%": {
        "protein": 10.3,
        "carbs": 3.64,
        "fat": 0.37,
        "fdc_id": 330137,
        "category": "snack_protein",
    },
    "Fresas": {
        "protein": 0.67,
        "carbs": 7.68,
        "fat": 0.3,
        "fdc_id": 167762,
        "category": "fruit",
    },
    "Manzana": {
        "protein": 0.148,
        "carbs": 15.7,
        "fat": 0.162,
        "fdc_id": 1750340,
        "category": "fruit",
    },
    "Almendras": {
        "protein": 21.5,
        "carbs": 20.0,
        "fat": 51.1,
        "fdc_id": 2346393,
        "category": "fat_snack",
    },
}

FOOD_DATABASE["Pechuga de pollo cocida"]["category"] = "protein"
FOOD_DATABASE["Arroz blanco cocido"]["category"] = "carb"
PROTEIN_OPTIONS = [name for name, data in FOOD_DATABASE.items() if data["category"] == "protein"]
MAIN_CARB_OPTIONS = ["Arroz blanco cocido", "Pasta integral cocida", "Patata cocida", "Boniato al horno"]

SHOPPING_CATEGORIES = {
    "Proteínas / Carnes y lácteos": {
        *PROTEIN_OPTIONS,
        "Huevo entero",
        "Claras de huevo",
        "Leche semidesnatada",
        "Yogur griego natural 0%",
    },
    "Carbohidratos / Granos": {
        *MAIN_CARB_OPTIONS,
        "Avena seca",
        "Copos de maíz sin azúcar",
        "Tortitas de arroz",
        "Pan integral",
        "Miel",
    },
    "Frutas / Verduras": {"Plátano", "Fresas", "Manzana"},
    "Grasas / Complementos": {"Aceite de oliva", "Almendras"},
}

MAIN_RECIPE_CATALOG = {
    ("Pechuga de pollo cocida", "Arroz blanco cocido"): "Arroz con pollo salteado",
    ("Pechuga de pollo cocida", "Pasta integral cocida"): "Pasta integral con pollo mediterráneo",
    ("Pechuga de pollo cocida", "Patata cocida"): "Pollo especiado con patatas al horno",
    ("Ternera magra cocida", "Arroz blanco cocido"): "Ternera salteada con arroz",
    ("Ternera magra cocida", "Pasta integral cocida"): "Pasta boloñesa fit de ternera",
    ("Ternera magra cocida", "Patata cocida"): "Filete de ternera con patatas al horno",
    ("Salmón cocido", "Arroz blanco cocido"): "Bowl de salmón con arroz",
    ("Salmón cocido", "Pasta integral cocida"): "Pasta integral con salmón",
    ("Salmón cocido", "Patata cocida"): "Salmón al horno con patata",
    ("Atún al natural escurrido", "Arroz blanco cocido"): "Bowl fresco de arroz con atún",
    ("Atún al natural escurrido", "Pasta integral cocida"): "Ensalada de pasta integral con atún",
    ("Atún al natural escurrido", "Patata cocida"): "Ensalada templada de patata y atún",
    ("Pavo cocido", "Arroz blanco cocido"): "Arroz salteado con pavo especiado",
    ("Pavo cocido", "Pasta integral cocida"): "Pasta integral con pavo mediterráneo",
    ("Pavo cocido", "Patata cocida"): "Pavo a la plancha con patatas al horno",
    ("Pechuga de pollo cocida", "Boniato al horno"): "Pollo especiado con boniato al horno",
    ("Ternera magra cocida", "Boniato al horno"): "Ternera a la plancha con boniato",
    ("Salmón cocido", "Boniato al horno"): "Salmón al horno con boniato",
    ("Atún al natural escurrido", "Boniato al horno"): "Ensalada templada de atún y boniato",
    ("Pavo cocido", "Boniato al horno"): "Pavo especiado con boniato al horno",
}

BREAKFAST_TEMPLATES = {
    "pancakes": {
        "recipe": "Tortitas fit de avena y plátano",
        "foods": {
            "Avena seca": 40.0,
            "Huevo entero": 50.0,
            "Leche semidesnatada": 180.0,
            "Plátano": 100.0,
        },
    },
    "porridge": {
        "recipe": "Porridge caliente de manzana y almendras",
        "foods": {
            "Avena seca": 55.0,
            "Leche semidesnatada": 200.0,
            "Manzana": 150.0,
            "Almendras": 10.0,
        },
    },
    "toast_eggs": {
        "recipe": "Tostadas integrales con revuelto de huevo y claras",
        "foods": {
            "Pan integral": 60.0,
            "Huevo entero": 50.0,
            "Claras de huevo": 100.0,
        },
    },
    "yogurt_oats": {
        "recipe": "Bol proteico de yogur, avena y fresas",
        "foods": {
            "Yogur griego natural 0%": 180.0,
            "Avena seca": 45.0,
            "Fresas": 150.0,
        },
    },
    # Alternativas de respaldo para mantener variedad cuando el Tutor excluye alimentos.
    "potato_scramble": {
        "recipe": "Revuelto de huevo y claras con patata cocida",
        "foods": {"Patata cocida": 200.0, "Huevo entero": 50.0, "Claras de huevo": 120.0},
    },
    "rice_pudding": {
        "recipe": "Arroz con leche fit y plátano",
        "foods": {"Arroz blanco cocido": 150.0, "Leche semidesnatada": 200.0, "Plátano": 80.0},
    },
    "rice_cakes_yogurt": {
        "recipe": "Tortitas de arroz con yogur y manzana",
        "foods": {"Tortitas de arroz": 30.0, "Yogur griego natural 0%": 150.0, "Manzana": 150.0},
    },
}

SNACK_TEMPLATES = {
    "sandwich": {
        "recipe": "Sándwich integral fit con manzana",
        "foods": {"Pan integral": 60.0, "Manzana": 150.0},
    },
    "yogurt": {
        "recipe": "Bol proteico de yogur y fresas con tortitas de arroz",
        "foods": {
            "Yogur griego natural 0%": 120.0,
            "Fresas": 150.0,
            "Tortitas de arroz": 25.0,
        },
    },
    "banana_honey": {
        "recipe": "Plátano natural con un toque de miel",
        "foods": {"Plátano": 120.0, "Miel": 15.0},
    },
    "oat_cup": {
        "recipe": "Vaso de avena cremosa con leche",
        "foods": {"Avena seca": 35.0, "Leche semidesnatada": 180.0},
    },
    "nuts": {
        "recipe": "Puñado medido de almendras tostadas",
        "foods": {"Almendras": 25.0},
    },
}

ROTATING_CARB_AND_FRUIT_FOODS = {
    "Avena seca",
    "Copos de maíz sin azúcar",
    "Plátano",
    "Miel",
    "Tortitas de arroz",
    "Pan integral",
    "Fresas",
    "Manzana",
    *MAIN_CARB_OPTIONS,
}

# Alimentos que no pueden repetirse en la misma franja de dos días consecutivos.
WEEKLY_ROTATION_FOODS = {
    "Avena seca",
    "Copos de maíz sin azúcar",
    "Arroz blanco cocido",
    "Patata cocida",
    "Pan integral",
    "Pasta integral cocida",
    "Boniato al horno",
    "Plátano",
    "Manzana",
    "Fresas",
}

FOOD_ALIASES = {
    "pollo": "Pechuga de pollo cocida",
    "pechuga": "Pechuga de pollo cocida",
    "ternera": "Ternera magra cocida",
    "salmón": "Salmón cocido",
    "salmon": "Salmón cocido",
    "atún": "Atún al natural escurrido",
    "atun": "Atún al natural escurrido",
    "pavo": "Pavo cocido",
    "arroz": "Arroz blanco cocido",
    "pasta": "Pasta integral cocida",
    "patata": "Patata cocida",
    "boniato": "Boniato al horno",
    "avena": "Avena seca",
    "aceite": "Aceite de oliva",
    "miel": "Miel",
    "tortitas de arroz": "Tortitas de arroz",
    "pan integral": "Pan integral",
    "yogur": "Yogur griego natural 0%",
    "fresa": "Fresas",
    "frutos rojos": "Fresas",
    "manzana": "Manzana",
    "almendra": "Almendras",
    "frutos secos": "Almendras",
    "huevo": "Huevo entero",
    "plátano": "Plátano",
    "platano": "Plátano",
    "leche": "Leche semidesnatada",
    "nueces": "Almendras",
}

REPLACEMENTS = {
    "Pechuga de pollo cocida": "Atún al natural escurrido",
    "Ternera magra cocida": "Pechuga de pollo cocida",
    "Salmón cocido": "Atún al natural escurrido",
    "Atún al natural escurrido": "Pechuga de pollo cocida",
    "Pavo cocido": "Pechuga de pollo cocida",
    "Arroz blanco cocido": "Patata cocida",
    "Pasta integral cocida": "Arroz blanco cocido",
    "Patata cocida": "Arroz blanco cocido",
    "Boniato al horno": "Patata cocida",
    "Avena seca": "Patata cocida",
    "Huevo entero": "Claras de huevo",
    "Plátano": "Avena seca",
    "Leche semidesnatada": "Claras de huevo",
    "Miel": "Plátano",
    "Tortitas de arroz": "Pan integral",
    "Pan integral": "Tortitas de arroz",
    "Yogur griego natural 0%": "Leche semidesnatada",
    "Fresas": "Manzana",
    "Manzana": "Fresas",
    "Almendras": "Aceite de oliva",
}


def calculate_bmr(age: int, weight_kg: float, height_cm: float, sex: str) -> float:
    """Calcula metabolismo basal estimado con Mifflin-St Jeor."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "Hombre" else base - 161


def calculate_nutrition(
    age: int,
    weight_kg: float,
    height_cm: float,
    sex: str,
    activity: str,
    goal: str,
    reduce_carbs: bool = False,
) -> dict[str, float]:
    """Calcula macros locales. La reducción de carbohidratos solo se aplica en recuperación."""
    bmr = calculate_bmr(age, weight_kg, height_cm, sex)
    maintenance = bmr * ACTIVITY_FACTORS[activity]
    target_calories = max(1200, round(maintenance + GOAL_ADJUSTMENTS[goal]))
    protein_multiplier = 2.2 if goal in ("Definición", "Volumen") else 1.8
    protein_g = round(weight_kg * protein_multiplier, 1)
    fat_g = round(weight_kg * 0.8, 1)
    base_carbs_g = max(0, round((target_calories - protein_g * 4 - fat_g * 9) / 4, 1))
    carbs_g = round(base_carbs_g * 0.75, 1) if reduce_carbs else base_carbs_g
    calories = round(protein_g * 4 + fat_g * 9 + carbs_g * 4)
    return {
        "bmr": round(bmr),
        "maintenance": round(maintenance),
        "calories": calories,
        "protein_g": protein_g,
        "fat_g": fat_g,
        "carbs_g": carbs_g,
        "base_carbs_g": base_carbs_g,
        "carb_reduction": reduce_carbs,
    }


def detect_food_in_message(message: str) -> str | None:
    """Identifica alimentos por alias; no usa modelos ni servicios externos."""
    text = message.lower()
    return next((food for alias, food in FOOD_ALIASES.items() if alias in text), None)


def tutor_response(message: str) -> tuple[str, str | None]:
    """Genera una respuesta local por reglas y devuelve el alimento que debe excluirse."""
    food = detect_food_in_message(message)
    text = message.lower()
    allergy = any(term in text for term in ("alérg", "alerg", "intoler", "reacción"))
    dislike = any(term in text for term in ("no me gusta", "no quiero", "odio", "evita"))
    if not food:
        return (
            "Gracias por contármelo. Puedo gestionar alimentos de la base fija; escribe, por ejemplo, "
            "“no me gusta el salmón” o “alérgico al arroz”.",
            None,
        )
    replacement = REPLACEMENTS.get(food, "una alternativa de la base fija")
    if allergy:
        return (
            f"Entiendo. Marcaré {food} como excluido y usaré {replacement} como alternativa de macros. "
            "Esto no certifica que el reemplazo sea seguro para tu alergia: revisa siempre etiquetas y contacto cruzado.",
            food,
        )
    if dislike:
        return (
            f"Perfecto, quitaré {food} del menú de hoy y recalcularé con {replacement} cuando sea posible.",
            food,
        )
    return (
        f"He identificado {food}. Si quieres eliminarlo, indica “alérgico a {food}” o “no me gusta {food}”.",
        None,
    )


def normalize_search_text(value: str) -> str:
    """Normaliza texto libre para localizar días, comidas y recetas sin depender de tildes."""
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def is_cooking_request(message: str) -> bool:
    """Detecta peticiones culinarias explícitas sin confundirlas con exclusiones alimentarias."""
    text = normalize_search_text(message)
    cooking_terms = (
        "como preparo",
        "como preparar",
        "como cocino",
        "como cocinar",
        "como se hace",
        "como hago",
        "dame la receta",
        "receta",
        "receta paso a paso",
        "paso a paso",
        "quiero preparar",
        "quiero cocinar",
        "hacer un batido",
        "preparar un batido",
    )
    return any(term in text for term in cooking_terms)


def locate_recipe_in_plan(
    message: str,
    plan: dict,
) -> tuple[str, str, str, list[dict[str, float | str]]] | None:
    """Localiza la comida del menú activo que mejor coincide con la consulta del usuario."""
    text = normalize_search_text(message)
    weekly_menus = plan.get("weekly_menus", {})
    selected_day = next(
        (day for day in WEEKDAYS if normalize_search_text(day) in text),
        "Lunes",
    )
    rows = weekly_menus.get(selected_day) or plan.get("menu_rows", [])
    grouped: dict[tuple[str, str], list[dict[str, float | str]]] = {}
    for row in rows:
        key = (str(row["Comida"]), str(row["Receta"]))
        grouped.setdefault(key, []).append(row)

    meal_aliases = {
        "Desayuno": ("desayuno",),
        "Media Mañana": ("media manana", "media mañana"),
        "Comida (Mediodía)": ("comida", "mediodia", "almuerzo"),
        "Merienda": ("merienda", "snack"),
        "Cena": ("cena",),
    }
    scored: list[tuple[int, str, str, list[dict[str, float | str]]]] = []
    for (meal, recipe), meal_rows in grouped.items():
        recipe_text = normalize_search_text(recipe)
        score = 0
        if recipe_text in text:
            score += 100
        score += sum(12 for alias in meal_aliases.get(meal, ()) if normalize_search_text(alias) in text)
        for token in set(recipe_text.split()):
            if len(token) >= 4 and token in text:
                score += 4
        for row in meal_rows:
            food_text = normalize_search_text(str(row["Alimento"]))
            if food_text in text:
                score += 25
            score += sum(
                8
                for token in set(food_text.split())
                if len(token) >= 4 and token in text
            )
        foods = {str(row["Alimento"]) for row in meal_rows}
        if "batido" in text and "Leche semidesnatada" in foods and foods.intersection({"Plátano", "Fresas", "Manzana"}):
            score += 40
        scored.append((score, meal, recipe, meal_rows))

    if not scored:
        return None
    score, meal, recipe, meal_rows = max(scored, key=lambda item: item[0])
    if score <= 0:
        return None
    return selected_day, meal, recipe, meal_rows


def cooking_steps(recipe: str, rows: list[dict[str, float | str]], as_shake: bool) -> list[str]:
    """Crea instrucciones culinarias deterministas usando solo los alimentos del plato calculado."""
    foods = {str(row["Alimento"]) for row in rows}
    recipe_text = normalize_search_text(recipe)
    if as_shake:
        return [
            "Pesa por separado cada ingrediente con las cantidades indicadas.",
            "Añade primero la leche al vaso de la batidora y después incorpora la fruta y el resto de ingredientes del plato.",
            "Tritura durante 30-45 segundos hasta obtener una textura uniforme; añade únicamente agua o hielo si necesitas aligerarlo.",
            "Sirve inmediatamente y consume toda la preparación para respetar los macros calculados.",
        ]
    if "tortitas" in recipe_text and "Avena seca" in foods:
        return [
            "Pesa todos los ingredientes antes de empezar y reserva cualquier topping para el final.",
            "Tritura la avena con el huevo, la leche y la fruta que aparezcan en tu ración hasta obtener una masa homogénea.",
            "Calienta una sartén antiadherente a fuego medio; no añadas aceite salvo que figure expresamente en los ingredientes.",
            "Vierte pequeñas porciones y cocina cada tortita 1-2 minutos por lado, hasta que quede firme y dorada.",
            "Sirve todas las tortitas y reparte por encima los toppings calculados sin añadir cantidades extra.",
        ]
    if "porridge" in recipe_text or ("Avena seca" in foods and "Leche semidesnatada" in foods):
        return [
            "Pesa la avena, la leche, la fruta y los toppings exactamente como aparecen en el menú.",
            "Calienta la leche a fuego medio sin dejar que hierva.",
            "Incorpora la avena y remueve durante 4-6 minutos hasta conseguir una textura cremosa.",
            "Retira del fuego, añade la fruta troceada y termina con los toppings calculados.",
        ]
    if "Yogur griego natural 0%" in foods:
        return [
            "Pesa el yogur y cada acompañamiento en recipientes separados.",
            "Coloca el yogur como base del bol y añade la fruta limpia y troceada.",
            "Incorpora la avena, las tortitas o los frutos secos que correspondan a la ración.",
            "Mezcla justo antes de comer para conservar la textura, sin añadir toppings fuera del menú.",
        ]
    if "Pan integral" in foods and foods.intersection({"Huevo entero", "Claras de huevo"}):
        return [
            "Pesa el pan, el huevo y las claras según las cantidades del menú.",
            "Tuesta el pan sin añadir mantequilla ni aceite adicional.",
            "Bate el huevo y las claras y cocínalos en una sartén antiadherente a fuego medio, removiendo hasta que cuajen.",
            "Sirve el revuelto sobre las tostadas y consume la ración completa.",
        ]

    protein = next((food for food in foods if food in PROTEIN_OPTIONS), None)
    carbohydrate = next((food for food in foods if food in MAIN_CARB_OPTIONS), None)
    oil_present = "Aceite de oliva" in foods
    steps = ["Pesa todos los ingredientes ya cocinados o escurridos según indique el menú."]
    if protein:
        steps.append(
            f"Calienta o termina {protein.lower()} a fuego medio hasta que esté bien caliente; "
            f"{'utiliza únicamente el aceite asignado' if oil_present else 'no añadas aceite extra'} y sazona al gusto."
        )
    if carbohydrate:
        steps.append(
            f"Calienta {carbohydrate.lower()} por separado para mantener la cantidad exacta y evitar que absorba grasas adicionales."
        )
    steps.extend(
        [
            "Combina los componentes en el plato respetando todas las cantidades calculadas.",
            "Sirve inmediatamente y no añadas salsas o toppings calóricos que no aparezcan en la receta.",
        ]
    )
    return steps


def build_cooking_response(message: str, plan: dict | None) -> str:
    """Genera una receta paso a paso enlazada al menú y a los macros del perfil activo."""
    if not plan:
        return (
            "Para darte una receta con cantidades y macros exactos, completa primero el Perfil y el Check-in diario. "
            "Después pregúntame cómo preparar cualquiera de los platos de tu menú semanal."
        )
    match = locate_recipe_in_plan(message, plan)
    if not match:
        monday_rows = plan.get("weekly_menus", {}).get("Lunes", plan.get("menu_rows", []))
        available = list(dict.fromkeys(str(row["Receta"]) for row in monday_rows))
        options = ", ".join(available[:5])
        return (
            "Dime qué plato o momento del día quieres preparar. Por ejemplo: “¿Cómo preparo mi desayuno?” "
            f"o escribe uno de estos platos del lunes: {options}."
        )

    day, meal, recipe, rows = match
    protein = sum(float(row["Proteína (g)"]) for row in rows)
    carbs = sum(float(row["Carbohidratos (g)"]) for row in rows)
    fat = sum(float(row["Grasas (g)"]) for row in rows)
    calories = round(protein * 4 + carbs * 4 + fat * 9)
    nutrition = plan["nutrition"]
    ingredients = "\n".join(
        f"- **{row['Alimento']}:** {float(row['Gramos']):.1f} g ({row['Medida práctica']})"
        for row in rows
    )
    as_shake = "batido" in normalize_search_text(message)
    steps = "\n".join(
        f"{index}. {instruction}"
        for index, instruction in enumerate(cooking_steps(recipe, rows, as_shake), start=1)
    )
    display_name = f"Batido adaptado de {recipe.lower()}" if as_shake else recipe
    return (
        f"### 🍳 {display_name}\n"
        f"**{day} · {meal}**\n\n"
        f"**Ingredientes exactos de tu menú**\n{ingredients}\n\n"
        f"**Macros de esta ración:** {calories} kcal · P {protein:.1f} g · C {carbs:.1f} g · G {fat:.1f} g.\n\n"
        f"**Preparación paso a paso**\n{steps}\n\n"
        f"Estas cantidades forman parte de tu objetivo diario calculado de **{nutrition['calories']} kcal** "
        f"(metabolismo basal estimado: **{nutrition['bmr']} kcal**). "
        "No añadas ingredientes calóricos adicionales si quieres conservar los macros del plan."
    )


def solve_macro_vectors(
    vectors: tuple[dict[str, float], dict[str, float], dict[str, float]],
    target: dict[str, float],
) -> list[float] | None:
    """Resuelve tres correctores nutricionales sin inventar valores de alimentos."""
    nutrients = ("protein", "carbs", "fat")
    matrix = [[vector[nutrient] for vector in vectors] + [target[nutrient]] for nutrient in nutrients]
    for column in range(3):
        pivot = max(range(column, 3), key=lambda row: abs(matrix[row][column]))
        if abs(matrix[pivot][column]) < 1e-9:
            return None
        matrix[column], matrix[pivot] = matrix[pivot], matrix[column]
        divisor = matrix[column][column]
        matrix[column] = [value / divisor for value in matrix[column]]
        for row in range(3):
            if row == column:
                continue
            factor = matrix[row][column]
            matrix[row] = [matrix[row][index] - factor * matrix[column][index] for index in range(4)]
    solution = [matrix[index][3] for index in range(3)]
    return solution if all(value >= -1e-8 for value in solution) else None


def practical_measure(food: str, grams: float) -> str:
    """Traduce gramos exactos a una referencia fácil de usar en la cocina."""
    if food == "Huevo entero":
        units = max(1, round(grams / 50))
        return f"{units} huevo{'s' if units != 1 else ''} entero{'s' if units != 1 else ''}"
    if food == "Claras de huevo":
        return f"{grams:.0f} g de claras pasteurizadas"
    if food == "Leche semidesnatada":
        return f"{grams:.0f} ml aproximadamente"
    if food == "Aceite de oliva":
        teaspoons = grams / 5
        return f"{teaspoons:.1f} cucharaditas"
    if food == "Miel":
        tablespoons = grams / 15
        return f"{tablespoons:.1f} cucharadas"
    if food == "Tortitas de arroz":
        units = max(1, round(grams / 9))
        return f"{units} tortita{'s' if units != 1 else ''} aproximadamente"
    if food == "Pan integral":
        slices = max(1, round(grams / 30))
        return f"{slices} rebanada{'s' if slices != 1 else ''} aproximadamente"
    if food == "Yogur griego natural 0%":
        return f"1 bol con {grams:.0f} g"
    if food == "Fresas":
        return f"1 bol pequeño de {grams:.0f} g"
    if food == "Manzana":
        units = max(0.5, round(grams / 180 * 2) / 2)
        return f"{units:g} manzana{'s' if units != 1 else ''} aproximadamente"
    if food == "Almendras":
        units = max(1, round(grams / 1.2))
        return f"{units} almendras aproximadamente"
    if food == "Atún al natural escurrido":
        return f"1 ración escurrida de {grams:.0f} g"
    if food in PROTEIN_OPTIONS:
        return f"1 filete o ración de {grams:.0f} g"
    return f"{grams:.0f} g pesados"


def grams_to_row(meal: str, recipe: str, food: str, grams: float) -> dict[str, float | str]:
    data = FOOD_DATABASE[food]
    portion = grams / 100
    return {
        "Comida": meal,
        "Receta": recipe,
        "Alimento": food,
        "Gramos": round(grams, 2),
        "Medida práctica": practical_measure(food, grams),
        "Proteína (g)": round(portion * data["protein"], 2),
        "Carbohidratos (g)": round(portion * data["carbs"], 2),
        "Grasas (g)": round(portion * data["fat"], 2),
    }


def add_food_portion(
    plan: dict[tuple[str, str, str], float],
    meal: str,
    recipe: str,
    food: str,
    grams: float,
) -> None:
    if grams > 1e-7:
        key = (meal, recipe, food)
        plan[key] = plan.get(key, 0.0) + grams


def plan_macros(plan: dict[tuple[str, str, str], float]) -> dict[str, float]:
    totals = {"protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for (_, _, food), grams in plan.items():
        for nutrient in totals:
            totals[nutrient] += grams / 100 * float(FOOD_DATABASE[food][nutrient])
    return totals


def compatible_snack_orders(
    breakfast_variant: str,
    meals_per_day: int,
    excluded: set[str],
) -> list[tuple[str, ...]]:
    """Devuelve snacks completos sin repetir carbohidratos principales ni frutas del desayuno."""
    breakfast_foods = set(BREAKFAST_TEMPLATES[breakfast_variant]["foods"])
    used_rotating_foods = breakfast_foods.intersection(ROTATING_CARB_AND_FRUIT_FOODS)
    required_snacks = 2 if meals_per_day == 5 else 1
    available = [
        variant
        for variant, template in SNACK_TEMPLATES.items()
        if not set(template["foods"]).intersection(excluded)
        and not set(template["foods"]).intersection(used_rotating_foods)
    ]
    orders = []
    for order in permutations(available, required_snacks):
        used_foods = set(used_rotating_foods)
        valid = True
        for variant in order:
            snack_foods = set(SNACK_TEMPLATES[variant]["foods"]).intersection(
                ROTATING_CARB_AND_FRUIT_FOODS
            )
            if used_foods.intersection(snack_foods):
                valid = False
                break
            used_foods.update(snack_foods)
        if valid:
            orders.append(order)
    return orders


def morning_base_plan(
    meals_per_day: int,
    excluded: set[str],
    high_carb_day: bool,
    daily_carbs: float,
    daily_protein: float,
    daily_fat: float,
    breakfast_variant: str,
    snack_variants: tuple[str, ...],
) -> dict[tuple[str, str, str], float]:
    """Crea desayuno y snacks sin repetir carbohidratos ni frutas durante el día."""
    breakfast_template = BREAKFAST_TEMPLATES[breakfast_variant]
    layouts: dict[str, tuple[str, dict[str, float]]] = {
        "Desayuno": (
            str(breakfast_template["recipe"]),
            dict(breakfast_template["foods"]),
        ),
    }
    if meals_per_day == 5:
        first_template = SNACK_TEMPLATES[snack_variants[0]]
        second_template = SNACK_TEMPLATES[snack_variants[1]]
        layouts["Media Mañana"] = (str(first_template["recipe"]), dict(first_template["foods"]))
        layouts["Merienda"] = (str(second_template["recipe"]), dict(second_template["foods"]))
    else:
        template = SNACK_TEMPLATES[snack_variants[0]]
        layouts["Merienda"] = (str(template["recipe"]), dict(template["foods"]))

    scalable_totals = {"protein": 0.0, "carbs": 0.0, "fat": 0.0}
    fixed_totals = {"protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for _, foods in layouts.values():
        for food, grams in foods.items():
            if food in excluded:
                continue
            destination = fixed_totals if food == "Huevo entero" else scalable_totals
            for nutrient in destination:
                destination[nutrient] += grams / 100 * float(FOOD_DATABASE[food][nutrient])

    morning_carb_budget = daily_carbs * (0.72 if high_carb_day else 0.55)
    morning_protein_budget = daily_protein * (0.45 if meals_per_day == 5 else 0.38)
    morning_fat_budget = daily_fat * (0.55 if meals_per_day == 5 else 0.50)
    morning_scale = min(
        1.0,
        max(0.0, morning_carb_budget - fixed_totals["carbs"])
        / max(scalable_totals["carbs"], 1e-9),
        max(0.0, morning_protein_budget - fixed_totals["protein"])
        / max(scalable_totals["protein"], 1e-9),
        max(0.0, morning_fat_budget - fixed_totals["fat"])
        / max(scalable_totals["fat"], 1e-9),
    )
    plan: dict[tuple[str, str, str], float] = {}
    for meal, (recipe, foods) in layouts.items():
        available_count = 0
        for food, grams in foods.items():
            if food not in excluded:
                if food != "Huevo entero":
                    grams *= morning_scale
                add_food_portion(plan, meal, recipe, food, grams)
                available_count += 1
        if not available_count:
            raise ValueError(f"No quedan ingredientes compatibles para preparar {meal.lower()}.")
    return plan


def build_recipe_candidate(
    nutrition: dict[str, float],
    meals_per_day: int,
    excluded: set[str],
    lunch_protein: str,
    dinner_protein: str,
    lunch_carb: str,
    dinner_carb: str,
    breakfast_variant: str,
    snack_variants: tuple[str, ...],
    forbidden_foods_by_meal: tuple[tuple[str, ...], ...] | None = None,
) -> tuple[float, dict[tuple[str, str, str], float]] | None:
    """Cierra macros con límites humanos y correctores secundarios acotados."""
    carb_protein_ratio = nutrition["carbs_g"] / max(nutrition["protein_g"], 1)
    high_carb_day = carb_protein_ratio > 3
    lunch_recipe = MAIN_RECIPE_CATALOG[(lunch_protein, lunch_carb)]
    dinner_recipe = MAIN_RECIPE_CATALOG[(dinner_protein, dinner_carb)]
    best_candidate: tuple[float, dict[tuple[str, str, str], float]] | None = None
    nutrients = ("protein", "carbs", "fat")
    portion_limits = {
        "Claras de huevo": 300.0,
        "Yogur griego natural 0%": 400.0,
        "Tortitas de arroz": 60.0,
        "Pan integral": 160.0,
        "Avena seca": 100.0,
        "Copos de maíz sin azúcar": 100.0,
        "Miel": 90.0,
        "Boniato al horno": 300.0,
        "Pasta integral cocida": 300.0,
        "Plátano": 250.0,
        "Manzana": 300.0,
        "Fresas": 300.0,
        "Aceite de oliva": 60.0,
    }

    def destination_for(
        plan: dict[tuple[str, str, str], float], food: str
    ) -> tuple[str, str] | None:
        existing = {(meal, recipe) for meal, recipe, current_food in plan if current_food == food}
        if len(existing) == 1:
            return next(iter(existing))
        if len(existing) > 1:
            return None
        if food in ("Avena seca", "Copos de maíz sin azúcar", "Claras de huevo"):
            return "Desayuno", "Refuerzo de desayuno calculado"
        if food in ("Pan integral", "Tortitas de arroz", "Yogur griego natural 0%"):
            meal = "Media Mañana" if meals_per_day == 5 else "Merienda"
            return meal, "Snack energético calculado"
        if food == "Pasta integral cocida":
            swap_dense = breakfast_variant in {"toast_eggs", "rice_pudding", "potato_scramble"}
            meal = "Merienda" if swap_dense or meals_per_day == 4 else "Media Mañana"
            return meal, "Bowl energético de pasta integral"
        if food == "Boniato al horno":
            swap_dense = breakfast_variant in {"toast_eggs", "rice_pudding", "potato_scramble"}
            meal = "Media Mañana" if swap_dense and meals_per_day == 5 else "Merienda"
            return meal, "Boniato al horno para completar energía"
        return "Merienda", "Acompañamiento calculado"

    # Los perfiles de definición pueden terminar con un presupuesto diario de
    # carbohidratos muy bajo. Mantener opciones pequeñas evita declarar el menú
    # imposible sin obligar a usar raciones grandes o cantidades negativas.
    main_carb_portions = (
        (300.0, 250.0)
        if high_carb_day
        else (250.0, 200.0, 150.0, 100.0, 75.0, 50.0, 35.0, 25.0)
    )
    for protein_grams in (150.0, 135.0, 165.0, 120.0, 180.0):
        for main_carb_grams in main_carb_portions:
            plan = morning_base_plan(
                meals_per_day,
                excluded,
                high_carb_day,
                nutrition["carbs_g"],
                nutrition["protein_g"],
                nutrition["fat_g"],
                breakfast_variant,
                snack_variants,
            )
            add_food_portion(plan, "Comida (Mediodía)", lunch_recipe, lunch_protein, protein_grams)
            add_food_portion(plan, "Cena", dinner_recipe, dinner_protein, protein_grams)
            add_food_portion(plan, "Comida (Mediodía)", lunch_recipe, lunch_carb, main_carb_grams)
            add_food_portion(plan, "Cena", dinner_recipe, dinner_carb, main_carb_grams)

            used = plan_macros(plan)
            remaining = {
                "protein": nutrition["protein_g"] - used["protein"],
                "carbs": nutrition["carbs_g"] - used["carbs"],
                "fat": nutrition["fat_g"] - used["fat"],
            }
            if min(remaining.values()) < -1e-7:
                continue

            entries: dict[str, tuple[tuple[str, str], float, dict[str, float]]] = {}
            for food, limit in portion_limits.items():
                if food in excluded:
                    continue
                destination = destination_for(plan, food)
                if destination is None:
                    continue
                meal_index = {
                    "Desayuno": 0,
                    "Media Mañana": 1,
                    "Comida (Mediodía)": 2,
                    "Merienda": 3,
                    "Cena": 4,
                }[destination[0]]
                if (
                    forbidden_foods_by_meal is not None
                    and food in WEEKLY_ROTATION_FOODS
                    and food in set(forbidden_foods_by_meal[meal_index])
                ):
                    continue
                current_grams = sum(grams for (_, _, current_food), grams in plan.items() if current_food == food)
                capacity = limit - current_grams
                if capacity <= 1e-7:
                    continue
                entries[food] = (
                    destination,
                    capacity,
                    {nutrient: float(FOOD_DATABASE[food][nutrient]) for nutrient in nutrients},
                )
            if "Aceite de oliva" not in entries:
                continue

            non_oil = [food for food in entries if food != "Aceite de oliva"]
            pair_options = list(combinations(non_oil, 2))
            booster_options: list[tuple[tuple[str, float], ...]] = [tuple()]
            for booster in non_oil:
                capacity = entries[booster][1]
                booster_options.extend((((booster, capacity * 0.5),), ((booster, capacity),)))
            booster_pool = [
                food
                for food in non_oil
                if food in (
                    "Tortitas de arroz", "Pan integral", "Avena seca", "Copos de maíz sin azúcar", "Miel",
                    "Boniato al horno", "Pasta integral cocida", "Plátano", "Manzana", "Fresas",
                )
            ]
            booster_options.extend(
                ((first, entries[first][1]), (second, entries[second][1]))
                for first, second in combinations(booster_pool, 2)
            )

            for fixed_boosters in booster_options:
                adjusted_remaining = dict(remaining)
                for booster, booster_grams in fixed_boosters:
                    booster_vector = entries[booster][2]
                    for nutrient in nutrients:
                        adjusted_remaining[nutrient] -= booster_grams / 100 * booster_vector[nutrient]
                if min(adjusted_remaining.values()) < -1e-7:
                    continue
                for first_food, second_food in pair_options:
                    fixed_foods = {food for food, _ in fixed_boosters}
                    if fixed_foods.intersection((first_food, second_food)):
                        continue
                    solution = solve_macro_vectors(
                        (entries[first_food][2], entries[second_food][2], entries["Aceite de oliva"][2]),
                        adjusted_remaining,
                    )
                    if solution is None or min(solution) < -1e-7:
                        continue
                    first_grams, second_grams, oil_grams = (value * 100 for value in solution)
                    if (
                        first_grams > entries[first_food][1] + 1e-7
                        or second_grams > entries[second_food][1] + 1e-7
                        or oil_grams > entries["Aceite de oliva"][1] + 1e-7
                    ):
                        continue
                    candidate_plan = dict(plan)
                    additions = [*fixed_boosters, (first_food, first_grams), (second_food, second_grams), ("Aceite de oliva", oil_grams)]
                    for food, grams in additions:
                        if grams <= 1e-7:
                            continue
                        meal, recipe = entries[food][0]
                        add_food_portion(candidate_plan, meal, recipe, food, grams)
                    try:
                        validate_carb_rotation(candidate_plan)
                    except ValueError:
                        continue
                    rice_cake_portions = [
                        grams for (meal, _, food), grams in candidate_plan.items()
                        if food == "Tortitas de arroz" and meal in ("Media Mañana", "Merienda")
                    ]
                    if any(grams > 60.0001 for grams in rice_cake_portions):
                        continue
                    totals = plan_macros(candidate_plan)
                    if any(abs(totals[key] - nutrition[f"{key}_g"]) > 1e-4 for key in nutrients):
                        continue
                    score = (
                        abs(protein_grams - 150) * 2
                        + abs(main_carb_grams - 275) * 0.3
                        + sum((grams / max(portion_limits.get(food, grams), 1)) ** 2 for food, grams in additions if food)
                        + sum(grams * 0.06 for food, grams in additions if food == "Miel")
                    )
                    return score, candidate_plan
    return best_candidate


def validate_carb_rotation(plan: dict[tuple[str, str, str], float]) -> None:
    """Impide que un carbohidrato principal o una fruta aparezca en dos comidas."""
    meal_order = ("Desayuno", "Media Mañana", "Comida (Mediodía)", "Merienda", "Cena")
    first_meal_by_food: dict[str, str] = {}
    for meal in meal_order:
        meal_foods = {
            food
            for current_meal, _, food in plan
            if current_meal == meal and food in ROTATING_CARB_AND_FRUIT_FOODS
        }
        repeated = meal_foods.intersection(first_meal_by_food)
        if repeated:
            details = ", ".join(
                f"{food} ({first_meal_by_food[food]} y {meal})"
                for food in sorted(repeated)
            )
            raise ValueError(f"Rotación de carbohidratos inválida: {details}.")
        first_meal_by_food.update({food: meal for food in meal_foods})


def plan_rotation_signature(
    plan: dict[tuple[str, str, str], float],
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[tuple[str, ...], ...],
]:
    """Resume las fuentes que deben cambiar entre días consecutivos."""
    main_meals = ("Comida (Mediodía)", "Cena")
    snack_meals = ("Media Mañana", "Merienda")
    breakfasts = tuple(
        dict.fromkeys(
            recipe
            for meal, recipe, _ in plan
            if meal == "Desayuno"
        )
    )
    proteins = tuple(
        next(
            food
            for current_meal, _, food in plan
            if current_meal == meal and food in PROTEIN_OPTIONS
        )
        for meal in main_meals
    )
    carbs = tuple(
        next(
            food
            for current_meal, _, food in plan
            if current_meal == meal and food in MAIN_CARB_OPTIONS
        )
        for meal in main_meals
    )
    snacks = tuple(
        " | ".join(
            sorted(
                {
                    recipe
                    for current_meal, recipe, _ in plan
                    if current_meal == meal
                }
            )
        )
        for meal in snack_meals
        if any(current_meal == meal for current_meal, _, _ in plan)
    )
    meal_rotation = tuple(
        tuple(
            sorted(
                food
                for current_meal, _, food in plan
                if current_meal == meal and food in WEEKLY_ROTATION_FOODS
            )
        )
        for meal in ("Desayuno", "Media Mañana", "Comida (Mediodía)", "Merienda", "Cena")
    )
    return breakfasts, proteins, carbs, snacks, meal_rotation


def signatures_rotate(
    current: tuple,
    previous: tuple,
) -> bool:
    """Exige recetas distintas y cero repetición de carb/fruta por franja consecutiva."""
    current_breakfast, current_proteins, current_carbs, current_snacks, current_foods = current
    previous_breakfast, previous_proteins, previous_carbs, previous_snacks, previous_foods = previous
    return (
        current_breakfast != previous_breakfast
        and all(current != old for current, old in zip(current_proteins, previous_proteins))
        and all(current != old for current, old in zip(current_carbs, previous_carbs))
        and len(current_snacks) == len(previous_snacks)
        and all(current != old for current, old in zip(current_snacks, previous_snacks))
        and all(not set(now).intersection(before) for now, before in zip(current_foods, previous_foods))
    )


def build_dynamic_menu(
    nutrition: dict[str, float],
    excluded: set[str] | None = None,
    meals_per_day: int = 4,
    preferred_breakfast_variant: str | None = None,
    previous_signature: tuple | None = None,
    forbidden_signatures: set[tuple] | None = None,
    forbidden_main_recipes: set[str] | None = None,
) -> list[dict[str, float | str]]:
    """Construye recetas variadas y cierra exactamente los macros del día completo."""
    if meals_per_day not in (4, 5):
        raise ValueError("El número de comidas debe ser 4 o 5.")
    excluded = set(excluded or set())
    if "Huevo entero" in excluded:
        excluded.add("Claras de huevo")
    proteins = [food for food in PROTEIN_OPTIONS if food not in excluded]
    carbs = [food for food in MAIN_CARB_OPTIONS if food not in excluded]
    if len(proteins) < 2 or len(carbs) < 2 or "Aceite de oliva" in excluded:
        raise ValueError("No quedan alternativas suficientes para crear comida y cena variadas.")

    candidates: list[tuple[float, dict[tuple[str, str, str], float]]] = []
    protein_pairs = [(first, second) for first in proteins for second in proteins if first != second]
    carb_pairs = [(first, second) for first in carbs for second in carbs if first != second]
    if previous_signature is not None:
        previous_proteins = previous_signature[1]
        previous_carbs = previous_signature[2]
        protein_pairs = [
            pair for pair in protein_pairs
            if pair[0] != previous_proteins[0] and pair[1] != previous_proteins[1]
        ]
        carb_pairs = [
            pair for pair in carb_pairs
            if pair[0] != previous_carbs[0] and pair[1] != previous_carbs[1]
        ]
    if preferred_breakfast_variant is not None and preferred_breakfast_variant not in BREAKFAST_TEMPLATES:
        raise ValueError("La variante de desayuno solicitada no existe.")
    available_breakfasts = [
        variant
        for variant, template in BREAKFAST_TEMPLATES.items()
        if not set(template["foods"]).intersection(excluded)
    ]
    breakfast_variants = (
        [preferred_breakfast_variant]
        if preferred_breakfast_variant in available_breakfasts
        else available_breakfasts
        if preferred_breakfast_variant is None
        else []
    )
    if not breakfast_variants:
        raise ValueError("No queda un desayuno completo compatible con las exclusiones actuales.")
    if previous_signature is not None:
        previous_breakfast_foods = set(previous_signature[4][0])
        previous_breakfast_recipes = set(previous_signature[0])
        breakfast_variants = [
            variant for variant in breakfast_variants
            if str(BREAKFAST_TEMPLATES[variant]["recipe"]) not in previous_breakfast_recipes
            and not set(BREAKFAST_TEMPLATES[variant]["foods"]).intersection(
                WEEKLY_ROTATION_FOODS
            ).intersection(previous_breakfast_foods)
        ]
    protein_pairs.sort(
        key=lambda pair: (
            sum(food in set(previous_signature[1]) for food in pair) if previous_signature else 0,
            sum(float(FOOD_DATABASE[food]["protein"]) for food in pair),
        )
    )
    carb_pairs.sort(
        key=lambda pair: sum(
            float(FOOD_DATABASE[food]["protein"]) / max(float(FOOD_DATABASE[food]["carbs"]), 1e-9)
            for food in pair
        )
    )
    for breakfast_variant in breakfast_variants:
        snack_orders = compatible_snack_orders(breakfast_variant, meals_per_day, excluded)
        if previous_signature is not None:
            previous_snacks = previous_signature[3]
            meal_indexes = (1, 3) if meals_per_day == 5 else (3,)
            snack_orders = [
                order for order in snack_orders
                if all(
                    str(SNACK_TEMPLATES[variant]["recipe"]) != previous_snacks[position]
                    and not set(SNACK_TEMPLATES[variant]["foods"]).intersection(
                        WEEKLY_ROTATION_FOODS
                    ).intersection(previous_signature[4][meal_indexes[position]])
                    for position, variant in enumerate(order)
                )
            ]
        for snack_variants in snack_orders:
            for lunch_protein, dinner_protein in protein_pairs:
                for lunch_carb, dinner_carb in carb_pairs:
                    candidate = build_recipe_candidate(
                        nutrition,
                        meals_per_day,
                        excluded,
                        lunch_protein,
                        dinner_protein,
                        lunch_carb,
                        dinner_carb,
                        breakfast_variant,
                        snack_variants,
                        previous_signature[4] if previous_signature is not None else None,
                    )
                    if candidate is not None:
                        try:
                            validate_carb_rotation(candidate[1])
                        except ValueError:
                            continue
                        signature = plan_rotation_signature(candidate[1])
                        main_recipes = {
                            recipe
                            for meal, recipe, _ in candidate[1]
                            if meal in ("Comida (Mediodía)", "Cena")
                        }
                        if main_recipes.intersection(forbidden_main_recipes or set()):
                            continue
                        if previous_signature is not None and not signatures_rotate(signature, previous_signature):
                            continue
                        if signature in (forbidden_signatures or set()):
                            continue
                        candidates.append(candidate)
                        if len(candidates) >= 1:
                            break
                if len(candidates) >= 1:
                    break
            if len(candidates) >= 1:
                break
        if len(candidates) >= 1:
            break
    if not candidates:
        raise ValueError("Las exclusiones actuales no permiten construir un menú completo con macros positivos.")

    candidates.sort(key=lambda candidate: candidate[0])
    best_pool = candidates[: min(4, len(candidates))]
    _, selected_plan = choice(best_pool)
    validate_carb_rotation(selected_plan)
    meal_order = {"Desayuno": 0, "Media Mañana": 1, "Comida (Mediodía)": 2, "Merienda": 3, "Cena": 4}
    ordered_items = sorted(selected_plan.items(), key=lambda item: (meal_order[item[0][0]], item[0][2]))
    return [
        grams_to_row(meal, recipe, food, grams)
        for (meal, recipe, food), grams in ordered_items
    ]


def menu_rows_signature(
    rows: list[dict[str, float | str]],
) -> tuple:
    """Obtiene la firma semanal a partir de las filas visibles del menú."""
    plan = {
        (str(row["Comida"]), str(row["Receta"]), str(row["Alimento"])): float(row["Gramos"])
        for row in rows
    }
    return plan_rotation_signature(plan)


def build_weekly_menu(
    nutrition: dict[str, float],
    excluded: set[str] | None = None,
    meals_per_day: int = 4,
) -> dict[str, list[dict[str, float | str]]]:
    """Genera siete menús exactos, únicos y rotados respecto al día anterior."""
    weekly_menus: dict[str, list[dict[str, float | str]]] = {}
    previous_signature = None
    used_signatures: set[tuple] = set()
    main_recipe_counts: dict[str, int] = {}
    main_recipe_last_day: dict[str, int] = {}
    excluded = set(excluded or set())
    if "Huevo entero" in excluded:
        excluded.add("Claras de huevo")
    available_breakfasts = [
        variant
        for variant, template in BREAKFAST_TEMPLATES.items()
        if not set(template["foods"]).intersection(excluded)
    ]
    breakfast_variants = list(available_breakfasts)
    if len(breakfast_variants) < 4:
        raise ValueError(
            "Los macros y exclusiones actuales no dejan cuatro desayunos completos distintos para organizar la semana."
        )
    used_breakfasts: set[str] = set()
    weekly_breakfast_order = (
        "pancakes",
        "toast_eggs",
        "porridge",
        "potato_scramble",
        "yogurt_oats",
        "rice_pudding",
        "rice_cakes_yogurt",
    )
    for index, day in enumerate(WEEKDAYS):
        forbidden_main_recipes = {
            recipe
            for recipe, count in main_recipe_counts.items()
            if count >= 2 or index - main_recipe_last_day[recipe] <= 2
        }
        preferred_breakfast = weekly_breakfast_order[index]
        ordered_breakfasts = sorted(
            breakfast_variants,
            key=lambda variant: (
                variant != preferred_breakfast,
                variant in used_breakfasts,
                breakfast_variants.index(variant),
            ),
        )
        rows = None
        selected_variant = None
        for variant in ordered_breakfasts:
            try:
                candidate_rows = build_dynamic_menu(
                    nutrition,
                    excluded,
                    meals_per_day,
                    preferred_breakfast_variant=variant,
                    previous_signature=previous_signature,
                    forbidden_signatures=used_signatures,
                    forbidden_main_recipes=forbidden_main_recipes,
                )
            except ValueError:
                continue
            rows = candidate_rows
            selected_variant = variant
            break
        if rows is None or selected_variant is None:
            raise ValueError(
                f"No se pudo construir {day} sin repetir carbohidratos o fruta en la misma franja."
            )
        signature = menu_rows_signature(rows)
        weekly_menus[day] = rows
        day_main_recipes = {
            str(row["Receta"])
            for row in rows
            if row["Comida"] in ("Comida (Mediodía)", "Cena")
            and row["Alimento"] in PROTEIN_OPTIONS
        }
        for recipe in day_main_recipes:
            main_recipe_counts[recipe] = main_recipe_counts.get(recipe, 0) + 1
            main_recipe_last_day[recipe] = index
        used_breakfasts.add(selected_variant)
        used_signatures.add(signature)
        previous_signature = signature
    breakfast_names = {
        str(next(row["Receta"] for row in rows if row["Comida"] == "Desayuno"))
        for rows in weekly_menus.values()
    }
    if len(breakfast_names) < 4:
        raise ValueError("El plan semanal necesita al menos cuatro desayunos diferentes.")
    return weekly_menus


def fatigue_score(sleep_hours: float, discomfort: str) -> int:
    """Puntúa la fatiga solo con sueño y molestias, de forma explicable."""
    score = 0
    if sleep_hours < 5.5:
        score += 2
    elif sleep_hours < 7:
        score += 1

    score += {"Sin molestias": 0, "Molestia leve": 1, "Dolor Agudo": 0}[discomfort]
    return score


def recovery_plan(score: int, discomfort: str) -> tuple[float, str, str]:
    """Aplica el único ajuste autónomo autorizado sobre el volumen de series."""
    if discomfort == "Dolor Agudo":
        return 0.0, "Plan bloqueado", "Has indicado Dolor Agudo. SmartFit AI no generará un entrenamiento hoy."
    if score >= 3:
        return 0.5, "Fatiga alta", "Series ajustadas automáticamente al 50% de la sesión base."
    if score == 2:
        return 0.7, "Fatiga moderada", "Series ajustadas automáticamente al 70% de la sesión base."
    if score == 1:
        return 0.85, "Fatiga ligera", "Series ajustadas automáticamente al 85% de la sesión base."
    return 1.0, "Buena recuperación", "Puedes completar la sesión planificada con técnica controlada."


def adjusted_sets(base_sets: int, multiplier: float) -> int:
    """Reduce series sin prescribir menos de una por ejercicio cuando se entrena."""
    return max(1, ceil(base_sets * multiplier)) if multiplier else 0


def epley_1rm(weight_kg: float, repetitions_to_failure: int) -> float:
    """Estima la repetición máxima: 1RM = peso × (1 + repeticiones / 30)."""
    if weight_kg <= 0 or repetitions_to_failure <= 0:
        return 0.0
    return weight_kg * (1 + repetitions_to_failure / 30)


def daily_load_percentage(fatigue_multiplier: float) -> float:
    """Devuelve 75%, 67,5% o 60% de 1RM según el resultado del Check-in."""
    if fatigue_multiplier <= 0.5:
        return 0.60
    if fatigue_multiplier <= 0.7:
        return 0.675
    return 0.75


def suggested_weight(one_rm: float, fatigue_multiplier: float) -> float:
    """Calcula la carga diaria y la redondea a una décima de kilogramo para mostrarla."""
    return round(one_rm * daily_load_percentage(fatigue_multiplier), 1)


def exercise_image_url(exercise: str) -> str:
    """Resuelve por clave exacta para impedir imágenes cruzadas entre ejercicios."""
    return EXERCISE_MEDIA[exercise]


def exercise_equipment_label(exercise: dict[str, str | int]) -> str:
    """Traduce la clasificación interna a una etiqueta sencilla para el usuario."""
    name = str(exercise["name"]).lower()
    if "discos" in name or "hammer de pecho" in name or "sentadilla jaca" in name:
        return "Máquina de discos"
    if exercise["guided"]:
        return "Máquina guiada/polea"
    return "Peso libre/corporal"


def selected_exercises(muscles: list[str]) -> list[dict[str, str | int]]:
    """Filtra la base fija por la división o músculos elegidos para la sesión."""
    return [exercise for exercise in EXERCISE_DATABASE if exercise["muscle"] in muscles]


def exercises_for_block(block: str, prioritize_guided: bool = False) -> list[dict[str, str | int]]:
    """Devuelve el catálogo del patrón y, cuando procede, ordena primero las máquinas."""
    exercises = [exercise for exercise in EXERCISE_DATABASE if exercise["block"] == block]
    if prioritize_guided:
        return sorted(exercises, key=lambda exercise: not bool(exercise["guided"]))
    return exercises


def strength_inputs_for_session(
    exercises: list[dict[str, str | int]],
    fatigue_multiplier: float,
) -> dict[str, dict[str, float | int]]:
    """Pide datos solo para la sesión elegida y calcula Epley en cada rerun."""
    strength_data: dict[str, dict[str, float | int]] = {}
    load_percentage = daily_load_percentage(fatigue_multiplier)
    st.markdown("### Cargas de los ejercicios elegidos")
    st.caption(
        "Introduce una serie previa llevada al fallo técnico. La estimación y la carga de hoy "
        "se actualizan al cambiar cualquier valor."
    )
    for exercise in exercises:
        name = str(exercise["name"])
        with st.container(border=True):
            st.markdown(f"**{name}**")
            weight_column, repetitions_column, result_column = st.columns([1, 1, 1.15])
            previous_weight = weight_column.number_input(
                "Peso previo (kg)",
                min_value=0.0,
                max_value=500.0,
                value=0.0,
                step=0.5,
                key=f"session_weight_{name}",
            )
            failure_repetitions = repetitions_column.number_input(
                "Repeticiones al fallo",
                min_value=1,
                max_value=20,
                value=8,
                step=1,
                key=f"session_reps_{name}",
            )
            one_rm = epley_1rm(previous_weight, failure_repetitions)
            daily_weight = suggested_weight(one_rm, fatigue_multiplier) if one_rm else 0.0
            if one_rm:
                result_column.metric("1RM estimada", f"{one_rm:.1f} kg")
                result_column.caption(f"Carga de hoy: {daily_weight:.1f} kg ({load_percentage * 100:.1f}%)")
            else:
                result_column.metric("1RM estimada", "Pendiente")
                result_column.caption("Introduce un peso mayor que 0 kg.")
            strength_data[name] = {
                "weight": previous_weight,
                "repetitions": failure_repetitions,
                "one_rm": one_rm,
            }
    return strength_data


def render_workout_cards(
    exercises: list[dict[str, str | int]],
    multiplier: float,
    strength_data: dict[str, dict[str, float | int]],
    goal: str,
) -> None:
    """Agrupa los ejercicios por sinergia y muestra tarjetas en dos columnas."""
    for block in ("Empuje", "Tirón", "Tren Inferior"):
        block_exercises = [exercise for exercise in exercises if exercise["block"] == block]
        if not block_exercises:
            continue
        st.markdown(f"### {block}")
        st.info(BLOCK_DESCRIPTIONS[block])
        for exercise in block_exercises:
            with st.container(border=True):
                info_column, media_column = st.columns([1.15, 0.85], gap="large")
                with info_column:
                    st.markdown(f"## {exercise['name']}")
                    st.caption(f"🎯 {exercise['muscle']} · {exercise_equipment_label(exercise)}")
                    sets_column, reps_column = st.columns(2)
                    today_sets = adjusted_sets(int(exercise["sets"]), multiplier)
                    sets_column.metric("Series de hoy", today_sets)
                    reps_column.metric("Repeticiones", str(exercise["reps"]))
                    exercise_strength = strength_data.get(str(exercise["name"]), {})
                    estimated_1rm = float(exercise_strength.get("one_rm", 0))
                    if estimated_1rm > 0:
                        today_weight = suggested_weight(estimated_1rm, multiplier)
                        st.markdown(
                            f"""
                            <div class="load-chip">
                                <span class="load-chip-label">CARGA RECOMENDADA HOY</span>
                                <span class="load-chip-value">{today_weight:.1f} KG</span>
                                <span class="load-chip-detail">{today_sets} series × {exercise['reps']} reps</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        st.caption(
                            f"1RM estimada: {estimated_1rm:.1f} kg · Intensidad aplicada: "
                            f"{daily_load_percentage(multiplier) * 100:.1f}%"
                        )
                    else:
                        st.warning("Introduce el peso previo de este ejercicio para calcular la carga de hoy.")
                    st.caption(
                        f"Base: {exercise['sets']} series · "
                        f"Filtro de recuperación: {round(multiplier * 100)}%."
                    )
                    st.info(f"⏱️ {REST_BY_GOAL.get(goal, REST_BY_GOAL['Hipertrofia'])}")
                with media_column:
                    st.image(
                        exercise_image_url(str(exercise["name"])),
                        caption=f"Demostración: {exercise['name']}",
                        width="stretch",
                    )


def render_smart_cardio(goal: str) -> None:
    """Muestra una propuesta de cinta determinista según el objetivo del perfil."""
    recommendation = CARDIO_RECOMMENDATIONS.get(goal, CARDIO_RECOMMENDATIONS["Hipertrofia"])
    st.divider()
    st.markdown("### 🏃 Cardio Inteligente")
    st.caption("Propuesta automática de cinta basada en el objetivo guardado en tu Perfil.")
    with st.container(border=True):
        duration_column, activity_column = st.columns([0.35, 0.65])
        duration_column.metric("Duración propuesta", recommendation["duration"])
        with activity_column:
            st.markdown(f"#### {recommendation['title']}")
            st.write(recommendation["detail"])
        st.caption(
            "La propuesta es orientativa: reduce la intensidad o detente si aparece dolor, mareo "
            "o una sensación anormal."
        )


def current_core_plan(multiplier: float) -> dict[str, str | bool]:
    """Devuelve el trabajo de core correspondiente al día actual."""
    weekday = WEEKDAYS[datetime.now().weekday()]
    exercise, prescription, instruction = CORE_BY_WEEKDAY[weekday]
    return {
        "weekday": weekday,
        "exercise": exercise,
        "prescription": prescription,
        "instruction": instruction,
        "omitted": multiplier <= 0.5,
    }


def render_daily_core(multiplier: float) -> None:
    """Rota el trabajo de core con el día real y respeta el filtro de recuperación."""
    core = current_core_plan(multiplier)
    st.divider()
    st.markdown("### 🔥 Core & Abdominales")
    st.caption(f"Bloque rotativo de {core['weekday']}, coordinado con el filtro anti-sobreentrenamiento.")
    with st.container(border=True):
        if core["omitted"]:
            st.warning("Hoy se omite el bloque de core: el check-in indica descanso obligatorio.")
            return
        st.markdown(f"#### {core['exercise']}")
        st.metric("Trabajo propuesto", str(core["prescription"]))
        st.write(str(core["instruction"]))


def profile_details() -> None:
    """Formulario y resultados del perfil, aislados del Tutor IA."""
    st.write("Introduce tus datos para obtener una estimación inicial de energía y macros.")
    with st.form("profile_form"):
        left, right = st.columns(2)
        with left:
            age = st.number_input("Edad", min_value=16, max_value=100, value=25)
            weight = st.number_input("Peso (kg)", min_value=35.0, max_value=250.0, value=70.0, step=0.1)
            height = st.number_input("Altura (cm)", min_value=130.0, max_value=230.0, value=175.0, step=0.5)
        with right:
            sex = st.selectbox("Sexo (para la fórmula basal)", ["Hombre", "Mujer"])
            goal = st.selectbox(
                "Objetivo",
                list(GOAL_ADJUSTMENTS),
                help="Volumen ayuda a subir peso; Definición busca bajar grasa manteniendo una proteína alta.",
            )
            activity = st.selectbox("Nivel de actividad", list(ACTIVITY_FACTORS))
            meals_per_day = st.radio(
                "¿Cuántas comidas prefieres hacer al día?",
                [4, 5],
                horizontal=True,
                help="Las calorías y macros no cambian: solo se reparten entre más o menos comidas.",
            )
        st.caption(f"🎯 {goal}: {GOAL_EXPLANATIONS[goal]}")
        submitted = st.form_submit_button("💾 Guardar perfil y calcular", width="stretch")

    if submitted:
        nutrition = calculate_nutrition(age, weight, height, sex, activity, goal)
        st.session_state.profile = {
            "age": age,
            "weight": weight,
            "height": height,
            "sex": sex,
            "activity": activity,
            "goal": goal,
            "meals_per_day": meals_per_day,
            "nutrition": nutrition,
        }
        st.success("Perfil guardado. Ya puedes abrir el Check-in diario.")

    if "profile" in st.session_state:
        result = st.session_state.profile["nutrition"]
        if st.session_state.profile["age"] >= 50:
            st.success(
                "🛡️ Perfil 50+: en el Check-in priorizaremos máquinas guiadas para aportar más "
                "estabilidad y facilitar el control del movimiento. Ningún equipo elimina por completo el riesgo. "
                "Si tienes patologías, dolor, limitaciones o vuelves tras inactividad, consulta antes con un "
                "profesional sanitario y pide supervisión para ajustar asiento, recorrido y carga."
            )
        st.subheader("Estimación diaria inicial")
        a, b, c, d = st.columns(4)
        a.metric("Calorías", f"{result['calories']} kcal")
        b.metric("Proteína", f"{result['protein_g']:.1f} g")
        c.metric("Carbohidratos", f"{result['carbs_g']:.1f} g")
        d.metric("Grasas", f"{result['fat_g']:.1f} g")
        st.caption(
            f"Metabolismo basal estimado: {result['bmr']} kcal. "
            f"Mantenimiento estimado: {result['maintenance']} kcal. "
            f"Menú elegido: {st.session_state.profile.get('meals_per_day', 4)} comidas."
        )


def profile_page() -> None:
    st.header("1. Tu perfil")
    profile_tab, tutor_tab = st.tabs(["👤 Datos y objetivos", "💬 Tutor IA"])
    with profile_tab:
        profile_details()
    with tutor_tab:
        tutor_page(embedded=True)


def cooking_suggestions(meal: str, recipe: str, foods: set[str]) -> list[str]:
    """Genera ideas culinarias locales usando los ingredientes de la propia comida."""
    suggestions = [f"🍽️ **Plato principal:** prepara {recipe.lower()} y reparte exactamente las cantidades indicadas."]
    if "Avena seca" in foods and "Huevo entero" in foods:
        suggestions.append("🥞 **Alternativa:** tritura la avena, el huevo y el plátano para hacer tortitas en sartén.")
        suggestions.append("☕ **Snack rápido:** cocina la misma mezcla en una taza durante 1-2 minutos para un mugcake.")
    elif "Avena seca" in foods and "Leche semidesnatada" in foods:
        suggestions.append("🥣 **Alternativa:** deja avena y leche en frío durante la noche para un porridge rápido.")
    if "Plátano" in foods and "Leche semidesnatada" in foods:
        suggestions.append("🥤 **Opción rápida:** bate el plátano con la leche; añade la avena si quieres más textura.")
    if "Miel" in foods:
        suggestions.append("🍯 **Topping:** reparte la miel calculada sobre las tortitas, el porridge o el batido del día.")
    if "Pan integral" in foods:
        suggestions.append("🥪 **Sándwich fit:** tuesta el pan y prepara un sándwich ligero respetando la ración calculada.")
    if "Manzana" in foods:
        suggestions.append("🍎 **Snack práctico:** lleva la manzana entera o córtala en gajos junto al sándwich.")
    if "Yogur griego natural 0%" in foods and "Fresas" in foods:
        suggestions.append("🍓 **Bol proteico:** mezcla el yogur con las fresas y sírvelo bien frío.")
    if "Tortitas de arroz" in foods:
        suggestions.append("🍘 **Aperitivo crujiente:** usa las tortitas de arroz como base y acompáñalas con el bol.")
    if "Almendras" in foods:
        suggestions.append("🌰 **Topping medido:** trocea las almendras sobre el yogur sin superar los gramos indicados.")
    if "Arroz blanco cocido" in foods:
        suggestions.append("🍚 **Idea de cocina:** saltea el arroz con especias y la proteína ya cocinada, sin añadir otro aceite.")
        suggestions.append("⚡ **Aperitivo rápido:** reserva parte del arroz calculado y sírvelo como mini bowl; no suma macros extra.")
    if "Pasta integral cocida" in foods:
        suggestions.append("🍝 **Idea de cocina:** sirve la pasta templada con hierbas y la única proteína indicada en el plato.")
        suggestions.append("⚡ **Aperitivo rápido:** aparta una pequeña porción como ensalada fría, dentro de los gramos calculados.")
    if "Patata cocida" in foods:
        suggestions.append("🥔 **Idea de cocina:** termina la patata en horno o airfryer con especias y el aceite asignado.")
        suggestions.append("⚡ **Aperitivo rápido:** corta parte de la patata en dados crujientes usando la misma ración del plato.")
    if meal in ("Comida (Mediodía)", "Cena"):
        suggestions.append("🥗 **Acompañamiento libre:** añade verduras sin sustituir ni mezclar la proteína principal calculada.")
    return suggestions[:4]


def render_menu_by_meal(menu_rows: list[dict[str, float | str]]) -> None:
    """Presenta las comidas disponibles en pestañas horizontales compactas."""
    meal_sections = [
        ("Desayuno", "🌅"),
        ("Media Mañana", "🥛"),
        ("Comida (Mediodía)", "🍽️"),
        ("Merienda", "🍌"),
        ("Cena", "🌙"),
    ]
    visible_sections = [
        (meal, icon, [row for row in menu_rows if row["Comida"] == meal])
        for meal, icon in meal_sections
        if any(row["Comida"] == meal for row in menu_rows)
    ]
    tabs = st.tabs(
        [
            f"{icon} {'Comida' if meal == 'Comida (Mediodía)' else meal}"
            for meal, icon, _ in visible_sections
        ]
    )
    for tab, (meal, icon, meal_rows) in zip(tabs, visible_sections):
        with tab:
            st.markdown(f"### {icon} {meal}")
            recipes = list(dict.fromkeys(str(row.get("Receta", "Plato personalizado")) for row in meal_rows))
            st.markdown(f"#### 🍲 {' + '.join(recipes)}")
            st.caption("Una receta completa con cantidades exactas y referencias fáciles para cocinar.")
            display_rows = [
                {key: value for key, value in row.items() if key not in ("Comida", "Receta")}
                for row in meal_rows
            ]
            st.dataframe(display_rows, width="stretch", hide_index=True)
            total_grams = sum(float(row["Gramos"]) for row in meal_rows)
            protein = sum(float(row["Proteína (g)"]) for row in meal_rows)
            carbs = sum(float(row["Carbohidratos (g)"]) for row in meal_rows)
            fat = sum(float(row["Grasas (g)"]) for row in meal_rows)
            st.caption(
                f"Total: {total_grams:.1f} g de alimentos · "
                f"P {protein:.1f} g · C {carbs:.1f} g · G {fat:.1f} g"
            )
            foods = {str(row["Alimento"]) for row in meal_rows}
            with st.expander("🍳 Sugerencias de Cocina y Snacks"):
                for suggestion in cooking_suggestions(meal, recipes[0], foods):
                    st.markdown(suggestion)


def build_shopping_list(
    weekly_menus: dict[str, list[dict[str, float | str]]],
) -> dict[str, list[dict[str, float | str]]]:
    """Suma los gramos visibles de los siete días y los agrupa para el supermercado."""
    totals: dict[str, float] = {}
    for rows in weekly_menus.values():
        for row in rows:
            food = str(row["Alimento"])
            totals[food] = totals.get(food, 0.0) + float(row["Gramos"])

    shopping: dict[str, list[dict[str, float | str]]] = {}
    assigned_foods: set[str] = set()
    for category, category_foods in SHOPPING_CATEGORIES.items():
        items = []
        for food in sorted(category_foods.intersection(totals)):
            grams = round(totals[food], 2)
            items.append(
                {
                    "Alimento": food,
                    "Total exacto (g)": grams,
                    "Equivalencia": f"{grams / 1000:.2f} kg" if grams >= 1000 else f"{grams:.2f} g",
                }
            )
            assigned_foods.add(food)
        if items:
            shopping[category] = items

    remaining = sorted(set(totals).difference(assigned_foods))
    if remaining:
        shopping["Otros"] = [
            {
                "Alimento": food,
                "Total exacto (g)": round(totals[food], 2),
                "Equivalencia": f"{totals[food] / 1000:.2f} kg" if totals[food] >= 1000 else f"{totals[food]:.2f} g",
            }
            for food in remaining
        ]
    return shopping


def weekly_plan_pdf(
    weekly_menus: dict[str, list[dict[str, float | str]]],
    shopping_list: dict[str, list[dict[str, float | str]]],
    nutrition: dict[str, float],
    goal: str,
) -> bytes:
    """Crea un PDF profesional e imprimible sin servicios externos."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=16 * mm,
        bottomMargin=15 * mm,
        title="Plan semanal SmartFit AI",
        author="SmartFit AI",
    )
    stylesheet = getSampleStyleSheet()
    lime = colors.HexColor("#9BCB20")
    charcoal = colors.HexColor("#151A1E")
    slate = colors.HexColor("#E9EDF0")
    title_style = ParagraphStyle(
        "SmartFitTitle",
        parent=stylesheet["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=charcoal,
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    day_style = ParagraphStyle(
        "SmartFitDay",
        parent=stylesheet["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        textColor=charcoal,
        spaceAfter=7,
    )
    meal_style = ParagraphStyle(
        "SmartFitMeal",
        parent=stylesheet["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#50630B"),
        spaceBefore=5,
        spaceAfter=3,
    )
    body_style = ParagraphStyle(
        "SmartFitBody",
        parent=stylesheet["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=charcoal,
    )
    small_style = ParagraphStyle(
        "SmartFitSmall",
        parent=body_style,
        fontSize=7,
        leading=9,
    )

    story = [
        Paragraph("SMARTFIT AI", title_style),
        Paragraph("Plan nutricional semanal", day_style),
        Table(
            [
                ["Objetivo", "Calorías/día", "Proteína/día", "Carbohidratos/día", "Grasas/día"],
                [
                    escape(goal),
                    f"{nutrition['calories']} kcal",
                    f"{nutrition['protein_g']:.1f} g",
                    f"{nutrition['carbs_g']:.1f} g",
                    f"{nutrition['fat_g']:.1f} g",
                ],
            ],
            colWidths=[34 * mm, 34 * mm, 34 * mm, 39 * mm, 31 * mm],
        ),
        Spacer(1, 5 * mm),
        Paragraph(
            "Cantidades calculadas por día. Los valores son orientativos y no sustituyen a un dietista-nutricionista.",
            body_style,
        ),
        PageBreak(),
    ]

    meal_order = ("Desayuno", "Media Mañana", "Comida (Mediodía)", "Merienda", "Cena")
    for day_index, day in enumerate(WEEKDAYS):
        rows = weekly_menus[day]
        story.append(Paragraph(escape(day), day_style))
        for meal in meal_order:
            meal_rows = [row for row in rows if row["Comida"] == meal]
            if not meal_rows:
                continue
            recipes = " + ".join(dict.fromkeys(str(row["Receta"]) for row in meal_rows))
            story.append(Paragraph(f"{escape(meal)} - {escape(recipes)}", meal_style))
            table_data = [["Alimento", "g", "P", "C", "G"]]
            table_data.extend(
                [
                    Paragraph(escape(str(row["Alimento"])), small_style),
                    f"{float(row['Gramos']):.2f}",
                    f"{float(row['Proteína (g)']):.2f}",
                    f"{float(row['Carbohidratos (g)']):.2f}",
                    f"{float(row['Grasas (g)']):.2f}",
                ]
                for row in meal_rows
            )
            meal_table = Table(
                table_data,
                colWidths=[76 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm],
                repeatRows=1,
            )
            meal_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), charcoal),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#AEB7BD")),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, slate]),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.extend([meal_table, Spacer(1, 2.2 * mm)])
        if day_index < len(WEEKDAYS) - 1:
            story.append(PageBreak())

    story.extend([PageBreak(), Paragraph("Lista de la compra semanal", day_style)])
    for category, items in shopping_list.items():
        story.append(Paragraph(escape(category), meal_style))
        category_table = Table(
            [["Alimento", "Total exacto", "Referencia"]]
            + [
                [
                    Paragraph(escape(str(item["Alimento"])), body_style),
                    f"{float(item['Total exacto (g)']):.2f} g",
                    escape(str(item["Equivalencia"])),
                ]
                for item in items
            ],
            colWidths=[83 * mm, 40 * mm, 41 * mm],
            repeatRows=1,
        )
        category_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), charcoal),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#AEB7BD")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, slate]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.extend([category_table, Spacer(1, 4 * mm)])

    def draw_page(canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(lime)
        canvas.setLineWidth(1.3)
        canvas.line(14 * mm, 11 * mm, 196 * mm, 11 * mm)
        canvas.setFillColor(charcoal)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(14 * mm, 7 * mm, "SmartFit AI - Plan semanal")
        canvas.drawRightString(196 * mm, 7 * mm, f"Página {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    buffer.seek(0)
    return buffer.getvalue()


def training_plan_pdf(plan: dict) -> bytes:
    """Compila la rutina elegida, cardio, core y descansos en un PDF independiente."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=16 * mm,
        bottomMargin=15 * mm,
        title="Plan de entrenamiento SmartFit AI",
        author="SmartFit AI",
    )
    stylesheet = getSampleStyleSheet()
    charcoal = colors.HexColor("#151A1E")
    lime = colors.HexColor("#9BCB20")
    slate = colors.HexColor("#E9EDF0")
    title_style = ParagraphStyle(
        "TrainingTitle",
        parent=stylesheet["Title"],
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=25,
        textColor=charcoal,
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    heading_style = ParagraphStyle(
        "TrainingHeading",
        parent=stylesheet["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#50630B"),
        spaceBefore=7,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "TrainingBody",
        parent=stylesheet["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=charcoal,
    )
    small_style = ParagraphStyle("TrainingSmall", parent=body_style, fontSize=7, leading=9)
    goal = str(plan.get("goal", "Hipertrofia"))
    rest_text = REST_BY_GOAL.get(goal, REST_BY_GOAL["Hipertrofia"])
    story = [
        Paragraph("SMARTFIT AI", title_style),
        Paragraph("Plan de entrenamiento de hoy", heading_style),
        Paragraph(
            f"Sesión: {escape(str(plan.get('division', 'Personalizada')))} | "
            f"Objetivo: {escape(goal)} | Volumen aplicado: {round(float(plan['multiplier']) * 100)}%",
            body_style,
        ),
        Spacer(1, 4 * mm),
    ]
    table_data: list[list[object]] = [["Ejercicio", "Equipo", "Series", "Reps", "Carga", "1RM"]]
    rest_rows: list[int] = []
    for exercise in plan["exercises"]:
        name = str(exercise["name"])
        strength = plan["strength_data"].get(name, {})
        one_rm = float(strength.get("one_rm", 0))
        load = suggested_weight(one_rm, float(plan["multiplier"])) if one_rm else 0.0
        table_data.append(
            [
                Paragraph(escape(name), small_style),
                Paragraph(escape(exercise_equipment_label(exercise)), small_style),
                str(adjusted_sets(int(exercise["sets"]), float(plan["multiplier"]))),
                escape(str(exercise["reps"])),
                f"{load:.1f} kg" if load else "Pendiente",
                f"{one_rm:.1f} kg" if one_rm else "Pendiente",
            ]
        )
        rest_rows.append(len(table_data))
        table_data.append([Paragraph(escape(rest_text), small_style), "", "", "", "", ""])
    workout_table = Table(
        table_data,
        colWidths=[55 * mm, 37 * mm, 15 * mm, 20 * mm, 27 * mm, 27 * mm],
        repeatRows=1,
    )
    table_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), charcoal),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#AEB7BD")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for row in rest_rows:
        table_commands.extend(
            [
                ("SPAN", (0, row), (-1, row)),
                ("BACKGROUND", (0, row), (-1, row), slate),
                ("ALIGN", (0, row), (-1, row), "LEFT"),
            ]
        )
    workout_table.setStyle(TableStyle(table_commands))
    story.extend([workout_table, Spacer(1, 4 * mm)])

    cardio = CARDIO_RECOMMENDATIONS.get(goal, CARDIO_RECOMMENDATIONS["Hipertrofia"])
    story.extend(
        [
            Paragraph("Cardio inteligente", heading_style),
            Paragraph(
                f"{escape(str(cardio['title']))}: {escape(str(cardio['duration']))}. "
                f"{escape(str(cardio['detail']))}",
                body_style,
            ),
        ]
    )
    core = current_core_plan(float(plan["multiplier"]))
    story.append(Paragraph("Core y abdominales", heading_style))
    if core["omitted"]:
        story.append(Paragraph("Bloque omitido por descanso obligatorio indicado en el check-in.", body_style))
    else:
        story.append(
            Paragraph(
                f"{escape(str(core['exercise']))}: {escape(str(core['prescription']))}. "
                f"{escape(str(core['instruction']))}",
                body_style,
            )
        )

    def draw_page(canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(lime)
        canvas.setLineWidth(1.3)
        canvas.line(14 * mm, 11 * mm, 196 * mm, 11 * mm)
        canvas.setFillColor(charcoal)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(14 * mm, 7 * mm, "SmartFit AI - Entrenamiento")
        canvas.drawRightString(196 * mm, 7 * mm, f"Página {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    buffer.seek(0)
    return buffer.getvalue()


def render_rest_timer() -> None:
    """Muestra un temporizador de descanso en tiempo real sin bloquear Streamlit."""
    st.divider()
    st.markdown("### ⏱️ Temporizador de descanso")
    seconds = st.selectbox(
        "Selecciona el descanso",
        [60, 90, 120, 180],
        format_func=lambda value: f"{value} segundos",
        key="rest_timer_seconds",
    )
    components.html(
        f"""
        <div class="timer-card">
          <div id="timer-display">{seconds // 60:02d}:{seconds % 60:02d}</div>
          <button id="timer-button" onclick="startTimer()">Iniciar cuenta atrás</button>
          <div id="timer-finished" role="alert">¡Descanso completado! Empieza la siguiente serie.</div>
        </div>
        <style>
          body {{ margin: 0; background: transparent; font-family: Montserrat, Arial, sans-serif; }}
          .timer-card {{ padding: 20px; text-align: center; color: #fff; border-radius: 18px;
            border: 1px solid rgba(217,255,50,.55); background: rgba(18,18,18,.55);
            backdrop-filter: blur(8px); box-shadow: 0 14px 34px rgba(0,0,0,.34); }}
          #timer-display {{ font-size: 54px; font-weight: 800; letter-spacing: .08em; color: #37f29b; }}
          #timer-button {{ margin-top: 12px; padding: 13px 24px; border: 0; border-radius: 12px;
            background: linear-gradient(135deg,#d9ff32,#37f29b); color:#07100b; font-weight:800;
            cursor:pointer; transition: transform .18s ease, filter .18s ease; }}
          #timer-button:hover {{ transform: translateY(-2px) scale(1.03); filter: brightness(1.08); }}
          #timer-finished {{ display:none; margin-top:14px; padding:12px; border-radius:12px;
            color:#07100b; background:#d9ff32; font-weight:800; }}
          #timer-finished.done {{ display:block; animation:pulse 1s ease-in-out infinite alternate; }}
          @keyframes pulse {{ from {{ transform:scale(1); box-shadow:0 0 0 rgba(217,255,50,0); }}
            to {{ transform:scale(1.025); box-shadow:0 0 24px rgba(217,255,50,.65); }} }}
        </style>
        <script>
          let intervalId = null;
          function startTimer() {{
            clearInterval(intervalId);
            let remaining = {seconds};
            const display = document.getElementById('timer-display');
            const finished = document.getElementById('timer-finished');
            const button = document.getElementById('timer-button');
            finished.classList.remove('done'); button.textContent = 'Reiniciar cuenta atrás';
            const paint = () => {{
              const minutes = Math.floor(remaining / 60).toString().padStart(2,'0');
              const secondsPart = (remaining % 60).toString().padStart(2,'0');
              display.textContent = `${{minutes}}:${{secondsPart}}`;
            }};
            paint();
            intervalId = setInterval(() => {{
              remaining -= 1; paint();
              if (remaining <= 0) {{ clearInterval(intervalId); finished.classList.add('done');
                button.textContent = 'Iniciar de nuevo'; }}
            }}, 1000);
          }}
        </script>
        """,
        height=265,
    )


def render_weekly_menu(plan: dict) -> None:
    """Muestra siete días, la compra consolidada y el PDF descargable."""
    weekly_menus = plan["weekly_menus"]
    st.markdown("### 📅 Planificador semanal completo")
    st.caption(
        "Cada día conserva exactamente tus macros; desayuno, proteína, carbohidrato principal y cada "
        "snack rotan para evitar dos jornadas consecutivas iguales."
    )
    day_tabs = st.tabs([f"📆 {day}" for day in WEEKDAYS])
    for tab, day in zip(day_tabs, WEEKDAYS):
        with tab:
            rows = weekly_menus[day]
            st.markdown(f"## {day}")
            day_protein = sum(float(row["Proteína (g)"]) for row in rows)
            day_carbs = sum(float(row["Carbohidratos (g)"]) for row in rows)
            day_fat = sum(float(row["Grasas (g)"]) for row in rows)
            st.caption(
                f"Macros del día: P {day_protein:.1f} g · C {day_carbs:.1f} g · G {day_fat:.1f} g"
            )
            render_menu_by_meal(rows)

    shopping_list = build_shopping_list(weekly_menus)
    st.divider()
    st.markdown("### 🛒 Lista de la compra para 7 días")
    st.caption("Suma exacta de todos los gramos mostrados en el plan semanal, agrupada por pasillos.")
    for category, items in shopping_list.items():
        with st.expander(f"🧺 {category}", expanded=True):
            st.dataframe(items, width="stretch", hide_index=True)

    pdf_bytes = weekly_plan_pdf(
        weekly_menus,
        shopping_list,
        plan["nutrition"],
        plan.get("goal", "Objetivo personalizado"),
    )
    st.download_button(
        "📄 Descargar Plan Semanal en PDF",
        data=pdf_bytes,
        file_name="SmartFit_AI_Plan_Semanal.pdf",
        mime="application/pdf",
        type="primary",
        width="stretch",
        key="download_weekly_plan_pdf",
    )


def render_daily_plan(plan: dict) -> None:
    nutrition = plan["nutrition"]
    if "weekly_menus" not in plan:
        plan["weekly_menus"] = build_weekly_menu(
            nutrition,
            st.session_state.get("excluded_foods", set()),
            plan.get("meals_per_day", 4),
        )
        plan["menu_rows"] = plan["weekly_menus"]["Lunes"]
    st.subheader(plan["status"])
    left, right = st.columns(2)
    left.metric("Volumen recomendado", f"{round(plan['multiplier'] * 100)}% de la sesión base")
    right.metric("Calorías de hoy", f"{nutrition['calories']} kcal")
    st.info(plan["advice"])

    training_tab, diet_tab = st.tabs(["🏋️ Entrenamiento", "🍽️ Dieta inteligente"])
    with training_tab:
        if plan["multiplier"] == 0:
            st.warning("No se ha generado ningún plan de entrenamiento.")
        else:
            st.subheader(f"Sesión sugerida: {plan['division']}")
            render_workout_cards(
                plan["exercises"],
                plan["multiplier"],
                plan["strength_data"],
                plan.get("goal", "Hipertrofia"),
            )
            st.caption(
                f"Puntuación de fatiga: {plan['score']}. Las series base se multiplican por el filtro "
                "de recuperación y se redondean hacia arriba."
            )
            render_daily_core(plan["multiplier"])
            render_smart_cardio(plan.get("goal", "Hipertrofia"))
            st.download_button(
                "📥 Descargar Plan de Entrenamiento en PDF",
                data=training_plan_pdf(plan),
                file_name="SmartFit_AI_Entrenamiento_Hoy.pdf",
                mime="application/pdf",
                type="primary",
                width="stretch",
                key="download_training_plan_pdf",
            )
            render_rest_timer()

    with diet_tab:
        st.subheader("Plan nutricional semanal dinámico")
        st.caption(
            f"{plan.get('goal', 'Objetivo')}: "
            f"{GOAL_EXPLANATIONS.get(plan.get('goal', ''), 'macros adaptados a tu perfil.')} "
            f"Cada jornada se reparte en {plan.get('meals_per_day', 4)} comidas sin cambiar tus macros diarios."
        )
        p, c, f = st.columns(3)
        p.metric("Proteína", f"{nutrition['protein_g']:.1f} g")
        c.metric("Carbohidratos", f"{nutrition['carbs_g']:.1f} g")
        f.metric("Grasas", f"{nutrition['fat_g']:.1f} g")
        if plan["recovery_day"]:
            st.warning(
                f"Día de recuperación: carbohidratos reducidos un 25% "
                f"({nutrition['base_carbs_g']:.1f} g → {nutrition['carbs_g']:.1f} g)."
            )
        render_weekly_menu(plan)
        st.caption(
            "Cada comida se resuelve matemáticamente; cada día completo suma los macros diarios del perfil."
        )
        with st.expander("Base fija de alimentos - macros por 100 g"):
            database_rows = [
                {
                    "Alimento": name,
                    "FDC ID": data["fdc_id"],
                    "Proteína (g)": data["protein"],
                    "Carbohidratos (g)": data["carbs"],
                    "Grasas (g)": data["fat"],
                }
                for name, data in FOOD_DATABASE.items()
            ]
            st.dataframe(database_rows, width="stretch", hide_index=True)


def checkin_page() -> None:
    st.header("2. Check-in diario")
    st.info(
        "💡 NOTA DE ASISTENCIA: En caso de que prefieras no consumir los datos de tu tarifa móvil o si "
        "la cobertura dentro de la sala de tu gimnasio no es buena, puedes descargar tu Dieta Semanal y "
        "tu Plan de Entrenamiento de hoy en formato PDF para tenerlos siempre a mano y utilizarlos sin "
        "necesidad de conexión a internet."
    )
    if "profile" not in st.session_state:
        st.info("Completa primero tu perfil para personalizar la sesión.")
        return

    st.write("El volumen se ajusta solo a partir del sueño y las molestias reportadas.")
    profile = st.session_state.profile
    st.caption(f"🎯 {profile['goal']}: {GOAL_EXPLANATIONS[profile['goal']]}")
    sleep = st.slider("¿Cuántas horas has dormido?", 0.0, 12.0, 7.0, 0.5)
    discomfort = st.radio("¿Tienes molestias?", ["Sin molestias", "Molestia leve", "Dolor Agudo"])
    score = fatigue_score(sleep, discomfort)
    multiplier, status, advice = recovery_plan(score, discomfort)
    prioritize_guided = st.session_state.profile["age"] >= 50
    if prioritize_guided:
        st.success(
            "🛡️ Modo de estabilidad 50+ activado: las máquinas guiadas aparecen primero y son "
            "la selección inicial. Ajusta asiento y recorrido sin dolor; si tienes una condición médica o "
            "limitaciones de movilidad, consulta a un profesional sanitario antes de entrenar."
        )
    division = st.selectbox("¿Qué vas a entrenar hoy?", ["Tren Superior", "Tren Inferior"])
    if division == "Tren Superior":
        upper_selection = st.selectbox(
            "Selecciona el bloque del tren superior",
            ["Empuje", "Tirón"],
            help="Empuje agrupa pecho, hombro y tríceps; Tirón agrupa espalda y bíceps.",
        )
        st.info(MOVEMENT_EXPLANATIONS[upper_selection])
        available_exercises = exercises_for_block(upper_selection, prioritize_guided)
        training_label = f"{division} · {upper_selection}"
    else:
        upper_selection = "Tren Inferior"
        available_exercises = exercises_for_block("Tren Inferior", prioritize_guided)
        training_label = division

    exercise_lookup = {str(exercise["name"]): exercise for exercise in available_exercises}
    selected_names = st.multiselect(
        "Elige los ejercicios que realizarás hoy",
        options=list(exercise_lookup),
        default=list(exercise_lookup)[:3],
        format_func=lambda name: (
            f"🛡️ {exercise_equipment_label(exercise_lookup[name])} · {name}"
            if exercise_lookup[name]["guided"]
            else f"🏋️ {exercise_equipment_label(exercise_lookup[name])} · {name}"
        ),
        help="Puedes combinar libremente los movimientos disponibles del bloque elegido.",
    )
    session_exercises = [exercise_lookup[name] for name in selected_names]

    st.info(f"{status}: {advice}")
    strength_data = (
        strength_inputs_for_session(session_exercises, multiplier)
        if session_exercises and multiplier > 0
        else {}
    )
    if not session_exercises:
        st.warning("Selecciona al menos un ejercicio para construir la sesión.")
    if multiplier == 0:
        st.error("El plan está bloqueado por Dolor Agudo; no se calcularán cargas ni entrenamiento.")

    if st.button(
        "⚡ Calcular sesión y menú de hoy",
        type="primary",
        disabled=not session_exercises,
        width="stretch",
    ):
        recovery_day = multiplier <= 0.5
        nutrition = calculate_nutrition(
            profile["age"], profile["weight"], profile["height"], profile["sex"],
            profile["activity"], profile["goal"], reduce_carbs=recovery_day,
        )
        exclusions = st.session_state.get("excluded_foods", set())
        try:
            weekly_menus = build_weekly_menu(
                nutrition,
                exclusions,
                profile.get("meals_per_day", 4),
            )
        except ValueError as error:
            st.error(str(error))
            return
        st.session_state.daily_plan = {
            "nutrition": nutrition,
            "menu_rows": weekly_menus["Lunes"],
            "weekly_menus": weekly_menus,
            "goal": profile["goal"],
            "meals_per_day": profile.get("meals_per_day", 4),
            "score": score,
            "multiplier": multiplier,
            "status": status,
            "advice": advice,
            "division": training_label,
            "exercises": session_exercises,
            "strength_data": strength_data,
            "recovery_day": recovery_day,
        }

    if "daily_plan" in st.session_state:
        render_daily_plan(st.session_state.daily_plan)


def tutor_page(embedded: bool = False) -> None:
    """Chat local para exclusiones alimentarias; no usa llamadas a modelos de IA."""
    if embedded:
        st.markdown("## ¡Cocina Conmigo!")
        st.markdown(
            "En este apartado puedes poner qué parte de tu dieta no sabes cómo preparar y el Tutor IA "
            "se encargará de darte la receta paso a paso con todo lo que tienes que hacer."
        )
        st.caption("También puedes indicar una alergia, intolerancia o alimento que no te guste para ajustar el menú activo.")
    else:
        st.header("¡Cocina Conmigo!")
        st.markdown(
            "En este apartado puedes poner qué parte de tu dieta no sabes cómo preparar y el Tutor IA "
            "se encargará de darte la receta paso a paso con todo lo que tienes que hacer."
        )
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {
                "role": "assistant",
                "content": (
                    "Hola. Pregúntame cómo preparar cualquier plato de tu menú y te daré los ingredientes exactos, "
                    "sus macros y los pasos. También puedo gestionar alergias o alimentos que no te gusten."
                ),
            }
        ]
    if "excluded_foods" not in st.session_state:
        st.session_state.excluded_foods = set()

    for message in st.session_state.chat_history:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.write(message["content"])

    # Contraste estricto para las entradas renderizadas dentro de la vista del Tutor IA.
    st.markdown(
        """
        <style>
        /* Fuerza el color de la caja de texto en cualquier estado (activo o deshabilitado) */
        .stTextInput input,
        .stTextInput input:disabled,
        [data-testid="stTextInput"] input {
            color: #111111 !important;
            -webkit-text-fill-color: #111111 !important;
            background-color: #ffffff !important;
            opacity: 1 !important;
        }

        /* Fuerza que el texto de ejemplo (placeholder) sea gris oscuro bien visible */
        .stTextInput input::placeholder,
        [data-testid="stTextInput"] input::placeholder {
            color: #555555 !important;
            -webkit-text-fill-color: #555555 !important;
            opacity: 1 !important;
        }

        /* Streamlit renderiza la barra inferior del Tutor como este textarea. */
        [data-testid="stChatInput"] {
            background-color: #ffffff !important;
        }
        [data-testid="stChatInputTextArea"],
        [data-testid="stChatInputTextArea"]:hover,
        [data-testid="stChatInputTextArea"]:focus,
        [data-testid="stChatInputTextArea"]:focus-visible,
        [data-testid="stChatInputTextArea"]:active,
        [data-testid="stChatInputTextArea"]:disabled,
        [data-testid="stChatInputTextArea"]:autofill,
        [data-testid="stChatInputTextArea"]:-webkit-autofill {
            color: #111111 !important;
            -webkit-text-fill-color: #111111 !important;
            background-color: #ffffff !important;
            caret-color: #111111 !important;
            opacity: 1 !important;
            text-shadow: none !important;
        }
        [data-testid="stChatInputTextArea"]::placeholder {
            color: #555555 !important;
            -webkit-text-fill-color: #555555 !important;
            opacity: 1 !important;
        }
        [data-testid="stChatInputTextArea"]::spelling-error,
        [data-testid="stChatInputTextArea"]::grammar-error {
            color: #111111 !important;
            -webkit-text-fill-color: #111111 !important;
            background-color: transparent !important;
            text-decoration-color: #d93025 !important;
        }
        [data-testid="stChatInputTextArea"]::selection {
            color: #111111 !important;
            -webkit-text-fill-color: #111111 !important;
            background-color: #b9e7ff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    prompt = st.chat_input("Ej.: “¿Cómo preparo mi desayuno?” o “No me gusta el salmón”")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.write(prompt)

        cooking_request = is_cooking_request(prompt)
        spinner_text = "Preparando tu receta con los gramos y macros exactos..." if cooking_request else "Analizando perfil y alérgenos..."
        with st.spinner(spinner_text):
            time.sleep(3)
            plan = st.session_state.get("daily_plan")
            if cooking_request:
                answer = build_cooking_response(prompt, plan)
                food_to_exclude = None
            else:
                answer, food_to_exclude = tutor_response(prompt)
            if food_to_exclude and food_to_exclude in FOOD_DATABASE and plan:
                previous_exclusions = set(st.session_state.excluded_foods)
                st.session_state.excluded_foods.add(food_to_exclude)
                try:
                    plan["weekly_menus"] = build_weekly_menu(
                        plan["nutrition"],
                        st.session_state.excluded_foods,
                        plan.get("meals_per_day", 4),
                    )
                    plan["menu_rows"] = plan["weekly_menus"]["Lunes"]
                    answer += " He eliminado el ingrediente y recalculado los siete días con alternativas equivalentes de la base fija."
                except ValueError:
                    st.session_state.excluded_foods = previous_exclusions
                    answer += " No quedan suficientes combinaciones para sustituirlo sin romper los macros; mantengo el menú anterior."
            elif food_to_exclude and food_to_exclude not in FOOD_DATABASE:
                answer += " Ese ingrediente no forma parte de la base de alimentos que calcula el menú actual."
            elif food_to_exclude and not plan:
                answer += " Completa primero el Check-in para que pueda aplicar la exclusión al menú del día."

        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant", avatar="🤖"):
            response_placeholder = st.empty()
            rendered = ""
            for token in re.findall(r"\S+\s*", answer):
                rendered += token
                response_placeholder.markdown(rendered + "▌")
                time.sleep(0.035)
            response_placeholder.markdown(rendered)

    plan = st.session_state.get("daily_plan")
    if plan:
        st.subheader("Menú del lunes actualizado")
        st.caption("El resto de la semana también se ha recalculado y está disponible en el Check-in.")
        render_menu_by_meal(plan["menu_rows"])
    else:
        st.info("Aún no hay un menú activo. Completa el Check-in diario para crear uno.")


def apply_premium_styles() -> None:
    """Aplica una identidad visual oscura y neón sin alterar los cálculos."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&family=Oswald:wght@500;600;700&display=swap');

        :root {
            --gym-bg: #080b0d;
            --gym-panel: #11161a;
            --gym-panel-soft: #171d21;
            --gym-lime: #d9ff32;
            --gym-green: #37f29b;
            --gym-orange: #ff7a18;
            --gym-text: #ffffff;
            --gym-muted: #e0e0e0;
        }

        .stApp {
            background-color: #07090b;
            background-image:
                radial-gradient(ellipse at center, rgba(4, 7, 9, 0.10) 0%, rgba(3, 5, 7, 0.35) 58%, rgba(0, 0, 0, 0.78) 100%),
                radial-gradient(circle at 92% 5%, rgba(217, 255, 50, 0.12), transparent 26rem),
                radial-gradient(circle at 5% 78%, rgba(255, 122, 24, 0.10), transparent 30rem),
                url("https://images.unsplash.com/photo-1778828450059-f39d5bbb01af?auto=format&fit=crop&w=2400&q=85");
            background-size: cover, auto, auto, cover;
            background-position: center, center, center, center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            color: var(--gym-text);
            min-height: 100vh;
            font-family: 'Montserrat', system-ui, -apple-system, sans-serif;
        }

        .smartfit-title {
            margin: 0 0 0.2rem;
            color: #ffffff !important;
            font-family: 'Oswald', 'Arial Narrow', sans-serif !important;
            font-size: clamp(2.7rem, 7vw, 5.2rem);
            font-weight: 700;
            line-height: 1;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            text-shadow: 0 2px 0 rgba(255,255,255,0.10), 0 0 18px rgba(55,242,155,0.20);
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        .stMain {
            background-color: transparent !important;
            background-image: none !important;
        }

        /* Una única lámina de cristal base: evita que varias capas translúcidas se vuelvan negras. */
        [data-testid="stMainBlockContainer"],
        .block-container {
            background-color: rgba(18, 18, 18, 0.55) !important;
            background-image: none !important;
            border: 1px solid rgba(217, 255, 50, 0.14);
            border-radius: 24px;
            box-shadow: 0 26px 70px rgba(0, 0, 0, 0.48);
            backdrop-filter: blur(8px) !important;
            -webkit-backdrop-filter: blur(8px) !important;
            margin-top: 1rem;
            margin-bottom: 2rem;
        }

        /* Las envolventes anidadas permanecen transparentes: el cristal visible vive en la base,
           las tarjetas y los controles, evitando la antigua pared negra por capas acumuladas. */
        .stTabs,
        .stTabs > div,
        div[data-baseweb="tab-panel"] {
            background-color: transparent !important;
            background-image: none !important;
            box-shadow: none !important;
        }

        div[data-baseweb="tab-panel"] {
            border: 0 !important;
            backdrop-filter: none !important;
            -webkit-backdrop-filter: none !important;
        }

        .stApp p,
        .stApp label,
        .stApp li,
        .stApp span:not(.load-chip-label):not(.load-chip-value):not(.load-chip-detail) {
            color: var(--gym-muted);
        }

        [data-testid="stMarkdownContainer"] p,
        [data-testid="stText"],
        [data-testid="stCaptionContainer"] p {
            color: var(--gym-muted) !important;
        }

        [data-testid="stHeader"] {
            background-color: rgba(18, 18, 18, 0.55) !important;
            border-bottom: 1px solid rgba(217, 255, 50, 0.10);
            backdrop-filter: blur(8px) !important;
            -webkit-backdrop-filter: blur(8px) !important;
        }

        [data-testid="stSidebar"] {
            background-color: rgba(18, 18, 18, 0.55) !important;
            background-image: none !important;
            border-right: 1px solid rgba(217, 255, 50, 0.38);
            box-shadow: 18px 0 45px rgba(0, 0, 0, 0.38);
            backdrop-filter: blur(8px) !important;
            -webkit-backdrop-filter: blur(8px) !important;
        }

        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stWidgetLabel"] p {
            color: #ffffff !important;
            font-weight: 650;
        }

        /* Navegación lateral táctil: tarjetas grandes, foco inequívoco y zoom fluido. */
        [data-testid="stSidebar"] [data-testid="stRadio"] > div {
            gap: 0.7rem;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            min-height: 3.2rem;
            padding: 0.72rem 0.9rem;
            background: #151c21;
            border: 1px solid #52616a;
            border-radius: 14px;
            box-shadow: 0 7px 18px rgba(0, 0, 0, 0.24);
            transform-origin: left center;
            cursor: pointer;
            transition: transform 190ms cubic-bezier(.2,.8,.2,1), border-color 190ms ease,
                        background-color 190ms ease, box-shadow 190ms ease, filter 190ms ease;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
            transform: translateX(6px) translateY(-2px) scale(1.035);
            background: #202a30;
            border-color: var(--gym-lime);
            box-shadow: 0 13px 28px rgba(0, 0, 0, 0.38), 0 0 20px rgba(217, 255, 50, 0.12);
            filter: brightness(1.08);
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label:active {
            transform: translateX(3px) scale(0.99);
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
            background: linear-gradient(120deg, var(--gym-lime), var(--gym-green));
            border-color: #efffb3;
            box-shadow: 0 10px 26px rgba(55, 242, 155, 0.22);
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p,
        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) span {
            color: #07100b !important;
            font-weight: 850 !important;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label:focus-within {
            outline: 3px solid #4aa8ff;
            outline-offset: 3px;
        }

        [data-testid="stCaptionContainer"] p {
            color: #e0e0e0 !important;
        }

        [data-testid="stAlert"] p {
            color: #f4f7f8 !important;
        }

        /* Contraste global: los textos informativos siempre son legibles sobre la fotografía. */
        .stApp h1,
        .stApp h2,
        .stApp h3,
        .stApp h4,
        .stApp h5,
        .stApp h6,
        [data-testid="stWidgetLabel"],
        [data-testid="stExpander"] summary,
        [data-testid="stChatMessage"] {
            color: #ffffff !important;
        }

        .stApp a {
            color: var(--gym-lime) !important;
            text-decoration-color: rgba(217, 255, 50, 0.55);
        }

        .stApp a:hover {
            color: #ffffff !important;
            text-decoration-color: #ffffff;
        }

        h1, h2, h3 {
            letter-spacing: -0.025em;
        }

        h1 {
            color: var(--gym-lime) !important;
            text-shadow: 0 0 28px rgba(217, 255, 50, 0.22);
        }

        h2, h3 {
            color: #ffffff !important;
        }

        /* Entradas y selectores: superficie antracita, texto blanco y foco visible. */
        div[data-baseweb="input"],
        div[data-baseweb="base-input"],
        div[data-baseweb="select"] > div,
        [data-testid="stNumberInputContainer"],
        [data-testid="stSelectbox"] [role="group"],
        [data-testid="stTextInputRootElement"],
        [data-testid="stChatInput"] {
            background: #1b2227 !important;
            color: #ffffff !important;
            border: 1px solid #64727a !important;
            border-radius: 12px !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
            transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
        }

        div[data-baseweb="input"]:focus-within,
        div[data-baseweb="select"] > div:focus-within,
        [data-testid="stChatInput"]:focus-within {
            border-color: var(--gym-lime) !important;
            box-shadow: 0 0 0 3px rgba(217, 255, 50, 0.16) !important;
        }

        div[data-baseweb="input"] input,
        div[data-baseweb="select"] *,
        [data-testid="stNumberInputField"],
        [data-testid="stSelectbox"] input,
        [data-testid="stChatInput"] textarea {
            color: #ffffff !important;
            background: transparent !important;
            caret-color: var(--gym-lime);
        }

        div[data-baseweb="input"] input::placeholder,
        [data-testid="stChatInput"] textarea::placeholder {
            color: #b8c0c4 !important;
            opacity: 1;
        }

        [data-testid="stNumberInput"] button {
            color: #ffffff !important;
            background: #252e34 !important;
            border-color: #64727a !important;
        }

        [data-testid="stSelectbox"] button,
        [data-testid="stSelectbox"] svg {
            color: #ffffff !important;
            fill: #ffffff !important;
        }

        [data-testid="stMultiSelect"] [role="group"] {
            background: #1b2227 !important;
            color: #ffffff !important;
            border: 1px solid #64727a !important;
            border-radius: 12px !important;
            transition: border-color 180ms ease, box-shadow 180ms ease;
        }

        [data-testid="stMultiSelect"] [role="group"]:focus-within {
            border-color: var(--gym-lime) !important;
            box-shadow: 0 0 0 3px rgba(217, 255, 50, 0.16) !important;
        }

        [data-testid="stMultiSelect"] input,
        [data-testid="stMultiSelect"] button,
        [data-testid="stMultiSelect"] svg {
            color: #ffffff !important;
            fill: #ffffff !important;
        }

        [data-testid="stMultiSelect"] span[aria-label^="🏋"],
        [data-testid="stMultiSelect"] span[aria-label^="🛡"] {
            color: #080a0b !important;
            background: linear-gradient(120deg, var(--gym-lime), var(--gym-green)) !important;
            border: 1px solid rgba(255, 255, 255, 0.55);
            border-radius: 9px !important;
        }

        [data-testid="stMultiSelect"] span[aria-label^="🏋"] span,
        [data-testid="stMultiSelect"] span[aria-label^="🏋"] button,
        [data-testid="stMultiSelect"] span[aria-label^="🛡"] span,
        [data-testid="stMultiSelect"] span[aria-label^="🛡"] button {
            color: #080a0b !important;
            fill: #080a0b !important;
        }

        [data-baseweb="popover"],
        [role="listbox"] {
            background: #161c20 !important;
            color: #ffffff !important;
            border: 1px solid #64727a !important;
        }

        [role="option"] {
            color: #ffffff !important;
            background: #161c20 !important;
        }

        [role="option"]:hover,
        [aria-selected="true"][role="option"] {
            color: #090b0c !important;
            background: var(--gym-lime) !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: rgba(18, 18, 18, 0.55) !important;
            background-image: none !important;
            backdrop-filter: blur(8px) !important;
            -webkit-backdrop-filter: blur(8px) !important;
            border: 1px solid rgba(217, 255, 50, 0.42) !important;
            border-left: 3px solid var(--gym-lime) !important;
            border-radius: 18px !important;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.38), inset 0 1px 0 rgba(255, 255, 255, 0.035);
            transition: transform 220ms ease, border-color 220ms ease, box-shadow 220ms ease, filter 220ms ease;
            will-change: transform;
        }

        [data-testid="stVerticalBlockBorderWrapper"]:hover {
            transform: translateY(-4px);
            border-color: rgba(217, 255, 50, 0.72) !important;
            box-shadow: 0 20px 44px rgba(0, 0, 0, 0.42), 0 0 22px rgba(217, 255, 50, 0.10);
            filter: brightness(1.045);
        }

        [data-testid="stVerticalBlockBorderWrapper"]:active {
            transform: translateY(-1px) scale(0.995);
        }

        [data-testid="stExpander"] {
            background-color: rgba(18, 18, 18, 0.55) !important;
            backdrop-filter: blur(8px) !important;
            -webkit-backdrop-filter: blur(8px) !important;
            border: 1px solid #596970 !important;
            border-radius: 14px !important;
            overflow: hidden;
            transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
        }

        [data-testid="stExpander"]:hover {
            transform: translateY(-2px);
            border-color: var(--gym-lime) !important;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.32);
        }

        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary p,
        [data-testid="stExpander"] summary svg {
            color: #ffffff !important;
            fill: #ffffff !important;
            font-weight: 750;
        }

        [data-testid="stMetric"] {
            background-color: rgba(18, 18, 18, 0.55) !important;
            backdrop-filter: blur(8px) !important;
            -webkit-backdrop-filter: blur(8px) !important;
            border: 1px solid rgba(55, 242, 155, 0.34);
            border-radius: 14px;
            padding: 0.85rem 1rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.035);
            transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
        }

        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            border-color: var(--gym-green);
            box-shadow: 0 10px 22px rgba(0, 0, 0, 0.28);
        }

        [data-testid="stMetricValue"] {
            color: var(--gym-green);
            font-weight: 800;
            font-family: 'Oswald', 'Arial Narrow', sans-serif !important;
            letter-spacing: 0.035em;
        }

        [data-testid="stMetricLabel"] p {
            color: #ffffff !important;
            font-weight: 700;
            font-family: 'Montserrat', system-ui, sans-serif !important;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.45rem;
            background-color: rgba(18, 18, 18, 0.55) !important;
            backdrop-filter: blur(8px) !important;
            -webkit-backdrop-filter: blur(8px) !important;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 0.35rem;
        }

        .stTabs [data-baseweb="tab"] {
            height: 2.85rem;
            border-radius: 10px;
            padding: 0 1rem;
            color: #c5ced3;
            font-weight: 700;
            border: 1px solid transparent;
            transition: transform 180ms ease, background-color 180ms ease, color 180ms ease, box-shadow 180ms ease;
        }

        .stTabs [data-baseweb="tab"] p {
            color: inherit !important;
        }

        .stTabs [aria-selected="true"] {
            color: #090b0c !important;
            background: linear-gradient(135deg, var(--gym-lime), #a9f53a) !important;
            box-shadow: 0 0 20px rgba(217, 255, 50, 0.22);
        }

        .stTabs [aria-selected="true"] p {
            color: #090b0c !important;
        }

        .stTabs [data-baseweb="tab"]:hover {
            color: #ffffff !important;
            background: rgba(217, 255, 50, 0.10);
            border-color: rgba(217, 255, 50, 0.35);
            transform: translateY(-2px);
            box-shadow: 0 8px 18px rgba(0, 0, 0, 0.24);
        }

        .stTabs [aria-selected="true"]:hover,
        .stTabs [aria-selected="true"]:hover p {
            color: #090b0c !important;
        }

        /* Radios grandes tipo tarjeta, especialmente claros para 4/5 comidas. */
        [data-testid="stMainBlockContainer"] [data-testid="stRadio"] label {
            min-height: 2.8rem;
            padding: 0.55rem 0.9rem;
            background: #1b2227;
            border: 1px solid #64727a;
            border-radius: 12px;
            transition: transform 180ms ease, border-color 180ms ease, background-color 180ms ease, box-shadow 180ms ease;
        }

        [data-testid="stMainBlockContainer"] [data-testid="stRadio"] label:hover {
            transform: translateY(-2px);
            background: #242d33;
            border-color: var(--gym-lime);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.26);
        }

        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] > button {
            border: 1px solid var(--gym-lime);
            border-radius: 12px;
            font-weight: 800;
            min-height: 3.35rem;
            font-size: 1.04rem;
            letter-spacing: 0.01em;
            color: #080a0b !important;
            background: linear-gradient(120deg, var(--gym-lime), var(--gym-green)) !important;
            box-shadow: 0 10px 24px rgba(55, 242, 155, 0.15);
            transition: transform 180ms ease, box-shadow 180ms ease, filter 180ms ease;
        }

        .stButton > button p,
        .stDownloadButton > button p,
        [data-testid="stFormSubmitButton"] > button p {
            color: #080a0b !important;
            font-weight: 850;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover {
            border-color: var(--gym-lime);
            color: #080a0b !important;
            transform: translateY(-3px) scale(1.01);
            filter: brightness(1.08);
            box-shadow: 0 14px 32px rgba(217, 255, 50, 0.24);
        }

        .stButton > button:focus-visible,
        .stDownloadButton > button:focus-visible,
        [data-testid="stFormSubmitButton"] > button:focus-visible,
        .stTabs [data-baseweb="tab"]:focus-visible {
            outline: 3px solid #4aa8ff !important;
            outline-offset: 3px;
        }

        .stButton > button:disabled {
            color: #d8dde0 !important;
            background: #343c42 !important;
            border-color: #59656c !important;
            filter: none;
            box-shadow: none;
            transform: none;
        }

        [data-testid="stChatMessage"] {
            background-color: rgba(18, 18, 18, 0.55) !important;
            backdrop-filter: blur(8px) !important;
            -webkit-backdrop-filter: blur(8px) !important;
            border: 1px solid rgba(55, 242, 155, 0.34);
            border-radius: 16px;
            box-shadow: 0 10px 26px rgba(0, 0, 0, 0.28);
        }

        [data-testid="stRadio"] label p,
        [data-testid="stSlider"] p,
        [data-testid="stCheckbox"] label p,
        [data-testid="stToggle"] label p {
            color: #ffffff !important;
        }

        [data-testid="stSlider"] [role="slider"] {
            background: var(--gym-lime) !important;
            border: 2px solid #ffffff !important;
            box-shadow: 0 0 0 4px rgba(217, 255, 50, 0.16);
        }

        [data-testid="stSlider"] [data-baseweb="slider"] > div > div {
            background-color: #56636a;
        }

        button[aria-label],
        [role="button"] {
            transition: transform 170ms ease, filter 170ms ease, box-shadow 170ms ease;
        }

        button[aria-label]:hover,
        [role="button"]:hover {
            filter: brightness(1.12);
        }

        [data-testid="stImage"] img {
            border-radius: 14px;
            border: 1px solid rgba(255, 122, 24, 0.30);
        }

        .load-chip {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            gap: 0.1rem;
            margin: 0.8rem 0 0.45rem;
            padding: 0.9rem 1rem;
            color: #080a0b;
            background: linear-gradient(120deg, var(--gym-lime), var(--gym-green));
            border: 1px solid rgba(255, 255, 255, 0.55);
            border-radius: 14px;
            box-shadow: 0 0 24px rgba(55, 242, 155, 0.20);
        }

        .load-chip-label {
            font-size: 0.70rem;
            font-weight: 900;
            letter-spacing: 0.10em;
            opacity: 0.72;
        }

        .load-chip-value {
            font-size: 2rem;
            line-height: 1.05;
            font-weight: 950;
        }

        .load-chip-detail {
            font-size: 0.86rem;
            font-weight: 750;
        }

        [data-testid="stDataFrame"] {
            background-color: rgba(18, 18, 18, 0.55) !important;
            backdrop-filter: blur(8px) !important;
            -webkit-backdrop-filter: blur(8px) !important;
            border: 1px solid rgba(217, 255, 50, 0.32);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.28);
        }

        table,
        th,
        td {
            color: #ffffff !important;
            border-color: #435159 !important;
        }

        th {
            background-color: rgba(18, 18, 18, 0.72) !important;
        }

        td {
            background-color: rgba(18, 18, 18, 0.55) !important;
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                scroll-behavior: auto !important;
                transition-duration: 0.01ms !important;
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
            }
        }

        @media (max-width: 700px) {
            .stApp {
                background-attachment: scroll;
                background-position: 58% center;
            }
            [data-testid="stMainBlockContainer"] {
                border-radius: 16px;
                margin-top: 0.45rem;
                margin-bottom: 1rem;
                background-color: rgba(18, 18, 18, 0.48) !important;
                backdrop-filter: blur(6px) !important;
                -webkit-backdrop-filter: blur(6px) !important;
            }
            [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
                transform: translateX(3px) translateY(-1px) scale(1.015);
            }
            .stTabs [data-baseweb="tab"] {
                padding: 0 0.55rem;
                font-size: 0.82rem;
            }
            .load-chip-value {
                font-size: 1.65rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def require_password() -> None:
    """Detiene toda la aplicación hasta validar la contraseña de esta sesión."""
    if st.session_state.get("authenticated", False):
        return

    st.markdown(
        """
        <style>
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        .block-container {
            max-width: 34rem !important;
            padding-top: 18vh !important;
        }
        /* Contraste del campo de contraseña, incluido el estado revelado con el icono del ojo. */
        [data-testid="stTextInput"] input,
        [data-testid="stTextInput"] input:hover,
        [data-testid="stTextInput"] input:focus,
        [data-testid="stTextInput"] input:focus-visible,
        [data-testid="stTextInput"] input:active,
        [data-testid="stTextInput"] input:disabled,
        [data-testid="stTextInput"] input:autofill,
        [data-testid="stTextInput"] input:-webkit-autofill {
            color: #111111 !important;
            -webkit-text-fill-color: #111111 !important;
            background-color: #ffffff !important;
            caret-color: #111111 !important;
            opacity: 1 !important;
            text-shadow: none !important;
        }
        [data-testid="stTextInput"] input::placeholder {
            color: #555555 !important;
            -webkit-text-fill-color: #555555 !important;
            opacity: 1 !important;
        }
        [data-testid="stTextInputRootElement"],
        [data-testid="stTextInputRootElement"] > div {
            background-color: #ffffff !important;
        }
        [data-testid="stTextInput"] button,
        button[aria-label="Show password"],
        button[aria-label="Hide password"] {
            color: #111111 !important;
            background-color: transparent !important;
            opacity: 1 !important;
        }
        [data-testid="stTextInput"] button svg,
        [data-testid="stTextInput"] button svg path,
        button[aria-label="Show password"] svg,
        button[aria-label="Show password"] svg path,
        button[aria-label="Hide password"] svg,
        button[aria-label="Hide password"] svg path {
            color: #111111 !important;
            fill: #111111 !important;
            stroke: #111111 !important;
            opacity: 1 !important;
        }
        button[aria-label="Show password"] *,
        button[aria-label="Hide password"] * {
            color: #111111 !important;
            -webkit-text-fill-color: #111111 !important;
            opacity: 1 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("## 🔐 Acceso privado")
    st.caption("Introduce la contraseña para desbloquear SmartFit AI.")
    with st.form("password_lock_form", clear_on_submit=True):
        password = st.text_input(
            "Contraseña",
            type="password",
            placeholder="Escribe tu clave privada",
            autocomplete="current-password",
        )
        submitted = st.form_submit_button("🔓 Desbloquear aplicación", width="stretch")

    if submitted:
        if hmac.compare_digest(password, APP_PASSWORD):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")

    st.stop()


def main() -> None:
    st.set_page_config(
        page_title="SmartFit AI",
        page_icon="💪",
        layout="wide",
        initial_sidebar_state="auto",
    )
    apply_premium_styles()
    require_password()
    st.markdown('<h1 class="smartfit-title">SMARTFIT AI</h1>', unsafe_allow_html=True)
    st.caption("Entrena lo necesario. Progresa de verdad. Sin APIs de pago.")
    st.error(
        "¡ATENCIÓN! Si tienes alergias alimentarias, intolerancias o hay algún alimento que no te guste, "
        "escríbelo directamente en la pestaña Tutor IA de tu Perfil para cambiar el ingrediente y recalcular "
        "tus gramos de forma segura."
    )
    st.info(
        '💡 SECCIÓN DE SOPORTE: Recuerda que tienes a tu disposición el módulo de recetas personalizadas '
        '"¡Cocina Conmigo!" dentro de la pestaña del Tutor IA para adaptar tu menú semanal.'
    )
    page = st.sidebar.radio("Navegación", ["Perfil", "Check-in diario"])
    if page == "Perfil":
        profile_page()
    else:
        checkin_page()
    st.divider()
    st.caption("Información orientativa. No sustituye a profesionales sanitarios, dietistas-nutricionistas ni entrenadores cualificados.")


if __name__ == "__main__":
    main()

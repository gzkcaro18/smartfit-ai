"""SmartFit AI - prototipo local sin APIs de pago."""

from __future__ import annotations

import hmac
from itertools import combinations
from math import ceil
from random import choice, sample, shuffle
import time

import streamlit as st


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
            "Mantén un ritmo cómodo y sostenible. El objetivo es cuidar la salud cardiovascular "
            "sin añadir una fatiga que interfiera con la ganancia de masa muscular."
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
            "Utiliza una inclinación y velocidad que puedas sostener sin perder la técnica. "
            "Aumenta el gasto energético mientras el entrenamiento de fuerza ayuda a proteger el músculo."
        ),
    },
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
    "Avena seca": {
        "protein": 16.9,
        "carbs": 66.3,
        "fat": 6.9,
        "fdc_id": 20132,
        "category": "carb",
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
}

FOOD_DATABASE["Pechuga de pollo cocida"]["category"] = "protein"
FOOD_DATABASE["Arroz blanco cocido"]["category"] = "carb"
PROTEIN_OPTIONS = [name for name, data in FOOD_DATABASE.items() if data["category"] == "protein"]
CARB_OPTIONS = [name for name, data in FOOD_DATABASE.items() if data["category"] == "carb"]
MAIN_CARB_OPTIONS = ["Arroz blanco cocido", "Pasta integral cocida", "Patata cocida"]
BREAKFAST_OPTIONS = ["Avena seca", "Huevo entero", "Claras de huevo", "Plátano", "Leche semidesnatada"]

FOOD_ALIASES = {
    "pollo": "Pechuga de pollo cocida",
    "pechuga": "Pechuga de pollo cocida",
    "ternera": "Ternera magra cocida",
    "salmón": "Salmón cocido",
    "salmon": "Salmón cocido",
    "atún": "Atún al natural escurrido",
    "atun": "Atún al natural escurrido",
    "arroz": "Arroz blanco cocido",
    "pasta": "Pasta integral cocida",
    "patata": "Patata cocida",
    "avena": "Avena seca",
    "aceite": "Aceite de oliva",
    "huevo": "Huevo entero",
    "plátano": "Plátano",
    "platano": "Plátano",
    "leche": "Leche semidesnatada",
    "nueces": "Nueces",
}

REPLACEMENTS = {
    "Pechuga de pollo cocida": "Atún al natural escurrido",
    "Ternera magra cocida": "Pechuga de pollo cocida",
    "Salmón cocido": "Atún al natural escurrido",
    "Atún al natural escurrido": "Pechuga de pollo cocida",
    "Arroz blanco cocido": "Patata cocida",
    "Pasta integral cocida": "Arroz blanco cocido",
    "Patata cocida": "Arroz blanco cocido",
    "Avena seca": "Patata cocida",
    "Huevo entero": "Claras de huevo",
    "Plátano": "Avena seca",
    "Leche semidesnatada": "Claras de huevo",
    "Nueces": "Aceite de oliva",
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
    protein_multiplier = 2.2 if goal == "Definición" else 1.8
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


def choose_food_alternatives(excluded_foods: set[str] | None = None) -> tuple[str, str]:
    """Elige una proteína y un carbohidrato de las listas fijas para el plan del día."""
    excluded_foods = excluded_foods or set()
    proteins = [food for food in PROTEIN_OPTIONS if food not in excluded_foods]
    carbs = [food for food in CARB_OPTIONS if food not in excluded_foods]
    if not proteins or not carbs:
        raise ValueError("No quedan alternativas suficientes en la base fija para calcular el menú.")
    return choice(proteins), choice(carbs)


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


def solve_three_foods(foods: tuple[str, str, str], target: dict[str, float]) -> list[float] | None:
    """Resuelve exactamente un sistema 3x3 de macros; devuelve porciones de 100 g."""
    nutrients = ("protein", "carbs", "fat")
    matrix = [
        [float(FOOD_DATABASE[food][nutrient]) for food in foods] + [target[nutrient]]
        for nutrient in nutrients
    ]
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
            matrix[row] = [matrix[row][i] - factor * matrix[column][i] for i in range(4)]
    solution = [matrix[i][3] for i in range(3)]
    return solution if all(value >= -1e-8 for value in solution) else None


def macro_target(nutrition: dict[str, float], share: float) -> dict[str, float]:
    return {
        "protein": nutrition["protein_g"] * share,
        "carbs": nutrition["carbs_g"] * share,
        "fat": nutrition["fat_g"] * share,
    }


def portions_to_rows(meal: str, portions: dict[str, float]) -> list[dict[str, float | str]]:
    rows = []
    for food, portion in portions.items():
        if portion <= 1e-8:
            continue
        data = FOOD_DATABASE[food]
        rows.append(
            {
                "Comida": meal,
                "Alimento": food,
                "Gramos": round(portion * 100, 2),
                "Proteína (g)": round(portion * data["protein"], 2),
                "Carbohidratos (g)": round(portion * data["carbs"], 2),
                "Grasas (g)": round(portion * data["fat"], 2),
            }
        )
    return rows


def solve_morning_meal(
    meal: str,
    nutrition: dict[str, float],
    share: float,
    excluded: set[str],
    avoided_combos: set[tuple[str, str, str]] | None = None,
) -> tuple[list[dict[str, float | str]], tuple[str, str, str]]:
    """Busca aleatoriamente una combinación lógica y no negativa para desayuno/merienda."""
    target = macro_target(nutrition, share)
    avoided_combos = avoided_combos or set()
    combos = [combo for combo in combinations(BREAKFAST_OPTIONS, 3) if not excluded.intersection(combo)]
    shuffle(combos)
    for combo in combos:
        if combo in avoided_combos:
            continue
        solution = solve_three_foods(combo, target)
        if solution is not None:
            return portions_to_rows(meal, dict(zip(combo, solution))), combo
    raise ValueError(f"No existe una combinación válida para {meal} con las exclusiones actuales.")


def solve_main_meal(
    meal: str,
    nutrition: dict[str, float],
    share: float,
    primary_protein: str,
    primary_carb: str,
    excluded: set[str],
) -> list[dict[str, float | str]]:
    """Incluye las elecciones aleatorias y usa correctores para cuadrar los macros exactos."""
    target = macro_target(nutrition, share)
    safe_proteins = [food for food in PROTEIN_OPTIONS if food not in excluded]
    safe_carbs = [food for food in MAIN_CARB_OPTIONS if food not in excluded]
    protein_corrector = min(safe_proteins, key=lambda food: FOOD_DATABASE[food]["fat"] / FOOD_DATABASE[food]["protein"])
    carb_corrector = min(safe_carbs, key=lambda food: FOOD_DATABASE[food]["protein"] / FOOD_DATABASE[food]["carbs"])

    protein_primary_portion = target["protein"] * 0.25 / FOOD_DATABASE[primary_protein]["protein"]
    carb_primary_portion = target["carbs"] * 0.25 / FOOD_DATABASE[primary_carb]["carbs"]
    carb_corrector_portion = (
        target["carbs"] - carb_primary_portion * FOOD_DATABASE[primary_carb]["carbs"]
    ) / FOOD_DATABASE[carb_corrector]["carbs"]
    protein_corrector_portion = (
        target["protein"]
        - protein_primary_portion * FOOD_DATABASE[primary_protein]["protein"]
        - carb_primary_portion * FOOD_DATABASE[primary_carb]["protein"]
        - carb_corrector_portion * FOOD_DATABASE[carb_corrector]["protein"]
    ) / FOOD_DATABASE[protein_corrector]["protein"]
    fat_used = sum(
        portion * FOOD_DATABASE[food]["fat"]
        for food, portion in [
            (primary_protein, protein_primary_portion),
            (primary_carb, carb_primary_portion),
            (protein_corrector, protein_corrector_portion),
            (carb_corrector, carb_corrector_portion),
        ]
    )
    oil_portion = (target["fat"] - fat_used) / FOOD_DATABASE["Aceite de oliva"]["fat"]
    portions: dict[str, float] = {}
    for food, portion in [
        (primary_protein, protein_primary_portion),
        (primary_carb, carb_primary_portion),
        (protein_corrector, protein_corrector_portion),
        (carb_corrector, carb_corrector_portion),
        ("Aceite de oliva", oil_portion),
    ]:
        portions[food] = portions.get(food, 0) + portion
    if any(value < -1e-8 for value in portions.values()):
        raise ValueError(f"La combinación aleatoria de {meal} no admite una solución positiva.")
    return portions_to_rows(meal, portions)


def build_dynamic_menu(
    nutrition: dict[str, float],
    excluded: set[str] | None = None,
    meals_per_day: int = 4,
) -> list[dict[str, float | str]]:
    """Distribuye exactamente los macros diarios entre cuatro o cinco comidas."""
    if meals_per_day not in (4, 5):
        raise ValueError("El número de comidas debe ser 4 o 5.")
    excluded = excluded or set()
    proteins = [food for food in PROTEIN_OPTIONS if food not in excluded]
    carbs = [food for food in MAIN_CARB_OPTIONS if food not in excluded]
    if len(proteins) < 2 or len(carbs) < 2 or "Aceite de oliva" in excluded:
        raise ValueError("No quedan suficientes alternativas para crear comida y cena distintas.")
    chosen_proteins = sample(proteins, 2)
    chosen_carbs = sample(carbs, 2)

    if meals_per_day == 4:
        breakfast_share, mid_morning_share, snack_share = 0.25, 0.0, 0.15
    else:
        breakfast_share, mid_morning_share, snack_share = 0.20, 0.10, 0.10

    breakfast, breakfast_combo = solve_morning_meal("Desayuno", nutrition, breakfast_share, excluded)
    avoided_combos = {breakfast_combo}
    mid_morning: list[dict[str, float | str]] = []
    if mid_morning_share:
        mid_morning, mid_morning_combo = solve_morning_meal(
            "Media Mañana", nutrition, mid_morning_share, excluded, avoided_combos
        )
        avoided_combos.add(mid_morning_combo)
    snack, _ = solve_morning_meal("Merienda", nutrition, snack_share, excluded, avoided_combos)
    lunch = solve_main_meal("Comida (Mediodía)", nutrition, 0.30, chosen_proteins[0], chosen_carbs[0], excluded)
    dinner = solve_main_meal("Cena", nutrition, 0.30, chosen_proteins[1], chosen_carbs[1], excluded)
    return breakfast + mid_morning + lunch + snack + dinner


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
            display_rows = [
                {key: value for key, value in row.items() if key != "Comida"}
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


def render_daily_plan(plan: dict) -> None:
    nutrition = plan["nutrition"]
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
            render_workout_cards(plan["exercises"], plan["multiplier"], plan["strength_data"])
            st.caption(
                f"Puntuación de fatiga: {plan['score']}. Las series base se multiplican por el filtro "
                "de recuperación y se redondean hacia arriba."
            )
            render_smart_cardio(plan.get("goal", "Hipertrofia"))

    with diet_tab:
        st.subheader("Menú dinámico del día")
        st.caption(
            f"{plan.get('goal', 'Objetivo')}: "
            f"{GOAL_EXPLANATIONS.get(plan.get('goal', ''), 'macros adaptados a tu perfil.')} "
            f"El total se reparte en {plan.get('meals_per_day', 4)} comidas sin cambiar tus macros diarios."
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
        render_menu_by_meal(plan["menu_rows"])
        st.caption(
            "Cada comida se resuelve matemáticamente y todas las contribuciones suman los macros diarios."
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
            menu_rows = build_dynamic_menu(
                nutrition,
                exclusions,
                profile.get("meals_per_day", 4),
            )
        except ValueError as error:
            st.error(str(error))
            return
        st.session_state.daily_plan = {
            "nutrition": nutrition,
            "menu_rows": menu_rows,
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
        st.markdown("#### 💬 Tutor IA de nutrición y alergias")
        st.caption("Asistente integrado: escribe una alergia o preferencia para ajustar el menú activo.")
    else:
        st.header("3. Tutor de nutrición y alergias")
        st.caption("Tutor local basado en reglas. Puede excluir alimentos y recalcular el menú activo.")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {
                "role": "assistant",
                "content": "Hola. Cuéntame si tienes una alergia o un alimento que no te guste y ajustaré el menú del día.",
            }
        ]
    if "excluded_foods" not in st.session_state:
        st.session_state.excluded_foods = set()

    for message in st.session_state.chat_history:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.write(message["content"])

    prompt = st.chat_input("Ej.: “Soy alérgico al atún” o “No me gusta el salmón”")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.write(prompt)

        with st.spinner("Analizando perfil y alérgenos..."):
            time.sleep(3)
            answer, food_to_exclude = tutor_response(prompt)
            plan = st.session_state.get("daily_plan")
            if food_to_exclude and food_to_exclude in FOOD_DATABASE and plan:
                previous_exclusions = set(st.session_state.excluded_foods)
                st.session_state.excluded_foods.add(food_to_exclude)
                try:
                    plan["menu_rows"] = build_dynamic_menu(
                        plan["nutrition"],
                        st.session_state.excluded_foods,
                        plan.get("meals_per_day", 4),
                    )
                    answer += " He eliminado el ingrediente y recalculado todas las cantidades con alternativas equivalentes de la base fija."
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
            for word in answer.split():
                rendered += word + " "
                response_placeholder.markdown(rendered + "▌")
                time.sleep(0.035)
            response_placeholder.markdown(rendered)

    plan = st.session_state.get("daily_plan")
    if plan:
        st.subheader("Menú del día actualizado")
        render_menu_by_meal(plan["menu_rows"])
    else:
        st.info("Aún no hay un menú activo. Completa el Check-in diario para crear uno.")


def apply_premium_styles() -> None:
    """Aplica una identidad visual oscura y neón sin alterar los cálculos."""
    st.markdown(
        """
        <style>
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
            background:
                radial-gradient(circle at 92% 5%, rgba(217, 255, 50, 0.10), transparent 24rem),
                radial-gradient(circle at 5% 75%, rgba(255, 122, 24, 0.08), transparent 28rem),
                linear-gradient(145deg, #080b0d 0%, #0d1114 55%, #080a0c 100%);
            color: var(--gym-text);
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
            background: rgba(8, 11, 13, 0.78);
            backdrop-filter: blur(12px);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0d1114 0%, #090c0e 100%);
            border-right: 1px solid rgba(217, 255, 50, 0.25);
        }

        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stWidgetLabel"] p {
            color: #ffffff !important;
            font-weight: 650;
        }

        [data-testid="stCaptionContainer"] p {
            color: #e0e0e0 !important;
        }

        [data-testid="stAlert"] p {
            color: #f4f7f8 !important;
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
            background: linear-gradient(145deg, rgba(23, 29, 33, 0.96), rgba(13, 17, 20, 0.96));
            border: 1px solid rgba(217, 255, 50, 0.32) !important;
            border-radius: 18px !important;
            box-shadow: 0 14px 36px rgba(0, 0, 0, 0.30);
            transition: transform 220ms ease, border-color 220ms ease, box-shadow 220ms ease, filter 220ms ease;
            will-change: transform;
        }

        [data-testid="stVerticalBlockBorderWrapper"]:hover {
            transform: translateY(-4px);
            border-color: rgba(217, 255, 50, 0.72) !important;
            box-shadow: 0 20px 44px rgba(0, 0, 0, 0.42), 0 0 22px rgba(217, 255, 50, 0.10);
            filter: brightness(1.045);
        }

        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.035);
            border: 1px solid rgba(55, 242, 155, 0.22);
            border-radius: 14px;
            padding: 0.85rem 1rem;
        }

        [data-testid="stMetricValue"] {
            color: var(--gym-green);
            font-weight: 800;
        }

        [data-testid="stMetricLabel"] p {
            color: #ffffff !important;
            font-weight: 700;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.45rem;
            background: rgba(255, 255, 255, 0.025);
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
        [data-testid="stFormSubmitButton"] > button p {
            color: #080a0b !important;
            font-weight: 850;
        }

        .stButton > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover {
            border-color: var(--gym-lime);
            color: #080a0b !important;
            transform: translateY(-3px) scale(1.01);
            filter: brightness(1.08);
            box-shadow: 0 14px 32px rgba(217, 255, 50, 0.24);
        }

        .stButton > button:focus-visible,
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
            background: rgba(17, 22, 26, 0.88);
            border: 1px solid rgba(55, 242, 155, 0.18);
            border-radius: 16px;
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
            border: 1px solid rgba(217, 255, 50, 0.16);
            border-radius: 12px;
            overflow: hidden;
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
        initial_sidebar_state="expanded",
    )
    apply_premium_styles()
    require_password()
    st.title("💪 SmartFit AI")
    st.caption("Entrena lo necesario. Progresa de verdad. Sin APIs de pago.")
    st.error(
        "¡ATENCIÓN! Si tienes alergias alimentarias, intolerancias o hay algún alimento que no te guste, "
        "escríbelo directamente en la pestaña Tutor IA de tu Perfil para cambiar el ingrediente y recalcular "
        "tus gramos de forma segura."
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

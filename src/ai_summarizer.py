import os
import json
import numpy as np
import streamlit as st
from dotenv import load_dotenv

# Configuración de variables de entorno
load_dotenv()

class NumpyEncoder(json.JSONEncoder):
    """Custom encoder for numpy data types"""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.intc, np.intp, np.int8,
                            np.int16, np.int32, np.int64, np.uint8,
                            np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        import decimal
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

@st.cache_data(ttl=3600)  # Caché de 1 hora para no quemar la API en cada reload
def _cached_ai_call(kpi_id: str, data_str: str) -> str:
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        return "⚠️ Alerta: No se encontró la API Key de Groq. El AI Insight no está disponible."
        
    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)
    except ImportError:
        return "⏳ Instalando dependencias de IA..."
    
    # Simple mapping of KPI instructions to give the AI context
    prompts = {
        'pct_surtido': """Eres un analista de operaciones de almacén reportando KPIs.
TONO: Reporte ejecutivo escrito (LIMPIO, SIN MATEMÁTICAS VISIBLES). NUNCA primera persona. Usa infinitivos o imperativo.
REGLAS DE ESTILO:
1. Primera oración: 'Periodo [Periodo_Analisis]: [Nombre KPI] pasó de X% a Y% (±Zpp)'.
2. Segunda oración: Diagnóstico operativo directo. Sin 'esto indica' o redundancias.
3. Tercera oración: Gap vs target (ejemplo: 95% para completados).
4. Última oración: Acción ESPECÍFICA, MEDIBLE y PROPORCIONAL al gap.

IMPORTANTE SOBRE CÁLCULOS (INTERNO):
- USA 'Gap_Puntos' y 'Total_Pedidos' para calcular la acción correcta (1 orden ≈ 100/Total%).
- NO MUESTRES el cálculo en el reporte. SOLO di la acción resultante.
- Si Total_Pedidos < 20: Acción conservadora (2-4 órdenes). 
- Si Total_Pedidos > 50: Acción proporcional (5-10 órdenes).
- Máximo 10% del total, nunca sugerir >50 órdenes por turno.

PROHIBIDO: 'Equipo', 'analicemos', 'logro positivo', 'significativo', 'asegurarnos', 'probablemente', 'recomiendo', 'debemos', 'revisaremos', 'mejorar gestión', 'optimizar proceso'.
Máximo 4 líneas.""",
        
        'cumpl_72h': """Eres un analista de calidad de almacén reportando KPIs de inbound.
TONO: Reporte ejecutivo escrito (LIMPIO, SIN MATEMÁTICAS VISIBLES). NUNCA primera persona. Usa infinitivos o imperativo.
REGLAS DE ESTILO:
1. Primera oración: 'Periodo [Periodo_Analisis]: [Nombre KPI] pasó de X% a Y% (±Zpp)'.
2. Segunda oración: Causa operativa técnica directa.
3. Tercera oración: Gap vs target (>95% calidad A).
4. Última oración: Acción ESPECÍFICA, MEDIBLE y PROPORCIONAL al gap.

IMPORTANTE SOBRE CÁLCULOS (INTERNO):
- USA 'Gap_Puntos' y 'Total_Recibos' para calcular (1 recibo ≈ 100/Total%).
- NO MUESTRES el cálculo en el reporte. SOLO di la acción resultante.
- Si Total_Recibos < 20: 2-4 tarimas. Si > 50: 5-10 tarimas.
- Nunca sugerir auditar >50 tarimas en un turno.

PROHIBIDO: jerga motivacional, frases corporativas, especulaciones vagas, primera persona, 'optimizar proceos', 'mejorar gestión'.
Máximo 4 líneas.""",
        
        'default': """Eres un analista de indicadores operativos de almacén.
REGLAS DE ESTILO:
1. Primera oración: 'Periodo [Periodo_Analisis]: [KPI] de X a Y (±Zpp)'.
2. Diagnóstico operativo seco.
3. Acción ESPECÍFICA y PROPORCIONAL.
NO MUESTRES CÁLCULOS. Solo resultado. Proporción matemática (Gap * Total / 100).
Máximo 4 líneas. Sin intros ni rellenos corporativos."""
    }
    
    system_prompt = prompts.get(kpi_id, prompts['default'])
    
    try:
        # Usamos Llama-3-70b porque en Groq es ultra rápido y muy inteligente
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": f"El KPI es '{kpi_id}'. Los datos actuales son: {data_str}"
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3, # Baja varianza para respuestas consistentes
            max_tokens=200
        )
        insight = response.choices[0].message.content.strip()
        return f"🤖✨ **AI Insight:** {insight}"
    except Exception as e:
        return f"Error al generar AI Insight: {str(e)}"

def clear_ai_cache():
    """Limpia el caché de las llamadas a la IA."""
    _cached_ai_call.clear()

def get_ai_insight(kpi_id: str, data: dict) -> str:
    """Genera un resumen gerencial usando Groq (LLM). Los resultados se cachean por 1 hora."""
    data_str = json.dumps(data, ensure_ascii=False, cls=NumpyEncoder)
    # Evitar enviar datas masivos de tablas enteras si los hay, 
    # truncando a los primeros 2000 chars si es necesario (para que no consuma todos los tokens del contexto)
    if len(data_str) > 3000:
        data_str = data_str[:3000] + "... (truncated)"
    return _cached_ai_call(kpi_id, data_str)

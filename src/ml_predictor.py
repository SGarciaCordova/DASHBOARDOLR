"""
ML Predictor for SLA Breach Risk
Uses RandomForest to predict which orders are likely to breach SLA.
"""
import pandas as pd
import numpy as np
from datetime import datetime

# Try to import sklearn, fall back to simple heuristic if not available
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

def prepare_features(df, date_col='FECHA DE LLEGADA'):
    """Extracts features for ML prediction."""
    df = df.copy()
    
    # Parse dates
    df['_dt'] = pd.to_datetime(df[date_col], errors='coerce')
    now = datetime.now()
    
    # Feature 1: Hours since arrival
    df['hours_elapsed'] = (now - df['_dt']).dt.total_seconds() / 3600
    df['hours_elapsed'] = df['hours_elapsed'].fillna(0).clip(lower=0)
    
    # Feature 2: Day of week (0=Monday, 6=Sunday)
    df['day_of_week'] = df['_dt'].dt.dayofweek.fillna(0)
    
    # Feature 3: Is weekend
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    
    # Feature 4: Volume (if available)
    if 'CAJAS' in df.columns:
        df['volume'] = pd.to_numeric(df['CAJAS'], errors='coerce').fillna(0)
    else:
        df['volume'] = 0
        
    return df

def train_model(df_historical, target_col='SLA_BREACHED'):
    """
    Trains a RandomForest model on historical data.
    Returns trained model or None if not enough data.
    """
    if not ML_AVAILABLE:
        return None
        
    df = prepare_features(df_historical)
    
    if target_col not in df.columns or len(df) < 10:
        return None
    
    features = ['hours_elapsed', 'day_of_week', 'is_weekend', 'volume']
    X = df[features].fillna(0)
    y = df[target_col].fillna(0)
    
    model = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
    model.fit(X, y)
    
    return model

def predict_sla_risk_heuristic(df_entradas, date_col='FECHA DE LLEGADA', hours_threshold=72):
    """
    Simple heuristic-based prediction when ML is not available.
    Uses time elapsed and historical patterns.
    """
    df = prepare_features(df_entradas, date_col)
    
    # Check if already completed
    if 'FECHA ENVIO DE REPORTE' in df.columns:
        df['completed'] = pd.to_datetime(df['FECHA ENVIO DE REPORTE'], errors='coerce').notna()
    else:
        df['completed'] = False
    
    # Filter to pending orders only
    pending = df[~df['completed'] & df['hours_elapsed'] > 0].copy()
    
    if pending.empty:
        return {'at_risk': [], 'risk_count': 0, 'high_risk_count': 0}
    
    # Calculate risk score (0-100)
    # Higher score = higher risk of breach
    pending['risk_score'] = (pending['hours_elapsed'] / hours_threshold * 100).clip(upper=150)
    
    # Adjust for weekend effect (+10% risk)
    pending.loc[pending['is_weekend'] == 1, 'risk_score'] *= 1.1
    
    # Adjust for high volume (+5% risk per 10 boxes)
    pending['risk_score'] += pending['volume'] / 100 * 5
    
    # Categorize risk
    pending['risk_level'] = pd.cut(pending['risk_score'], 
                                     bins=[-1, 50, 75, 100, 200],
                                     labels=['Low', 'Medium', 'High', 'Critical'])
    
    high_risk = pending[pending['risk_score'] >= 75].copy()
    
    # Prepare output with identifying columns
    detail_cols = ['hours_elapsed', 'risk_score', 'risk_level']
    for col in ['PEDIMENTO', 'TIPO DE MERCANCIA']:
        if col in high_risk.columns:
            detail_cols.append(col)
    
    # Add formatted arrival date
    if '_dt' in high_risk.columns:
        high_risk['fecha_llegada_str'] = high_risk['_dt'].dt.strftime('%d/%m/%Y').fillna('-')
        detail_cols.append('fecha_llegada_str')
    
    at_risk_list = high_risk.nlargest(10, 'risk_score')[detail_cols].to_dict('records')
    
    # Clean risk_level (Categorical -> str)
    for item in at_risk_list:
        item['risk_level'] = str(item.get('risk_level', ''))
        item['hours_elapsed'] = round(item.get('hours_elapsed', 0), 1)
        item['risk_score'] = round(item.get('risk_score', 0), 1)
    
    return {
        'at_risk': at_risk_list,
        'risk_count': len(pending[pending['risk_score'] >= 50]),
        'high_risk_count': len(high_risk),
        'critical_count': len(pending[pending['risk_score'] >= 100])
    }

def predict_sla_risk(df_entradas, model=None, date_col='FECHA DE LLEGADA'):
    """
    Main function to predict SLA breach risk.
    Uses ML model if available, otherwise falls back to heuristic.
    """
    if model is not None and ML_AVAILABLE:
        df = prepare_features(df_entradas, date_col)
        features = ['hours_elapsed', 'day_of_week', 'is_weekend', 'volume']
        X = df[features].fillna(0)
        
        # Get probability of breach
        probs = model.predict_proba(X)[:, 1] if len(model.classes_) > 1 else np.zeros(len(df))
        df['risk_score'] = probs * 100
        
        high_risk = df[df['risk_score'] >= 50]
        
        return {
            'at_risk': high_risk.nsmallest(10, 'risk_score')[['risk_score']].to_dict('records'),
            'risk_count': len(df[df['risk_score'] >= 30]),
            'high_risk_count': len(high_risk),
            'critical_count': len(df[df['risk_score'] >= 80]),
            'model_used': 'RandomForest'
        }
    else:
        result = predict_sla_risk_heuristic(df_entradas, date_col)
        result['model_used'] = 'Heuristic'
        return result

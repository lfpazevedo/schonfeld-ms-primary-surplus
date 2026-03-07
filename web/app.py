import dash
from dash import dcc, html, Input, Output, State, no_update
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import os
import glob

# Initialize the Dash app
app = dash.Dash(__name__, title="Schonfeld | Primary Surplus", suppress_callback_exceptions=True)

# Load real data
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "data", "processed")
FISCAL_PATH = os.path.join(DATA_DIR, "focus", "primary_1y_3y_4y_interp.csv")
REGIME_DIR = os.path.join(DATA_DIR, "regime_analysis")
CALENDAR_PATH = os.path.join(DATA_DIR, "calendar", "fiscal_release_dates.csv")
PREDI_PATH = os.path.join(DATA_DIR, "b3", "predi_252_pivot.csv")
FRA_PATH = os.path.join(DATA_DIR, "b3", "predi_fra_1y1y_3y3y.csv")
IPCA_PATH = os.path.join(DATA_DIR, "focus", "ipca_12m_forecast.csv")
SELIC_PATH = os.path.join(DATA_DIR, "focus", "selic_1y_forecast.csv")

# EPU data URL
EPU_URL = "https://www.policyuncertainty.com/media/Brazil_Policy_Uncertainty_Data.xlsx"

# VIX data URL (FRED CSV)
VIX_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS"

def load_vix_data():
    """Load VIX data from FRED"""
    try:
        df = pd.read_csv(VIX_URL)
        df["date"] = pd.to_datetime(df["observation_date"])
        df = df.rename(columns={"VIXCLS": "VIX"})
        # Filter out NaN values (FRED uses '.' for missing)
        df = df[df["VIX"] != "."]
        df["VIX"] = pd.to_numeric(df["VIX"])
        return df[["date", "VIX"]]
    except Exception as e:
        print(f"Error loading VIX data: {e}")
        return pd.DataFrame()

def load_epu_data():
    """Load Brazil EPU data from policyuncertainty.com"""
    try:
        df = pd.read_excel(EPU_URL)
        # Filter out footer rows where year is not numeric
        df = df[pd.to_numeric(df["year"], errors="coerce").notna()]
        # Handle month as float (e.g., 1.0 -> 1)
        df["date"] = pd.to_datetime(
            df["year"].astype(int).astype(str) + "-" + 
            df["month"].astype(int).astype(str) + "-01",
            format="%Y-%m-%d"
        )
        # Get end-of-month dates
        df["date"] = df["date"] + pd.offsets.MonthEnd(0)
        # Rename EPU column
        df = df.rename(columns={"Brazil News-Based EPU": "EPU"})
        return df[["date", "EPU"]]
    except Exception as e:
        print(f"Error loading EPU data: {e}")
        return pd.DataFrame()

def load_data(version="v5"):
    # Handle version 1 which has no suffix
    if version == "" or version == "v1":
        results_dir = os.path.join(DATA_DIR, "strategy_results")
    else:
        results_dir = os.path.join(DATA_DIR, f"strategy_results_{version}")
        
    pnl_path = os.path.join(results_dir, "daily_pnl.csv")
    trades_path = os.path.join(results_dir, "trades.csv")
    
    if os.path.exists(pnl_path):
        df_pnl = pd.read_csv(pnl_path)
        df_pnl["date"] = pd.to_datetime(df_pnl["date"])
        
        # Standardize columns across versions
        if "total_pnl" not in df_pnl.columns and "daily_pnl" in df_pnl.columns:
            df_pnl["total_pnl"] = df_pnl["daily_pnl"]
            
        if "position_size" not in df_pnl.columns and "position" in df_pnl.columns:
            df_pnl["position_size"] = df_pnl["position"]
            
        if "curve_pnl" not in df_pnl.columns:
            df_pnl["curve_pnl"] = 0
            
        if "carry_pnl" not in df_pnl.columns:
            df_pnl["carry_pnl"] = 0

        if "gamma_pnl" not in df_pnl.columns:
            df_pnl["gamma_pnl"] = 0

        if "cost_pnl" not in df_pnl.columns:
            df_pnl["cost_pnl"] = 0
            
        # Calculate cumulative returns assuming total_pnl is simple return
        df_pnl["Cumulative PnL"] = df_pnl["total_pnl"].cumsum()
        df_pnl["Cumulative Curve PnL"] = df_pnl["curve_pnl"].cumsum()
        df_pnl["Cumulative Carry PnL"] = df_pnl["carry_pnl"].cumsum()
        df_pnl["Cumulative Gamma PnL"] = df_pnl["gamma_pnl"].cumsum()
        df_pnl["Cumulative Cost PnL"] = df_pnl["cost_pnl"].cumsum()
    else:
        df_pnl = pd.DataFrame()
        
    if os.path.exists(trades_path):
        df_trades = pd.read_csv(trades_path)
        df_trades["date"] = pd.to_datetime(df_trades["date"])
    else:
        df_trades = pd.DataFrame()
        
    return df_pnl, df_trades

def load_market_data():
    """Load pre-di and FRA market data"""
    df_predi = pd.DataFrame()
    df_fra = pd.DataFrame()
    
    if os.path.exists(PREDI_PATH):
        df_predi = pd.read_csv(PREDI_PATH)
        df_predi["date"] = pd.to_datetime(df_predi["date"])
    
    if os.path.exists(FRA_PATH):
        df_fra = pd.read_csv(FRA_PATH)
        df_fra["date"] = pd.to_datetime(df_fra["date"])
    
    return df_predi, df_fra

def load_macro_data():
    """Load macro/FOCUS data"""
    df_macro = pd.DataFrame()
    if os.path.exists(FISCAL_PATH):
        df_macro = pd.read_csv(FISCAL_PATH)
        df_macro["date"] = pd.to_datetime(df_macro["date"])
    return df_macro


def load_ipca_data():
    """Load IPCA 12-month forecast data"""
    df_ipca = pd.DataFrame()
    if os.path.exists(IPCA_PATH):
        df_ipca = pd.read_csv(IPCA_PATH, index_col=0, parse_dates=True)
        df_ipca.index.name = "date"
        df_ipca = df_ipca.reset_index()
    return df_ipca


def load_selic_forecast_data():
    """Load SELIC 1-year ahead forecast data"""
    df_selic = pd.DataFrame()
    if os.path.exists(SELIC_PATH):
        df_selic = pd.read_csv(SELIC_PATH, index_col=0, parse_dates=True)
        df_selic.index.name = "date"
        df_selic = df_selic.reset_index()
    return df_selic

# Initial data load
df_pnl, df_trades = load_data()
df_predi, df_fra = load_market_data()
df_macro = load_macro_data()

# Styling constants based on Schonfeld palette
COLORS = {
    "teal": "#00acac",
    "dark": "#282828",
    "beige": "#f2ece3",
    "gold": "#b4a680",
    "gray": "#d9d9d9",
    "light_gray": "#f8f9fa",
    "white": "#ffffff",
    "red": "#e74c3c",
    "blue": "#3498db",
    "light_blue": "#5dade2"
}

def create_pnl_chart(df):
    if df.empty:
        return go.Figure()
        
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["Cumulative PnL"],
        mode="lines", name="Total PnL",
        line=dict(color=COLORS["teal"], width=3)
    ))
    
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["Cumulative Curve PnL"],
        mode="lines", name="Curve PnL",
        line=dict(color=COLORS["gold"], width=2, dash="dash")
    ))
    
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["Cumulative Carry PnL"],
        mode="lines", name="Carry PnL",
        line=dict(color=COLORS["dark"], width=2, dash="dot")
    ))
    
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        title="Strategy Cumulative PnL Components",
        title_font_size=20,
        xaxis=dict(showgrid=True, gridcolor=COLORS["gray"], zerolinecolor=COLORS["gray"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], zerolinecolor=COLORS["beige"]),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def create_position_chart(df):
    if df.empty or "position_size" not in df.columns:
        return go.Figure()
        
    fig = go.Figure()
    
    # Check if position_size is numeric
    if pd.api.types.is_numeric_dtype(df["position_size"]):
        y_vals = df["position_size"]
        marker_color = np.where(df["position_size"] > 0, COLORS["teal"], COLORS["dark"])
        hover_text = None
    else:
        # For categorical position data (e.g. Version 1)
        y_vals = np.where(df["position_size"].str.contains("steepener", case=False, na=False), 1, 
                 np.where(df["position_size"].str.contains("flattener", case=False, na=False), -1, 0))
        marker_color = np.where(y_vals > 0, COLORS["teal"], COLORS["dark"])
        hover_text = df["position_size"]
    
    fig.add_trace(go.Bar(
        x=df["date"], y=y_vals,
        name="Position",
        hovertext=hover_text,
        marker_color=marker_color
    ))
    
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        title="Dynamic Position Sizing",
        title_font_size=20,
        xaxis=dict(showgrid=True, gridcolor=COLORS["gray"], zerolinecolor=COLORS["gray"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], zerolinecolor=COLORS["beige"], title="Size (1y1y equivalents)"),
        hovermode="x unified"
    )
    return fig

def create_spread_chart(df):
    if df.empty or "curve_spread" not in df.columns:
        return go.Figure()
        
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["curve_spread"],
        mode="lines", name="Curve Spread",
        line=dict(color=COLORS["dark"], width=2)
    ))
    
    # Highlight high uncertainty regimes
    if "regime" in df.columns:
        high_unc = df[df["regime"] == "high_uncertainty"]
        fig.add_trace(go.Scatter(
            x=high_unc["date"], y=high_unc["curve_spread"],
            mode="markers", name="High Uncertainty",
            marker=dict(color=COLORS["gold"], size=6)
        ))
        
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        title="1y1y-3y3y Spread & Market Regimes",
        title_font_size=20,
        xaxis=dict(showgrid=True, gridcolor=COLORS["gray"], zerolinecolor=COLORS["gray"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], zerolinecolor=COLORS["beige"], title="Spread"),
        hovermode="x unified"
    )
    return fig


def create_fiscal_chart(df):
    """Std_4y (fiscal uncertainty) with regime-coloured background."""
    if df.empty or "std_4y" not in df.columns:
        return go.Figure()

    fig = go.Figure()

    # Background shading per regime
    if "regime" in df.columns:
        regime_colors = {
            "high_uncertainty": "rgba(231,76,60,0.10)",
            "medium_uncertainty": "rgba(180,166,128,0.10)",
            "low_uncertainty": "rgba(0,172,172,0.10)",
        }
        prev_regime = None
        start_date = None
        for _, row in df.iterrows():
            r = row["regime"]
            if r != prev_regime:
                if prev_regime is not None and start_date is not None:
                    fig.add_vrect(
                        x0=start_date, x1=row["date"],
                        fillcolor=regime_colors.get(prev_regime, "rgba(0,0,0,0)"),
                        layer="below", line_width=0,
                    )
                start_date = row["date"]
                prev_regime = r
        # Close last segment
        if prev_regime is not None and start_date is not None:
            fig.add_vrect(
                x0=start_date, x1=df["date"].iloc[-1],
                fillcolor=regime_colors.get(prev_regime, "rgba(0,0,0,0)"),
                layer="below", line_width=0,
            )

    fig.add_trace(go.Scatter(
        x=df["date"], y=df["std_4y"],
        mode="lines", name="Std 4Y (level)",
        line=dict(color=COLORS["dark"], width=2),
    ))

    # Add Z-score on secondary axis if available
    if "std_4y_zscore" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["std_4y_zscore"],
            mode="lines", name="Z-Score (rolling)",
            line=dict(color=COLORS["teal"], width=2, dash="dash"),
            yaxis="y2",
        ))

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        title="4Y Primary Surplus Std Dev & Rolling Z-Score",
        title_font_size=20,
        xaxis=dict(showgrid=True, gridcolor=COLORS["gray"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], title="Std Dev (level)"),
        yaxis2=dict(title="Z-Score", overlaying="y", side="right", showgrid=False),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def create_regime_chart(df):
    """Regime probability time series."""
    if df.empty or "prob_high_vol" not in df.columns:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["date"], y=df["prob_high_vol"],
        mode="lines", name="P(Rising Uncertainty)",
        fill="tozeroy",
        line=dict(color="#e74c3c", width=1),
        fillcolor="rgba(231,76,60,0.2)",
    ))

    # 50% threshold line
    fig.add_hline(y=0.5, line_dash="dot", line_color=COLORS["gold"],
                  annotation_text="50% threshold", annotation_position="top left")

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        title="Markov Regime Probability (Differenced Model)",
        title_font_size=20,
        xaxis=dict(showgrid=True, gridcolor=COLORS["gray"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], title="Probability", range=[0, 1]),
        hovermode="x unified",
    )
    return fig


def create_market_variables_chart():
    """Create 3-subplot chart for market variables: swaps, FRA, and steepening"""
    df_predi, df_fra = load_market_data()
    
    if df_predi.empty or df_fra.empty:
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=("DI Swap Rates", "FRA Rates", "Steepening Spread (1y1y - 3y3y)"),
            vertical_spacing=0.12
        )
        return fig
    
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=(
            "DI Swap Rates: 1Y vs 2Y and 3Y vs 6Y",
            "FRA Rates: 1y1y vs 3y3y",
            "Steepening Spread (3y3y - 1y1y)"
        ),
        vertical_spacing=0.10
    )
    
    # Subplot 1: DI Swap rates
    # predi_252 = 1Y, predi_504 = 2Y
    # predi_756 = 3Y, predi_1512 = 6Y
    fig.add_trace(go.Scatter(
        x=df_predi["date"], y=df_predi["predi_252"],
        mode="lines", name="1Y (252d)",
        line=dict(color=COLORS["teal"], width=2),
        legendgroup="group1"
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=df_predi["date"], y=df_predi["predi_504"],
        mode="lines", name="2Y (504d)",
        line=dict(color=COLORS["dark"], width=2),
        legendgroup="group1"
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=df_predi["date"], y=df_predi["predi_756"],
        mode="lines", name="3Y (756d)",
        line=dict(color=COLORS["gold"], width=2, dash="dash"),
        legendgroup="group1"
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=df_predi["date"], y=df_predi["predi_1512"],
        mode="lines", name="6Y (1512d)",
        line=dict(color=COLORS["red"], width=2, dash="dash"),
        legendgroup="group1"
    ), row=1, col=1)
    
    # Subplot 2: FRA rates
    fig.add_trace(go.Scatter(
        x=df_fra["date"], y=df_fra["1y1y"],
        mode="lines", name="FRA 1y1y",
        line=dict(color=COLORS["teal"], width=2),
        legendgroup="group2"
    ), row=2, col=1)
    
    fig.add_trace(go.Scatter(
        x=df_fra["date"], y=df_fra["3y3y"],
        mode="lines", name="FRA 3y3y",
        line=dict(color=COLORS["dark"], width=2),
        legendgroup="group2"
    ), row=2, col=1)
    
    # Subplot 3: Steepening spread
    steepening = df_fra["1y1y"] - df_fra["3y3y"]
    fig.add_trace(go.Scatter(
        x=df_fra["date"], y=steepening,
        mode="lines", name="Steepening (3y3y - 1y1y)",
        line=dict(color=COLORS["teal"], width=2),
        fill='tozeroy',
        fillcolor="rgba(0,172,172,0.1)",
        legendgroup="group3"
    ), row=3, col=1)
    
    # Add zero line for steepening
    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["gray"], row=3, col=1)
    
    # Update layout
    fig.update_layout(
        height=900,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )
    
    # Update axes
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["gray"])
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="Rate (%)", row=1, col=1)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="Rate (%)", row=2, col=1)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="Spread (%)", row=3, col=1)
    
    return fig


def create_macro_chart():
    """Create 2-subplot chart for macro variables"""
    df_macro = load_macro_data()
    
    if df_macro.empty:
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=("Primary Surplus Median Forecasts", "Primary Surplus Std Dev Forecasts"),
            vertical_spacing=0.15
        )
        return fig
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            "Median Forecasts: 1Y vs 4Y Ahead",
            "Std Dev Forecasts: 1Y vs 4Y Ahead"
        ),
        vertical_spacing=0.12
    )
    
    # Subplot 1: Median forecasts
    # Add filled area to zero for 4Y median (like std dev plot)
    fig.add_trace(go.Scatter(
        x=df_macro["date"], y=df_macro["median_4y"],
        mode="lines", name="Median 4Y Ahead",
        line=dict(color=COLORS["dark"], width=2),
        fill='tozeroy',
        fillcolor="rgba(40,40,40,0.1)",
        legendgroup="macro1"
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=df_macro["date"], y=df_macro["median_1y"],
        mode="lines", name="Median 1Y Ahead",
        line=dict(color=COLORS["teal"], width=2),
        legendgroup="macro1"
    ), row=1, col=1)
    
    # Add zero line
    fig.add_hline(
        y=0, line_dash="solid", line_color=COLORS["gold"], line_width=2,
        annotation_text="0% threshold", annotation_position="top left",
        row=1, col=1
    )
    
    # Subplot 2: Std dev forecasts
    fig.add_trace(go.Scatter(
        x=df_macro["date"], y=df_macro["std_1y"],
        mode="lines", name="Std Dev 1Y Ahead",
        line=dict(color=COLORS["gold"], width=2),
        legendgroup="macro2"
    ), row=2, col=1)
    
    fig.add_trace(go.Scatter(
        x=df_macro["date"], y=df_macro["std_4y"],
        mode="lines", name="Std Dev 4Y Ahead",
        line=dict(color=COLORS["red"], width=2),
        fill='tozeroy',
        fillcolor="rgba(231,76,60,0.1)",
        legendgroup="macro2"
    ), row=2, col=1)
    
    # Update layout
    fig.update_layout(
        height=700,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )
    
    # Update axes
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["gray"])
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="% GDP", row=1, col=1)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="% GDP", row=2, col=1)
    
    return fig


def create_focus_expectations_chart():
    """Create 2x2 subplot chart for Focus expectations:
    1. IPCA median 12m ahead forecast
    2. IPCA std dev 12m ahead forecast
    3. SELIC 1y ahead median forecast
    4. SELIC 1y ahead std dev forecast
    """
    df_ipca = load_ipca_data()
    df_selic = load_selic_forecast_data()
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "IPCA Median 12M Ahead Forecast",
            "IPCA Std Dev 12M Ahead Forecast",
            "SELIC 1Y Ahead Median Forecast",
            "SELIC 1Y Ahead Std Dev Forecast"
        ),
        vertical_spacing=0.15,
        horizontal_spacing=0.10
    )
    
    # Subplot 1: IPCA Median 12M
    if not df_ipca.empty and "median_forecast" in df_ipca.columns:
        fig.add_trace(go.Scatter(
            x=df_ipca["date"], y=df_ipca["median_forecast"],
            mode="lines", name="IPCA Median 12M",
            line=dict(color=COLORS["teal"], width=2),
            fill='tozeroy',
            fillcolor="rgba(0,172,172,0.1)",
            legendgroup="ipca"
        ), row=1, col=1)
    
    # Subplot 2: IPCA Std Dev 12M
    if not df_ipca.empty and "std_forecast" in df_ipca.columns:
        fig.add_trace(go.Scatter(
            x=df_ipca["date"], y=df_ipca["std_forecast"],
            mode="lines", name="IPCA Std Dev 12M",
            line=dict(color=COLORS["red"], width=2),
            fill='tozeroy',
            fillcolor="rgba(231,76,60,0.1)",
            legendgroup="ipca"
        ), row=1, col=2)
    
    # Subplot 3: SELIC Median 1Y
    if not df_selic.empty and "median_forecast" in df_selic.columns:
        fig.add_trace(go.Scatter(
            x=df_selic["date"], y=df_selic["median_forecast"],
            mode="lines", name="SELIC Median 1Y",
            line=dict(color=COLORS["dark"], width=2),
            fill='tozeroy',
            fillcolor="rgba(40,40,40,0.1)",
            legendgroup="selic"
        ), row=2, col=1)
    
    # Subplot 4: SELIC Std Dev 1Y
    if not df_selic.empty and "std_forecast" in df_selic.columns:
        fig.add_trace(go.Scatter(
            x=df_selic["date"], y=df_selic["std_forecast"],
            mode="lines", name="SELIC Std Dev 1Y",
            line=dict(color=COLORS["gold"], width=2),
            fill='tozeroy',
            fillcolor="rgba(180,166,128,0.2)",
            legendgroup="selic"
        ), row=2, col=2)
    
    # Update layout
    fig.update_layout(
        height=800,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )
    
    # Update axes
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["gray"])
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"])
    
    # Update y-axis titles
    fig.update_yaxes(title_text="Inflation (%)", row=1, col=1)
    fig.update_yaxes(title_text="Std Dev (%)", row=1, col=2)
    fig.update_yaxes(title_text="Rate (%)", row=2, col=1)
    fig.update_yaxes(title_text="Std Dev (%)", row=2, col=2)
    
    return fig


def create_strategy_chart():
    """Create 3-subplot chart for Strategy tab:
    1. Spread between 1y1y and 3y3y
    2. Std dev 4y (line) + EPU markers (secondary axis, end-of-month only)
    3. VIX (lightweight - rhetorical comparison)
    """
    df_fra = load_market_data()[1]  # Get FRA data
    df_macro = load_macro_data()
    df_epu = load_epu_data()
    df_vix = load_vix_data()
    
    # Align data to steepening spread start date (2012)
    if not df_fra.empty:
        start_date = df_fra["date"].min()
        df_macro = df_macro[df_macro["date"] >= start_date] if not df_macro.empty else df_macro
        df_epu = df_epu[df_epu["date"] >= start_date] if not df_epu.empty else df_epu
        df_vix = df_vix[df_vix["date"] >= start_date] if not df_vix.empty else df_vix
    
    # Get date range from steepening spread data for alignment
    x_min = df_fra["date"].min() if not df_fra.empty else None
    x_max = df_fra["date"].max() if not df_fra.empty else None
    
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=(
            "Steepening Spread: 3y3y - 1y1y",
            "Fiscal Uncertainty vs EPU",
            "VIX — Rhetorical: Shows EPU & Std Dev 4Y are not driven by short-term risk factors"
        ),
        vertical_spacing=0.10,
        specs=[[{"secondary_y": False}], [{"secondary_y": True}], [{"secondary_y": False}]],
        shared_xaxes=True,
        row_heights=[0.4, 0.4, 0.2]
    )
    
    if not df_fra.empty:
        # Subplot 1: Steepening spread
        spread = df_fra["3y3y"] - df_fra["1y1y"]
        fig.add_trace(go.Scatter(
            x=df_fra["date"], y=spread,
            mode="lines", name="Steepening Spread",
            line=dict(color=COLORS["teal"], width=2),
            fill='tozeroy',
            fillcolor="rgba(0,172,172,0.1)",
            legendgroup="strategy1"
        ), row=1, col=1)
        
        # Add zero line
        fig.add_hline(y=0, line_dash="dot", line_color=COLORS["gray"], row=1, col=1)
    
    if not df_macro.empty:
        # Subplot 2: Std dev 4y (primary axis)
        fig.add_trace(go.Scatter(
            x=df_macro["date"], y=df_macro["std_4y"],
            mode="lines", name="Std Dev 4Y",
            line=dict(color=COLORS["red"], width=2),
            legendgroup="strategy2"
        ), row=2, col=1, secondary_y=False)
    
    if not df_epu.empty and not df_macro.empty:
        # Filter EPU to only end-of-month dates that exist in macro data
        df_epu_filtered = df_epu[df_epu["date"].isin(df_macro["date"])]
        
        # Add EPU markers on secondary axis
        fig.add_trace(go.Scatter(
            x=df_epu_filtered["date"], y=df_epu_filtered["EPU"],
            mode="markers", name="EPU (month-end)",
            marker=dict(color=COLORS["gold"], size=6, symbol="diamond"),
            legendgroup="strategy2"
        ), row=2, col=1, secondary_y=True)
    
    # Subplot 3: VIX (lightweight)
    if not df_vix.empty:
        fig.add_trace(go.Scatter(
            x=df_vix["date"], y=df_vix["VIX"],
            mode="lines", name="VIX",
            line=dict(color=COLORS["blue"], width=1.5, dash="dot"),
            legendgroup="strategy3"
        ), row=3, col=1)
    
    # Update layout
    fig.update_layout(
        height=900,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )
    
    # Update axes with shared x-range
    fig.update_xaxes(
        showgrid=True, 
        gridcolor=COLORS["gray"],
        range=[x_min, x_max] if x_min is not None and x_max is not None else None
    )
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="Spread (%)", row=1, col=1)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="Std Dev (% GDP)", row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text="EPU Index", showgrid=False, row=2, col=1, secondary_y=True)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="VIX", row=3, col=1)
    
    return fig


def create_pca_chart():
    """
    Create PCA chart using 4 series:
    - IPCA median 12M
    - IPCA std dev 12M  
    - SELIC median 1Y
    - SELIC std dev 1Y
    
    Plots PC1 for the full sample starting from Jan 2005 (when SELIC data begins).
    """
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    
    # Load data
    df_ipca = load_ipca_data()
    df_selic = load_selic_forecast_data()
    
    if df_ipca.empty or df_selic.empty:
        return go.Figure()
    
    # Start from Jan 2005 when SELIC data begins
    start_date = pd.Timestamp("2005-01-03")
    
    # Filter data since Jan 2005
    df_ipca = df_ipca[df_ipca["date"] >= start_date].copy()
    df_selic = df_selic[df_selic["date"] >= start_date].copy()
    
    # Merge all data on date
    df_merged = pd.merge(
        df_ipca[["date", "median_forecast", "std_forecast"]].rename(
            columns={"median_forecast": "ipca_median", "std_forecast": "ipca_std"}
        ),
        df_selic[["date", "median_forecast", "std_forecast"]].rename(
            columns={"median_forecast": "selic_median", "std_forecast": "selic_std"}
        ),
        on="date",
        how="inner"
    )
    
    if df_merged.empty:
        return go.Figure()
    
    # Prepare data for PCA (drop NaN)
    features = ["ipca_median", "ipca_std", "selic_median", "selic_std"]
    df_pca = df_merged.dropna(subset=features)
    
    if len(df_pca) < 10:
        return go.Figure()
    
    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_pca[features])
    
    # Apply PCA
    pca = PCA(n_components=2)
    pc_scores = pca.fit_transform(X_scaled)
    
    # Add PC1 to dataframe
    df_pca["PC1"] = pc_scores[:, 0]
    
    # Get explained variance
    explained_var = pca.explained_variance_ratio_[0] * 100
    
    # Get loadings for annotation
    loadings = pca.components_[0]
    
    # Create figure
    fig = go.Figure()
    
    # Plot PC1
    fig.add_trace(go.Scatter(
        x=df_pca["date"],
        y=df_pca["PC1"],
        mode="lines",
        name="PC1",
        line=dict(color=COLORS["teal"], width=2),
        fill='tozeroy',
        fillcolor="rgba(0,172,172,0.1)"
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["gray"])
    
    # Create loadings annotation text
    loadings_text = (
        f"<b>PC1 Loadings:</b><br>"
        f"IPCA Median: {loadings[0]:.3f}<br>"
        f"IPCA Std Dev: {loadings[1]:.3f}<br>"
        f"SELIC Median: {loadings[2]:.3f}<br>"
        f"SELIC Std Dev: {loadings[3]:.3f}"
    )
    
    # Add annotation
    fig.add_annotation(
        x=0.02,
        y=0.98,
        xref="paper",
        yref="paper",
        text=loadings_text,
        showarrow=False,
        font=dict(size=11, color=COLORS["dark"]),
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor=COLORS["gray"],
        borderwidth=1,
        borderpad=4,
        align="left"
    )
    
    # Update layout
    fig.update_layout(
        height=500,
        title=f"PC1 - Macro Expectations Factor ({explained_var:.1f}% variance explained)",
        title_font_size=16,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        showlegend=False,
        hovermode="x unified",
        xaxis=dict(showgrid=True, gridcolor=COLORS["gray"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], title="PC1 Score")
    )
    
    return fig


# =====================================================================
# P&L ATTRIBUTION CHART FUNCTIONS
# =====================================================================

def create_pnl_attribution_cumulative_chart(df):
    """Stacked area chart of cumulative curve, gamma, carry, cost P&L."""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    # Total P&L on top
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["Cumulative PnL"],
        mode="lines", name="Total P&L",
        line=dict(color=COLORS["dark"], width=3),
    ))

    # Stacked components
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["Cumulative Curve PnL"],
        mode="lines", name="Curve P&L",
        line=dict(color=COLORS["teal"], width=2),
        fill="tozeroy",
        fillcolor="rgba(0,172,172,0.15)",
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["Cumulative Gamma PnL"],
        mode="lines", name="Gamma P&L",
        line=dict(color=COLORS["gold"], width=2, dash="dash"),
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["Cumulative Carry PnL"],
        mode="lines", name="Carry P&L",
        line=dict(color=COLORS["blue"], width=2, dash="dot"),
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["Cumulative Cost PnL"],
        mode="lines", name="Cost P&L",
        line=dict(color=COLORS["red"], width=2, dash="dashdot"),
    ))

    fig.update_layout(
        height=500,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        title="Cumulative P&L Attribution",
        title_font_size=20,
        xaxis=dict(showgrid=True, gridcolor=COLORS["gray"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], title="Cumulative P&L (bps)"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def create_pnl_attribution_waterfall_chart(df):
    """Monthly waterfall chart — each bar is one month with stacked attribution."""
    if df.empty:
        return go.Figure()

    df = df.copy()
    df["month"] = df["date"].dt.to_period("M").astype(str)

    monthly = df.groupby("month").agg(
        curve=("curve_pnl", "sum"),
        gamma=("gamma_pnl", "sum"),
        carry=("carry_pnl", "sum"),
        cost=("cost_pnl", "sum"),
        total=("total_pnl", "sum"),
    ).reset_index()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=monthly["month"], y=monthly["curve"],
        name="Curve", marker_color=COLORS["teal"],
    ))
    fig.add_trace(go.Bar(
        x=monthly["month"], y=monthly["gamma"],
        name="Gamma", marker_color=COLORS["gold"],
    ))
    fig.add_trace(go.Bar(
        x=monthly["month"], y=monthly["carry"],
        name="Carry", marker_color=COLORS["blue"],
    ))
    fig.add_trace(go.Bar(
        x=monthly["month"], y=monthly["cost"],
        name="Cost", marker_color=COLORS["red"],
    ))

    fig.update_layout(
        barmode="relative",
        height=500,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        title="Monthly P&L Attribution Waterfall",
        title_font_size=20,
        xaxis=dict(showgrid=False, title="Month", tickangle=-45, dtick=3, type="category"),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], title="P&L (bps)"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def create_pnl_attribution_summary_chart(df):
    """Horizontal bar chart — total attribution by component for the whole backtest."""
    if df.empty:
        return go.Figure()

    components = ["Curve P&L", "Gamma P&L", "Carry", "Costs"]
    values = [
        df["curve_pnl"].sum(),
        df["gamma_pnl"].sum(),
        df["carry_pnl"].sum(),
        df["cost_pnl"].sum(),
    ]
    bar_colors = [COLORS["teal"], COLORS["gold"], COLORS["blue"], COLORS["red"]]

    fig = go.Figure(go.Bar(
        x=values,
        y=components,
        orientation="h",
        marker_color=bar_colors,
        text=[f"{v:+.1f}" for v in values],
        textposition="outside",
        textfont=dict(size=13, family="monospace"),
    ))

    fig.update_layout(
        height=320,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        title="Total P&L Attribution Summary (bps)",
        title_font_size=20,
        xaxis=dict(showgrid=True, gridcolor=COLORS["beige"], title="Total P&L (bps)"),
        yaxis=dict(showgrid=False),
        margin=dict(l=120),
    )
    return fig


def create_pnl_daily_decomposition_chart(df):
    """Daily stacked bar chart showing P&L decomposition."""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["date"], y=df["curve_pnl"],
        name="Curve", marker_color=COLORS["teal"],
    ))
    fig.add_trace(go.Bar(
        x=df["date"], y=df["gamma_pnl"],
        name="Gamma", marker_color=COLORS["gold"],
    ))
    fig.add_trace(go.Bar(
        x=df["date"], y=df["carry_pnl"],
        name="Carry", marker_color=COLORS["blue"],
    ))
    fig.add_trace(go.Bar(
        x=df["date"], y=df["cost_pnl"],
        name="Cost", marker_color=COLORS["red"],
    ))

    fig.update_layout(
        barmode="relative",
        height=400,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        title="Daily P&L Decomposition",
        title_font_size=20,
        xaxis=dict(showgrid=True, gridcolor=COLORS["gray"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], title="Daily P&L (bps)"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


# =====================================================================
# PERFORMANCE ATTRIBUTION CHART FUNCTIONS
# =====================================================================

def create_drawdown_chart(df):
    """Drawdown curve from peak cumulative P&L."""
    if df.empty:
        return go.Figure()

    cumulative = df["total_pnl"].cumsum()
    peak = cumulative.expanding().max()
    drawdown = cumulative - peak

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["date"], y=drawdown,
        mode="lines", name="Drawdown",
        fill="tozeroy",
        line=dict(color=COLORS["red"], width=2),
        fillcolor="rgba(231,76,60,0.15)",
    ))

    fig.update_layout(
        height=400,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        title="Drawdown from Peak (bps)",
        title_font_size=20,
        xaxis=dict(showgrid=True, gridcolor=COLORS["gray"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], title="Drawdown (bps)"),
        hovermode="x unified",
    )
    return fig


def create_monthly_heatmap(df):
    """Monthly P&L heatmap — rows = years, columns = months."""
    if df.empty:
        return go.Figure()

    df = df.copy()
    df["year"] = df["date"].dt.year
    df["month_num"] = df["date"].dt.month

    pivot = df.groupby(["year", "month_num"])["total_pnl"].sum().reset_index()
    pivot = pivot.pivot(index="year", columns="month_num", values="total_pnl")

    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Re-index columns 1-12 to fill missing months with NaN
    pivot = pivot.reindex(columns=range(1, 13))

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=month_labels,
        y=pivot.index.astype(str),
        colorscale=[
            [0, "#e74c3c"],
            [0.5, "#ffffff"],
            [1, "#00acac"],
        ],
        zmid=0,
        text=np.where(np.isnan(pivot.values), "", np.round(pivot.values, 1).astype(str)),
        texttemplate="%{text}",
        textfont=dict(size=11),
        hovertemplate="Year: %{y}<br>Month: %{x}<br>P&L: %{z:.1f} bps<extra></extra>",
        colorbar=dict(title="P&L (bps)"),
    ))

    fig.update_layout(
        height=max(300, len(pivot) * 40 + 120),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        title="Monthly P&L Heatmap (bps)",
        title_font_size=20,
        xaxis=dict(side="top"),
        yaxis=dict(autorange="reversed"),
    )
    return fig


def create_regime_attribution_chart(df):
    """Grouped bar chart showing P&L attribution per regime."""
    if df.empty or "regime" not in df.columns:
        return go.Figure()

    grouped = df.groupby("regime").agg(
        days=("total_pnl", "count"),
        total=("total_pnl", "sum"),
        curve=("curve_pnl", "sum"),
        gamma=("gamma_pnl", "sum"),
        carry=("carry_pnl", "sum"),
        cost=("cost_pnl", "sum"),
    ).reset_index()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=grouped["regime"], y=grouped["curve"],
        name="Curve", marker_color=COLORS["teal"],
    ))
    fig.add_trace(go.Bar(
        x=grouped["regime"], y=grouped["gamma"],
        name="Gamma", marker_color=COLORS["gold"],
    ))
    fig.add_trace(go.Bar(
        x=grouped["regime"], y=grouped["carry"],
        name="Carry", marker_color=COLORS["blue"],
    ))
    fig.add_trace(go.Bar(
        x=grouped["regime"], y=grouped["cost"],
        name="Cost", marker_color=COLORS["red"],
    ))

    # Add total as scatter markers
    fig.add_trace(go.Scatter(
        x=grouped["regime"], y=grouped["total"],
        mode="markers+text", name="Total",
        marker=dict(color=COLORS["dark"], size=12, symbol="diamond"),
        text=[f"{v:+.1f}" for v in grouped["total"]],
        textposition="top center",
        textfont=dict(size=11, family="monospace"),
    ))

    fig.update_layout(
        barmode="group",
        height=450,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        title="P&L Attribution by Regime",
        title_font_size=20,
        xaxis=dict(showgrid=False, title="Regime"),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], title="P&L (bps)"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def create_rolling_sharpe_chart(df, window=63):
    """Rolling Sharpe ratio chart (default 63-day = ~3 months)."""
    if df.empty:
        return go.Figure()

    rolling_mean = df["total_pnl"].rolling(window).mean()
    rolling_std = df["total_pnl"].rolling(window).std()
    rolling_sharpe = (rolling_mean / rolling_std.replace(0, np.nan)) * np.sqrt(252)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["date"], y=rolling_sharpe,
        mode="lines", name=f"{window}d Rolling Sharpe",
        line=dict(color=COLORS["teal"], width=2),
    ))

    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["gray"])
    fig.add_hline(y=1, line_dash="dot", line_color=COLORS["gold"],
                  annotation_text="Sharpe = 1", annotation_position="top left")

    fig.update_layout(
        height=350,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        title=f"Rolling {window}-Day Annualized Sharpe Ratio",
        title_font_size=20,
        xaxis=dict(showgrid=True, gridcolor=COLORS["gray"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], title="Sharpe Ratio"),
        hovermode="x unified",
    )
    return fig


# Define the components of the layout
navbar = html.Nav(
    className="navbar",
    children=[
        html.Div("SCHONFELD", className="logo"),
        html.Div(
            className="nav-links",
            children=[
                html.A("Home", href="#", className="nav-link"),
                html.A("About Us", href="#", className="nav-link"),
                html.A("Strategies", href="#", className="nav-link"),
                html.A("Insights", href="#", className="nav-link"),
            ]
        )
    ]
)

hero = html.Section(
    className="hero-section",
    children=[
        html.H1("Primary Surplus Strategy Dashboard"),
        html.P("Interactive performance analytics for the Steepener/Flattener Strategy, adapting to fiscal uncertainty regimes.", style={"maxWidth": "800px", "margin": "0 auto", "fontSize": "1.2rem"}),
        html.Br(),
        html.Div(
            style={"display": "flex", "justifyContent": "center", "alignItems": "center", "gap": "1rem", "marginTop": "2rem"},
            children=[
                html.Label("Select Strategy Version: ", style={"fontWeight": "bold"}),
                dcc.Dropdown(
                    id="version-selector",
                    options=[
                        {"label": "Version 6 (PCA Inflation Filter)", "value": "v6"},
                        {"label": "Version 5 (Advanced Dynamic Size)", "value": "v5"},
                        {"label": "Version 4 (Regime Filtered)", "value": "v4"},
                        {"label": "Version 3 (Volatility Scaled)", "value": "v3"},
                        {"label": "Version 2 (Base Steepener)", "value": "v2"},
                        {"label": "Version 1 (Initial)", "value": ""}
                    ],
                    value="v6",
                    clearable=False,
                    style={"width": "300px", "textAlign": "left"}
                )
            ]
        )
    ]
)

metrics_section = html.Section(
    className="metrics-section",
    style={"padding": "2rem 5%", "backgroundColor": COLORS["light_gray"], "display": "flex", "justifyContent": "space-around", "flexWrap": "wrap", "gap": "1rem"},
    children=[
        html.Div(className="metric-card", id="metric-total-return", style={"textAlign": "center", "padding": "1.5rem", "backgroundColor": COLORS["white"], "borderRadius": "8px", "boxShadow": "0 4px 6px rgba(0,0,0,0.05)", "flex": "1", "minWidth": "200px"}),
        html.Div(className="metric-card", id="metric-sharpe", style={"textAlign": "center", "padding": "1.5rem", "backgroundColor": COLORS["white"], "borderRadius": "8px", "boxShadow": "0 4px 6px rgba(0,0,0,0.05)", "flex": "1", "minWidth": "200px"}),
        html.Div(className="metric-card", id="metric-win-rate", style={"textAlign": "center", "padding": "1.5rem", "backgroundColor": COLORS["white"], "borderRadius": "8px", "boxShadow": "0 4px 6px rgba(0,0,0,0.05)", "flex": "1", "minWidth": "200px"}),
        html.Div(className="metric-card", id="metric-trades", style={"textAlign": "center", "padding": "1.5rem", "backgroundColor": COLORS["white"], "borderRadius": "8px", "boxShadow": "0 4px 6px rgba(0,0,0,0.05)", "flex": "1", "minWidth": "200px"}),
    ]
)

# --- Tab Content: Performance (original content) ---
performance_tab = html.Div(
    children=[
        html.Section(
            id="chart-section",
            className="accent-section",
            style={"padding": "4rem 5%"},
            children=[
                html.H2("Performance Analytics", style={"textAlign": "center", "marginBottom": "2rem"}),
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr", "gap": "2rem"},
                    children=[
                        html.Div(
                            className="chart-container",
                            style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)"},
                            children=[dcc.Graph(id="pnl-chart", config={"displayModeBar": False})]
                        ),
                        html.Div(
                            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "2rem"},
                            children=[
                                html.Div(
                                    className="chart-container",
                                    style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)"},
                                    children=[dcc.Graph(id="position-chart", config={"displayModeBar": False})]
                                ),
                                html.Div(
                                    className="chart-container",
                                    style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)"},
                                    children=[dcc.Graph(id="spread-chart", config={"displayModeBar": False})]
                                )
                            ]
                        )
                    ]
                )
            ]
        ),
        # --- Fiscal Uncertainty & Regime Section (point-in-time, driven by date picker) ---
        html.Section(
            className="accent-section",
            style={"padding": "4rem 5%", "backgroundColor": COLORS["white"]},
            children=[
                html.H2("Fiscal Uncertainty & Regime Analysis", style={"textAlign": "center", "marginBottom": "0.5rem"}),
                html.P(
                    id="fiscal-section-subtitle",
                    children="Select a date below to see the point-in-time view.",
                    style={"textAlign": "center", "marginBottom": "2rem", "opacity": 0.6, "fontStyle": "italic"},
                ),
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "2rem"},
                    children=[
                        html.Div(
                            className="chart-container",
                            style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)"},
                            children=[dcc.Graph(id="fiscal-chart", config={"displayModeBar": False})],
                        ),
                        html.Div(
                            className="chart-container",
                            style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)"},
                            children=[dcc.Graph(id="regime-chart", config={"displayModeBar": False})],
                        ),
                    ],
                ),
            ],
        ),
        # --- PCA Regime Analysis Section (V6 only, point-in-time) ---
        html.Section(
            className="accent-section",
            style={"padding": "4rem 5%", "backgroundColor": COLORS["light_gray"]},
            children=[
                html.H2("PCA Regime Analysis (3-Regime Markov)", style={"textAlign": "center", "marginBottom": "0.5rem"}),
                html.P(
                    id="pca-section-subtitle",
                    children="Point-in-time view of inflation expectations regime (uses same date as Trading Details).",
                    style={"textAlign": "center", "marginBottom": "2rem", "opacity": 0.6, "fontStyle": "italic"},
                ),
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "2rem"},
                    children=[
                        html.Div(
                            className="chart-container",
                            style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)"},
                            children=[dcc.Graph(id="pca1-chart", config={"displayModeBar": False})],
                        ),
                        html.Div(
                            className="chart-container",
                            style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)"},
                            children=[dcc.Graph(id="pca-regime-chart", config={"displayModeBar": False})],
                        ),
                    ],
                ),
            ],
        ),
        # --- Trading Details Section ---
        html.Section(
            className="accent-section",
            style={"padding": "3rem 5%", "backgroundColor": COLORS["light_gray"]},
            children=[
                html.H2("Trading Details Explorer", style={"textAlign": "center", "marginBottom": "1.5rem"}),
                html.P(
                    "Select a date to see the regime classification, position, execution style, and P&L breakdown.",
                    style={"textAlign": "center", "marginBottom": "2rem", "opacity": 0.7},
                ),
                html.Div(
                    style={"display": "flex", "justifyContent": "center", "gap": "2rem", "flexWrap": "wrap"},
                    children=[
                        # Date picker
                        html.Div(
                            style={
                                "backgroundColor": COLORS["white"],
                                "padding": "1.5rem",
                                "borderRadius": "8px",
                                "boxShadow": "0 4px 12px rgba(0,0,0,0.05)",
                                "minWidth": "280px",
                            },
                            children=[
                                html.Label("Pick a trading date:", style={"fontWeight": "bold", "display": "block", "marginBottom": "0.5rem"}),
                                dcc.DatePickerSingle(
                                    id="trade-date-picker",
                                    display_format="YYYY-MM-DD",
                                    style={"width": "100%"},
                                ),
                            ],
                        ),
                        # Detail cards
                        html.Div(
                            id="trade-detail-panel",
                            style={
                                "backgroundColor": COLORS["white"],
                                "padding": "1.5rem 2rem",
                                "borderRadius": "8px",
                                "boxShadow": "0 4px 12px rgba(0,0,0,0.05)",
                                "flex": "1",
                                "maxWidth": "800px",
                                "minHeight": "180px",
                            },
                            children=[html.P("← Select a date to view details", style={"opacity": 0.5, "marginTop": "3rem", "textAlign": "center"})],
                        ),
                    ],
                ),
            ],
        ),
    ]
)

# --- Tab Content: Market Variables ---
market_variables_tab = html.Div(
    children=[
        html.Section(
            className="accent-section",
            style={"padding": "4rem 5%", "backgroundColor": COLORS["white"]},
            children=[
                html.H2("Market Variables", style={"textAlign": "center", "marginBottom": "1rem"}),
                html.P(
                    "Key rate components used in the steepener strategy construction",
                    style={"textAlign": "center", "marginBottom": "2rem", "opacity": 0.7}
                ),
                html.Div(
                    className="chart-container",
                    style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)", "marginBottom": "2rem"},
                    children=[dcc.Graph(id="market-variables-chart", config={"displayModeBar": False}, figure=create_market_variables_chart())]
                ),
                # LaTeX Formulas Section
                html.Div(
                    style={
                        "backgroundColor": COLORS["light_gray"],
                        "padding": "2rem",
                        "borderRadius": "8px",
                        "marginTop": "2rem"
                    },
                    children=[
                        html.H3("Composition Formulas", style={"textAlign": "center", "marginBottom": "1.5rem"}),
                        html.Div(
                            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "2rem"},
                            children=[
                                html.Div(
                                    children=[
                                        html.H4("DI Swap Pre-DI Rates", style={"color": COLORS["teal"], "marginBottom": "1rem"}),
                                        dcc.Markdown(
                                            r"""
                                            **Short-end (1Y vs 2Y):**
                                            $$r_{1Y} = \text{predi}_{252}, \quad r_{2Y} = \text{predi}_{504}$$
                                            
                                            **Long-end (3Y vs 6Y):**
                                            $$r_{3Y} = \text{predi}_{756}, \quad r_{6Y} = \text{predi}_{1512}$$
                                            
                                            where $\text{predi}_n$ is the n-day pre-DI swap rate.
                                            """,
                                            mathjax=True,
                                            style={"fontSize": "0.95rem"}
                                        )
                                    ]
                                ),
                                html.Div(
                                    children=[
                                        html.H4("Forward Rate Agreements (FRA)", style={"color": COLORS["teal"], "marginBottom": "1rem"}),
                                        dcc.Markdown(
                                            r"""
                                            **1Y×1Y FRA:**
                                            $$\text{FRA}_{1y1y} = \frac{(1 + r_{2Y})^2}{(1 + r_{1Y})} - 1$$
                                            
                                            **3Y×3Y FRA:**
                                            $$\text{FRA}_{3y3y} = \frac{(1 + r_{6Y})^6}{(1 + r_{3Y})^3}^{1/3} - 1$$
                                            """,
                                            mathjax=True,
                                            style={"fontSize": "0.95rem"}
                                        )
                                    ]
                                ),
                                html.Div(
                                    style={"gridColumn": "1 / -1"},
                                    children=[
                                        html.H4("Steepening Spread", style={"color": COLORS["teal"], "marginBottom": "1rem"}),
                                        dcc.Markdown(
                                            r"""
                                            $$\text{Steepening} = \text{FRA}_{3y3y} - \text{FRA}_{1y1y}$$
                                            
                                            The strategy takes a **steepener** position when the spread is expected to widen (short-end rises relative to long-end),
                                            and a **flattener** position when the spread is expected to narrow.
                                            """,
                                            mathjax=True,
                                            style={"fontSize": "0.95rem"}
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                )
            ]
        )
    ]
)

# --- Tab Content: Macro Variables ---
macro_tab = html.Div(
    children=[
        html.Section(
            className="accent-section",
            style={"padding": "4rem 5%", "backgroundColor": COLORS["white"]},
            children=[
                html.H2("Macro Variables", style={"textAlign": "center", "marginBottom": "1rem"}),
                html.P(
                    "Primary surplus forecasts from FOCUS survey with temporal interpolation",
                    style={"textAlign": "center", "marginBottom": "2rem", "opacity": 0.7}
                ),
                html.Div(
                    className="chart-container",
                    style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)", "marginBottom": "2rem"},
                    children=[dcc.Graph(id="macro-chart", config={"displayModeBar": False}, figure=create_macro_chart())]
                ),
                # LaTeX Formulas Section
                html.Div(
                    style={
                        "backgroundColor": COLORS["light_gray"],
                        "padding": "2rem",
                        "borderRadius": "8px",
                        "marginTop": "2rem"
                    },
                    children=[
                        html.H3("Temporal Interpolation Formula", style={"textAlign": "center", "marginBottom": "1.5rem"}),
                        dcc.Markdown(
                            r"""
                            The FOCUS survey provides forecasts at specific horizons (1Y, 3Y, 4Y). 
                            To create continuous time series, we use **linear temporal interpolation**:
                            
                            For a target horizon $h$ (in years) between available survey horizons $h_1$ and $h_2$:
                            
                            $$X_h(t) = X_{h_1}(t) + \frac{h - h_1}{h_2 - h_1} \cdot \left[X_{h_2}(t) - X_{h_1}(t)\right]$$
                            
                            where:
                            - $X_h(t)$ = interpolated value at horizon $h$ on date $t$
                            - $X_{h_1}(t), X_{h_2}(t)$ = surveyed values at adjacent horizons
                            - The interpolation weight $\omega = \frac{h - h_1}{h_2 - h_1} \in [0,1]$
                            
                            **Applied to our case:**
                            - Median forecasts: $\text{median}_{1Y}(t), \text{median}_{4Y}(t)$ — interpolated to daily frequency
                            - Uncertainty measure: $\sigma_{1Y}(t), \sigma_{4Y}(t)$ — standard deviation across forecasters
                            """,
                            mathjax=True,
                            style={"fontSize": "0.95rem", "maxWidth": "900px", "margin": "0 auto"}
                        )
                    ]
                )
            ]
        )
    ]
)

# --- Tab Content: Strategy ---
strategy_tab = html.Div(
    children=[
        html.Section(
            className="accent-section",
            style={"padding": "4rem 5%", "backgroundColor": COLORS["white"]},
            children=[
                html.H2("Strategy", style={"textAlign": "center", "marginBottom": "1rem"}),
                html.P(
                    "Steepening spread and fiscal uncertainty vs Economic Policy Uncertainty (EPU)",
                    style={"textAlign": "center", "marginBottom": "2rem", "opacity": 0.7}
                ),
                html.Div(
                    className="chart-container",
                    style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)", "marginBottom": "2rem"},
                    children=[dcc.Graph(id="strategy-chart", config={"displayModeBar": False}, figure=create_strategy_chart())]
                ),
                # Description Section
                html.Div(
                    style={
                        "backgroundColor": COLORS["light_gray"],
                        "padding": "2rem",
                        "borderRadius": "8px",
                        "marginTop": "2rem"
                    },
                    children=[
                        html.H3("Strategy Components", style={"textAlign": "center", "marginBottom": "1.5rem"}),
                        html.Div(
                            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "2rem"},
                            children=[
                                html.Div(
                                    children=[
                                        html.H4("Steepening Spread", style={"color": COLORS["teal"], "marginBottom": "1rem"}),
                                        dcc.Markdown(
                                            r"""
                                            The spread between 1y1y and 3y3y forward rates captures the 
                                            slope of the yield curve between the 2nd and 4th years.
                                            
                                            $$\text{Spread} = \text{FRA}_{3y3y} - \text{FRA}_{1y1y}$$
                                            
                                            A **positive** spread indicates an upward sloping curve (steepener opportunity).
                                            A **negative** spread indicates inversion (flattener opportunity).
                                            """,
                                            mathjax=True,
                                            style={"fontSize": "0.95rem"}
                                        )
                                    ]
                                ),
                                html.Div(
                                    children=[
                                        html.H4("Fiscal Uncertainty vs EPU", style={"color": COLORS["teal"], "marginBottom": "1rem"}),
                                        dcc.Markdown(
                                            r"""
                                            **Std Dev 4Y** (red line): Cross-sectional standard deviation of 
                                            FOCUS survey forecasts for 4-year ahead primary surplus.
                                            
                                            **EPU** (gold diamonds): Economic Policy Uncertainty index from 
                                            Baker, Bloom & Davis. Monthly data shown as markers on month-end dates.
                                            
                                            Both measures capture uncertainty but from different sources: 
                                            fiscal expectations vs broader economic policy uncertainty.
                                            """,
                                            mathjax=True,
                                            style={"fontSize": "0.95rem"}
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                )
            ]
        ),
        # --- Focus Expectations Section ---
        html.Section(
            className="accent-section",
            style={"padding": "4rem 5%", "backgroundColor": COLORS["light_gray"]},
            children=[
                html.H2("Focus Survey Expectations", style={"textAlign": "center", "marginBottom": "1rem"}),
                html.P(
                    "IPCA (12M ahead) and SELIC (1Y ahead) forecasts with uncertainty bands",
                    style={"textAlign": "center", "marginBottom": "2rem", "opacity": 0.7}
                ),
                html.Div(
                    className="chart-container",
                    style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)", "marginBottom": "2rem"},
                    children=[dcc.Graph(id="focus-expectations-chart", config={"displayModeBar": False}, figure=create_focus_expectations_chart())]
                ),
                # Description Section
                html.Div(
                    style={
                        "backgroundColor": COLORS["white"],
                        "padding": "2rem",
                        "borderRadius": "8px",
                        "marginTop": "2rem"
                    },
                    children=[
                        html.H3("Focus Survey Components", style={"textAlign": "center", "marginBottom": "1.5rem"}),
                        html.Div(
                            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "2rem"},
                            children=[
                                html.Div(
                                    children=[
                                        html.H4("IPCA Inflation Expectations", style={"color": COLORS["teal"], "marginBottom": "1rem"}),
                                        dcc.Markdown(
                                            r"""
                                            **Median 12M**: Median 12-month ahead inflation forecast from FOCUS survey.
                                            
                                            **Std Dev 12M**: Cross-sectional standard deviation of forecaster expectations,
                                            measuring disagreement/uncertainty about future inflation.
                                            
                                            Source: BCB Focus Survey (ExpectativasMercadoInflacao12Meses)
                                            """,
                                            mathjax=True,
                                            style={"fontSize": "0.95rem"}
                                        )
                                    ]
                                ),
                                html.Div(
                                    children=[
                                        html.H4("SELIC Rate Expectations", style={"color": COLORS["teal"], "marginBottom": "1rem"}),
                                        dcc.Markdown(
                                            r"""
                                            **Median 1Y**: Median SELIC rate forecast for the Copom meeting ~1-year ahead.
                                            
                                            **Std Dev 1Y**: Cross-sectional standard deviation measuring uncertainty
                                            about the future policy rate path.
                                            
                                            Source: BCB Focus Survey (ExpectativasMercadoSelic) mapped to Copom calendar.
                                            """,
                                            mathjax=True,
                                            style={"fontSize": "0.95rem"}
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                )
            ]
        ),
        # --- PCA Analysis Section (Full Sample) ---
        html.Section(
            className="accent-section",
            style={"padding": "4rem 5%", "backgroundColor": COLORS["white"]},
            children=[
                html.H2("PCA Analysis (Full Sample)", style={"textAlign": "center", "marginBottom": "1rem"}),
                html.P(
                    "First Principal Component of IPCA and SELIC expectations (median and std dev) - Full Sample",
                    style={"textAlign": "center", "marginBottom": "2rem", "opacity": 0.7}
                ),
                html.Div(
                    className="chart-container",
                    style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)", "marginBottom": "2rem"},
                    children=[dcc.Graph(id="pca-chart", config={"displayModeBar": False}, figure=create_pca_chart())]
                ),
                # Description Section
                html.Div(
                    style={
                        "backgroundColor": COLORS["light_gray"],
                        "padding": "2rem",
                        "borderRadius": "8px",
                        "marginTop": "2rem"
                    },
                    children=[
                        html.H3("Principal Component Analysis", style={"textAlign": "center", "marginBottom": "1.5rem"}),
                        html.Div(
                            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "2rem"},
                            children=[
                                html.Div(
                                    children=[
                                        html.H4("Methodology", style={"color": COLORS["teal"], "marginBottom": "1rem"}),
                                        dcc.Markdown(
                                            r"""
                                            PCA is applied to 4 standardized series:
                                            - IPCA Median 12M
                                            - IPCA Std Dev 12M
                                            - SELIC Median 1Y
                                            - SELIC Std Dev 1Y
                                            
                                            PC1 captures the dominant co-movement pattern 
                                            in macro expectations since 2005 (when SELIC data begins).
                                            """,
                                            mathjax=True,
                                            style={"fontSize": "0.95rem"}
                                        )
                                    ]
                                ),
                                html.Div(
                                    children=[
                                        html.H4("Interpretation", style={"color": COLORS["teal"], "marginBottom": "1rem"}),
                                        dcc.Markdown(
                                            r"""
                                            PC1 typically represents a **"macro expectations factor"**:
                                            - Positive loadings on median forecasts (tightening expectations)
                                            - Positive loadings on std dev (higher uncertainty)
                                            
                                            High PC1 values indicate expectations of 
                                            tighter policy with greater uncertainty.
                                            """,
                                            mathjax=True,
                                            style={"fontSize": "0.95rem"}
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                )
            ]
        ),
        # --- Dynamic PCA Analysis Section ---
        html.Section(
            className="accent-section",
            style={"padding": "4rem 5%", "backgroundColor": COLORS["light_gray"]},
            children=[
                html.H2("Dynamic PCA Analysis", style={"textAlign": "center", "marginBottom": "1rem"}),
                html.P(
                    "First Principal Component computed over a user-selected date range",
                    style={"textAlign": "center", "marginBottom": "2rem", "opacity": 0.7}
                ),
                # Date range selector
                html.Div(
                    style={
                        "display": "flex",
                        "justifyContent": "center",
                        "alignItems": "center",
                        "gap": "1.5rem",
                        "marginBottom": "2rem",
                        "flexWrap": "wrap"
                    },
                    children=[
                        html.Div(
                            children=[
                                html.Label("Start Date:", style={"fontWeight": "bold", "display": "block", "marginBottom": "0.5rem"}),
                                dcc.DatePickerSingle(
                                    id="pca-start-date",
                                    display_format="YYYY-MM-DD",
                                    date="2005-01-03",  # Default to Jan 2005 (SELIC data start)
                                    min_date_allowed="2001-11-07",
                                    max_date_allowed="2026-02-27",
                                ),
                            ]
                        ),
                        html.Div(
                            children=[
                                html.Label("End Date:", style={"fontWeight": "bold", "display": "block", "marginBottom": "0.5rem"}),
                                dcc.DatePickerSingle(
                                    id="pca-end-date",
                                    display_format="YYYY-MM-DD",
                                    date="2011-12-31",  # Default end date as requested
                                    min_date_allowed="2001-11-07",
                                    max_date_allowed="2026-02-27",
                                ),
                            ]
                        ),
                        html.Button(
                            "Run Partial Sample PCA",
                            id="run-pca-button",
                            n_clicks=0,
                            style={
                                "backgroundColor": COLORS["teal"],
                                "color": "white",
                                "border": "none",
                                "padding": "0.75rem 1.5rem",
                                "borderRadius": "4px",
                                "cursor": "pointer",
                                "fontWeight": "bold",
                                "marginTop": "1.5rem"
                            }
                        ),
                    ]
                ),
                html.Div(
                    className="chart-container",
                    style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)", "marginBottom": "2rem"},
                    children=[dcc.Graph(id="dynamic-pca-chart", config={"displayModeBar": False})]
                ),
                # Dynamic PCA loadings display
                html.Div(
                    id="dynamic-pca-loadings",
                    style={
                        "backgroundColor": COLORS["white"],
                        "padding": "1.5rem",
                        "borderRadius": "8px",
                        "marginTop": "1rem"
                    },
                    children=[
                        html.P("Select a date range and click 'Run Partial Sample PCA' to see the results.", 
                               style={"textAlign": "center", "opacity": 0.6})
                    ]
                )
            ]
        )
    ]
)

# =====================================================================
# RISK MANAGEMENT CHART FUNCTIONS
# =====================================================================

# Tenor mapping: column name → business days to expiry (DAP)
TENOR_MAP = {
    "predi_21": 21, "predi_63": 63, "predi_126": 126, "predi_252": 252,
    "predi_378": 378, "predi_504": 504, "predi_630": 630, "predi_756": 756,
    "predi_882": 882, "predi_1008": 1008, "predi_1260": 1260, "predi_1512": 1512,
    "predi_1764": 1764, "predi_2016": 2016, "predi_2268": 2268, "predi_2520": 2520,
}
# Friendly year labels for each tenor
TENOR_LABELS = {
    "predi_21": "1M", "predi_63": "3M", "predi_126": "6M", "predi_252": "1Y",
    "predi_378": "1.5Y", "predi_504": "2Y", "predi_630": "2.5Y", "predi_756": "3Y",
    "predi_882": "3.5Y", "predi_1008": "4Y", "predi_1260": "5Y", "predi_1512": "6Y",
    "predi_1764": "7Y", "predi_2016": "8Y", "predi_2268": "9Y", "predi_2520": "10Y",
}
PREDI_COLS = list(TENOR_MAP.keys())


def create_swap_curve_pca_chart():
    """
    PCA on **daily yield changes** of the full DI swap curve.
    Returns a 2×2 subplot:
      1. PC scores (PC1, PC2, PC3) time series
      2. Factor loadings bar chart (one group per PC)
      3. Scree plot (explained variance)
      4. Rolling PC2 (slope factor) 63-day window
    """
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    df_predi, _ = load_market_data()
    if df_predi.empty:
        return go.Figure()

    # Use only predi columns (not forward rates)
    cols = [c for c in PREDI_COLS if c in df_predi.columns]
    if len(cols) < 5:
        return go.Figure()

    df = df_predi[["date"] + cols].dropna().sort_values("date").reset_index(drop=True)

    # Daily yield CHANGES (first differences)
    df_changes = df[cols].diff().iloc[1:].reset_index(drop=True)
    dates = df["date"].iloc[1:].reset_index(drop=True)

    # Drop rows with any NaN
    mask = df_changes.notna().all(axis=1)
    df_changes = df_changes[mask].reset_index(drop=True)
    dates = dates[mask].reset_index(drop=True)

    if len(df_changes) < 60:
        return go.Figure()

    # Standardize
    scaler = StandardScaler()
    X = scaler.fit_transform(df_changes)

    # PCA — extract all components to build scree plot
    n_comps = min(len(cols), len(df_changes))
    pca = PCA(n_components=n_comps)
    scores = pca.fit_transform(X)

    explained = pca.explained_variance_ratio_ * 100
    loadings = pca.components_  # shape (n_comps, n_features)

    labels = [TENOR_LABELS.get(c, c) for c in cols]

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            f"Principal Component Scores",
            "Factor Loadings (PC1, PC2, PC3)",
            "Scree Plot — Explained Variance",
            "Rolling PC2 (Slope Factor) — 63-day window",
        ),
        vertical_spacing=0.14,
        horizontal_spacing=0.10,
    )

    # --- 1. PC score time series ---
    pc_names = ["PC1 (Level)", "PC2 (Slope)", "PC3 (Curvature)"]
    pc_colors = [COLORS["teal"], COLORS["gold"], COLORS["red"]]
    for i in range(3):
        fig.add_trace(go.Scatter(
            x=dates, y=scores[:, i],
            mode="lines", name=pc_names[i],
            line=dict(color=pc_colors[i], width=2 if i == 0 else 1.5),
            legendgroup="scores",
        ), row=1, col=1)

    # --- 2. Loadings bar chart ---
    bar_colors = [COLORS["teal"], COLORS["gold"], COLORS["red"]]
    for i in range(3):
        fig.add_trace(go.Bar(
            x=labels, y=loadings[i],
            name=f"PC{i+1}",
            marker_color=bar_colors[i],
            opacity=0.8,
            legendgroup="loadings",
            showlegend=True if i == 0 else False,  # Reduce legend clutter
        ), row=1, col=2)

    # --- 3. Scree plot ---
    fig.add_trace(go.Bar(
        x=[f"PC{i+1}" for i in range(min(8, len(explained)))],
        y=explained[:8],
        marker_color=COLORS["teal"],
        showlegend=False,
    ), row=2, col=1)
    # Cumulative line
    cum_var = np.cumsum(explained[:8])
    fig.add_trace(go.Scatter(
        x=[f"PC{i+1}" for i in range(min(8, len(explained)))],
        y=cum_var,
        mode="lines+markers", name="Cumulative %",
        line=dict(color=COLORS["dark"], width=2, dash="dash"),
        marker=dict(size=6),
        showlegend=False,
        yaxis="y5",  # secondary y
    ), row=2, col=1)

    # --- 4. Rolling PC2 (slope) 63-day window ---
    window = 63
    if len(df_changes) > window:
        rolling_pc2 = pd.Series(scores[:, 1]).rolling(window).mean()
        fig.add_trace(go.Scatter(
            x=dates, y=rolling_pc2,
            mode="lines", name="Rolling PC2 (63d avg)",
            line=dict(color=COLORS["gold"], width=2),
            fill="tozeroy", fillcolor="rgba(180,166,128,0.1)",
            showlegend=False,
        ), row=2, col=2)
        fig.add_hline(y=0, line_dash="dot", line_color=COLORS["gray"], row=2, col=2)

    # Annotations for explained variance
    fig.add_annotation(
        x=0.02, y=1.05, xref="paper", yref="paper",
        text=f"<b>Variance explained:</b><br>PC1: {explained[0]:.1f}%  |  PC2: {explained[1]:.1f}%  |  PC3: {explained[2]:.1f}%",
        showarrow=False, font=dict(size=10), bgcolor="rgba(255,255,255,0.85)",
        bordercolor=COLORS["gray"], borderwidth=1, borderpad=4, align="left",
    )

    fig.update_layout(
        height=800,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif", font_color=COLORS["dark"],
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        barmode="group",
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["gray"])
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"])
    fig.update_yaxes(title_text="Score", row=1, col=1)
    fig.update_yaxes(title_text="Loading", row=1, col=2)
    fig.update_yaxes(title_text="Variance (%)", row=2, col=1)
    fig.update_yaxes(title_text="PC2 (avg)", row=2, col=2)

    return fig


def create_dv01_krd_chart():
    """
    DV01 profile across DI futures tenors using the DI formula:
        DV01 = Notional × 0.0001 × (DAP / 252)
    Shows:
      1. Bar chart of DV01 per tenor (latest date)
      2. DV01-neutral hedge ratio time series for a 2s10s steepener
    """
    df_predi, _ = load_market_data()
    if df_predi.empty:
        return go.Figure()

    cols = [c for c in PREDI_COLS if c in df_predi.columns]
    if len(cols) < 5:
        return go.Figure()

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=(
            "DV01 per R$100k Notional (Latest Snapshot)",
            "DV01-Neutral Hedge Ratio: Front / Back Leg (1Y vs 5Y)"
        ),
        horizontal_spacing=0.12,
    )

    notional = 100_000  # R$100,000 standard contract

    # Latest snapshot DV01 bar
    labels = [TENOR_LABELS.get(c, c) for c in cols]
    daps = [TENOR_MAP[c] for c in cols]
    dv01s = [notional * 0.0001 * (dap / 252) for dap in daps]

    fig.add_trace(go.Bar(
        x=labels, y=dv01s,
        marker_color=[COLORS["teal"] if d <= 504 else COLORS["gold"] if d <= 1260 else COLORS["red"] for d in daps],
        showlegend=False,
        hovertemplate="Tenor: %{x}<br>DV01: R$%{y:.2f}<extra></extra>",
    ), row=1, col=1)

    # DV01-neutral hedge ratio time series: front_dv01/back_dv01
    # Front = predi_252 (1Y, DAP=252), Back = predi_1260 (5Y, DAP=1260)
    front_col, back_col = "predi_252", "predi_1260"
    if front_col in df_predi.columns and back_col in df_predi.columns:
        front_dap, back_dap = TENOR_MAP[front_col], TENOR_MAP[back_col]
        front_dv01 = notional * 0.0001 * (front_dap / 252)
        back_dv01 = notional * 0.0001 * (back_dap / 252)
        # Static DV01 ratio (doesn't change for DI futures since DAP is fixed per contract)
        hedge_ratio = back_dv01 / front_dv01

        # However, as DAP decreases for a position, show the time-varying concept
        # For simplicity, show the ratio as a constant reference + how many front contracts per 1 back
        fig.add_trace(go.Scatter(
            x=df_predi["date"],
            y=[hedge_ratio] * len(df_predi),
            mode="lines", name=f"Hedge Ratio = {hedge_ratio:.2f}x",
            line=dict(color=COLORS["teal"], width=2),
            showlegend=True,
        ), row=1, col=2)

        # Add annotation explaining
        fig.add_annotation(
            x=0.98, y=0.95, xref="x2 domain", yref="y2 domain",
            text=f"<b>{hedge_ratio:.1f}× front per 1 back</b><br>"
                 f"Front DV01 (1Y): R${front_dv01:.2f}<br>Back DV01 (5Y): R${back_dv01:.2f}",
            showarrow=False, font=dict(size=10), bgcolor="rgba(255,255,255,0.9)",
            bordercolor=COLORS["gray"], borderwidth=1, borderpad=4, align="right",
            xanchor="right",
        )

    fig.update_layout(
        height=450,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif", font_color=COLORS["dark"],
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["gray"])
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="DV01 (R$)", row=1, col=1)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="Ratio (×)", row=1, col=2)

    return fig


def create_var_es_chart():
    """
    Historical Simulation VaR (99%, 1-day) and Expected Shortfall
    on the steepening spread (fwd_3y1y − fwd_1y1y), with regime-conditional breakdown.
    Returns 2 subplots:
      1. Histogram of daily spread changes with VaR/ES markers
      2. Rolling 252-day VaR & ES time series + regime-conditional VaR
    """
    df_predi, df_fra = load_market_data()
    if df_fra.empty:
        return go.Figure()

    df = df_fra.dropna(subset=["1y1y", "3y3y"]).sort_values("date").reset_index(drop=True)
    spread = df["3y3y"] - df["1y1y"]
    spread_changes = spread.diff().dropna() * 10000  # in bps
    dates = df["date"].iloc[1:].reset_index(drop=True)
    spread_changes = spread_changes.reset_index(drop=True)

    if len(spread_changes) < 252:
        return go.Figure()

    # Full-sample VaR & ES
    sorted_changes = np.sort(spread_changes.values)
    var_99 = np.percentile(sorted_changes, 1)  # 1st percentile (loss tail)
    tail = sorted_changes[sorted_changes <= var_99]
    es_99 = tail.mean() if len(tail) > 0 else var_99

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=(
            "Daily Spread Change Distribution (bps)",
            "Rolling 252-day VaR & ES (99%)"
        ),
        horizontal_spacing=0.10,
    )

    # --- 1. Histogram ---
    fig.add_trace(go.Histogram(
        x=spread_changes, nbinsx=80,
        marker_color=COLORS["teal"], opacity=0.7,
        showlegend=False,
        hovertemplate="Change: %{x:.1f} bps<br>Count: %{y}<extra></extra>",
    ), row=1, col=1)

    # VaR & ES lines
    fig.add_vline(x=var_99, line_dash="dash", line_color=COLORS["red"], line_width=2, row=1, col=1,
                  annotation_text=f"VaR 99%: {var_99:.1f} bps", annotation_position="top left",
                  annotation_font_color=COLORS["red"])
    fig.add_vline(x=es_99, line_dash="solid", line_color=COLORS["dark"], line_width=2, row=1, col=1,
                  annotation_text=f"ES 99%: {es_99:.1f} bps", annotation_position="top left",
                  annotation_font_color=COLORS["dark"])

    # --- 2. Rolling VaR & ES ---
    window = 252
    rolling_var = spread_changes.rolling(window).apply(lambda x: np.percentile(x, 1), raw=True)
    rolling_es = spread_changes.rolling(window).apply(
        lambda x: x[x <= np.percentile(x, 1)].mean() if len(x[x <= np.percentile(x, 1)]) > 0 else np.percentile(x, 1),
        raw=True,
    )

    fig.add_trace(go.Scatter(
        x=dates, y=rolling_var,
        mode="lines", name="VaR 99% (1d)",
        line=dict(color=COLORS["red"], width=2),
    ), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=dates, y=rolling_es,
        mode="lines", name="ES 99% (1d)",
        line=dict(color=COLORS["dark"], width=2, dash="dash"),
        fill="tonexty", fillcolor="rgba(231,76,60,0.08)",
    ), row=1, col=2)

    # Regime-conditional VaR overlay using strategy data
    df_pnl_v5, _ = load_data("v5")
    if not df_pnl_v5.empty and "regime" in df_pnl_v5.columns:
        # Merge regime info
        df_regime = df_pnl_v5[["date", "regime"]].copy()
        df_regime["date"] = pd.to_datetime(df_regime["date"])
        merged = pd.DataFrame({"date": dates, "change": spread_changes.values})
        merged = merged.merge(df_regime, on="date", how="left")
        merged["regime"] = merged["regime"].fillna("unknown")

        regime_vars = {}
        for regime in ["high_uncertainty", "medium_uncertainty", "low_uncertainty"]:
            regime_data = merged[merged["regime"] == regime]["change"]
            if len(regime_data) > 10:
                regime_vars[regime] = np.percentile(regime_data.values, 1)

        # Add regime VaR annotation
        if regime_vars:
            regime_text = "<b>Regime-Conditional VaR (99%):</b><br>"
            regime_map = {"high_uncertainty": "High Unc.", "medium_uncertainty": "Med Unc.", "low_uncertainty": "Low Unc."}
            for reg, val in regime_vars.items():
                regime_text += f"{regime_map.get(reg, reg)}: {val:.1f} bps<br>"
            fig.add_annotation(
                x=0.98, y=0.98, xref="x2 domain", yref="y2 domain",
                text=regime_text, showarrow=False, font=dict(size=10),
                bgcolor="rgba(255,255,255,0.9)", bordercolor=COLORS["gray"],
                borderwidth=1, borderpad=4, align="left", xanchor="right", yanchor="top",
            )

    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["gray"], row=1, col=2)

    fig.update_layout(
        height=450,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif", font_color=COLORS["dark"],
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["gray"])
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="Count", row=1, col=1)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="bps", row=1, col=2)

    return fig


def create_carry_rolldown_chart():
    """
    Carry = Forward Rate − Spot Rate (per tenor bucket, annualised).
    Roll-down = yield pickup from tenor shortening by ~1Y.
    Includes breakeven: how much curve flattening wipes out carry.
    Returns 2 subplots:
      1. Bar chart across tenors (latest date): carry, roll-down, total, breakeven
      2. Time series of steepener carry + roll-down
    """
    df_predi, df_fra = load_market_data()
    if df_predi.empty or df_fra.empty:
        return go.Figure()

    cols = [c for c in PREDI_COLS if c in df_predi.columns]
    if len(cols) < 5:
        return go.Figure()

    # Latest row
    latest = df_predi.iloc[-1]

    # Forward curve columns (if available)
    fwd_cols = [c for c in ["fwd_1y1y", "fwd_2y1y", "fwd_3y1y", "fwd_5y5y"] if c in df_predi.columns]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=(
            "Carry & Roll-Down by Tenor (Latest)",
            "Steepener Carry + Roll-Down (annualised bps)"
        ),
        horizontal_spacing=0.12,
    )

    # --- 1. Bar chart per tenor ---
    # Carry ≈ forward_rate(t, t+1y) − spot_rate(t) for each tenor
    # Roll-down ≈ spot_rate(tenor) - spot_rate(tenor - 252d)
    # Use adjacent tenors as proxy for roll-down
    tenor_labels = []
    carry_vals = []
    rolldown_vals = []
    total_vals = []

    for i in range(1, len(cols)):
        prev_col = cols[i - 1]
        curr_col = cols[i]
        prev_dap = TENOR_MAP[prev_col]
        curr_dap = TENOR_MAP[curr_col]

        label = TENOR_LABELS.get(curr_col, curr_col)
        spot = latest[curr_col]
        spot_shorter = latest[prev_col]

        # Carry = implied forward (longer) - spot (shorter) — annualised
        carry = (spot - spot_shorter) * 10000  # bps

        # Roll-down = yield pickup from moving down the curve
        rolldown = (spot - spot_shorter) * 10000 * (252 / (curr_dap - prev_dap)) if curr_dap != prev_dap else 0

        tenor_labels.append(label)
        carry_vals.append(carry)
        rolldown_vals.append(rolldown)
        total_vals.append(carry + rolldown)

    fig.add_trace(go.Bar(
        x=tenor_labels, y=carry_vals, name="Carry", marker_color=COLORS["teal"], opacity=0.8,
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=tenor_labels, y=rolldown_vals, name="Roll-Down", marker_color=COLORS["gold"], opacity=0.8,
    ), row=1, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["gray"], row=1, col=1)

    # --- 2. Steepener carry + roll-down time series ---
    # For the 1y1y vs 3y3y steepener: net carry = carry on short leg − carry on long leg
    if not df_fra.empty and "1y1y" in df_fra.columns and "3y3y" in df_fra.columns:
        # Carry of the steepener ≈ fwd spread - spot spread (annualised)
        if "fwd_1y1y" in df_predi.columns and "fwd_3y1y" in df_predi.columns:
            merged = pd.merge(
                df_fra[["date", "1y1y", "3y3y"]],
                df_predi[["date", "fwd_1y1y", "fwd_3y1y"]],
                on="date", how="inner"
            )
            spot_spread = merged["3y3y"] - merged["1y1y"]
            fwd_spread = merged["fwd_3y1y"] - merged["fwd_1y1y"]
            carry_ts = (fwd_spread - spot_spread) * 10000  # bps annualised
            breakeven = spot_spread.diff() * 10000  # daily move that wipes carry

            fig.add_trace(go.Scatter(
                x=merged["date"], y=carry_ts,
                mode="lines", name="Net Carry (bps)",
                line=dict(color=COLORS["teal"], width=2),
                fill="tozeroy", fillcolor="rgba(0,172,172,0.08)",
            ), row=1, col=2)

            # Breakeven: rolling 21-day avg daily carry vs realised spread change
            rolling_carry_daily = carry_ts / 252
            rolling_avg = rolling_carry_daily.rolling(21).mean()
            fig.add_trace(go.Scatter(
                x=merged["date"], y=rolling_avg,
                mode="lines", name="Breakeven (21d avg daily carry)",
                line=dict(color=COLORS["red"], width=1.5, dash="dash"),
            ), row=1, col=2)

            fig.add_hline(y=0, line_dash="dot", line_color=COLORS["gray"], row=1, col=2)

    fig.update_layout(
        height=450,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif", font_color=COLORS["dark"],
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        barmode="group",
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["gray"])
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="bps", row=1, col=1)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="bps", row=1, col=2)

    return fig


def create_rolling_correlation_chart():
    """
    Rolling correlation between front and back legs of the steepener.
    Correlation breakdown indicator: alert when 30-day rolling correlation
    drops below historical norms (−1σ from the mean).
    """
    _, df_fra = load_market_data()
    if df_fra.empty or "1y1y" not in df_fra.columns or "3y3y" not in df_fra.columns:
        return go.Figure()

    df = df_fra.dropna(subset=["1y1y", "3y3y"]).sort_values("date").reset_index(drop=True)

    # Daily changes
    d1y1y = df["1y1y"].diff()
    d3y3y = df["3y3y"].diff()
    dates = df["date"]

    # Rolling correlations
    corr_30d = d1y1y.rolling(30).corr(d3y3y)
    corr_63d = d1y1y.rolling(63).corr(d3y3y)
    corr_252d = d1y1y.rolling(252).corr(d3y3y)

    # Breakdown threshold: mean − 1.5σ of 252-day corr
    mean_corr = corr_252d.mean()
    std_corr = corr_252d.std()
    breakdown_threshold = mean_corr - 1.5 * std_corr

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates, y=corr_30d, mode="lines", name="30-day corr",
        line=dict(color=COLORS["red"], width=1.5),
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=corr_63d, mode="lines", name="63-day corr",
        line=dict(color=COLORS["gold"], width=2),
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=corr_252d, mode="lines", name="252-day corr",
        line=dict(color=COLORS["teal"], width=2.5),
    ))

    # Breakdown threshold
    fig.add_hline(
        y=breakdown_threshold, line_dash="dash", line_color="#e74c3c", line_width=1.5,
        annotation_text=f"⚠ Breakdown ({breakdown_threshold:.2f})",
        annotation_position="bottom right",
        annotation_font_color="#e74c3c",
    )

    # Shade breakdown events (30d corr below threshold)
    breakdown_mask = corr_30d < breakdown_threshold
    if breakdown_mask.any():
        # Find contiguous breakdown periods
        breakdown_dates = dates[breakdown_mask]
        fig.add_trace(go.Scatter(
            x=breakdown_dates, y=corr_30d[breakdown_mask],
            mode="markers", name="Breakdown Events",
            marker=dict(color="#e74c3c", size=4, symbol="x"),
        ))

    fig.update_layout(
        height=400,
        title="Rolling Correlation: FRA 1y1y vs 3y3y (Daily Changes)",
        title_font_size=16,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif", font_color=COLORS["dark"],
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=True, gridcolor=COLORS["gray"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], title="Correlation", range=[-0.5, 1.1]),
    )

    return fig


def create_yield_curve_surface_chart():
    """
    3D surface plot of the DI swap curve: x=date, y=tenor (DAP), z=yield.
    Downsampled to weekly for performance.
    """
    df_predi, _ = load_market_data()
    if df_predi.empty:
        return go.Figure()

    cols = [c for c in PREDI_COLS if c in df_predi.columns]
    if len(cols) < 5:
        return go.Figure()

    df = df_predi[["date"] + cols].dropna().sort_values("date")

    # Downsample to weekly (last obs per week) for performance
    df["week"] = df["date"].dt.isocalendar().week.astype(int) + df["date"].dt.year * 100
    df_weekly = df.groupby("week").last().reset_index(drop=True)

    if len(df_weekly) < 10:
        return go.Figure()

    z_data = df_weekly[cols].values * 100  # convert to %
    x_dates = df_weekly["date"].values
    y_tenors = [TENOR_MAP[c] / 252 for c in cols]  # in years

    fig = go.Figure(data=[go.Surface(
        x=x_dates,
        y=y_tenors,
        z=z_data.T,
        colorscale=[[0, COLORS["teal"]], [0.5, COLORS["gold"]], [1, COLORS["red"]]],
        colorbar=dict(title="Yield (%)", len=0.6),
        hovertemplate="Date: %{x}<br>Tenor: %{y:.1f}Y<br>Yield: %{z:.2f}%<extra></extra>",
    )])

    fig.update_layout(
        height=800,
        title="DI Swap Curve Surface (Weekly)",
        title_font_size=16,
        font_family="Unica77LLSub, Verdana, sans-serif", font_color=COLORS["dark"],
        margin=dict(t=80, b=40, l=40, r=40),
        scene=dict(
            xaxis_title="Date",
            yaxis_title="Tenor (Years)",
            zaxis_title="Yield (%)",
            xaxis=dict(backgroundcolor="rgba(0,0,0,0)"),
            yaxis=dict(backgroundcolor="rgba(0,0,0,0)"),
            zaxis=dict(backgroundcolor="rgba(0,0,0,0)"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig


# =====================================================================
# PORTFOLIO-AWARE RISK MANAGEMENT CHART FUNCTIONS
# =====================================================================

def _normalize_position_size(position_col):
    """Convert position_size to numeric, handling categorical values."""
    if pd.api.types.is_numeric_dtype(position_col):
        return position_col.astype(float)
    else:
        # For categorical position data (e.g., Version 1)
        return np.where(
            position_col.str.contains("steepener", case=False, na=False), 1.0,
            np.where(position_col.str.contains("flattener", case=False, na=False), -1.0, 0.0)
        )


def create_portfolio_dv01_chart(df_pnl):
    """
    Portfolio-scaled DV01 exposure based on actual position sizes.
    Shows:
      1. Current position DV01 exposure (1y1y and 3y3y legs)
      2. Historical DV01 exposure over time
    """
    if df_pnl.empty or "position_size" not in df_pnl.columns:
        return create_dv01_krd_chart()  # Fallback to market-level
    
    # DV01 per unit position (using DI futures formula)
    # 1y1y leg: ~252 business days
    # 3y3y leg: ~756 business days
    front_dap, back_dap = 252, 756
    base_notional = 100_000  # R$100k per unit position
    
    # DV01 per unit position for each leg
    front_dv01_per_unit = base_notional * 0.0001 * (front_dap / 252)  # = R$10
    back_dv01_per_unit = base_notional * 0.0001 * (back_dap / 252)   # = R$30
    
    # Calculate portfolio DV01 based on position sizes
    # Position > 0: steepener (long back, short front)
    # Position < 0: flattener (short back, long front)
    df = df_pnl.copy()
    
    # Ensure position_size is numeric
    pos_numeric = _normalize_position_size(df["position_size"])
    
    df["front_dv01"] = -pos_numeric * front_dv01_per_unit  # opposite sign
    df["back_dv01"] = pos_numeric * back_dv01_per_unit    # same sign
    df["net_dv01"] = df["front_dv01"] + df["back_dv01"]
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            "Portfolio DV01 Exposure Over Time",
            "Current DV01 Breakdown by Leg"
        ),
        vertical_spacing=0.20,
    )
    
    # Historical DV01 exposure
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["front_dv01"],
        mode="lines", name="Front Leg (1y1y) DV01",
        line=dict(color=COLORS["gold"], width=1.5),
        stackgroup=None,
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["back_dv01"],
        mode="lines", name="Back Leg (3y3y) DV01",
        line=dict(color=COLORS["teal"], width=1.5),
        stackgroup=None,
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["net_dv01"],
        mode="lines", name="Net Portfolio DV01",
        line=dict(color=COLORS["dark"], width=2.5, dash="solid"),
        fill="tozeroy", fillcolor="rgba(40,40,40,0.05)",
    ), row=1, col=1)
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["gray"], row=1, col=1)
    
    # Current position breakdown (pie/bar)
    latest = df.iloc[-1]
    current_pos = latest["position_size"] if pd.notna(latest["position_size"]) else 0
    
    # Bar chart of current DV01
    dv01_components = ["Front Leg\n(Short)", "Back Leg\n(Long)"]
    dv01_values = [latest["front_dv01"], latest["back_dv01"]]
    bar_colors = [COLORS["gold"], COLORS["teal"]]
    
    fig.add_trace(go.Bar(
        x=dv01_components, y=dv01_values,
        marker_color=bar_colors,
        showlegend=False,
        text=[f"R${v:,.0f}" for v in dv01_values],
        textposition="outside",
    ), row=2, col=1)
    
    # Add net DV01 annotation
    net_dv01 = latest["net_dv01"]
    position_type = latest.get("position_type", "neutral")
    
    fig.add_annotation(
        x=0.98, y=1.05, xref="paper", yref="paper",
        text=f"<b>Current Position:</b> {position_type}<br>"
             f"<b>Net DV01:</b> R${net_dv01:,.0f}<br>"
             f"<b>Position Size:</b> {current_pos:+.2%}" if isinstance(current_pos, (int, float)) else str(current_pos),
        showarrow=False, font=dict(size=11), bgcolor="rgba(255,255,255,0.95)",
        bordercolor=COLORS["teal"], borderwidth=2, borderpad=8, align="left",
        xanchor="right", yanchor="bottom",
    )
    
    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["gray"], row=2, col=1)
    
    fig.update_layout(
        height=650,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif", font_color=COLORS["dark"],
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["gray"])
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="DV01 (R$)", row=1, col=1)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="DV01 (R$)", row=2, col=1)
    
    return fig


def create_portfolio_var_es_chart(df_pnl):
    """
    Position-weighted VaR and ES based on actual portfolio exposure.
    Scales market VaR by the position size to show actual portfolio risk.
    """
    # Get market-level VaR first
    df_predi, df_fra = load_market_data()
    if df_fra.empty or df_pnl.empty:
        return create_var_es_chart()  # Fallback
    
    # Calculate market spread changes
    df_market = df_fra.dropna(subset=["1y1y", "3y3y"]).sort_values("date").reset_index(drop=True)
    spread = df_market["3y3y"] - df_market["1y1y"]
    spread_changes = spread.diff().dropna() * 10000  # in bps
    dates_market = df_market["date"].iloc[1:].reset_index(drop=True)
    
    if len(spread_changes) < 252:
        return create_var_es_chart()
    
    # Market VaR (per unit position)
    sorted_changes = np.sort(spread_changes.values)
    var_99_market = np.percentile(sorted_changes, 1)
    tail = sorted_changes[sorted_changes <= var_99_market]
    es_99_market = tail.mean() if len(tail) > 0 else var_99_market
    
    # Merge with portfolio data to get position sizes
    df_pnl_clean = df_pnl.copy()
    df_pnl_clean["date"] = pd.to_datetime(df_pnl_clean["date"]).dt.normalize()
    
    # Select columns (regime may not exist in all versions)
    cols = ["date", "position_size"]
    if "regime" in df_pnl_clean.columns:
        cols.append("regime")
    
    # Calculate position-weighted VaR over time
    df_risk = df_pnl_clean[cols].copy()
    
    # Add regime if missing
    if "regime" not in df_risk.columns:
        df_risk["regime"] = "unknown"
    
    # Ensure position_size is numeric
    pos_numeric = _normalize_position_size(df_risk["position_size"])
    df_risk["position_size"] = pos_numeric
    
    # Calculate rolling 63-day position-weighted VaR
    # Position-weighted VaR = Position Size * Market VaR * Position Volatility Factor
    df_risk["abs_position"] = df_risk["position_size"].abs()
    df_risk["weighted_var_99"] = df_risk["abs_position"] * abs(var_99_market)
    df_risk["weighted_es_99"] = df_risk["abs_position"] * abs(es_99_market)
    
    # Calculate 21-day rolling average position for smoother VaR
    df_risk["position_rolling"] = df_risk["abs_position"].rolling(21, min_periods=1).mean()
    df_risk["portfolio_var"] = -df_risk["position_rolling"] * var_99_market  # Negative for loss
    df_risk["portfolio_es"] = -df_risk["position_rolling"] * es_99_market
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Position-Weighted VaR Over Time (bps)",
            "Position-Weighted ES Over Time (bps)",
            "Daily Spread Change Distribution",
            "Regime-Conditional VaR (bps)"
        ),
        vertical_spacing=0.20,
        horizontal_spacing=0.10,
    )
    
    # Row 1: Position-weighted VaR
    fig.add_trace(go.Scatter(
        x=df_risk["date"], y=df_risk["portfolio_var"],
        mode="lines", name="Portfolio VaR 99%",
        line=dict(color=COLORS["red"], width=2),
        fill="tozeroy", fillcolor="rgba(231,76,60,0.1)",
    ), row=1, col=1)
    
    # Add position size as secondary indicator
    fig.add_trace(go.Scatter(
        x=df_risk["date"], y=df_risk["abs_position"],
        mode="lines", name="|Position Size|",
        line=dict(color=COLORS["gray"], width=1, dash="dot"),
        yaxis="y2",
        showlegend=True,
    ), row=1, col=1)
    
    # Row 1 Col 2: Position-weighted ES
    fig.add_trace(go.Scatter(
        x=df_risk["date"], y=df_risk["portfolio_es"],
        mode="lines", name="Portfolio ES 99%",
        line=dict(color=COLORS["dark"], width=2),
        fill="tozeroy", fillcolor="rgba(40,40,40,0.08)",
    ), row=1, col=2)
    
    # Row 2 Col 1: Histogram (market-level, unchanged)
    fig.add_trace(go.Histogram(
        x=spread_changes, nbinsx=60,
        marker_color=COLORS["teal"], opacity=0.6,
        showlegend=False,
        name="Spread Changes",
    ), row=2, col=1)
    
    fig.add_vline(x=var_99_market, line_dash="dash", line_color=COLORS["red"], line_width=2, 
                  row=2, col=1)
    fig.add_vline(x=es_99_market, line_dash="solid", line_color=COLORS["dark"], line_width=2,
                  row=2, col=1)
    
    # Row 2 Col 2: Regime-conditional VaR
    if "regime" in df_risk.columns:
        regime_var = df_risk.groupby("regime").agg(
            avg_position=("abs_position", "mean"),
            max_position=("abs_position", "max"),
            days=("date", "count"),
        ).reset_index()
        
        regime_var["var_at_avg"] = -regime_var["avg_position"] * var_99_market
        regime_var["var_at_max"] = -regime_var["max_position"] * var_99_market
        
        regime_colors = {
            "high_uncertainty": COLORS["red"],
            "medium_uncertainty": COLORS["gold"],
            "low_uncertainty": COLORS["teal"],
        }
        
        for _, row in regime_var.iterrows():
            color = regime_colors.get(row["regime"], COLORS["gray"])
            fig.add_trace(go.Bar(
                x=[row["regime"].replace("_", " ").title()],
                y=[abs(row["var_at_avg"])],
                name=f"{row['regime'][:3]} VaR",
                marker_color=color,
                text=[f"{abs(row['var_at_avg']):.1f}"],
                textposition="outside",
                showlegend=False,
            ), row=2, col=2)
    
    # Current position summary
    latest = df_risk.iloc[-1]
    current_var = latest["portfolio_var"]
    current_es = latest["portfolio_es"]
    current_pos = latest["position_size"]
    
    fig.add_annotation(
        x=0.02, y=1.05, xref="paper", yref="paper",
        text=f"<b>Current Portfolio Risk:</b><br>"
             f"VaR 99% (1d): {current_var:.1f} bps<br>"
             f"ES 99% (1d): {current_es:.1f} bps<br>"
             f"Position: {current_pos:+.2%}" if isinstance(current_pos, (int, float)) else str(current_pos),
        showarrow=False, font=dict(size=10), bgcolor="rgba(255,255,255,0.95)",
        bordercolor=COLORS["red"], borderwidth=1, borderpad=6, align="left",
        xanchor="left", yanchor="bottom",
    )
    
    fig.update_layout(
        height=750,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif", font_color=COLORS["dark"],
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        barmode="group",
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["gray"])
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"])
    fig.update_yaxes(title_text="Portfolio VaR (bps)", row=1, col=1)
    fig.update_yaxes(title_text="|Position|", overlaying="y", side="right", showgrid=False, row=1, col=1)
    fig.update_yaxes(title_text="Portfolio ES (bps)", row=1, col=2)
    fig.update_yaxes(title_text="Count", row=2, col=1)
    fig.update_yaxes(title_text="VaR (bps)", row=2, col=2)
    
    return fig


def create_portfolio_carry_chart(df_pnl):
    """
    Portfolio-scaled carry and roll-down based on actual position sizes.
    Shows the actual carry being earned given the position.
    """
    if df_pnl.empty or "position_size" not in df_pnl.columns:
        return create_carry_rolldown_chart()  # Fallback
    
    # Get market carry data
    df_predi, df_fra = load_market_data()
    if df_predi.empty or df_fra.empty:
        return create_carry_rolldown_chart()
    
    # Merge portfolio data with FRA data
    df = df_pnl.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    
    df_fra_clean = df_fra.copy()
    df_fra_clean["date"] = pd.to_datetime(df_fra_clean["date"]).dt.normalize()
    
    df_merged = pd.merge(df, df_fra_clean[["date", "1y1y", "3y3y"]], on="date", how="left")
    
    if df_merged.empty:
        return create_carry_rolldown_chart()
    
    # Calculate steepening spread
    df_merged["spread"] = df_merged["3y3y"] - df_merged["1y1y"]
    
    # Ensure position_size is numeric
    pos_numeric = _normalize_position_size(df_merged["position_size"])
    df_merged["position_size"] = pos_numeric
    
    # Estimate carry: for a steepener, positive carry when spread is positive
    # This is a simplified model - actual carry depends on forward curve
    df_merged["market_carry_bps"] = df_merged["spread"] * 100  # Convert to bps
    
    # Position-scaled carry
    # If position > 0 (steepener), we earn carry when spread > 0
    # If position < 0 (flattener), we earn carry when spread < 0
    df_merged["position_carry_bps"] = df_merged["position_size"] * df_merged["market_carry_bps"]
    
    # Calculate rolling carry (21-day average)
    df_merged["carry_21d"] = df_merged["position_carry_bps"].rolling(21, min_periods=1).mean()
    
    # Cumulative carry earned
    df_merged["cumulative_carry"] = df_merged["position_carry_bps"].cumsum()
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Position-Scaled Carry Over Time (bps)",
            "Cumulative Carry Earned (bps)",
            "Carry vs Position Size",
            "Average Carry by Regime"
        ),
        vertical_spacing=0.22,
        horizontal_spacing=0.10,
    )
    
    # Row 1 Col 1: Daily position-scaled carry
    colors = [COLORS["teal"] if x > 0 else COLORS["red"] for x in df_merged["position_carry_bps"]]
    fig.add_trace(go.Bar(
        x=df_merged["date"], y=df_merged["position_carry_bps"],
        marker_color=colors, opacity=0.7,
        showlegend=False, name="Daily Carry",
    ), row=1, col=1)
    
    # Add 21-day moving average
    fig.add_trace(go.Scatter(
        x=df_merged["date"], y=df_merged["carry_21d"],
        mode="lines", name="21d Avg Carry",
        line=dict(color=COLORS["dark"], width=2),
    ), row=1, col=1)
    
    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["gray"], row=1, col=1)
    
    # Row 1 Col 2: Cumulative carry
    fig.add_trace(go.Scatter(
        x=df_merged["date"], y=df_merged["cumulative_carry"],
        mode="lines", name="Cumulative Carry",
        line=dict(color=COLORS["teal"], width=2.5),
        fill="tozeroy", fillcolor="rgba(0,172,172,0.1)",
    ), row=1, col=2)
    
    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["gray"], row=1, col=2)
    
    # Row 2 Col 1: Scatter of position size vs carry
    # Fix date colorbar ticks
    date_ticks = df_merged["date"].iloc[[0, len(df_merged)//2, -1]]
    fig.add_trace(go.Scatter(
        x=df_merged["position_size"], y=df_merged["market_carry_bps"],
        mode="markers", name="Carry vs Position",
        marker=dict(
            color=df_merged["date"].astype(np.int64),
            colorscale="Viridis",
            showscale=True,
            colorbar=dict(
                title="Date", 
                len=0.4, 
                y=0.2,
                tickmode="array",
                tickvals=[d.value for d in date_ticks],
                ticktext=[d.strftime("%Y-%m") for d in date_ticks]
            ),
            size=6,
            opacity=0.6,
        ),
    ), row=2, col=1)
    
    # Row 2 Col 2: Average carry by regime
    if "regime" in df_merged.columns:
        regime_carry = df_merged.groupby("regime").agg(
            avg_carry=("position_carry_bps", "mean"),
            total_carry=("position_carry_bps", "sum"),
            days=("date", "count"),
        ).reset_index()
        
        regime_colors = {
            "high_uncertainty": COLORS["red"],
            "medium_uncertainty": COLORS["gold"],
            "low_uncertainty": COLORS["teal"],
        }
        
        for _, row in regime_carry.iterrows():
            color = regime_colors.get(row["regime"], COLORS["gray"])
            fig.add_trace(go.Bar(
                x=[row["regime"].replace("_", " ").title()],
                y=[row["avg_carry"]],
                name=f"{row['regime'][:3]} Avg",
                marker_color=color,
                text=[f"{row['avg_carry']:.2f}"],
                textposition="outside",
                showlegend=False,
            ), row=2, col=2)
    
    # Summary annotation
    latest = df_merged.iloc[-1]
    total_carry = df_merged["position_carry_bps"].sum()
    avg_daily = df_merged["position_carry_bps"].mean()
    
    fig.add_annotation(
        x=0.98, y=0.45, xref="paper", yref="paper",
        text=f"<b>Carry Summary:</b><br>"
             f"Total: {total_carry:.1f} bps<br>"
             f"Daily Avg: {avg_daily:.2f} bps<br>"
             f"Current Pos: {latest['position_size']:+.2%}" if isinstance(latest['position_size'], (int, float)) else str(latest['position_size']),
        showarrow=False, font=dict(size=10), bgcolor="rgba(255,255,255,0.95)",
        bordercolor=COLORS["teal"], borderwidth=1, borderpad=6, align="right",
        xanchor="right",
    )
    
    fig.update_layout(
        height=750,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif", font_color=COLORS["dark"],
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        barmode="group",
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["gray"])
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"])
    fig.update_yaxes(title_text="Daily Carry (bps)", row=1, col=1)
    fig.update_yaxes(title_text="Cumulative (bps)", row=1, col=2)
    fig.update_yaxes(title_text="Market Carry (bps)", row=2, col=1)
    fig.update_yaxes(title_text="Position Size", row=2, col=1)
    fig.update_yaxes(title_text="Avg Carry (bps)", row=2, col=2)
    
    return fig


def create_portfolio_exposure_chart(df_pnl):
    """
    Shows portfolio exposure breakdown over time:
    - Position size by regime
    - Gross and net exposure
    - Leverage metrics
    """
    if df_pnl.empty or "position_size" not in df_pnl.columns:
        return go.Figure()
    
    df = df_pnl.copy()
    df["date"] = pd.to_datetime(df["date"])
    
    # Ensure position_size is numeric
    pos_numeric = _normalize_position_size(df["position_size"])
    df["position_size"] = pos_numeric
    
    # Calculate exposure metrics
    df["gross_exposure"] = df["position_size"].abs()
    df["net_exposure"] = df["position_size"]
    
    # Long/Short breakdown
    df["long_exposure"] = df["position_size"].clip(lower=0)  # Steepener positions
    df["short_exposure"] = (-df["position_size"]).clip(lower=0)  # Flattener positions
    
    # 21-day rolling averages
    df["gross_21d"] = df["gross_exposure"].rolling(21, min_periods=1).mean()
    df["net_21d"] = df["net_exposure"].rolling(21, min_periods=1).mean()
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            "Portfolio Exposure Over Time",
            "Exposure Distribution by Regime"
        ),
        vertical_spacing=0.20,
        specs=[[{"secondary_y": True}], [{}]],
    )
    
    # Row 1: Position size over time with regime background
    if "regime" in df.columns:
        regime_colors = {
            "high_uncertainty": "rgba(231,76,60,0.08)",
            "medium_uncertainty": "rgba(180,166,128,0.08)",
            "low_uncertainty": "rgba(0,172,172,0.08)",
        }
        
        # Add regime background shading
        prev_regime = None
        start_date = None
        for _, row in df.iterrows():
            r = row["regime"]
            if r != prev_regime and prev_regime is not None:
                fig.add_vrect(
                    x0=start_date, x1=row["date"],
                    fillcolor=regime_colors.get(prev_regime, "rgba(0,0,0,0)"),
                    layer="below", line_width=0,
                    row=1, col=1,
                )
                start_date = row["date"]
                prev_regime = r
            elif start_date is None:
                start_date = row["date"]
                prev_regime = r
        
        # Close last segment
        if prev_regime is not None and start_date is not None:
            fig.add_vrect(
                x0=start_date, x1=df["date"].iloc[-1],
                fillcolor=regime_colors.get(prev_regime, "rgba(0,0,0,0)"),
                layer="below", line_width=0,
                row=1, col=1,
            )
    
    # Position size area chart
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["position_size"],
        mode="lines", name="Net Position",
        line=dict(color=COLORS["dark"], width=2),
        fill="tozeroy",
        fillcolor="rgba(0,172,172,0.15)",
    ), row=1, col=1, secondary_y=False)
    
    # Add position size markers colored by position type
    steepener_mask = df["position_size"] > 0
    flattener_mask = df["position_size"] < 0
    
    if steepener_mask.any():
        fig.add_trace(go.Scatter(
            x=df.loc[steepener_mask, "date"], 
            y=df.loc[steepener_mask, "position_size"],
            mode="markers", name="Steepener",
            marker=dict(color=COLORS["teal"], size=4, opacity=0.5),
        ), row=1, col=1, secondary_y=False)
    
    if flattener_mask.any():
        fig.add_trace(go.Scatter(
            x=df.loc[flattener_mask, "date"], 
            y=df.loc[flattener_mask, "position_size"],
            mode="markers", name="Flattener",
            marker=dict(color=COLORS["red"], size=4, opacity=0.5),
        ), row=1, col=1, secondary_y=False)
    
    # Gross exposure on secondary axis
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["gross_21d"],
        mode="lines", name="Gross Exposure (21d avg)",
        line=dict(color=COLORS["gold"], width=2, dash="dash"),
    ), row=1, col=1, secondary_y=True)
    
    # Row 2: Exposure by regime
    if "regime" in df.columns:
        regime_exposure = df.groupby("regime").agg(
            avg_gross=("gross_exposure", "mean"),
            max_gross=("gross_exposure", "max"),
            avg_net=("net_exposure", "mean"),
            days=("date", "count"),
        ).reset_index()
        
        regime_colors = {
            "high_uncertainty": COLORS["red"],
            "medium_uncertainty": COLORS["gold"],
            "low_uncertainty": COLORS["teal"],
        }
        
        # Prepare data for bar chart
        regime_labels = []
        gross_values = []
        net_values = []
        bar_colors = []
        
        for _, row in regime_exposure.iterrows():
            regime_label = row["regime"].replace("_", " ").title()
            regime_labels.append(regime_label)
            gross_values.append(row["avg_gross"])
            net_values.append(abs(row["avg_net"]))
            bar_colors.append(regime_colors.get(row["regime"], COLORS["gray"]))
        
        # Add grouped bars - Gross exposure (lighter)
        fig.add_trace(go.Bar(
            x=regime_labels,
            y=gross_values,
            name="Avg Gross (|position|)",
            marker_color=bar_colors,
            opacity=0.5,
            width=0.35,
            offset=-0.2,
            hovertemplate="<b>%{x}</b><br>Avg Gross Exposure: %{y:.2%}<extra></extra>",
            legendgroup="exposure",
        ), row=2, col=1)
        
        # Add grouped bars - Net exposure (darker)
        fig.add_trace(go.Bar(
            x=regime_labels,
            y=net_values,
            name="Avg Net (directional)",
            marker_color=bar_colors,
            opacity=1.0,
            width=0.35,
            offset=0.2,
            hovertemplate="<b>%{x}</b><br>Avg Net Exposure: %{y:.2%}<extra></extra>",
            legendgroup="exposure",
        ), row=2, col=1)
    
    # Summary stats
    avg_gross = df["gross_exposure"].mean()
    max_gross = df["gross_exposure"].max()
    avg_position = df["position_size"].mean()
    current_pos = df["position_size"].iloc[-1]
    
    fig.add_annotation(
        x=0.02, y=1.05, xref="paper", yref="paper",
        text=f"<b>Exposure Metrics:</b><br>"
             f"Avg Gross: {avg_gross:.2%}<br>"
             f"Max Gross: {max_gross:.2%}<br>"
             f"Avg Position: {avg_position:+.2%}<br>"
             f"Current: {current_pos:+.2%}" if isinstance(current_pos, (int, float)) else str(current_pos),
        showarrow=False, font=dict(size=10), bgcolor="rgba(255,255,255,0.95)",
        bordercolor=COLORS["dark"], borderwidth=1, borderpad=6, align="left",
        xanchor="left", yanchor="bottom",
    )
    
    # Add annotation explaining the bars
    fig.add_annotation(
        x=0.5, y=-0.12, xref="paper", yref="paper",
        text="<b>Light bars</b> = Avg Gross Exposure (|position size|) &nbsp;|&nbsp; <b>Dark bars</b> = Avg Net Exposure (directional)",
        showarrow=False, font=dict(size=11), align="center",
        xanchor="center", yanchor="top",
    )
    
    fig.update_layout(
        height=750,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif", font_color=COLORS["dark"],
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        barmode="group",
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["gray"])
    fig.update_xaxes(type="category", row=2, col=1)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="Position Size", row=1, col=1)
    fig.update_yaxes(title_text="Gross Exposure", overlaying="y", side="right", showgrid=False, row=1, col=1, secondary_y=True)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["beige"], title_text="Avg Exposure", row=2, col=1)
    
    return fig


# --- Tab Content: Risk Management ---
risk_management_tab = html.Div(
    children=[
        html.Section(
            className="accent-section",
            style={"padding": "4rem 5%", "backgroundColor": COLORS["white"]},
            children=[
                html.H2("Risk Management", style={"textAlign": "center", "marginBottom": "0.5rem"}),
                html.Div(
                    id="risk-mgmt-version-label",
                    children="Portfolio-Aware Risk Analysis",
                    style={"textAlign": "center", "marginBottom": "0.5rem", "color": COLORS["teal"], "fontWeight": "bold"},
                ),
                html.P(
                    "Position-scaled risk metrics: DV01, VaR/ES, Carry, and Exposure based on actual strategy holdings",
                    style={"textAlign": "center", "marginBottom": "2rem", "opacity": 0.7}
                ),
                # Row 1: 3D Yield Curve Surface
                html.Div(
                    className="chart-container",
                    style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)", "marginBottom": "2rem"},
                    children=[dcc.Graph(id="risk-yield-surface", config={"displayModeBar": True})]
                ),
                # Row 2: PCA of the Swap Curve
                html.Div(
                    className="chart-container",
                    style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)", "marginBottom": "2rem"},
                    children=[dcc.Graph(id="risk-pca-chart", config={"displayModeBar": False})]
                ),
                # Row 3: DV01 / KRD + VaR/ES side by side
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "2rem", "marginBottom": "2rem"},
                    children=[
                        html.Div(
                            className="chart-container",
                            style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)"},
                            children=[dcc.Graph(id="risk-dv01-chart", config={"displayModeBar": False})]
                        ),
                        html.Div(
                            className="chart-container",
                            style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)"},
                            children=[dcc.Graph(id="risk-var-es-chart", config={"displayModeBar": False})]
                        ),
                    ]
                ),
                # Row 4: Portfolio Exposure Analysis
                html.Div(
                    className="chart-container",
                    style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)", "marginBottom": "2rem"},
                    children=[dcc.Graph(id="risk-exposure-chart", config={"displayModeBar": False})]
                ),
                # Row 5: Carry & Roll-Down
                html.Div(
                    className="chart-container",
                    style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)", "marginBottom": "2rem"},
                    children=[dcc.Graph(id="risk-carry-chart", config={"displayModeBar": False})]
                ),
                # Row 6: Rolling Correlation
                html.Div(
                    className="chart-container",
                    style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)", "marginBottom": "2rem"},
                    children=[dcc.Graph(id="risk-correlation-chart", config={"displayModeBar": False})]
                ),
                # Methodology note
                html.Div(
                    style={
                        "backgroundColor": COLORS["light_gray"],
                        "padding": "2rem",
                        "borderRadius": "8px",
                        "marginTop": "2rem"
                    },
                    children=[
                        html.H3("Methodology Notes", style={"textAlign": "center", "marginBottom": "1.5rem"}),
                        html.P(
                            "Risk metrics are scaled by actual portfolio positions from the selected strategy version.",
                            style={"textAlign": "center", "marginBottom": "1.5rem", "fontStyle": "italic", "opacity": 0.8}
                        ),
                        html.Div(
                            style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr 1fr", "gap": "1.5rem"},
                            children=[
                                html.Div(children=[
                                    html.H4("PCA", style={"color": COLORS["teal"], "marginBottom": "0.5rem"}),
                                    dcc.Markdown(
                                        r"""
                                        Applied to **daily yield changes** (not levels) across all DI tenors (1M–10Y).
                                        PC1 ≈ Level, PC2 ≈ Slope, PC3 ≈ Curvature.

                                        $$\Delta y_t(\tau) \approx w_1(\tau) \cdot PC_{1,t} + w_2(\tau) \cdot PC_{2,t} + w_3(\tau) \cdot PC_{3,t}$$
                                        """,
                                        mathjax=True, style={"fontSize": "0.8rem"}
                                    )
                                ]),
                                html.Div(children=[
                                    html.H4("Portfolio DV01", style={"color": COLORS["gold"], "marginBottom": "0.5rem"}),
                                    dcc.Markdown(
                                        r"""
                                        DI futures DV01 scaled by position size:

                                        $$\text{Portfolio DV01}_t = |S_t| \times \text{Notional} \times 0.0001 \times \frac{\text{DAP}}{252}$$

                                        where $S_t$ = position size. Shows actual $ at risk.
                                        """,
                                        mathjax=True, style={"fontSize": "0.8rem"}
                                    )
                                ]),
                                html.Div(children=[
                                    html.H4("Position-Weighted VaR", style={"color": COLORS["red"], "marginBottom": "0.5rem"}),
                                    dcc.Markdown(
                                        r"""
                                        VaR scaled by actual position exposure:

                                        $$\text{Portfolio VaR}_t = -|S_t| \times \text{VaR}_{99\%}^{\text{market}}$$

                                        Negative values indicate potential loss in bps.
                                        """,
                                        mathjax=True, style={"fontSize": "0.8rem"}
                                    )
                                ]),
                                html.Div(children=[
                                    html.H4("Carry Attribution", style={"color": COLORS["blue"], "marginBottom": "0.5rem"}),
                                    dcc.Markdown(
                                        r"""
                                        Position-weighted carry calculation:

                                        $$\text{Carry}_t = S_t \times (\text{FRA}_{3y3y} - \text{FRA}_{1y1y}) \times 100$$

                                        Shows actual carry earned given position size and direction.
                                        """,
                                        mathjax=True, style={"fontSize": "0.8rem"}
                                    )
                                ]),
                            ]
                        )
                    ]
                )
            ]
        )
    ]
)


# --- Tab Content: P&L Attribution ---
pnl_attribution_tab = html.Div(
    children=[
        html.Section(
            className="accent-section",
            style={"padding": "4rem 5%", "backgroundColor": COLORS["white"]},
            children=[
                html.H2("P&L Attribution", style={"textAlign": "center", "marginBottom": "1rem"}),
                html.P(
                    "Decomposition of strategy returns into Curve, Gamma, Carry, and Cost components",
                    style={"textAlign": "center", "marginBottom": "2rem", "opacity": 0.7}
                ),
                # Cumulative attribution chart
                html.Div(
                    className="chart-container",
                    style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)", "marginBottom": "2rem"},
                    children=[dcc.Graph(id="pnl-attrib-cumulative-chart", config={"displayModeBar": False})]
                ),
                # Summary bar + waterfall side by side
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr 2fr", "gap": "2rem", "marginBottom": "2rem"},
                    children=[
                        html.Div(
                            className="chart-container",
                            style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)"},
                            children=[dcc.Graph(id="pnl-attrib-summary-chart", config={"displayModeBar": False})]
                        ),
                        html.Div(
                            className="chart-container",
                            style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)"},
                            children=[dcc.Graph(id="pnl-attrib-waterfall-chart", config={"displayModeBar": False})]
                        ),
                    ]
                ),
                # Daily decomposition
                html.Div(
                    className="chart-container",
                    style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)", "marginBottom": "2rem"},
                    children=[dcc.Graph(id="pnl-attrib-daily-chart", config={"displayModeBar": False})]
                ),
                # Formulas section
                html.Div(
                    style={
                        "backgroundColor": COLORS["light_gray"],
                        "padding": "2rem",
                        "borderRadius": "8px",
                        "marginTop": "2rem"
                    },
                    children=[
                        html.H3("P&L Component Formulas", style={"textAlign": "center", "marginBottom": "1.5rem"}),
                        html.Div(
                            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "2rem"},
                            children=[
                                html.Div(
                                    children=[
                                        html.H4("Curve P&L", style={"color": COLORS["teal"], "marginBottom": "1rem"}),
                                        dcc.Markdown(
                                            r"""
                                            First-order spread change (DV01-neutral):

                                            $$\text{Curve PnL} = S \times \text{DV01}_{\text{neutral}} \times \Delta(\text{FRA}_{3y3y} - \text{FRA}_{1y1y})$$

                                            where $S$ is the position size and $\Delta$ denotes the daily spread change.
                                            """,
                                            mathjax=True,
                                            style={"fontSize": "0.95rem"}
                                        )
                                    ]
                                ),
                                html.Div(
                                    children=[
                                        html.H4("Gamma P&L", style={"color": COLORS["gold"], "marginBottom": "1rem"}),
                                        dcc.Markdown(
                                            r"""
                                            Second-order convexity effects:

                                            $$\text{Gamma PnL} = S \times \tfrac{1}{2}\left[C_{1y1y} (\Delta y_{1y1y})^2 - C_{3y3y} (\Delta y_{3y3y})^2\right]$$

                                            The 3y3y leg has ~7× higher convexity than 1y1y, creating **convexity bleed** in large moves.
                                            """,
                                            mathjax=True,
                                            style={"fontSize": "0.95rem"}
                                        )
                                    ]
                                ),
                                html.Div(
                                    children=[
                                        html.H4("Carry", style={"color": COLORS["blue"], "marginBottom": "1rem"}),
                                        dcc.Markdown(
                                            r"""
                                            Roll-down approximation:

                                            $$\text{Carry} = 0.01 \times S$$

                                            Represents the daily carry earned from holding the steepener as the curve rolls down.
                                            """,
                                            mathjax=True,
                                            style={"fontSize": "0.95rem"}
                                        )
                                    ]
                                ),
                                html.Div(
                                    children=[
                                        html.H4("Costs", style={"color": COLORS["red"], "marginBottom": "1rem"}),
                                        dcc.Markdown(
                                            r"""
                                            Execution costs and market impact:

                                            $$\text{Cost} = -(c_{\text{base}} + \alpha \cdot S^2) \times |S|$$

                                            Includes base spread cost ($c_{\text{base}}$) and non-linear market impact ($\alpha \cdot S^2$).
                                            """,
                                            mathjax=True,
                                            style={"fontSize": "0.95rem"}
                                        )
                                    ]
                                ),
                            ]
                        )
                    ]
                )
            ]
        )
    ]
)


# --- Tab Content: Performance Attribution ---
performance_attribution_tab = html.Div(
    children=[
        html.Section(
            className="accent-section",
            style={"padding": "4rem 5%", "backgroundColor": COLORS["white"]},
            children=[
                html.H2("Performance Attribution", style={"textAlign": "center", "marginBottom": "1rem"}),
                html.P(
                    "Risk-adjusted returns, drawdown analysis, and per-regime performance breakdown",
                    style={"textAlign": "center", "marginBottom": "2rem", "opacity": 0.7}
                ),
                # Drawdown + Rolling Sharpe side by side
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "2rem", "marginBottom": "2rem"},
                    children=[
                        html.Div(
                            className="chart-container",
                            style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)"},
                            children=[dcc.Graph(id="perf-drawdown-chart", config={"displayModeBar": False})]
                        ),
                        html.Div(
                            className="chart-container",
                            style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)"},
                            children=[dcc.Graph(id="perf-rolling-sharpe-chart", config={"displayModeBar": False})]
                        ),
                    ]
                ),
                # Monthly heatmap
                html.Div(
                    className="chart-container",
                    style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)", "marginBottom": "2rem"},
                    children=[dcc.Graph(id="perf-monthly-heatmap", config={"displayModeBar": False})]
                ),
                # Regime attribution
                html.Div(
                    className="chart-container",
                    style={"backgroundColor": COLORS["white"], "padding": "1rem", "borderRadius": "8px", "boxShadow": "0 4px 12px rgba(0,0,0,0.05)", "marginBottom": "2rem"},
                    children=[dcc.Graph(id="perf-regime-attrib-chart", config={"displayModeBar": False})]
                ),
                # Performance metrics table section
                html.Div(
                    id="perf-metrics-table",
                    style={
                        "backgroundColor": COLORS["light_gray"],
                        "padding": "2rem",
                        "borderRadius": "8px",
                        "marginTop": "1rem",
                    },
                ),
            ]
        )
    ]
)


# Main content with tabs
main_content = html.Div(
    children=[
        dcc.Tabs(
            id="main-tabs",
            value="market",
            className="custom-tabs",
            children=[
                dcc.Tab(
                    label="📈 Market Variables",
                    value="market",
                    className="custom-tab",
                    selected_className="custom-tab-selected",
                    children=[market_variables_tab]
                ),
                dcc.Tab(
                    label="🏛️ Macro Variables",
                    value="macro",
                    className="custom-tab",
                    selected_className="custom-tab-selected",
                    children=[macro_tab]
                ),
                dcc.Tab(
                    label="📉 Strategy",
                    value="strategy",
                    className="custom-tab",
                    selected_className="custom-tab-selected",
                    children=[strategy_tab]
                ),
                dcc.Tab(
                    label="📊 Performance",
                    value="performance",
                    className="custom-tab",
                    selected_className="custom-tab-selected",
                    children=[performance_tab]
                ),
                dcc.Tab(
                    label="💰 P&L Attribution",
                    value="pnl_attribution",
                    className="custom-tab",
                    selected_className="custom-tab-selected",
                    children=[pnl_attribution_tab]
                ),
                dcc.Tab(
                    label="🎯 Performance Attribution",
                    value="perf_attribution",
                    className="custom-tab",
                    selected_className="custom-tab-selected",
                    children=[performance_attribution_tab]
                ),
                dcc.Tab(
                    label="🛡️ Risk Management",
                    value="risk_mgmt",
                    className="custom-tab",
                    selected_className="custom-tab-selected",
                    children=[risk_management_tab]
                ),
            ]
        )
    ]
)

footer = html.Footer(
    children=[
        html.Div("© 2024 Schonfeld Strategic Advisors LLC.", style={"opacity": 0.8}),
        html.Div(
            className="footer-links",
            children=[
                html.A("Privacy Policy", href="#"),
                html.A("Terms of Use", href="#"),
                html.A("Contact Us", href="#"),
            ]
        )
    ]
)

# Assemble the final layout
app.layout = html.Div(
    style={"fontFamily": "Unica77LLSub, Verdana, sans-serif", "color": COLORS["dark"], "backgroundColor": COLORS["white"]},
    children=[
        navbar,
        hero,
        metrics_section,
        main_content,
        footer,
    ]
)

@app.callback(
    [Output("pnl-chart", "figure"),
     Output("position-chart", "figure"),
     Output("spread-chart", "figure"),
     Output("metric-total-return", "children"),
     Output("metric-sharpe", "children"),
     Output("metric-win-rate", "children"),
     Output("metric-trades", "children")],
    [Input("version-selector", "value")]
)
def update_dashboard(version):
    df_pnl, df_trades = load_data(version)
    
    if df_pnl.empty:
        empty_fig = go.Figure()
        return empty_fig, empty_fig, empty_fig, "N/A", "N/A", "N/A", "N/A"
        
    pnl_fig = create_pnl_chart(df_pnl)
    pos_fig = create_position_chart(df_pnl)
    spread_fig = create_spread_chart(df_pnl)
    
    # Calculate some basic metrics
    total_ret = df_pnl["total_pnl"].sum()
    
    # Daily returns
    daily_returns = df_pnl["total_pnl"]
    sharpe = 0
    if daily_returns.std() != 0:
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
        
    win_rate = (daily_returns > 0).mean() * 100
    num_trades = len(df_trades) if not df_trades.empty else len(df_pnl[df_pnl["position_size"].diff() != 0])
    
    metric_ret = [
        html.H3("Total PnL"),
        html.H2(f"{total_ret:.2f}", style={"color": COLORS["teal"] if total_ret > 0 else "red", "margin": "0"})
    ]
    
    metric_sr = [
        html.H3("Annualized Sharpe"),
        html.H2(f"{sharpe:.2f}", style={"margin": "0"})
    ]
    
    metric_wr = [
        html.H3("Daily Win Rate"),
        html.H2(f"{win_rate:.1f}%", style={"margin": "0"})
    ]
    
    metric_tr = [
        html.H3("Total Trades"),
        html.H2(f"{num_trades}", style={"margin": "0"})
    ]
    
    return pnl_fig, pos_fig, spread_fig, metric_ret, metric_sr, metric_wr, metric_tr


# --- Callback: update date picker range when version changes ---
@app.callback(
    [Output("trade-date-picker", "min_date_allowed"),
     Output("trade-date-picker", "max_date_allowed"),
     Output("trade-date-picker", "date")],
    [Input("version-selector", "value")],
)
def update_date_picker_range(version):
    df_pnl, _ = load_data(version)
    if df_pnl.empty:
        return None, None, None
    # Use 2005-01-03 as min date (when SELIC data starts) for full PCA history
    # But cap at actual data availability for trading
    min_d = pd.Timestamp("2005-01-03").date()
    max_d = df_pnl["date"].max().date()
    return min_d, max_d, None


# --- Helper: find point-in-time regime file ---
def _find_regime_file(selected_date):
    """Find the regime_probs CSV from the most recent fiscal release on or before selected_date."""
    sel = pd.to_datetime(selected_date)
    if os.path.exists(CALENDAR_PATH):
        cal = pd.read_csv(CALENDAR_PATH, parse_dates=["release_date"])
        # Releases on or before selected date
        available = cal[cal["release_date"] <= sel].sort_values("release_date")
        if available.empty:
            return None, None
        latest_release = available.iloc[-1]["release_date"]
        date_str = latest_release.strftime("%Y%m%d")
        regime_file = os.path.join(REGIME_DIR, f"regime_probs_{date_str}.csv")
        if os.path.exists(regime_file):
            return regime_file, latest_release
    # Fallback: find closest file by name
    files = sorted(glob.glob(os.path.join(REGIME_DIR, "regime_probs_*.csv")))
    if not files:
        return None, None
    sel_str = sel.strftime("%Y%m%d")
    for f in reversed(files):
        fname = os.path.basename(f).replace("regime_probs_", "").replace(".csv", "")
        if fname <= sel_str:
            return f, pd.to_datetime(fname)
    return files[0], None


# --- Callback: point-in-time fiscal + regime charts + trade detail panel ---
@app.callback(
    [Output("trade-detail-panel", "children"),
     Output("fiscal-chart", "figure"),
     Output("regime-chart", "figure"),
     Output("fiscal-section-subtitle", "children")],
    [Input("trade-date-picker", "date")],
    [State("version-selector", "value")],
)
def update_trade_details(selected_date, version):
    empty_fig = go.Figure()
    empty_fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    placeholder = [html.P("\u2190 Select a date to view details", style={"opacity": 0.5, "marginTop": "3rem", "textAlign": "center"})]
    default_subtitle = "Select a date below to see the point-in-time view."

    if selected_date is None:
        return placeholder, empty_fig, empty_fig, default_subtitle

    df_pnl, _ = load_data(version)
    if df_pnl.empty:
        return [html.P("No data.", style={"color": "red"})], empty_fig, empty_fig, default_subtitle

    sel = pd.to_datetime(selected_date).normalize()

    # --- Find the row in daily_pnl ---
    row = df_pnl[df_pnl["date"].dt.normalize() == sel]
    if row.empty:
        nearest_idx = (df_pnl["date"] - sel).abs().idxmin()
        nearest_date = df_pnl.loc[nearest_idx, "date"]
        row = df_pnl[df_pnl["date"] == nearest_date]
        date_label = f"{nearest_date.strftime('%Y-%m-%d')} (nearest to {sel.strftime('%Y-%m-%d')})"
        sel = nearest_date.normalize()
    else:
        date_label = sel.strftime("%Y-%m-%d")

    r = row.iloc[0]

    # --- Point-in-time regime file ---
    regime_file, model_release = _find_regime_file(sel)

    # Build fiscal chart (std_4y up to this date)
    fiscal_fig = go.Figure()
    if regime_file is not None:
        rdf = pd.read_csv(regime_file, parse_dates=["date"])
        rdf = rdf[rdf["date"] <= sel].sort_values("date")

        fiscal_fig.add_trace(go.Scatter(
            x=rdf["date"], y=rdf["std_4y"],
            mode="lines", name="Std 4Y",
            line=dict(color=COLORS["dark"], width=2),
        ))

        # Mark the selected date
        sel_row = rdf[rdf["date"] == rdf["date"].max()]
        if not sel_row.empty:
            fiscal_fig.add_trace(go.Scatter(
                x=sel_row["date"], y=sel_row["std_4y"],
                mode="markers", name="Selected Date",
                marker=dict(color="#e74c3c", size=12, symbol="diamond"),
            ))

    fiscal_fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif", font_color=COLORS["dark"],
        title=f"4Y Primary Surplus Std Dev (as of {date_label})",
        title_font_size=16,
        xaxis=dict(showgrid=True, gridcolor=COLORS["gray"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], title="Std Dev"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=40),
    )

    # Build regime chart (prob_high_vol from THIS model only, up to sel date)
    regime_fig = go.Figure()
    if regime_file is not None:
        rdf = pd.read_csv(regime_file, parse_dates=["date"])
        rdf = rdf[rdf["date"] <= sel].sort_values("date")

        if "prob_high_vol" in rdf.columns:
            regime_fig.add_trace(go.Scatter(
                x=rdf["date"], y=rdf["prob_high_vol"],
                mode="lines", name="P(Rising Uncertainty)",
                fill="tozeroy",
                line=dict(color="#e74c3c", width=1),
                fillcolor="rgba(231,76,60,0.2)",
            ))

        regime_fig.add_hline(y=0.5, line_dash="dot", line_color=COLORS["gold"],
                             annotation_text="50%", annotation_position="top left")

    model_label = model_release.strftime("%Y-%m-%d") if model_release is not None else "N/A"
    regime_fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif", font_color=COLORS["dark"],
        title=f"Markov Regime Prob (model fitted {model_label})",
        title_font_size=16,
        xaxis=dict(showgrid=True, gridcolor=COLORS["gray"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], title="Probability", range=[0, 1]),
        hovermode="x unified",
        margin=dict(t=60, b=40),
    )

    subtitle = f"Point-in-time view as of {date_label}  \u2014  Model fitted on fiscal release {model_label}"

    # --- Build trade detail cards ---
    regime = r.get("regime", "N/A")
    pos_type = r.get("position_type", "N/A")
    pos_size = r.get("position_size", 0)
    exec_style = r.get("execution_style", "N/A")
    spread = r.get("curve_spread", 0)
    z_score = r.get("std_4y_zscore", r.get("std_4y", 0))
    total_pnl = r.get("total_pnl", 0)
    curve_pnl = r.get("curve_pnl", 0)
    carry_pnl = r.get("carry_pnl", 0)
    cost_pnl = r.get("cost_pnl", 0)
    prob_high = r.get("prob_high_vol", None)
    
    # V6 specific: PCA regime data
    pca_regime = r.get("pca_regime", None)
    prob_pca_high = r.get("prob_pca_high", None)

    regime_color = {
        "high_uncertainty": "#e74c3c",
        "medium_uncertainty": COLORS["gold"],
        "low_uncertainty": COLORS["teal"],
    }.get(regime, COLORS["gray"])

    exec_label = {
        "pay_spread": "\ud83d\udcb0  Pay the Spread",
        "collect_carry": "\ud83d\udce5  Collect the Carry",
        "standard": "\ud83d\udcca  Standard",
        "no_trade": "\ud83d\udeab  Risk Off",
    }.get(exec_style, exec_style)

    def _card(label, value, color=COLORS["dark"]):
        return html.Div(
            style={"flex": "1", "minWidth": "120px", "textAlign": "center", "padding": "0.5rem"},
            children=[
                html.Div(label, style={"fontSize": "0.75rem", "opacity": 0.6, "marginBottom": "0.25rem"}),
                html.Div(value, style={"fontSize": "1.15rem", "fontWeight": "bold", "color": color}),
            ],
        )

    pnl_color = COLORS["teal"] if total_pnl >= 0 else "#e74c3c"
    
    # Build position cards (base)
    position_cards = [
        _card("Position", pos_type.replace("_", " ").title()),
        _card("Size", f"{pos_size:+.0%}" if isinstance(pos_size, (int, float)) else str(pos_size)),
        _card("Execution", exec_label),
        _card("Spread", f"{spread:.4f}" if isinstance(spread, (int, float)) else str(spread)),
        _card("Z-Score", f"{z_score:.2f}" if isinstance(z_score, (int, float)) and not pd.isna(z_score) else "N/A"),
    ]
    
    # Add volatility probability if available
    if prob_high is not None and not pd.isna(prob_high):
        position_cards.append(_card("P(High Vol)", f"{prob_high:.1%}"))
    
    # Add PCA regime info for V6
    if pca_regime is not None and not pd.isna(pca_regime):
        pca_regime_color = {
            "high": "#e74c3c",
            "medium": COLORS["gold"],
            "low": COLORS["teal"],
        }.get(pca_regime, COLORS["gray"])
        position_cards.append(_card("PCA Regime", pca_regime.upper(), pca_regime_color))
    
    if prob_pca_high is not None and not pd.isna(prob_pca_high):
        position_cards.append(_card("P(Infl High)", f"{prob_pca_high:.1%}"))

    detail_panel = [
        html.Div(
            style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "1rem", "flexWrap": "wrap", "gap": "0.5rem"},
            children=[
                html.H3(f"\ud83d\udcc5  {date_label}", style={"margin": 0}),
                html.Span(
                    regime.replace("_", " ").title(),
                    style={
                        "backgroundColor": regime_color, "color": "white",
                        "padding": "0.3rem 1rem", "borderRadius": "20px",
                        "fontSize": "0.85rem", "fontWeight": "bold",
                    },
                ),
            ],
        ),
        html.Hr(style={"border": "none", "borderTop": f"1px solid {COLORS['gray']}", "margin": "0 0 1rem 0"}),
        html.Div(
            style={"display": "flex", "gap": "0.5rem", "flexWrap": "wrap", "marginBottom": "1rem"},
            children=position_cards,
        ),
        html.Div(
            style={"display": "flex", "gap": "0.5rem", "flexWrap": "wrap", "backgroundColor": COLORS["light_gray"], "padding": "0.75rem", "borderRadius": "6px"},
            children=[
                _card("Total P&L", f"{total_pnl:+.3f} bps", pnl_color),
                _card("Curve P&L", f"{curve_pnl:+.3f} bps"),
                _card("Carry P&L", f"{carry_pnl:+.3f} bps"),
                _card("Cost P&L", f"{cost_pnl:+.3f} bps"),
            ],
        ),
    ]

    return detail_panel, fiscal_fig, regime_fig, subtitle


# --- Callback: PCA Regime Analysis (point-in-time for V6) ---
@app.callback(
    [Output("pca1-chart", "figure"),
     Output("pca-regime-chart", "figure"),
     Output("pca-section-subtitle", "children")],
    [Input("trade-date-picker", "date")],
)
def update_pca_regime_details(selected_date):
    """Update PCA regime charts showing point-in-time 3-regime analysis using full history."""
    empty_fig = go.Figure()
    empty_fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    default_subtitle = "Select a date below to see the point-in-time view of inflation expectations regime."
    
    if selected_date is None:
        return empty_fig, empty_fig, default_subtitle
    
    # Load full PCA history (goes back to 2001, not just 2012)
    pca_history_path = os.path.join(DATA_DIR, "pca_regime_full_history.csv")
    if os.path.exists(pca_history_path):
        df_pca = pd.read_csv(pca_history_path, parse_dates=["date"])
        # Rename columns to match expected format
        df_pca = df_pca.rename(columns={
            "regime": "pca_regime",
            "prob_high": "prob_pca_high",
            "prob_medium": "prob_pca_medium",
            "prob_low": "prob_pca_low",
        })
    else:
        # Fallback to V6 data if full history not available
        df_pnl, _ = load_data("v6")
        if df_pnl.empty or "pca1" not in df_pnl.columns:
            return empty_fig, empty_fig, "PCA data not available. Run V6 strategy first."
        df_pca = df_pnl[["date", "pca1", "pca_regime", "prob_pca_high"]].copy()
    
    sel = pd.to_datetime(selected_date).normalize()
    
    # Find the row in PCA data
    row = df_pca[df_pca["date"].dt.normalize() == sel]
    if row.empty:
        nearest_idx = (df_pca["date"] - sel).abs().idxmin()
        nearest_date = df_pca.loc[nearest_idx, "date"]
        sel = nearest_date.normalize()
        date_label = f"{nearest_date.strftime('%Y-%m-%d')} (nearest to {pd.to_datetime(selected_date).strftime('%Y-%m-%d')})"
    else:
        date_label = sel.strftime("%Y-%m-%d")
    
    # Get data up to selected date
    hist_df = df_pca[df_pca["date"] <= sel].copy()
    
    if hist_df.empty:
        return empty_fig, empty_fig, default_subtitle
    
    # Find the model release date (most recent non-null pca_regime)
    regime_df = hist_df[hist_df["pca_regime"].notna() & (hist_df["pca_regime"] != "unknown")]
    if regime_df.empty:
        model_label = "N/A"
    else:
        model_label = regime_df["date"].max().strftime("%Y-%m-%d")
    
    # Build PCA1 chart
    pca1_fig = go.Figure()
    
    # Plot PCA1 values
    pca_hist = hist_df[hist_df["pca1"].notna()]
    if not pca_hist.empty:
        pca1_fig.add_trace(go.Scatter(
            x=pca_hist["date"], y=pca_hist["pca1"],
            mode="lines", name="PC1 (Inflation Factor)",
            line=dict(color=COLORS["teal"], width=2),
        ))
        
        # Mark the selected date
        sel_row = pca_hist[pca_hist["date"] == pca_hist["date"].max()]
        if not sel_row.empty:
            pca1_fig.add_trace(go.Scatter(
                x=sel_row["date"], y=sel_row["pca1"],
                mode="markers", name="Selected Date",
                marker=dict(color="#e74c3c", size=12, symbol="diamond"),
            ))
    
    pca1_fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif", font_color=COLORS["dark"],
        title=f"PC1 - Inflation Expectations Factor (as of {date_label})",
        title_font_size=16,
        xaxis=dict(showgrid=True, gridcolor=COLORS["gray"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], title="PC1 Score"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=40),
    )
    
    # Build 3-regime probability chart
    regime_fig = go.Figure()
    
    # Plot regime probabilities if available
    prob_cols = ["prob_pca_high", "prob_pca_medium", "prob_pca_low"]
    available_probs = [c for c in prob_cols if c in hist_df.columns]
    
    if available_probs:
        # We need to reconstruct the 3 regime probabilities
        # From V6: prob_pca_high is stored, we can infer others if available
        if "prob_pca_high" in hist_df.columns:
            # Only high is directly stored, create a stacked area chart
            high_data = hist_df[hist_df["prob_pca_high"].notna()]
            if not high_data.empty:
                regime_fig.add_trace(go.Scatter(
                    x=high_data["date"], y=high_data["prob_pca_high"],
                    mode="lines", name="P(High Inflation)",
                    fill="tozeroy",
                    line=dict(color="#e74c3c", width=1),
                    fillcolor="rgba(231,76,60,0.3)",
                ))
        
        # Add threshold line
        regime_fig.add_hline(y=0.6, line_dash="dot", line_color=COLORS["gold"],
                            annotation_text="60% threshold", annotation_position="top left")
    else:
        # No probability data, show regime as colored regions
        if "pca_regime" in hist_df.columns:
            regime_colors = {
                "high": "rgba(231,76,60,0.3)",
                "medium": "rgba(180,166,128,0.3)",
                "low": "rgba(0,172,172,0.3)",
                "unknown": "rgba(200,200,200,0.1)",
            }
            
            # Add background shading per regime
            prev_regime = None
            start_date = None
            for _, row in hist_df.iterrows():
                r = row["pca_regime"]
                if r != prev_regime:
                    if prev_regime is not None and start_date is not None:
                        regime_fig.add_vrect(
                            x0=start_date, x1=row["date"],
                            fillcolor=regime_colors.get(prev_regime, "rgba(0,0,0,0)"),
                            layer="below", line_width=0,
                        )
                    start_date = row["date"]
                    prev_regime = r
            # Close last segment
            if prev_regime is not None and start_date is not None:
                regime_fig.add_vrect(
                    x0=start_date, x1=hist_df["date"].iloc[-1],
                    fillcolor=regime_colors.get(prev_regime, "rgba(0,0,0,0)"),
                    layer="below", line_width=0,
                )
    
    # Get current regime for title
    current_regime = hist_df["pca_regime"].iloc[-1] if not hist_df.empty and "pca_regime" in hist_df.columns else "unknown"
    current_prob_high = hist_df["prob_pca_high"].iloc[-1] if not hist_df.empty and "prob_pca_high" in hist_df.columns else None
    
    prob_text = f" | P(High)={current_prob_high:.1%}" if current_prob_high is not None and not pd.isna(current_prob_high) else ""
    
    regime_fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif", font_color=COLORS["dark"],
        title=f"3-Regime Markov: {current_regime.upper()} Regime{prob_text}",
        title_font_size=16,
        xaxis=dict(showgrid=True, gridcolor=COLORS["gray"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], title="Probability", range=[0, 1]),
        hovermode="x unified",
        margin=dict(t=60, b=40),
    )
    
    subtitle = f"Point-in-time view as of {date_label} — 3-regime Markov on Dynamic PCA (model fitted {model_label})"
    
    return pca1_fig, regime_fig, subtitle


# --- Callback: Dynamic PCA based on user-selected date range ---
@app.callback(
    [Output("dynamic-pca-chart", "figure"),
     Output("dynamic-pca-loadings", "children")],
    [Input("run-pca-button", "n_clicks")],
    [State("pca-start-date", "date"),
     State("pca-end-date", "date")]
)
def update_dynamic_pca(n_clicks, start_date, end_date):
    """Run PCA on user-selected date range and return chart + loadings."""
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    
    # Initialize empty outputs
    empty_fig = go.Figure()
    empty_fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        title="Click 'Run Partial Sample PCA' to see results"
    )
    
    if start_date is None or end_date is None:
        return empty_fig, html.P("Select a date range and click 'Run Partial Sample PCA' to see the results.", 
                                  style={"textAlign": "center", "opacity": 0.6})
    
    # Load data
    df_ipca = load_ipca_data()
    df_selic = load_selic_forecast_data()
    
    if df_ipca.empty or df_selic.empty:
        return empty_fig, html.P("Error: Could not load data files.", style={"color": "red", "textAlign": "center"})
    
    # Parse dates
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    # Ensure start <= end
    if start_dt > end_dt:
        return empty_fig, html.P("Error: Start date must be before end date.", style={"color": "red", "textAlign": "center"})
    
    # Filter data to selected range
    df_ipca_filtered = df_ipca[(df_ipca["date"] >= start_dt) & (df_ipca["date"] <= end_dt)].copy()
    df_selic_filtered = df_selic[(df_selic["date"] >= start_dt) & (df_selic["date"] <= end_dt)].copy()
    
    if df_ipca_filtered.empty or df_selic_filtered.empty:
        return empty_fig, html.P("Error: No data available in the selected date range.", 
                                  style={"color": "red", "textAlign": "center"})
    
    # Merge all data on date
    df_merged = pd.merge(
        df_ipca_filtered[["date", "median_forecast", "std_forecast"]].rename(
            columns={"median_forecast": "ipca_median", "std_forecast": "ipca_std"}
        ),
        df_selic_filtered[["date", "median_forecast", "std_forecast"]].rename(
            columns={"median_forecast": "selic_median", "std_forecast": "selic_std"}
        ),
        on="date",
        how="inner"
    )
    
    if df_merged.empty:
        return empty_fig, html.P("Error: No overlapping data between IPCA and SELIC in the selected range.", 
                                  style={"color": "red", "textAlign": "center"})
    
    # Prepare data for PCA (drop NaN)
    features = ["ipca_median", "ipca_std", "selic_median", "selic_std"]
    df_pca = df_merged.dropna(subset=features)
    
    if len(df_pca) < 10:
        return empty_fig, html.P(f"Error: Insufficient data points ({len(df_pca)}) for PCA. Need at least 10.", 
                                  style={"color": "red", "textAlign": "center"})
    
    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_pca[features])
    
    # Apply PCA
    pca = PCA(n_components=2)
    pc_scores = pca.fit_transform(X_scaled)
    
    # Add PC1 to dataframe
    df_pca["PC1"] = pc_scores[:, 0]
    
    # Get explained variance
    explained_var = pca.explained_variance_ratio_[0] * 100
    
    # Get loadings
    loadings = pca.components_[0]
    
    # Create figure
    fig = go.Figure()
    
    # Plot PC1
    fig.add_trace(go.Scatter(
        x=df_pca["date"],
        y=df_pca["PC1"],
        mode="lines",
        name="PC1",
        line=dict(color=COLORS["teal"], width=2),
        fill='tozeroy',
        fillcolor="rgba(0,172,172,0.1)"
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["gray"])
    
    # Update layout
    fig.update_layout(
        height=500,
        title=f"PC1 - Partial Sample PCA ({start_date} to {end_date}) - {explained_var:.1f}% variance explained",
        title_font_size=16,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Unica77LLSub, Verdana, sans-serif",
        font_color=COLORS["dark"],
        showlegend=False,
        hovermode="x unified",
        xaxis=dict(showgrid=True, gridcolor=COLORS["gray"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["beige"], title="PC1 Score")
    )
    
    # Create loadings display
    loadings_display = html.Div(
        style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "2rem"},
        children=[
            html.Div(
                children=[
                    html.H4("PC1 Loadings", style={"color": COLORS["teal"], "marginBottom": "1rem"}),
                    html.Table(
                        style={"width": "100%", "borderCollapse": "collapse"},
                        children=[
                            html.Thead(
                                html.Tr([
                                    html.Th("Variable", style={"textAlign": "left", "padding": "0.5rem", "borderBottom": f"2px solid {COLORS['teal']}"}),
                                    html.Th("Loading", style={"textAlign": "right", "padding": "0.5rem", "borderBottom": f"2px solid {COLORS['teal']}"}),
                                ])
                            ),
                            html.Tbody([
                                html.Tr([
                                    html.Td("IPCA Median 12M", style={"padding": "0.5rem", "borderBottom": f"1px solid {COLORS['gray']}"}),
                                    html.Td(f"{loadings[0]:.4f}", style={"padding": "0.5rem", "borderBottom": f"1px solid {COLORS['gray']}", "textAlign": "right", "fontFamily": "monospace"})
                                ]),
                                html.Tr([
                                    html.Td("IPCA Std Dev 12M", style={"padding": "0.5rem", "borderBottom": f"1px solid {COLORS['gray']}"}),
                                    html.Td(f"{loadings[1]:.4f}", style={"padding": "0.5rem", "borderBottom": f"1px solid {COLORS['gray']}", "textAlign": "right", "fontFamily": "monospace"})
                                ]),
                                html.Tr([
                                    html.Td("SELIC Median 1Y", style={"padding": "0.5rem", "borderBottom": f"1px solid {COLORS['gray']}"}),
                                    html.Td(f"{loadings[2]:.4f}", style={"padding": "0.5rem", "borderBottom": f"1px solid {COLORS['gray']}", "textAlign": "right", "fontFamily": "monospace"})
                                ]),
                                html.Tr([
                                    html.Td("SELIC Std Dev 1Y", style={"padding": "0.5rem", "borderBottom": f"1px solid {COLORS['gray']}"}),
                                    html.Td(f"{loadings[3]:.4f}", style={"padding": "0.5rem", "borderBottom": f"1px solid {COLORS['gray']}", "textAlign": "right", "fontFamily": "monospace"})
                                ]),
                            ])
                        ]
                    )
                ]
            ),
            html.Div(
                children=[
                    html.H4("Sample Statistics", style={"color": COLORS["teal"], "marginBottom": "1rem"}),
                    html.Table(
                        style={"width": "100%", "borderCollapse": "collapse"},
                        children=[
                            html.Tbody([
                                html.Tr([
                                    html.Td("Date Range:", style={"padding": "0.5rem", "borderBottom": f"1px solid {COLORS['gray']}", "fontWeight": "bold"}),
                                    html.Td(f"{start_date} to {end_date}", style={"padding": "0.5rem", "borderBottom": f"1px solid {COLORS['gray']}", "textAlign": "right"})
                                ]),
                                html.Tr([
                                    html.Td("Observations:", style={"padding": "0.5rem", "borderBottom": f"1px solid {COLORS['gray']}", "fontWeight": "bold"}),
                                    html.Td(f"{len(df_pca)}", style={"padding": "0.5rem", "borderBottom": f"1px solid {COLORS['gray']}", "textAlign": "right", "fontFamily": "monospace"})
                                ]),
                                html.Tr([
                                    html.Td("Variance Explained (PC1):", style={"padding": "0.5rem", "borderBottom": f"1px solid {COLORS['gray']}", "fontWeight": "bold"}),
                                    html.Td(f"{explained_var:.2f}%", style={"padding": "0.5rem", "borderBottom": f"1px solid {COLORS['gray']}", "textAlign": "right", "fontFamily": "monospace"})
                                ]),
                                html.Tr([
                                    html.Td("Variance Explained (PC2):", style={"padding": "0.5rem", "borderBottom": f"1px solid {COLORS['gray']}", "fontWeight": "bold"}),
                                    html.Td(f"{pca.explained_variance_ratio_[1] * 100:.2f}%", style={"padding": "0.5rem", "borderBottom": f"1px solid {COLORS['gray']}", "textAlign": "right", "fontFamily": "monospace"})
                                ]),
                            ])
                        ]
                    )
                ]
            )
        ]
    )
    
    return fig, loadings_display


# --- Callback: P&L Attribution tab ---
@app.callback(
    [Output("pnl-attrib-cumulative-chart", "figure"),
     Output("pnl-attrib-summary-chart", "figure"),
     Output("pnl-attrib-waterfall-chart", "figure"),
     Output("pnl-attrib-daily-chart", "figure")],
    [Input("version-selector", "value")]
)
def update_pnl_attribution(version):
    df_pnl, _ = load_data(version)
    if df_pnl.empty:
        empty = go.Figure()
        return empty, empty, empty, empty

    return (
        create_pnl_attribution_cumulative_chart(df_pnl),
        create_pnl_attribution_summary_chart(df_pnl),
        create_pnl_attribution_waterfall_chart(df_pnl),
        create_pnl_daily_decomposition_chart(df_pnl),
    )


# --- Callback: Performance Attribution tab ---
@app.callback(
    [Output("perf-drawdown-chart", "figure"),
     Output("perf-rolling-sharpe-chart", "figure"),
     Output("perf-monthly-heatmap", "figure"),
     Output("perf-regime-attrib-chart", "figure"),
     Output("perf-metrics-table", "children")],
    [Input("version-selector", "value")]
)
def update_performance_attribution(version):
    df_pnl, df_trades = load_data(version)
    if df_pnl.empty:
        empty = go.Figure()
        return empty, empty, empty, empty, html.P("No data available.", style={"textAlign": "center", "opacity": 0.6})

    # Charts
    drawdown_fig = create_drawdown_chart(df_pnl)
    sharpe_fig = create_rolling_sharpe_chart(df_pnl)
    heatmap_fig = create_monthly_heatmap(df_pnl)
    regime_fig = create_regime_attribution_chart(df_pnl)

    # Performance metrics table
    total_pnl = df_pnl["total_pnl"].sum()
    days = len(df_pnl)
    years = days / 252
    daily_std = df_pnl["total_pnl"].std()
    sharpe = (df_pnl["total_pnl"].mean() / daily_std * np.sqrt(252)) if daily_std > 0 else 0
    win_rate = (df_pnl["total_pnl"] > 0).mean() * 100

    cumulative = df_pnl["total_pnl"].cumsum()
    peak = cumulative.expanding().max()
    max_dd = (cumulative - peak).min()

    # Calmar ratio
    calmar = (total_pnl / years) / abs(max_dd) if max_dd != 0 and years > 0 else 0

    # Best / worst months
    df_pnl_copy = df_pnl.copy()
    df_pnl_copy["month"] = df_pnl_copy["date"].dt.to_period("M")
    monthly = df_pnl_copy.groupby("month")["total_pnl"].sum()
    best_month = monthly.max()
    worst_month = monthly.min()
    pct_positive_months = (monthly > 0).mean() * 100

    def _metric_row(label, value, color=COLORS["dark"]):
        return html.Tr([
            html.Td(label, style={"padding": "0.6rem 1rem", "borderBottom": f"1px solid {COLORS['gray']}", "fontWeight": "bold"}),
            html.Td(value, style={
                "padding": "0.6rem 1rem",
                "borderBottom": f"1px solid {COLORS['gray']}",
                "textAlign": "right",
                "fontFamily": "monospace",
                "fontSize": "1rem",
                "color": color,
            }),
        ])

    metrics_table = html.Div(
        children=[
            html.H3("Performance Summary", style={"textAlign": "center", "marginBottom": "1.5rem"}),
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "2rem"},
                children=[
                    html.Table(
                        style={"width": "100%", "borderCollapse": "collapse", "backgroundColor": COLORS["white"], "borderRadius": "8px"},
                        children=[
                            html.Thead(html.Tr([
                                html.Th("Return Metrics", colSpan=2, style={
                                    "textAlign": "left", "padding": "0.8rem 1rem",
                                    "borderBottom": f"2px solid {COLORS['teal']}",
                                    "color": COLORS["teal"], "fontSize": "1.05rem",
                                }),
                            ])),
                            html.Tbody([
                                _metric_row("Total P&L", f"{total_pnl:+.2f} bps", COLORS["teal"] if total_pnl > 0 else COLORS["red"]),
                                _metric_row("P&L / Year", f"{total_pnl / years:+.2f} bps" if years > 0 else "N/A"),
                                _metric_row("Sharpe Ratio", f"{sharpe:.2f}"),
                                _metric_row("Calmar Ratio", f"{calmar:.2f}"),
                                _metric_row("Daily Win Rate", f"{win_rate:.1f}%"),
                                _metric_row("Monthly Win Rate", f"{pct_positive_months:.1f}%"),
                            ]),
                        ]
                    ),
                    html.Table(
                        style={"width": "100%", "borderCollapse": "collapse", "backgroundColor": COLORS["white"], "borderRadius": "8px"},
                        children=[
                            html.Thead(html.Tr([
                                html.Th("Risk Metrics", colSpan=2, style={
                                    "textAlign": "left", "padding": "0.8rem 1rem",
                                    "borderBottom": f"2px solid {COLORS['red']}",
                                    "color": COLORS["red"], "fontSize": "1.05rem",
                                }),
                            ])),
                            html.Tbody([
                                _metric_row("Max Drawdown", f"{max_dd:.2f} bps", COLORS["red"]),
                                _metric_row("Daily Std Dev", f"{daily_std:.4f} bps"),
                                _metric_row("Best Month", f"{best_month:+.2f} bps", COLORS["teal"]),
                                _metric_row("Worst Month", f"{worst_month:+.2f} bps", COLORS["red"]),
                                _metric_row("Trading Days", f"{days}"),
                                _metric_row("Total Trades", f"{len(df_trades) if not df_trades.empty else len(df_pnl[df_pnl['position_size'].diff() != 0])}"),
                            ]),
                        ]
                    ),
                ]
            ),
        ]
    )

    return drawdown_fig, sharpe_fig, heatmap_fig, regime_fig, metrics_table


# --- Callback: Risk Management tab ---
@app.callback(
    [Output("risk-yield-surface", "figure"),
     Output("risk-pca-chart", "figure"),
     Output("risk-dv01-chart", "figure"),
     Output("risk-var-es-chart", "figure"),
     Output("risk-exposure-chart", "figure"),
     Output("risk-carry-chart", "figure"),
     Output("risk-correlation-chart", "figure"),
     Output("risk-mgmt-version-label", "children")],
    [Input("main-tabs", "value"),
     Input("version-selector", "value")]
)
def update_risk_management(tab, version):
    # Always update when version changes, even if not on risk tab
    # This ensures data is ready when user switches to the tab
    
    # Load portfolio data for the selected version
    df_pnl, _ = load_data(version)
    
    # Version label
    version_labels = {
        "": "Version 1 (Initial)",
        "v2": "Version 2 (Base Steepener)",
        "v3": "Version 3 (Volatility Scaled)",
        "v4": "Version 4 (Regime Filtered)",
        "v5": "Version 5 (Advanced Dynamic Size)",
        "v6": "Version 6 (PCA Inflation Filter)",
    }
    version_label = f"📊 {version_labels.get(version, version)} — Portfolio-Aware Risk Analysis"
    
    # Market-level charts (always available)
    surface_fig = create_yield_curve_surface_chart()
    pca_fig = create_swap_curve_pca_chart()
    correlation_fig = create_rolling_correlation_chart()
    
    # Portfolio-aware charts (use position data if available)
    if df_pnl.empty or "position_size" not in df_pnl.columns:
        # Fallback to market-level charts if no portfolio data
        dv01_fig = create_dv01_krd_chart()
        var_es_fig = create_var_es_chart()
        carry_fig = create_carry_rolldown_chart()
        exposure_fig = go.Figure()
    else:
        # Use portfolio-aware versions
        dv01_fig = create_portfolio_dv01_chart(df_pnl)
        var_es_fig = create_portfolio_var_es_chart(df_pnl)
        carry_fig = create_portfolio_carry_chart(df_pnl)
        exposure_fig = create_portfolio_exposure_chart(df_pnl)
    
    return (
        surface_fig,
        pca_fig,
        dv01_fig,
        var_es_fig,
        exposure_fig,
        carry_fig,
        correlation_fig,
        version_label,
    )


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)

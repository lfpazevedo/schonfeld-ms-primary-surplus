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
            
        # Calculate cumulative returns assuming total_pnl is simple return
        df_pnl["Cumulative PnL"] = df_pnl["total_pnl"].cumsum()
        df_pnl["Cumulative Curve PnL"] = df_pnl["curve_pnl"].cumsum()
        df_pnl["Cumulative Carry PnL"] = df_pnl["carry_pnl"].cumsum()
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
    
    Plots PC1 for the sample matching steepening spread (since 2012).
    """
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    
    # Load data
    df_ipca = load_ipca_data()
    df_selic = load_selic_forecast_data()
    df_fra = load_market_data()[1]  # Get FRA data for date alignment
    
    if df_ipca.empty or df_selic.empty or df_fra.empty:
        return go.Figure()
    
    # Get start date from steepening spread data (2012)
    start_date = df_fra["date"].min()
    
    # Filter data since 2012
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
                        {"label": "Version 5 (Advanced Dynamic Size)", "value": "v5"},
                        {"label": "Version 4 (Regime Filtered)", "value": "v4"},
                        {"label": "Version 3 (Volatility Scaled)", "value": "v3"},
                        {"label": "Version 2 (Base Steepener)", "value": "v2"},
                        {"label": "Version 1 (Initial)", "value": ""}
                    ],
                    value="v5",
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
        # --- PCA Analysis Section ---
        html.Section(
            className="accent-section",
            style={"padding": "4rem 5%", "backgroundColor": COLORS["white"]},
            children=[
                html.H2("PCA Analysis", style={"textAlign": "center", "marginBottom": "1rem"}),
                html.P(
                    "First Principal Component of IPCA and SELIC expectations (median and std dev)",
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
                                            in macro expectations since 2012.
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
    min_d = df_pnl["date"].min().date()
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

    regime_color = {
        "high_uncertainty": "#e74c3c",
        "medium_uncertainty": COLORS["gold"],
        "low_uncertainty": COLORS["teal"],
    }.get(regime, COLORS["gray"])

    exec_label = {
        "pay_spread": "\ud83d\udcb0  Pay the Spread",
        "collect_carry": "\ud83d\udce5  Collect the Carry",
        "standard": "\ud83d\udcca  Standard",
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
            children=[
                _card("Position", pos_type.replace("_", " ").title()),
                _card("Size", f"{pos_size:+.0%}" if isinstance(pos_size, (int, float)) else str(pos_size)),
                _card("Execution", exec_label),
                _card("Spread", f"{spread:.4f}" if isinstance(spread, (int, float)) else str(spread)),
                _card("Z-Score", f"{z_score:.2f}" if isinstance(z_score, (int, float)) and not pd.isna(z_score) else "N/A"),
            ] + ([_card("P(High Vol)", f"{prob_high:.1%}")] if prob_high is not None and not pd.isna(prob_high) else []),
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


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)

#!/usr/bin/env python3
"""
Real-time news analytics dashboard using Streamlit.
Features live-updating charts and statistics with auto-refresh.
Integrated with analyzer REST API.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import json
import numpy as np
import requests
from typing import Dict, List, Any, Optional

# Page configuration
st.set_page_config(
    page_title="News Analytics Dashboard",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3B82F6;
        transition: transform 0.2s ease-in-out;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .update-time {
        font-size: 0.8rem;
        color: #6B7280;
        text-align: right;
    }
    .live-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        background-color: #10B981;
        border-radius: 50%;
        margin-right: 5px;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    .api-status {
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
    }
    .api-status.healthy {
        background-color: #D1FAE5;
        color: #065F46;
        border: 1px solid #10B981;
    }
    .api-status.degraded {
        background-color: #FEF3C7;
        color: #92400E;
        border: 1px solid #F59E0B;
    }
    .api-status.unavailable {
        background-color: #FEE2E2;
        color: #991B1B;
        border: 1px solid #EF4444;
    }
    .chart-container {
        background-color: white;
        border-radius: 0.5rem;
        padding: 1rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
        margin-bottom: 1rem;
        transition: box-shadow 0.2s ease-in-out;
    }
    .chart-container:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .tab-content {
        padding: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()
if 'stats_data' not in st.session_state:
    st.session_state.stats_data = []
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = True
if 'api_available' not in st.session_state:
    st.session_state.api_available = False
if 'api_base_url' not in st.session_state:
    st.session_state.api_base_url = "http://localhost:8000"
if 'selected_tab' not in st.session_state:
    st.session_state.selected_tab = "overview"
if 'chart_history' not in st.session_state:
    st.session_state.chart_history = {}

# API Client
class AnalyzerAPIClient:
    """Client for analyzer REST API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.timeout = 5  # 5 second timeout
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=2)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "status": "unavailable",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get current metrics from API"""
        try:
            response = self.session.get(f"{self.base_url}/metrics", timeout=3)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None
    
    def get_stats(self) -> Optional[Dict[str, Any]]:
        """Get detailed statistics from API"""
        try:
            response = self.session.get(f"{self.base_url}/stats", timeout=3)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None
    
    def get_sources(self) -> Optional[Dict[str, Any]]:
        """Get source distribution from API"""
        try:
            response = self.session.get(f"{self.base_url}/sources", timeout=3)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None
    
    def get_history(self, hours: int = 24, limit: int = 100) -> Optional[Dict[str, Any]]:
        """Get historical data from API"""
        try:
            params = {"hours": hours, "limit": limit}
            response = self.session.get(f"{self.base_url}/history", params=params, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None
    
    def get_pipeline_status(self) -> Optional[Dict[str, Any]]:
        """Get pipeline status from API"""
        try:
            response = self.session.get(f"{self.base_url}/pipeline", timeout=3)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None

# Initialize API client
@st.cache_resource
def get_api_client():
    return AnalyzerAPIClient(st.session_state.api_base_url)

# Mock data for demonstration (fallback)
def get_mock_stats() -> List[Dict[str, Any]]:
    """Generate mock statistics for demonstration"""
    now = datetime.now()
    hours_ago = [now - timedelta(hours=i) for i in range(24, 0, -1)]
    
    stats = []
    for i, window_start in enumerate(hours_ago):
        window_end = window_start + timedelta(minutes=5)
        stats.append({
            'window_start': window_start,
            'window_end': window_end,
            'total_articles': np.random.randint(50, 200),
            'articles_by_source': {
                'Lenta.ru': np.random.randint(10, 50),
                'Interfax': np.random.randint(5, 30),
                'RIA Novosti': np.random.randint(5, 40),
                'BBC Russian': np.random.randint(2, 20),
            },
            'publishing_rate': np.random.uniform(0.5, 2.0),
            'avg_title_length': np.random.uniform(30, 60),
            'avg_desc_length': np.random.uniform(100, 300),
        })
    
    return stats

def fetch_api_metrics() -> Optional[Dict[str, Any]]:
    """Fetch metrics from analyzer API"""
    client = get_api_client()
    return client.get_metrics()

def fetch_api_stats() -> Optional[Dict[str, Any]]:
    """Fetch detailed statistics from analyzer API"""
    client = get_api_client()
    return client.get_stats()

def fetch_api_sources() -> Optional[Dict[str, Any]]:
    """Fetch source distribution from analyzer API"""
    client = get_api_client()
    return client.get_sources()

# Enhanced chart creation functions
def create_metrics_row(metrics: Dict[str, Any]) -> Dict[str, str]:
    """Create metrics row from API metrics"""
    if not metrics:
        return {}
    
    return {
        'Total Articles': str(metrics.get('total_articles', 0)),
        'Publishing Rate': f"{metrics.get('publishing_rate', 0):.1f}/min",
        'Avg Title Length': f"{metrics.get('avg_title_length', 0):.0f} chars",
        'Sources': str(metrics.get('sources_count', 0)),
    }

def create_source_distribution_chart(sources_data: Dict[str, Any]) -> Optional[go.Figure]:
    """Create enhanced source distribution chart from API data"""
    if not sources_data or 'sources' not in sources_data:
        return None
    
    sources = sources_data['sources']
    if not sources:
        return None
    
    df = pd.DataFrame({
        'Source': list(sources.keys()),
        'Articles': list(sources.values())
    }).sort_values('Articles', ascending=False)
    
    # Create bar chart with enhanced styling
    fig = px.bar(df, x='Source', y='Articles', 
                 title='📊 Articles by Source',
                 color='Articles',
                 color_continuous_scale='Viridis',
                 text='Articles')
    
    fig.update_layout(
        xaxis_title="",
        yaxis_title="Number of Articles",
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=12),
        hovermode='x unified',
        xaxis=dict(tickangle=45)
    )
    
    fig.update_traces(
        texttemplate='%{text}',
        textposition='outside',
        marker_line_color='rgb(8,48,107)',
        marker_line_width=1.5,
        opacity=0.8
    )
    
    return fig

def create_source_pie_chart(sources_data: Dict[str, Any]) -> Optional[go.Figure]:
    """Create pie chart for source distribution"""
    if not sources_data or 'sources' not in sources_data:
        return None
    
    sources = sources_data['sources']
    if not sources:
        return None
    
    df = pd.DataFrame({
        'Source': list(sources.keys()),
        'Articles': list(sources.values())
    }).sort_values('Articles', ascending=False)
    
    # Limit to top 8 sources for readability
    if len(df) > 8:
        other_count = df['Articles'][8:].sum()
        df = df.head(8)
        df = pd.concat([df, pd.DataFrame({'Source': ['Other'], 'Articles': [other_count]})])
    
    fig = px.pie(df, values='Articles', names='Source',
                 title='🥧 Source Distribution',
                 color_discrete_sequence=px.colors.sequential.Viridis)
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=12),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hole=0.3,
        marker=dict(line=dict(color='#FFFFFF', width=2))
    )
    
    return fig

def create_timeline_chart(history_data: Dict[str, Any]) -> Optional[go.Figure]:
    """Create enhanced timeline chart from historical data"""
    if not history_data or 'history' not in history_data:
        return None
    
    history = history_data['history']
    if len(history) < 2:
        return None
    
    # Prepare data
    times = [datetime.fromisoformat(h['window_start'].replace('Z', '+00:00')) for h in history]
    counts = [h['total_articles'] for h in history]
    
    # Calculate moving average
    window_size = min(5, len(counts))
    moving_avg = pd.Series(counts).rolling(window=window_size, center=True).mean().tolist()
    
    fig = go.Figure()
    
    # Add main line
    fig.add_trace(go.Scatter(
        x=times,
        y=counts,
        mode='lines+markers',
        name='Articles',
        line=dict(color='#3B82F6', width=3),
        marker=dict(size=8, color='#3B82F6'),
        hovertemplate='<b>%{x|%H:%M}</b><br>Articles: %{y}<extra></extra>'
    ))
    
    # Add moving average
    if len(moving_avg) > window_size:
        fig.add_trace(go.Scatter(
            x=times[window_size//2:-window_size//2],
            y=moving_avg[window_size//2:-window_size//2],
            mode='lines',
            name=f'{window_size}-window MA',
            line=dict(color='#EF4444', width=2, dash='dash'),
            hovertemplate='<b>%{x|%H:%M}</b><br>MA: %{y:.1f}<extra></extra>'
        ))
    
    fig.update_layout(
        title='📈 Article Volume Over Time',
        xaxis_title="Time",
        yaxis_title="Articles per 5-min Window",
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def create_publishing_rate_chart(history_data: Dict[str, Any]) -> Optional[go.Figure]:
    """Create enhanced publishing rate chart from historical data"""
    if not history_data or 'history' not in history_data:
        return None
    
    history = history_data['history']
    if len(history) < 2:
        return None
    
    times = [datetime.fromisoformat(h['window_start'].replace('Z', '+00:00')) for h in history]
    rates = [h['publishing_rate'] for h in history]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=times,
        y=rates,
        mode='lines',
        name='Publishing Rate',
        line=dict(color='#10B981', width=3),
        fill='tozeroy',
        fillcolor='rgba(16, 185, 129, 0.2)',
        hovertemplate='<b>%{x|%H:%M}</b><br>Rate: %{y:.2f}/min<extra></extra>'
    ))
    
    # Add threshold lines
    avg_rate = np.mean(rates) if rates else 0
    fig.add_hline(y=avg_rate, line_dash="dot", line_color="gray",
                  annotation_text=f"Avg: {avg_rate:.2f}/min",
                  annotation_position="bottom right")
    
    fig.update_layout(
        title='🚀 Publishing Rate (articles/minute)',
        xaxis_title="Time",
        yaxis_title="Articles per Minute",
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=12),
        showlegend=False
    )
    
    return fig

def create_heatmap_chart(history_data: Dict[str, Any]) -> Optional[go.Figure]:
    """Create heatmap of article activity by hour of day"""
    if not history_data or 'history' not in history_data:
        return None
    
    history = history_data['history']
    if len(history) < 24:  # Need at least 24 hours of data
        return None
    
    # Prepare data for heatmap
    data = []
    for h in history:
        dt = datetime.fromisoformat(h['window_start'].replace('Z', '+00:00'))
        hour = dt.hour
        day = dt.strftime('%Y-%m-%d')
        data.append({
            'day': day,
            'hour': hour,
            'articles': h['total_articles']
        })
    
    df = pd.DataFrame(data)
    
    # Pivot for heatmap
    pivot_df = df.pivot_table(index='hour', columns='day', values='articles', aggfunc='sum')
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=[f"{h:02d}:00" for h in pivot_df.index],
        colorscale='Viridis',
        hovertemplate='Day: %{x}<br>Hour: %{y}<br>Articles: %{z}<extra></extra>'
    ))
    
    fig.update_layout(
        title='🔥 Activity Heatmap (Articles by Hour)',
        xaxis_title="Date",
        yaxis_title="Hour of Day",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=12)
    )
    
    return fig

def create_trend_indicators(history_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate trend indicators from historical data"""
    if not history_data or 'history' not in history_data:
        return {}
    
    history = history_data['history']
    if len(history) < 2:
        return {}
    
    # Get recent data
    recent = history[-min(6, len(history)):]  # Last 6 windows (30 minutes)
    older = history[-min(12, len(history)):-6] if len(history) > 6 else []
    
    recent_avg = np.mean([h['total_articles'] for h in recent]) if recent else 0
    older_avg = np.mean([h['total_articles'] for h in older]) if older else recent_avg
    
    # Calculate trends
    if older_avg > 0:
        trend_pct = ((recent_avg - older_avg) / older_avg) * 100
    else:
        trend_pct = 0
    
    # Determine trend direction and color
    if trend_pct > 10:
        trend = "📈 Strong Increase"
        color = "#10B981"
    elif trend_pct > 2:
        trend = "↗️ Moderate Increase"
        color = "#34D399"
    elif trend_pct < -10:
        trend = "📉 Strong Decrease"
        color = "#EF4444"
    elif trend_pct < -2:
        trend = "↘️ Moderate Decrease"
        color = "#F87171"
    else:
        trend = "➡️ Stable"
        color = "#6B7280"
    
    return {
        'trend': trend,
        'trend_pct': abs(trend_pct),
        'color': color,
        'recent_avg': recent_avg,
        'older_avg': older_avg
    }

def get_api_status_class(status: str) -> str:
    """Get CSS class for API status"""
    if status == 'healthy':
        return 'api-status healthy'
    elif status == 'degraded':
        return 'api-status degraded'
    else:
        return 'api-status unavailable'

# Main app
def main():
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<h1 class="main-header">📰 News Analytics Dashboard</h1>', unsafe_allow_html=True)
        st.markdown("Real-time monitoring of news scraping pipeline")
    
    with col2:
        st.markdown(f'<div class="update-time">Last update: {st.session_state.last_update.strftime("%H:%M:%S")}</div>', unsafe_allow_html=True)
        auto_refresh = st.checkbox("Auto-refresh", value=st.session_state.auto_refresh)
        if st.button("🔄 Refresh Now"):
            st.session_state.last_update = datetime.now()
            st.rerun()
    
    # Sidebar
    with st.sidebar:
        st.header("Dashboard Controls")
        
        st.subheader("Data Source")
        data_source = st.radio(
            "Select data source:",
            ["Analyzer API", "Mock Data"],
            index=0
        )
        
        # API Configuration
        if data_source == "Analyzer API":
            st.subheader("API Configuration")
            api_url = st.text_input(
                "API Base URL",
                value=st.session_state.api_base_url,
                help="URL of the analyzer REST API (e.g., http://localhost:8000)"
            )
            
            if api_url != st.session_state.api_base_url:
                st.session_state.api_base_url = api_url
                st.rerun()
            
            # Test connection
            if st.button("Test API Connection"):
                client = get_api_client()
                health = client.health_check()
                status = health.get('status', 'unavailable')
                
                if status == 'healthy':
                    st.success("✅ API is healthy and responding")
                elif status == 'degraded':
                    st.warning("⚠️ API is degraded (pipeline not available)")
                else:
                    st.error("❌ API is unavailable")
                
                if 'error' in health:
                    st.error(f"Error: {health['error']}")
        
        st.subheader("Time Range")
        time_range = st.select_slider(
            "Select time range:",
            options=["1h", "6h", "12h", "24h", "48h"],
            value="24h"
        )
        
        st.subheader("Visualization")
        show_raw_data = st.checkbox("Show raw data", False)
        show_heatmap = st.checkbox("Show activity heatmap", True)
        show_trends = st.checkbox("Show trend indicators", True)
        
        st.divider()
        
        st.markdown("### System Status")
        
        # Check API status
        client = get_api_client()
        health = client.health_check()
        status = health.get('status', 'unavailable')
        
        col1, col2 = st.columns(2)
        with col1:
            if data_source == "Analyzer API":
                status_icon = "✅" if status == 'healthy' else "⚠️" if status == 'degraded' else "❌"
                st.metric("Analyzer API", status.title(), delta=status_icon)
            else:
                st.metric("Data Source", "Mock", delta="Test")
            
            st.metric("Dashboard", "Running", delta="Active")
        
        with col2:
            if data_source == "Analyzer API" and status == 'healthy':
                pipeline_status = client.get_pipeline_status()
                if pipeline_status:
                    st.metric("Pipeline", "Running", delta=f"{pipeline_status.get('total_articles', 0)} articles")
                else:
                    st.metric("Pipeline", "Unknown", delta="N/A")
            else:
                st.metric("Pipeline", "Mock", delta="Simulated")
            
            st.metric("Update Interval", "30s", delta="Auto")
        
        st.divider()
        
        st.markdown("### About")
        st.markdown("""
        This dashboard monitors the news scraping pipeline:
        
        - **Go Scraper**: Collects news from RSS/HTML sources
        - **Kafka/NATS**: Message broker for data streaming
        - **Python Analyzer**: Processes and analyzes articles
        - **REST API**: Provides metrics for this dashboard
        
        Data updates every 30 seconds.
        """)
    
    # Fetch data based on selected source
    metrics = None
    sources_data = None
    history_data = None
    
    if data_source == "Analyzer API":
        # Fetch from API
        metrics = fetch_api_metrics()
        sources_data = fetch_api_sources()
        
        # Convert time range to hours
        hours_map = {"1h": 1, "6h": 6, "12h": 12, "24h": 24, "48h": 48}
        hours = hours_map.get(time_range, 24)
        history_data = get_api_client().get_history(hours=hours, limit=100)
        
        # Update API availability
        st.session_state.api_available = metrics is not None
        
        # Show API status
        status_class = get_api_status_class(status)
        status_text = {
            'healthy': '✅ Analyzer API is healthy',
            'degraded': '⚠️ Analyzer API is degraded (pipeline not available)',
            'unavailable': '❌ Analyzer API is unavailable'
        }.get(status, '❌ Analyzer API is unavailable')
        
        st.markdown(f'<div class="{status_class}">{status_text}</div>', unsafe_allow_html=True)
        
        if not metrics:
            st.warning("Could not fetch metrics from API. Falling back to mock data.")
            stats = get_mock_stats()
            # Convert mock stats to metrics format
            if stats:
                latest = stats[-1]
                metrics = {
                    'total_articles': latest['total_articles'],
                    'publishing_rate': latest['publishing_rate'],
                    'avg_title_length': latest['avg_title_length'],
                    'sources_count': len(latest['articles_by_source']),
                    'articles_per_source': latest['articles_by_source']
                }
    else:
        # Use mock data
        stats = get_mock_stats()
        if stats:
            latest = stats[-1]
            metrics = {
                'total_articles': latest['total_articles'],
                'publishing_rate': latest['publishing_rate'],
                'avg_title_length': latest['avg_title_length'],
                'sources_count': len(latest['articles_by_source']),
                'articles_per_source': latest['articles_by_source']
            }
        
        # Generate mock sources data
        if metrics and 'articles_per_source' in metrics:
            sources_data = {
                'sources': metrics['articles_per_source'],
                'total_sources': metrics['sources_count'],
                'top_source': max(metrics['articles_per_source'].items(), key=lambda x: x[1])[0] if metrics['articles_per_source'] else None
            }
        
        # Generate mock history
        history_data = {
            'history': [
                {
                    'window_start': (datetime.now() - timedelta(minutes=i*5)).isoformat(),
                    'window_end': (datetime.now() - timedelta(minutes=i*5-5)).isoformat(),
                    'total_articles': np.random.randint(10, 100),
                    'publishing_rate': round(np.random.uniform(0.5, 5.0), 2)
                }
                for i in range(1, min(100, hours * 12) + 1)
            ]
        }
    
    # Metrics row with enhanced styling
    st.subheader("📊 Current Metrics")
    
    if metrics:
        metrics_row = create_metrics_row(metrics)
        if metrics_row:
            cols = st.columns(len(metrics_row))
            for col, (key, value) in zip(cols, metrics_row.items()):
                with col:
                    st.markdown(f'<div class="metric-card"><h3>{key}</h3><h2>{value}</h2></div>', unsafe_allow_html=True)
    else:
        st.warning("No metrics available")
    
    # Trend indicators
    if show_trends and history_data:
        trends = create_trend_indicators(history_data)
        if trends:
            st.markdown(f"""
            <div style="background-color:{trends['color']}20; padding:1rem; border-radius:0.5rem; border-left:4px solid {trends['color']}; margin-bottom:1rem;">
                <h4 style="margin:0; color:{trends['color']};">{trends['trend']}</h4>
                <p style="margin:0.5rem 0 0 0; color:#6B7280; font-size:0.9rem;">
                    Recent average: {trends['recent_avg']:.1f} articles/window • 
                    Change: {trends['trend_pct']:.1f}%
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    # Tabbed interface for charts
    tab1, tab2, tab3 = st.tabs(["📈 Overview", "📊 Sources", "🔥 Activity"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            timeline_chart = create_timeline_chart(history_data)
            if timeline_chart:
                st.plotly_chart(timeline_chart, use_container_width=True, config={'displayModeBar': True})
            else:
                st.info("No timeline data available")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            rate_chart = create_publishing_rate_chart(history_data)
            if rate_chart:
                st.plotly_chart(rate_chart, use_container_width=True, config={'displayModeBar': True})
            else:
                st.info("No publishing rate data available")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            source_chart = create_source_distribution_chart(sources_data)
            if source_chart:
                st.plotly_chart(source_chart, use_container_width=True, config={'displayModeBar': True})
            else:
                st.info("No source distribution data available")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            pie_chart = create_source_pie_chart(sources_data)
            if pie_chart:
                st.plotly_chart(pie_chart, use_container_width=True, config={'displayModeBar': True})
            else:
                st.info("No source data available for pie chart")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        if show_heatmap:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            heatmap_chart = create_heatmap_chart(history_data)
            if heatmap_chart:
                st.plotly_chart(heatmap_chart, use_container_width=True, config={'displayModeBar': True})
            else:
                st.info("Not enough data for heatmap (need at least 24 hours of data)")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Heatmap visualization is disabled. Enable it in the sidebar.")
    
    # Raw data table
    if show_raw_data and history_data and 'history' in history_data:
        st.subheader("📋 Raw Statistics Data")
        
        # Convert to DataFrame
        df_data = []
        for stat in history_data['history'][:20]:  # Show last 20 windows
            row = {
                'Window Start': stat['window_start'],
                'Window End': stat.get('window_end', ''),
                'Total Articles': stat['total_articles'],
                'Publishing Rate': f"{stat['publishing_rate']:.2f}/min",
            }
            df_data.append(row)
        
        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, height=300)
    
    # Auto-refresh logic with fragment
    if auto_refresh:
        time_since_update = (datetime.now() - st.session_state.last_update).seconds
        if time_since_update > 30:  # Refresh every 30 seconds
            st.session_state.last_update = datetime.now()
            st.rerun()
        
        # Show refresh countdown
        refresh_in = 30 - time_since_update
        if refresh_in > 0:
            st.sidebar.progress(refresh_in / 30, text=f"🔄 Refreshing in {refresh_in}s")
    
    # Footer
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Data Source:** {data_source}")
    with col2:
        if history_data and 'history' in history_data:
            st.markdown(f"**Windows Displayed:** {len(history_data['history'])}")
        else:
            st.markdown("**Windows Displayed:** 0")
    with col3:
        st.markdown(f"**Last Update:** {st.session_state.last_update.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()
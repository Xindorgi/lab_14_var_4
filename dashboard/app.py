#!/usr/bin/env python3
"""
Real-time news analytics dashboard using Streamlit.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import json
import numpy as np

# Try to import analytics modules
try:
    from analyzer.arrow_client import create_arrow_client
    from analyzer.config import load_config_from_env
    ARROW_AVAILABLE = True
except ImportError:
    ARROW_AVAILABLE = False

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
    }
    .update-time {
        font-size: 0.8rem;
        color: #6B7280;
        text-align: right;
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

# Load configuration
@st.cache_resource
def get_config():
    return load_config_from_env()

@st.cache_resource
def get_arrow_client():
    if ARROW_AVAILABLE:
        config = get_config()
        return create_arrow_client(config)
    return None

# Mock data for demonstration
def get_mock_stats():
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

def fetch_real_stats():
    """Fetch real statistics from Arrow Flight server"""
    client = get_arrow_client()
    if client and client.is_available():
        return client.get_aggregated_stats()
    return get_mock_stats()

def create_metrics_row(stats):
    """Create metrics row from latest statistics"""
    if not stats:
        return {}
    
    latest = stats[-1]
    
    return {
        'Total Articles': latest.get('total_articles', 0),
        'Publishing Rate': f"{latest.get('publishing_rate', 0):.1f}/min",
        'Avg Title Length': f"{latest.get('avg_title_length', 0):.0f} chars",
        'Sources': len(latest.get('articles_by_source', {})),
    }

def create_source_distribution_chart(stats):
    """Create source distribution chart"""
    if not stats:
        return None
    
    latest = stats[-1]
    sources = latest.get('articles_by_source', {})
    
    if not sources:
        return None
    
    df = pd.DataFrame({
        'Source': list(sources.keys()),
        'Articles': list(sources.values())
    }).sort_values('Articles', ascending=False)
    
    fig = px.bar(df, x='Source', y='Articles', 
                 title='Articles by Source',
                 color='Articles',
                 color_continuous_scale='Blues')
    
    fig.update_layout(
        xaxis_title="",
        yaxis_title="Number of Articles",
        showlegend=False
    )
    
    return fig

def create_timeline_chart(stats):
    """Create timeline chart of article counts"""
    if len(stats) < 2:
        return None
    
    # Prepare data
    times = [s['window_start'] for s in stats]
    counts = [s['total_articles'] for s in stats]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=times,
        y=counts,
        mode='lines+markers',
        name='Articles',
        line=dict(color='#3B82F6', width=2),
        marker=dict(size=6)
    ))
    
    fig.update_layout(
        title='Article Volume Over Time',
        xaxis_title="Time",
        yaxis_title="Articles per 5-min Window",
        hovermode='x unified'
    )
    
    return fig

def create_publishing_rate_chart(stats):
    """Create publishing rate chart"""
    if len(stats) < 2:
        return None
    
    times = [s['window_start'] for s in stats]
    rates = [s['publishing_rate'] for s in stats]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=times,
        y=rates,
        mode='lines',
        name='Publishing Rate',
        line=dict(color='#10B981', width=2),
        fill='tozeroy',
        fillcolor='rgba(16, 185, 129, 0.1)'
    ))
    
    fig.update_layout(
        title='Publishing Rate (articles/minute)',
        xaxis_title="Time",
        yaxis_title="Articles per Minute",
        hovermode='x unified'
    )
    
    return fig

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
        if st.button("Refresh Now"):
            st.session_state.last_update = datetime.now()
            st.rerun()
    
    # Sidebar
    with st.sidebar:
        st.header("Dashboard Controls")
        
        st.subheader("Data Source")
        data_source = st.radio(
            "Select data source:",
            ["Mock Data", "Arrow Flight Server"],
            index=0 if not ARROW_AVAILABLE else 1
        )
        
        st.subheader("Time Range")
        time_range = st.select_slider(
            "Select time range:",
            options=["1h", "6h", "12h", "24h", "48h"],
            value="24h"
        )
        
        st.subheader("Visualization")
        show_raw_data = st.checkbox("Show raw data", False)
        
        st.divider()
        
        st.markdown("### System Status")
        
        # Mock status indicators
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Go Scraper", "Running", delta="Active")
            st.metric("Kafka", "Healthy", delta="Online")
        with col2:
            st.metric("Python Analyzer", "Running", delta="Active")
            st.metric("Database", "Connected", delta="Online")
        
        st.divider()
        
        st.markdown("### About")
        st.markdown("""
        This dashboard monitors the news scraping pipeline:
        
        - **Go Scraper**: Collects news from RSS/HTML sources
        - **Kafka/NATS**: Message broker for data streaming
        - **Python Analyzer**: Processes and analyzes articles
        - **Arrow Flight**: High-performance data transfer
        
        Data updates every 30 seconds.
        """)
    
    # Fetch data
    if data_source == "Arrow Flight Server" and ARROW_AVAILABLE:
        stats = fetch_real_stats()
    else:
        stats = get_mock_stats()
    
    # Store in session state
    st.session_state.stats_data = stats
    
    # Metrics row
    st.subheader("Current Metrics")
    
    metrics = create_metrics_row(stats)
    if metrics:
        cols = st.columns(len(metrics))
        for col, (key, value) in zip(cols, metrics.items()):
            with col:
                st.markdown(f'<div class="metric-card"><h3>{key}</h3><h2>{value}</h2></div>', unsafe_allow_html=True)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        source_chart = create_source_distribution_chart(stats)
        if source_chart:
            st.plotly_chart(source_chart, use_container_width=True)
        else:
            st.info("No source distribution data available")
    
    with col2:
        timeline_chart = create_timeline_chart(stats)
        if timeline_chart:
            st.plotly_chart(timeline_chart, use_container_width=True)
        else:
            st.info("No timeline data available")
    
    # Publishing rate chart (full width)
    rate_chart = create_publishing_rate_chart(stats)
    if rate_chart:
        st.plotly_chart(rate_chart, use_container_width=True)
    
    # Raw data table
    if show_raw_data and stats:
        st.subheader("Raw Statistics Data")
        
        # Convert to DataFrame
        df_data = []
        for stat in stats[-10:]:  # Show last 10 windows
            row = {
                'Window Start': stat['window_start'].strftime('%H:%M:%S') if isinstance(stat['window_start'], datetime) else stat['window_start'],
                'Window End': stat['window_end'].strftime('%H:%M:%S') if isinstance(stat['window_end'], datetime) else stat['window_end'],
                'Total Articles': stat['total_articles'],
                'Publishing Rate': f"{stat['publishing_rate']:.2f}/min",
            }
            
            # Add source counts
            for source, count in stat.get('articles_by_source', {}).items():
                row[f'Source: {source}'] = count
            
            df_data.append(row)
        
        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
    
    # Auto-refresh logic
    if auto_refresh:
        time_since_update = (datetime.now() - st.session_state.last_update).seconds
        if time_since_update > 30:  # Refresh every 30 seconds
            st.session_state.last_update = datetime.now()
            st.rerun()
        
        # Show refresh countdown
        refresh_in = 30 - time_since_update
        if refresh_in > 0:
            st.sidebar.progress(refresh_in / 30, text=f"Refreshing in {refresh_in}s")
    
    # Footer
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Data Source:** " + ("Arrow Flight Server" if data_source == "Arrow Flight Server" and ARROW_AVAILABLE else "Mock Data"))
    with col2:
        st.markdown(f"**Windows Displayed:** {len(stats)}")
    with col3:
        st.markdown(f"**Last Update:** {st.session_state.last_update.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()
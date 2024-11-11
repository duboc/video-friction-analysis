import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import List, Dict, Any
from visualizations.analysis_charts import AnalysisVisualizer

def create_analysis_summary_chart(analyses: List[Dict[str, Any]]) -> go.Figure:
    """Create a summary chart showing analysis trends."""
    df = pd.DataFrame(analyses)
    
    # Convert timestamp to datetime if needed
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
    
    # Group by date and status
    daily_stats = df.groupby(['date', 'status']).size().unstack(fill_value=0)
    
    fig = go.Figure()
    
    # Add stacked bars for each status
    for status in ['completed', 'failed', 'processing']:
        if status in daily_stats.columns:
            fig.add_trace(go.Bar(
                name=status.capitalize(),
                x=daily_stats.index,
                y=daily_stats[status],
                hovertemplate="Date: %{x}<br>Count: %{y}<extra></extra>"
            ))
    
    fig.update_layout(
        title='Daily Analysis Summary',
        barmode='stack',
        xaxis_title='Date',
        yaxis_title='Number of Analyses',
        template='plotly_white',
        height=400,
        showlegend=True
    )
    
    return fig

def create_processing_time_chart(analyses: List[Dict[str, Any]]) -> go.Figure:
    """Create a chart showing processing times for completed analyses."""
    df = pd.DataFrame(analyses)
    
    # Calculate processing times for completed analyses
    completed_analyses = df[df['status'] == 'completed'].copy()
    if not completed_analyses.empty and 'timestamp' in completed_analyses.columns:
        completed_analyses['processing_time'] = pd.to_datetime(completed_analyses['updated_at']) - \
                                              pd.to_datetime(completed_analyses['timestamp'])
        completed_analyses['processing_minutes'] = completed_analyses['processing_time'].dt.total_seconds() / 60
        
        fig = go.Figure()
        fig.add_trace(go.Box(
            y=completed_analyses['processing_minutes'],
            name='Processing Time',
            boxpoints='all',
            jitter=0.3,
            pointpos=-1.8
        ))
        
        fig.update_layout(
            title='Analysis Processing Times',
            yaxis_title='Minutes',
            template='plotly_white',
            height=400,
            showlegend=False
        )
        
        return fig
    return None 

def render_analysis_metrics(analyses: List[Dict[str, Any]]):
    """Render key metrics and statistics about analyses."""
    total = len(analyses)
    completed = sum(1 for a in analyses if a.get('status') == 'completed')
    failed = sum(1 for a in analyses if a.get('status') == 'failed')
    processing = total - completed - failed
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Analyses", total)
    with col2:
        st.metric("Completed", completed, f"{(completed/total)*100:.1f}%" if total > 0 else "0%")
    with col3:
        st.metric("Failed", failed, f"{(failed/total)*100:.1f}%" if total > 0 else "0%")
    with col4:
        st.metric("Processing", processing, f"{(processing/total)*100:.1f}%" if total > 0 else "0%")

def create_analysis_timeline(analyses: List[Dict[str, Any]]) -> go.Figure:
    """Create an interactive timeline of video analyses."""
    df = pd.DataFrame(analyses)
    
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    fig = go.Figure()
    
    # Add timeline events
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['video_name'],
        mode='markers+text',
        name='Analyses',
        text=df['status'],
        textposition='top center',
        marker=dict(
            size=15,
            symbol='circle',
            color=['red' if status == 'failed' else 'green' if status == 'completed' else 'yellow' 
                   for status in df['status']],
            line=dict(color='white', width=1)
        )
    ))
    
    fig.update_layout(
        title='Analysis Timeline',
        xaxis_title='Time',
        yaxis_title='Video Name',
        template='plotly_white',
        height=400,
        showlegend=False
    )
    
    return fig

def render_analysis_viewer(collection):
    """Render a viewer for completed analyses."""
    # Get all completed analyses using keyword filter
    analyses = collection.filter(filter=('status', '==', 'completed')).stream()
    analyses_list = [{'id': doc.id, **doc.to_dict()} for doc in analyses]
    
    if not analyses_list:
        st.info("No completed analyses available.")
        return
    
    # Create columns for selection and delete button
    col1, col2 = st.columns([4, 1])
    
    with col1:
        # Create a selectbox for choosing the analysis
        selected_analysis = st.selectbox(
            "Select Analysis",
            options=analyses_list,
            format_func=lambda x: f"{x.get('video_name', 'Unnamed')} - {x.get('timestamp', 'No date')}"
        )
    
    with col2:
        if selected_analysis and st.button("🗑️ Delete", key="delete_analysis"):
            try:
                collection.document(selected_analysis['id']).delete()
                st.success("Analysis deleted successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting analysis: {str(e)}")
    
    if selected_analysis:
        # Create tabs for different analysis types
        analysis_tabs = st.tabs(["Video Analysis", "User Stories", "Task Backlog"])
        
        with analysis_tabs[0]:
            if 'video_analysis' in selected_analysis:
                charts = AnalysisVisualizer.create_video_analysis_charts(selected_analysis['video_analysis'])
                
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(charts['scores_overview'], use_container_width=True)
                with col2:
                    st.plotly_chart(charts['friction_severity'], use_container_width=True)
                
                with st.expander("Executive Summary"):
                    for point in selected_analysis['video_analysis']['executiveSummary']:
                        st.write(f"• {point}")
                
                with st.expander("Friction Log"):
                    for entry in selected_analysis['video_analysis']['frictionLog']:
                        st.markdown(f"""
                        **Time**: `{entry['timestamp']}`  
                        **Task**: {entry['task']}  
                        **Friction Point**: {entry['frictionPoint']}  
                        **Severity**: `{entry['severity']}`  
                        **Recommendation**: {entry['recommendation']}
                        ---
                        """)
            else:
                st.info("No video analysis data available for this entry.")
        
        with analysis_tabs[1]:
            if 'user_story' in selected_analysis:
                charts = AnalysisVisualizer.create_user_story_charts(selected_analysis['user_story'])
                
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(charts['priority_value_matrix'], use_container_width=True)
                with col2:
                    st.plotly_chart(charts['complexity_distribution'], use_container_width=True)
                
                with st.expander("User Stories Details"):
                    for story in selected_analysis['user_story']['userStories']:
                        st.markdown(f"""
                        **User Story**: {story['userStory']}  
                        **Priority**: `{story['priority']}` | **Complexity**: `{story['complexity']}` | **Business Value**: `{story['businessValue']}`  
                        **Pain Point**: {story['painPoint']}
                        
                        *Solution*:  
                        {story['proposedSolution']['description']}
                        
                        *Implementation Steps*:
                        """)
                        for step in story['proposedSolution']['implementation']:
                            st.markdown(f"- {step}")
                        st.markdown("---")
            else:
                st.info("No user story data available for this entry.")
        
        with analysis_tabs[2]:
            if 'task_backlog' in selected_analysis:
                charts = AnalysisVisualizer.create_task_backlog_charts(selected_analysis['task_backlog'])
                
                st.plotly_chart(charts['task_distribution'], use_container_width=True)
                st.plotly_chart(charts['task_timeline'], use_container_width=True)
                
                with st.expander("Task Details"):
                    for story in selected_analysis['task_backlog']['userStoryTasks']:
                        st.markdown(f"### {story['userStoryTitle']}")
                        for task in story['tasks']:
                            st.markdown(f"""
                            **{task['taskID']}**: {task['taskDescription']}  
                            **Effort**: `{task['estimatedEffortHours']}h` | **Priority**: `{task['priority']}` | **Category**: `{task['category']}`  
                            **Completion Criteria**:
                            """)
                            for criteria in task.get('completionCriteria', []):
                                st.markdown(f"- {criteria}")
                            st.markdown("---")
            else:
                st.info("No task backlog data available for this entry.")
# FILE: video_analysis_app.py

import streamlit as st
import logging
from datetime import datetime
import pandas as pd
from pathlib import Path
import time
from typing import Optional, Dict, Any
from google.cloud import firestore
import plotly.graph_objects as go
import networkx as nx

# Import custom services
from config.settings import Settings
from services.storage_service import StorageService
from services.firestore_service import FirestoreService
from services.vertex_service import VertexService
from utils.firestore_viewer import render_analysis_viewer
from utils.visualization import render_analysis_metrics, create_analysis_timeline
from visualizations.analysis_charts import AnalysisVisualizer

# Configure page settings
st.set_page_config(
    page_title="Video Analysis App",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services with caching
@st.cache_resource
def init_services() -> Optional[Dict]:
    """
    Initialize all required services with caching.
    Returns:
        Optional[Dict]: Dictionary containing service instances or None if initialization fails
    """
    try:
        # Validate settings before initializing services
        missing_settings = Settings.validate_settings()
        if missing_settings:
            st.error(f"Missing required settings: {', '.join(missing_settings)}")
            return None

        return {
            'storage': StorageService(),
            'firestore': FirestoreService(),
            'vertex': VertexService()
        }
    except Exception as e:
        logger.error(f"Error initializing services: {str(e)}")
        st.error(f"Failed to initialize services: {str(e)}")
        return None

class VideoAnalysisApp:
    def __init__(self):
        """Initialize the Video Analysis App."""
        self.services = init_services()
        if not self.services:
            st.stop()

        # Set up session state for tracking video processing
        if 'processing_videos' not in st.session_state:
            st.session_state.processing_videos = set()

    def render_sidebar(self):
        """Render the sidebar with app information and settings."""
        with st.sidebar:
            st.title("🎥 Video Analysis")
            st.markdown("---")
            
            # Display app information
            st.subheader("About")
            st.markdown("""
                This app allows you to:
                - Upload videos for analysis
                - Track processing status
                - View analysis results
                - Manage uploaded videos
            """)
            
            # Display current settings
            st.subheader("Settings")
            st.markdown(f"""
                - Max file size: {Settings.MAX_FILE_SIZE // (1024*1024)}MB
                - Allowed formats: {', '.join(Settings.ALLOWED_EXTENSIONS)}
                - Current region: {Settings.DEFAULT_REGION}
            """)
            
            # Display service status
            st.subheader("Service Status")
            model_status = self.services['vertex'].get_model_status()
            st.json(model_status)

    def upload_section(self):
        """Render the video upload section."""
        st.header("Upload Video")
        
        # Load and display the default prompt
        try:
            with open('prompts/video_analysis_prompt.md', 'r') as f:
                default_prompt = f.read()
        except Exception as e:
            default_prompt = "Error loading default prompt"
            st.error(f"Error loading default prompt: {str(e)}")

        # Add customizable prompt text area
        custom_prompt = st.text_area(
            "Customize Analysis Prompt (Optional)",
            value=default_prompt,
            height=200,
            help="Modify the analysis prompt to customize the video analysis process"
        )
        
        uploaded_file = st.file_uploader(
            "Choose a video file",
            type=Settings.ALLOWED_EXTENSIONS,
            help=f"Maximum file size: {Settings.MAX_FILE_SIZE // (1024*1024)}MB"
        )
        
        if uploaded_file:
            if st.button("Process Video"):
                with st.spinner("Uploading and processing video..."):
                    try:
                        # Upload video to storage
                        success, url, error = self.services['storage'].upload_video(uploaded_file)
                        
                        if not success or not url:
                            st.error(f"Upload failed: {error}")
                            return

                        # Create initial document in Firestore
                        doc_data = {
                            'video_name': uploaded_file.name,
                            'video_url': url,
                            'status': 'processing',
                            'timestamp': firestore.SERVER_TIMESTAMP,
                            'custom_prompt': custom_prompt != default_prompt
                        }
                        self.services['firestore'].collection.document(uploaded_file.name).set(doc_data)
                        
                        # Update processing status
                        st.session_state.processing_videos.add(uploaded_file.name)
                        
                        # Perform sequential analysis with better error handling
                        analyses_results = {}
                        
                        # Video Analysis with custom prompt
                        prompt_to_use = custom_prompt if custom_prompt != default_prompt else None
                        success, video_analysis, error = self.services['vertex'].analyze_video(
                            url,
                            prompt_to_use
                        )
                        if not success:
                            self._handle_analysis_error("Video analysis", error, uploaded_file.name)
                            return
                        analyses_results['video_analysis'] = video_analysis
                        
                        # User Story Generation
                        success, user_story, error = self.services['vertex'].generate_user_story(video_analysis)
                        if not success:
                            self._handle_analysis_error("User story generation", error, uploaded_file.name)
                            return
                        analyses_results['user_story'] = user_story
                        
                        # Task Backlog Generation
                        success, task_backlog, error = self.services['vertex'].generate_task_backlog(user_story)
                        if not success:
                            self._handle_analysis_error("Task backlog generation", error, uploaded_file.name)
                            return
                        analyses_results['task_backlog'] = task_backlog
                        
                        # Modify how analyses results are saved
                        analyses_results = {
                            'status': 'completed',
                            'timestamp': firestore.SERVER_TIMESTAMP,
                            'analyses_results': {
                                'video_analysis': video_analysis,
                                'user_story': user_story,
                                'task_backlog': task_backlog
                            }
                        }
                        
                        success, error = self.services['firestore'].save_analysis(
                            uploaded_file.name,
                            analyses_results,
                            url
                        )
                        
                        if success:
                            st.success("All analyses completed successfully!")
                            st.session_state.processing_videos.remove(uploaded_file.name)
                        else:
                            st.error(f"Error saving analysis results: {error}")
                    
                    except Exception as e:
                        logger.error(f"Error processing video: {str(e)}")
                        self._handle_analysis_error("Processing", str(e), uploaded_file.name)

    def _handle_analysis_error(self, stage: str, error: str, video_name: str):
        """Helper method to handle analysis errors."""
        logger.error(f"{stage} failed: {error}")
        
        try:
            # Get the video URL
            success, url, _ = self.services['storage'].get_video_url(video_name)
            video_url = url if success else None
            
            # Create or update document with failed status and more detailed error info
            doc_data = {
                'video_name': video_name,
                'video_url': video_url,
                'status': 'failed',
                'error': {
                    'stage': stage,
                    'message': str(error),
                    'timestamp': firestore.SERVER_TIMESTAMP
                },
                'timestamp': firestore.SERVER_TIMESTAMP
            }
            
            # Use set with merge=True to create or update
            self.services['firestore'].collection.document(video_name).set(
                doc_data, 
                merge=True
            )
            
        except Exception as e:
            logger.error(f"Error handling analysis failure: {str(e)}")
        
        # Update UI state and show error
        if video_name in st.session_state.processing_videos:
            st.session_state.processing_videos.remove(video_name)
        st.error(f"{stage} failed: {error}")
        
        # Add retry button
        if st.button("Retry Analysis"):
            self._rerun_analysis(video_name)

    def video_list_section(self):
        """Render the video list section."""
        st.header("Uploaded Videos")
        
        try:
            videos = self.services['storage'].list_videos()
            if not videos:
                st.info("No videos uploaded yet. Use the Upload tab to get started.")
                return
                
            # Create a clean table view of videos with status indicators
            video_data = []
            for video in videos:
                metadata = self.services['storage'].get_video_metadata(video['name'])
                if metadata:
                    # Get analysis status from Firestore
                    analysis_doc = self.services['firestore'].collection.document(video['name']).get()
                    status = 'Failed' if analysis_doc.exists and analysis_doc.to_dict().get('status') == 'failed' else \
                            'Processing' if video['name'] in st.session_state.processing_videos else 'Ready'
                    status_color = '🔴' if status == 'Failed' else '🟡' if status == 'Processing' else '🟢'
                    
                    # Add error message if failed
                    error_msg = ''
                    if status == 'Failed':
                        error_data = analysis_doc.to_dict().get('error', {})
                        error_msg = f"\n❌ {error_data.get('stage', 'Error')}: {error_data.get('message', 'Unknown error')}"
                    
                    video_data.append({
                        'Status': f"{status_color} {status}{error_msg}",
                        'Video Name': metadata['name'],
                        'Size': metadata['size'],
                        'Upload Date': datetime.fromtimestamp(
                            float(metadata['uploaded_at'])
                        ).strftime('%Y-%m-%d %H:%M:%S'),
                        'Type': metadata['content_type']
                    })
            
            # Display videos in a styled dataframe
            df = pd.DataFrame(video_data)
            
            # Custom CSS for the dataframe
            st.markdown("""
            <style>
            .stDataFrame {
                border-radius: 10px;
                border: 1px solid #e6e6e6;
                padding: 1rem;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Status": st.column_config.TextColumn(
                        "Status",
                        help="Current status of the video",
                        width="small",
                    ),
                    "Video Name": st.column_config.TextColumn(
                        "Video Name",
                        help="Name of the uploaded video",
                        width="medium",
                    ),
                    "Size": st.column_config.TextColumn(
                        "Size",
                        help="Size of the video file",
                        width="small",
                    ),
                    "Upload Date": st.column_config.DatetimeColumn(
                        "Upload Date",
                        help="When the video was uploaded",
                        format="D MMM YYYY, HH:mm",
                        width="medium",
                    ),
                    "Type": st.column_config.TextColumn(
                        "Type",
                        help="Video file format",
                        width="small",
                    )
                }
            )
            
            # Video selection and actions
            selected_video = st.selectbox(
                "Select a video to manage:",
                [video['Video Name'] for video in video_data]
            )
            
            if selected_video:
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Rerun Analysis"):
                        self._rerun_analysis(selected_video)
                
                with col2:
                    # Initialize deletion state if not exists
                    if 'delete_confirmation' not in st.session_state:
                        st.session_state.delete_confirmation = False
                    
                    # Delete video button with confirmation
                    if not st.session_state.delete_confirmation:
                        if st.button("Delete Video", type="secondary"):
                            st.session_state.delete_confirmation = True
                            st.rerun()
                    else:
                        st.warning(f"Are you sure you want to delete {selected_video}?")
                        col_yes, col_no = st.columns(2)
                        
                        with col_yes:
                            if st.button("Yes, Delete"):
                                # Delete from storage and firestore
                                storage_success, storage_error = self.services['storage'].delete_video(selected_video)
                                firestore_success, firestore_error = self.services['firestore'].delete_analysis(selected_video)
                                
                                if storage_success and firestore_success:
                                    st.session_state.delete_confirmation = False
                                    st.success("Video and analysis deleted successfully!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Error deleting video or analysis")
                        
                        with col_no:
                            if st.button("Cancel"):
                                st.session_state.delete_confirmation = False
                                st.rerun()

        except Exception as e:
            logger.error(f"Error in video list section: {str(e)}")
            st.error(f"Error loading video list: {str(e)}")

    def _rerun_analysis(self, video_name: str):
        """Helper method to rerun analysis for a video."""
        with st.spinner("Rerunning analysis..."):
            try:
                # Get video URL
                success, url, error = self.services['storage'].get_video_url(video_name)
                if not success:
                    st.error(f"Failed to get video URL: {error}")
                    return

                # Update processing status
                st.session_state.processing_videos.add(video_name)
                
                # Perform sequential analysis
                analyses_results = {}
                
                # Video Analysis (no custom prompt for rerun)
                success, video_analysis, error = self.services['vertex'].analyze_video(url)
                if not success:
                    self._handle_analysis_error("Video analysis", error, video_name)
                    return
                analyses_results['video_analysis'] = video_analysis
                
                # User Story Generation
                success, user_story, error = self.services['vertex'].generate_user_story(video_analysis)
                if not success:
                    self._handle_analysis_error("User story generation", error, video_name)
                    return
                analyses_results['user_story'] = user_story
                
                # Task Backlog Generation
                success, task_backlog, error = self.services['vertex'].generate_task_backlog(user_story)
                if not success:
                    self._handle_analysis_error("Task backlog generation", error, video_name)
                    return
                analyses_results['task_backlog'] = task_backlog
                
                # Save analysis results
                success, error = self.services['firestore'].save_analysis(
                    video_name,
                    analyses_results,
                    url
                )
                
                if success:
                    st.session_state.processing_videos.remove(video_name)
                    st.success("Analysis rerun completed successfully!")
                    st.rerun()
                else:
                    st.error(f"Error saving analysis results: {error}")
            
            except Exception as e:
                logger.error(f"Error rerunning analysis: {str(e)}")
                self._handle_analysis_error("Analysis rerun", str(e), video_name)

    def display_results(self, analyses_results: Dict[str, Any]):
        """Display analysis results."""
        st.header("Analysis Results")
        
        # Get completed analyses from Firestore
        analyses = self.services['firestore'].get_all_analyses()
        
        # Add debug logging
        logger.info(f"Retrieved analyses: {analyses}")
        
        if not analyses:
            st.info("No completed analyses available.")
            return
        
        # Create a selectbox for choosing the analysis
        selected_analysis = st.selectbox(
            "Select Analysis",
            options=analyses,
            format_func=lambda x: f"{x.get('video_name', 'Unnamed')} - {x.get('timestamp', 'No date')}"
        )
        
        if selected_analysis:
            # Add debug logging
            logger.info(f"Selected analysis: {selected_analysis}")
            
            # Create tabs for different analysis types
            analysis_tabs = st.tabs(["Video Analysis", "User Stories", "Task Backlog"])
            
            analyses_results = selected_analysis.get('analyses_results', {})
            
            with analysis_tabs[0]:
                video_analysis = analyses_results.get('video_analysis')
                if video_analysis:
                    st.json(video_analysis)
                else:
                    st.info("No video analysis data available.")
            
            with analysis_tabs[1]:
                user_story = analyses_results.get('user_story')
                if user_story:
                    st.json(user_story)
                else:
                    st.info("No user story data available.")
            
            with analysis_tabs[2]:
                task_backlog = analyses_results.get('task_backlog')
                if task_backlog:
                    st.json(task_backlog)
                else:
                    st.info("No task backlog data available.")

    def visualization_section(self):
        """Render the enhanced visualization section."""
        st.header("Analysis Insights")
        
        try:
            # Get analyses from Firestore
            analyses = self.services['firestore'].get_all_analyses()
            
            if not analyses:
                st.info("No analysis data available yet.")
                return
            
            # Create tabs for different visualizations
            viz_tabs = st.tabs(["Overview", "Detailed Analysis"])
            
            with viz_tabs[0]:
                self._render_overview_visualizations(analyses)
                
            with viz_tabs[1]:
                self._render_detailed_visualizations(analyses)
                
        except Exception as e:
            logger.error(f"Error in visualization section: {str(e)}")
            st.error("Error loading visualization. Please try again later.")

    def _render_overview_visualizations(self, analyses):
        """Render overview visualizations."""
        # Create a 2x2 grid for key metrics
        col1, col2 = st.columns(2)
        
        with col1:
            # Severity Distribution
            severity_data = self._get_severity_distribution(analyses)
            fig = go.Figure(data=[
                go.Pie(labels=list(severity_data.keys()), 
                      values=list(severity_data.values()),
                      hole=.3)
            ])
            fig.update_layout(title="Friction Points by Severity")
            st.plotly_chart(fig, use_container_width=True)
            
            # Task Flow Metrics
            task_metrics = self._get_task_flow_metrics(analyses)
            fig = go.Figure(data=[
                go.Bar(x=list(task_metrics.keys()),
                      y=list(task_metrics.values()))
            ])
            fig.update_layout(title="Task Flow Metrics")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Overall Scores
            scores = self._get_overall_scores(analyses)
            fig = go.Figure(data=[
                go.Indicator(
                    mode="gauge+number",
                    value=sum(scores)/len(scores) if scores else 0,
                    title={'text': "Average Overall Score"},
                    gauge={'axis': {'range': [0, 5]},
                           'steps': [
                               {'range': [0, 2], 'color': "lightgray"},
                               {'range': [2, 3.5], 'color': "gray"},
                               {'range': [3.5, 5], 'color': "darkgray"}
                           ]})
            ])
            st.plotly_chart(fig, use_container_width=True)
            
            # Priority Distribution
            priority_data = self._get_priority_distribution(analyses)
            fig = go.Figure(data=[
                go.Bar(x=list(priority_data.keys()),
                      y=list(priority_data.values()),
                      marker_color=['red', 'orange', 'yellow'])
            ])
            fig.update_layout(title="Issues by Priority")
            st.plotly_chart(fig, use_container_width=True)

    def _render_detailed_visualizations(self, analyses):
        """Render detailed analysis visualizations."""
        # Create subtabs for different types of detailed analysis
        detail_tabs = st.tabs(["Friction Analysis", "Task Analysis", "Dependencies"])
        
        # Select analysis to visualize
        selected_analysis = st.selectbox(
            "Select Analysis to Visualize",
            options=analyses,
            format_func=lambda x: f"{x.get('video_name', 'Unnamed')} - {x.get('timestamp', 'No date')}"
        )
        
        if selected_analysis:
            with detail_tabs[0]:
                self._render_friction_analysis(selected_analysis)
            
            with detail_tabs[1]:
                self._render_task_analysis(selected_analysis)
                
            with detail_tabs[2]:
                self._render_dependency_analysis(selected_analysis)

    def _render_friction_analysis(self, analysis):
        """Render friction point analysis visualizations."""
        analysis_data = analysis.get('analyses_results', {}).get('video_analysis', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Timeline of Friction Points
            friction_log = analysis_data.get('frictionLog', [])
            if friction_log:
                fig = go.Figure()
                
                for point in friction_log:
                    fig.add_trace(go.Scatter(
                        x=[point.get('timestamp')],
                        y=[point.get('severity')],
                        mode='markers+text',
                        name=point.get('frictionPoint'),
                        text=point.get('frictionPoint'),
                        marker=dict(
                            size=15,
                            color={'High': 'red', 'Medium': 'orange', 'Low': 'yellow'}[point.get('severity', 'Low')]
                        )
                    ))
                
                fig.update_layout(
                    title="Timeline of Friction Points",
                    xaxis_title="Time in Video",
                    yaxis_title="Severity"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Analysis Radar Chart
            analysis_metrics = analysis_data.get('analysis', {})
            if analysis_metrics:
                self._render_radar_chart(analysis_metrics)

    def _render_task_analysis(self, analysis):
        """Render task analysis visualizations."""
        task_data = analysis.get('analyses_results', {}).get('task_backlog', {}).get('userStoryTasks', [])
        
        if not task_data:
            st.info("No task data available for this analysis.")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Effort by Category
            tasks = task_data[0].get('tasks', [])
            category_effort = {}
            for task in tasks:
                category = task.get('category', 'Unknown')
                effort = task.get('estimatedEffortHours', 0)
                category_effort[category] = category_effort.get(category, 0) + effort
            
            fig = go.Figure(data=[
                go.Bar(
                    x=list(category_effort.keys()),
                    y=list(category_effort.values()),
                    text=list(category_effort.values()),
                    textposition='auto',
                )
            ])
            fig.update_layout(
                title="Estimated Effort by Category (Hours)",
                xaxis_title="Category",
                yaxis_title="Hours"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Priority Distribution
            priority_count = {'High': 0, 'Medium': 0, 'Low': 0}
            for task in tasks:
                priority = task.get('priority', 'Unknown')
                if priority in priority_count:
                    priority_count[priority] += 1
            
            fig = go.Figure(data=[
                go.Pie(
                    labels=list(priority_count.keys()),
                    values=list(priority_count.values()),
                    hole=.3
                )
            ])
            fig.update_layout(title="Task Priority Distribution")
            st.plotly_chart(fig, use_container_width=True)
        
        # Task Timeline
        tasks_df = []
        for task in tasks:
            tasks_df.append({
                'Task': task.get('taskID'),
                'Category': task.get('category'),
                'Effort': task.get('estimatedEffortHours'),
                'Priority': task.get('priority')
            })
        
        fig = go.Figure()
        
        categories = list(set(task['Category'] for task in tasks_df))
        for i, category in enumerate(categories):
            category_tasks = [task for task in tasks_df if task['Category'] == category]
            
            fig.add_trace(go.Bar(
                name=category,
                y=[task['Task'] for task in category_tasks],
                x=[task['Effort'] for task in category_tasks],
                orientation='h',
                marker=dict(
                    color=['red' if task['Priority'] == 'High' else 'orange' if task['Priority'] == 'Medium' else 'yellow' 
                           for task in category_tasks]
                )
            ))
        
        fig.update_layout(
            title="Task Timeline by Category",
            barmode='stack',
            yaxis={'categoryorder':'total ascending'},
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

    def _render_dependency_analysis(self, analysis):
        """Render dependency analysis visualizations."""
        task_data = analysis.get('analyses_results', {}).get('task_backlog', {}).get('userStoryTasks', [])
        
        if not task_data:
            st.info("No dependency data available for this analysis.")
            return
        
        tasks = task_data[0].get('tasks', [])
        
        # Create nodes and edges for dependency graph
        nodes = []
        edges = []
        
        for task in tasks:
            nodes.append(task.get('taskID'))
            for dep in task.get('dependencies', []):
                edges.append((dep, task.get('taskID')))
        
        # Create networkx graph visualization using plotly
        import networkx as nx
        G = nx.DiGraph()
        G.add_nodes_from(nodes)
        G.add_edges_from(edges)
        
        pos = nx.spring_layout(G)
        
        edge_trace = go.Scatter(
            x=[], y=[],
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines')
        
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_trace['x'] += tuple([x0, x1, None])
            edge_trace['y'] += tuple([y0, y1, None])
        
        node_trace = go.Scatter(
            x=[], y=[],
            text=[],
            mode='markers+text',
            textposition="top center",
            hoverinfo='text',
            marker=dict(
                showscale=True,
                colorscale='YlOrRd',
                size=10,
            ))
        
        for node in G.nodes():
            x, y = pos[node]
            node_trace['x'] += tuple([x])
            node_trace['y'] += tuple([y])
            node_trace['text'] += tuple([node])
        
        fig = go.Figure(data=[edge_trace, node_trace],
                       layout=go.Layout(
                           title='Task Dependencies',
                           showlegend=False,
                           hovermode='closest',
                           margin=dict(b=20,l=5,r=5,t=40),
                           xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                           yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                       )
        
        st.plotly_chart(fig, use_container_width=True)

    def _render_radar_chart(self, metrics):
        """Helper method to render radar chart."""
        categories = []
        values = []
        
        for category, metric_data in metrics.items():
            for metric, value in metric_data.items():
                if isinstance(value, (int, float)):
                    categories.append(f"{category}-{metric}")
                    values.append(value)
        
        fig = go.Figure(data=go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 5]
                )),
            showlegend=False,
            title="Analysis Metrics Radar"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Helper methods for data processing
    def _get_severity_distribution(self, analyses):
        severity_counts = {'High': 0, 'Medium': 0, 'Low': 0}
        for analysis in analyses:
            friction_log = analysis.get('analyses_results', {}).get('video_analysis', {}).get('frictionLog', [])
            for point in friction_log:
                severity = point.get('severity')
                if severity in severity_counts:
                    severity_counts[severity] += 1
        return severity_counts

    def _get_task_flow_metrics(self, analyses):
        metrics = {'Efficiency': 0, 'Clarity': 0}
        count = 0
        for analysis in analyses:
            task_flow = analysis.get('analyses_results', {}).get('video_analysis', {}).get('analysis', {}).get('taskFlow', {})
            if task_flow:
                metrics['Efficiency'] += task_flow.get('efficiency', 0)
                metrics['Clarity'] += task_flow.get('clarity', 0)
                count += 1
        
        if count:
            metrics = {k: v/count for k, v in metrics.items()}
        return metrics

    def _get_overall_scores(self, analyses):
        scores = []
        for analysis in analyses:
            conclusion = analysis.get('analyses_results', {}).get('video_analysis', {}).get('conclusion', {})
            score = conclusion.get('overallScore')
            if score:
                scores.append(score)
        return scores

    def _get_priority_distribution(self, analyses):
        priority_counts = {'High': 0, 'Medium': 0, 'Low': 0}
        for analysis in analyses:
            recommendations = analysis.get('analyses_results', {}).get('video_analysis', {}).get('recommendations', [])
            for rec in recommendations:
                priority = rec.get('priority')
                if priority in priority_counts:
                    priority_counts[priority] += 1
        return priority_counts

    def prompts_section(self):
        """Render the prompts section showing all analysis prompts."""
        st.header("Analysis Prompts")
        
        # Create tabs for different prompt types
        prompt_tabs = st.tabs(["Video Analysis", "User Story", "Task Backlog"])
        
        try:
            # Video Analysis Prompt
            with prompt_tabs[0]:
                with open('prompts/video_analysis_prompt.md', 'r') as f:
                    video_prompt = f.read()
                st.markdown("### Video Analysis Prompt")
                st.text_area("Prompt Template", video_prompt, height=400)
                st.markdown("This prompt is used to analyze the uploaded video and generate initial observations.")
            
            # User Story Prompt
            with prompt_tabs[1]:
                with open('prompts/user_story.md', 'r') as f:
                    story_prompt = f.read()
                st.markdown("### User Story Generation Prompt")
                st.text_area("Prompt Template", story_prompt, height=400)
                st.markdown("This prompt converts video analysis into structured user stories.")
            
            # Task Backlog Prompt
            with prompt_tabs[2]:
                with open('prompts/task_backlog.md', 'r') as f:
                    backlog_prompt = f.read()
                st.markdown("### Task Backlog Generation Prompt")
                st.text_area("Prompt Template", backlog_prompt, height=400)
                st.markdown("This prompt transforms user stories into detailed task backlogs.")
                
            # Add information about prompt customization
            with st.expander("About Prompts"):
                st.markdown("""
                ### Understanding the Prompts
                
                These prompts are used in sequence to analyze videos and generate actionable insights:
                
                1. **Video Analysis**: Analyzes user interactions and identifies friction points
                2. **User Story Generation**: Converts friction points into structured user stories
                3. **Task Backlog Creation**: Transforms user stories into detailed development tasks
                
                ### Customizing Prompts
                
                To customize these prompts:
                
                1. Edit the corresponding files in the `prompts/` directory
                2. Ensure the prompt structure maintains the expected output format
                3. Restart the application to apply changes
                
                > Note: Prompt modifications may affect the quality and structure of the analysis results.
                """)
                
        except Exception as e:
            st.error(f"Error loading prompts: {str(e)}")

    def run(self):
        """Run the Streamlit application."""
        self.render_sidebar()
        
        # Main content area
        st.title("Video Analysis Dashboard")
        
        # Create tabs for different sections
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Upload", "Videos", "Results", "Visualization", "Prompts"])
        
        with tab1:
            self.upload_section()
        
        with tab2:
            self.video_list_section()
        
        with tab3:
            self.display_results(self.services['firestore'].get_all_analyses())
            
        with tab4:
            self.visualization_section()
            
        with tab5:
            self.prompts_section()

if __name__ == "__main__":
    app = VideoAnalysisApp()
    app.run()
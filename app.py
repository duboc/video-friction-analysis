import streamlit as st
import logging
from datetime import datetime
import pandas as pd
from pathlib import Path
import time
from typing import Optional, Dict
from google.cloud import firestore

# Import custom services
from config.settings import Settings
from services.storage_service import StorageService
from services.firestore_service import FirestoreService
from services.vertex_service import VertexService
from utils.firestore_viewer import render_analysis_viewer


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
                            'timestamp': firestore.SERVER_TIMESTAMP
                        }
                        self.services['firestore'].collection.document(uploaded_file.name).set(doc_data)
                        
                        # Update processing status
                        st.session_state.processing_videos.add(uploaded_file.name)
                        
                        # Perform sequential analysis with better error handling
                        analyses_results = {}
                        
                        # Video Analysis
                        success, video_analysis, error = self.services['vertex'].analyze_video(url)
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
                        
                        # Save all analyses results
                        analyses_results['status'] = 'completed'
                        analyses_results['timestamp'] = firestore.SERVER_TIMESTAMP
                        
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
        self.services['firestore'].update_analysis_status(video_name, 'failed')
        st.session_state.processing_videos.remove(video_name)
        st.error(f"{stage} failed: {error}")

    def video_list_section(self):
        """Render the video list and management section."""
        st.header("Uploaded Videos")
        
        try:
            # Get list of videos
            videos = self.services['storage'].list_videos()
            if not videos:
                st.info("No videos uploaded yet.")
                return

            # Create DataFrame for better display
            df = pd.DataFrame(videos)
            
            # Ensure required columns exist
            if 'name' not in df.columns:
                logger.error("Video list missing 'name' column")
                st.error("Invalid video data format")
                return
                
            # Add status column
            df['Status'] = df['name'].apply(
                lambda x: 'Processing' if x in st.session_state.processing_videos else 'Completed'
            )
            
            # Display table with videos
            display_columns = ['name']
            if 'size' in df.columns:
                display_columns.append('size')
            if 'uploaded_at' in df.columns:
                display_columns.append('uploaded_at')
            display_columns.append('Status')
            
            st.dataframe(
                df[display_columns],
                use_container_width=True,
                hide_index=True
            )
            
            # Video selection for management
            selected_video = st.selectbox("Select a video to manage:", df['name'].tolist())
            
            if selected_video:
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    if st.button("View Analysis"):
                        analysis = self.services['firestore'].get_analysis(selected_video)
                        if analysis and 'analysis_result' in analysis:
                            st.write("Analysis Results:")
                            st.json(analysis['analysis_result'])
                        else:
                            st.info("No analysis available for this video.")
                
                with col2:
                    success, video_url, error = self.services['storage'].get_video_url(selected_video)
                    if success and video_url:
                        if st.button("Watch Video"):
                            st.video(video_url)
                    elif error:
                        st.error(f"Could not load video: {error}")

                with col3:
                    if st.button("Rerun Analysis"):
                        self._rerun_analysis(selected_video)

                with col4:
                    if st.button("Delete Analysis", type="secondary"):
                        success, error = self.services['firestore'].delete_analysis(selected_video)
                        if success:
                            st.success("Analysis deleted successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Error deleting analysis: {error}")

                with col5:
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
                                # Delete from storage
                                storage_success, storage_error = self.services['storage'].delete_video(selected_video)
                                # Delete from firestore
                                firestore_success, firestore_error = self.services['firestore'].delete_analysis(selected_video)
                                
                                if storage_success and firestore_success:
                                    st.session_state.delete_confirmation = False
                                    st.success("Video and analysis deleted successfully!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    error_msg = storage_error or firestore_error
                                    st.error(f"Error deleting video: {error_msg}")
                        
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
                
                # Video Analysis
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

    def analysis_results_section(self):
        """Render the analysis results section."""
        st.header("Analysis Results")
        
        try:
            analyses = self.services['firestore'].get_all_analyses()
            
            for analysis in analyses:
                with st.expander(f"Analysis for {analysis.get('video_name', 'Unknown')}"):
                    analysis_tabs = st.tabs(["Video Analysis", "User Story", "Task Backlog"])
                    
                    analysis_result = analysis.get('analysis_result', {})
                    
                    with analysis_tabs[0]:
                        video_analysis = analysis_result.get('video_analysis', {})
                        if video_analysis:
                            st.json(video_analysis)
                        else:
                            st.info("No video analysis available")
                    
                    with analysis_tabs[1]:
                        user_story = analysis_result.get('user_story', {})
                        if user_story:
                            st.json(user_story)
                        else:
                            st.info("No user story available")
                    
                    with analysis_tabs[2]:
                        task_backlog = analysis_result.get('task_backlog', {})
                        if task_backlog:
                            st.json(task_backlog)
                        else:
                            st.info("No task backlog available")
                    
                    st.text(f"Status: {analysis.get('status', 'Unknown')}")
                    st.text(f"Analyzed at: {analysis.get('timestamp', 'Unknown')}")
        
        except Exception as e:
            logger.error(f"Error in analysis results section: {str(e)}")
            st.error("Error loading analysis results. Please try again later.")

    def visualization_section(self):
        """Render the visualization section."""
        render_analysis_viewer(self.services['firestore'].collection)

    def run(self):
        """Run the Streamlit application."""
        self.render_sidebar()
        
        # Main content area
        st.title("Video Analysis Dashboard")
        
        # Create tabs for different sections
        tab1, tab2, tab3, tab4 = st.tabs(["Upload", "Videos", "Results", "Visualization"])
        
        with tab1:
            self.upload_section()
        
        with tab2:
            self.video_list_section()
        
        with tab3:
            self.analysis_results_section()
            
        with tab4:
            self.visualization_section()

if __name__ == "__main__":
    app = VideoAnalysisApp()
    app.run()
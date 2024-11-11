from typing import Dict, Any
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

class AnalysisVisualizer:
    @staticmethod
    def create_video_analysis_charts(analysis_data: Dict[str, Any]) -> Dict[str, go.Figure]:
        """Create charts for video analysis data."""
        charts = {}
        
        # Scores Overview Chart
        scores = {
            'Task Flow Efficiency': analysis_data['analysis']['taskFlow']['efficiency'],
            'Task Flow Clarity': analysis_data['analysis']['taskFlow']['clarity'],
            'Usability': analysis_data['analysis']['interactionDesign']['usability'],
            'Responsiveness': analysis_data['analysis']['interactionDesign']['responsiveness'],
            'Findability': analysis_data['analysis']['informationArchitecture']['findability'],
            'Organization': analysis_data['analysis']['informationArchitecture']['organization'],
            'Aesthetics': analysis_data['analysis']['visualDesign']['aesthetics'],
            'Branding': analysis_data['analysis']['visualDesign']['branding']
        }
        
        fig = go.Figure(data=[
            go.Scatterpolar(
                r=list(scores.values()),
                theta=list(scores.keys()),
                fill='toself',
                name='Scores'
            )
        ])
        
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=False,
            title='Analysis Scores Overview'
        )
        
        charts['scores_overview'] = fig
        
        # Friction Points Severity Distribution
        severity_counts = {'High': 0, 'Medium': 0, 'Low': 0}
        for entry in analysis_data['frictionLog']:
            severity_counts[entry['severity']] += 1
            
        fig = go.Figure(data=[
            go.Pie(
                labels=list(severity_counts.keys()),
                values=list(severity_counts.values()),
                hole=.3,
                marker_colors=['#ff4d4d', '#ffa64d', '#4da6ff']
            )
        ])
        
        fig.update_layout(
            title='Friction Points by Severity',
            annotations=[dict(text='Severity', x=0.5, y=0.5, font_size=20, showarrow=False)]
        )
        
        charts['friction_severity'] = fig
        
        return charts

    @staticmethod
    def create_user_story_charts(user_story_data: Dict[str, Any]) -> Dict[str, go.Figure]:
        """Create charts for user story data."""
        charts = {}
        
        # Priority vs Business Value Matrix
        priority_map = {'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1}
        value_map = {'High': 3, 'Medium': 2, 'Low': 1}
        
        stories = user_story_data['userStories']
        
        fig = go.Figure()
        
        for story in stories:
            fig.add_trace(go.Scatter(
                x=[priority_map[story['priority']]],
                y=[value_map[story['businessValue']]],
                mode='markers+text',
                marker=dict(size=20),
                text=[story['userStory'].split(',')[0]],  # First part of user story
                textposition="top center",
                name=story['userStory']
            ))
        
        fig.update_layout(
            title='User Stories: Priority vs Business Value',
            xaxis=dict(
                ticktext=['Low', 'Medium', 'High', 'Critical'],
                tickvals=[1, 2, 3, 4],
                title='Priority'
            ),
            yaxis=dict(
                ticktext=['Low', 'Medium', 'High'],
                tickvals=[1, 2, 3],
                title='Business Value'
            )
        )
        
        charts['priority_value_matrix'] = fig
        
        # Complexity Distribution
        complexity_counts = {'Simple': 0, 'Medium': 0, 'Complex': 0}
        for story in stories:
            complexity_counts[story['complexity']] += 1
            
        fig = go.Figure(data=[
            go.Bar(
                x=list(complexity_counts.keys()),
                y=list(complexity_counts.values()),
                marker_color=['#4dff4d', '#ffd24d', '#ff4d4d']
            )
        ])
        
        fig.update_layout(
            title='User Stories by Complexity',
            xaxis_title='Complexity Level',
            yaxis_title='Number of Stories'
        )
        
        charts['complexity_distribution'] = fig
        
        return charts

    @staticmethod
    def create_task_backlog_charts(task_backlog_data: Dict[str, Any]) -> Dict[str, go.Figure]:
        """Create charts for task backlog data."""
        charts = {}
        
        # Task Category Distribution
        category_counts = {}
        total_effort = {}
        
        for story in task_backlog_data['userStoryTasks']:
            for task in story['tasks']:
                category = task['category']
                category_counts[category] = category_counts.get(category, 0) + 1
                total_effort[category] = total_effort.get(category, 0) + task['estimatedEffortHours']
        
        # Create subplot with shared legend
        fig = make_subplots(rows=1, cols=2, specs=[[{'type':'pie'}, {'type':'pie'}]])
        
        fig.add_trace(
            go.Pie(
                labels=list(category_counts.keys()),
                values=list(category_counts.values()),
                name="Task Count",
                title="Task Count by Category"
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Pie(
                labels=list(total_effort.keys()),
                values=list(total_effort.values()),
                name="Effort Hours",
                title="Effort Hours by Category"
            ),
            row=1, col=2
        )
        
        fig.update_layout(
            title='Task Distribution and Effort',
            showlegend=True
        )
        
        charts['task_distribution'] = fig
        
        # Task Timeline (Gantt Chart)
        tasks_flat = []
        current_time = 0
        
        for story in task_backlog_data['userStoryTasks']:
            for task in story['tasks']:
                duration = task['estimatedEffortHours']
                tasks_flat.append({
                    'Task': f"{task['taskID']}: {task['taskDescription'][:30]}...",
                    'Start': current_time,
                    'Duration': duration,
                    'Category': task['category']
                })
                current_time += duration
        
        fig = px.timeline(
            tasks_flat,
            x_start='Start',
            x_end=lambda x: x['Start'] + x['Duration'],
            y='Task',
            color='Category',
            title='Task Timeline (Based on Effort Hours)'
        )
        
        fig.update_layout(
            xaxis_title='Cumulative Hours',
            yaxis_title='Tasks'
        )
        
        charts['task_timeline'] = fig
        
        return charts 
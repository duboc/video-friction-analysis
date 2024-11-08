import streamlit as st
import pandas as pd
import json
from typing import Union, Dict, List
from datetime import datetime
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import BaseQuery

def flatten_dict(d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
    """
    Flatten a nested dictionary by concatenating nested keys with separator.
    
    Args:
        d: Dictionary to flatten
        parent_key: Key from parent level
        sep: Separator to use between nested keys
    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Convert list to string representation
            items.append((new_key, str(v)))
        else:
            items.append((new_key, v))
    return dict(items)

def process_firestore_data(docs) -> List[Dict]:
    """Process and flatten Firestore documents"""
    processed_data = []
    
    for doc in docs:
        # Get the document data and add the document ID
        data = doc.to_dict()
        data['document_id'] = doc.id
        
        # Convert timestamps
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.strftime('%Y-%m-%d %H:%M:%S')
        
        # Flatten nested structures
        flattened_data = flatten_dict(data)
        processed_data.append(flattened_data)
    
    return processed_data

def render_analysis_viewer(collection_ref: Union[BaseQuery, List[firestore.DocumentSnapshot]]):
    """Render the analysis results viewer"""
    st.title("Analysis Results Viewer")
    
    try:
        # Get documents
        if isinstance(collection_ref, (firestore.Query, firestore.CollectionReference)):
            docs = collection_ref.get()
        else:
            docs = collection_ref
        
        # Process the Firestore data
        processed_data = process_firestore_data(docs)
        
        if not processed_data:
            st.info("No analysis results found.")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(processed_data)
        
        # Allow column selection
        if not df.empty:
            with st.expander("Column Settings"):
                all_columns = df.columns.tolist()
                selected_columns = st.multiselect(
                    "Select columns to display",
                    all_columns,
                    default=[col for col in all_columns if not col.startswith('_')]
                )
                
                if selected_columns:
                    df = df[selected_columns]
        
        # Display the table
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
        
        # Add download button
        if not df.empty:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download as CSV",
                csv,
                "analysis_results.csv",
                "text/csv",
                key='download-csv'
            )
            
    except Exception as e:
        st.error(f"Error rendering analysis viewer: {str(e)}")
        st.exception(e)

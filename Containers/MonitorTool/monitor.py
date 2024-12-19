import streamlit as st
import os
import pandas as pd
import time
from datetime import datetime
from pymongo import MongoClient

# MongoDB connection settings
DB_HOST = "dbstorage"
DB_PORT = 27017
DB_NAME = "cloneDetector"
STATUS_UPDATES = "statusUpdates"

# MongoDB connection helper
def connect_to_db():
    client = MongoClient(f"mongodb://{DB_HOST}:{DB_PORT}/")
    return client[DB_NAME]

db = connect_to_db()

# Helper functions
def get_step_data(step_name):
    """Fetch all records where step matches the given name."""
    return list(db[STATUS_UPDATES].find({"step": step_name}))

def get_timers_data(limit = None, reverse = False):
    """Fetch and format timing data for display in a table."""
    sort_order = -1 if reverse else 1
    raw_data = db[STATUS_UPDATES].find({"step": {"$in": ["chunkify-file", "expand-single-candidate"]}}).sort("timestamp", sort_order)

    if limit:
        raw_data = raw_data.limit(limit)
    formatted_data = []

    for record in raw_data:
        # Extract and truncate the timestamp to microseconds
        raw_timestamp = record.get("timestamp", "")
        try:
            # Truncate nanoseconds to microseconds if present
            formatted_timestamp = datetime.fromisoformat(raw_timestamp[:26]).strftime(f"%Y-%m-%d %H:%M:%S.{int(raw_timestamp[20:23])}")
        except ValueError:
            formatted_timestamp = "Invalid Timestamp"

        # Extract and format other fields
        formatted_data.append({
            "File Name": os.path.basename(record.get("fileName", "")),
            "Timestamp": formatted_timestamp,
            "Step": record.get("step", ""),
            "Duration (µs)": round(record.get("duration", 0) / 1000, 2),
            "Time per Chunk (µs)": round(record.get("time-per-chunk", 0) / 1000, 2),
            "No. chunks": record.get("chunks-count", 0),
        })

    return formatted_data

def get_info_data():
    """Fetch summary statistics."""
    total_files_processed = db["files"].count_documents({})
    total_clones_found = db["clones"].count_documents({})
    total_files_chunkified = db["statusUpdates"].count_documents({"step": "chunkify-file"})
    return {
        "total_files_processed": total_files_processed,
        "total_files_chunkified": total_files_chunkified,
        "clones_found": total_clones_found,
    }

# Initialize Streamlit app
st.title("Real-Time Statistics Interface")

# Initialize session state for data storage
if "chart_data" not in st.session_state:
    st.session_state.chart_data = pd.DataFrame(
        columns=["x", "Chunkify File Time", "Expand Single Candidate Time"]
    )
if "last_clones_found" not in st.session_state:
    st.session_state.last_clones_found = 0

# Function to fetch and append new data
def fetch_and_update_data():
    data = get_timers_data()

    if data:
        # Convert the data to a DataFrame
        df = pd.DataFrame(data)

        # Prepare data for the scatter plot
        chart_data = pd.DataFrame({
            "Index": range(1, len(df) + 1),  # Use index + 1 as the x-value
            "Duration (µs)": df["Duration (µs)"]  # Use the duration as the y-value
        })

        # Create the scatter plot
        st.scatter_chart(chart_data.set_index("Index"), x_label="represent no. operations", y_label="represent time (µs)", use_container_width=True)

def fetch_and_display_info():
    data = get_info_data()

    if data:
        st.subheader("File Statistics")
        
        clones_difference = data["clones_found"] - st.session_state.last_clones_found

        col1, col2= st.columns(2)
        col1.metric("Number of files processed", data["total_files_processed"])
        col2.metric(label="Number of files chunkified", value=f"{data['total_files_chunkified']}/{data['total_files_processed']}")
        # col3.metric("Number of clones found", data["clones_found"], clones_difference)

        st.session_state.last_clones_found = data["clones_found"]

def fetch_and_update_table():
    data = get_timers_data(limit=100, reverse=True)

    if data:
        st.subheader("Timer Statistics")
        st.write("Time taken for the last 100 recent operations:")
        df = pd.DataFrame(data)

        st.dataframe(data=df, use_container_width=True)

# Real-time fetching
st.write("Fetching data every 5 seconds...")
placeholder = st.empty()
placeholder_info = st.empty()
placeholder_table = st.empty()

while True:
    # Update metrics
    with placeholder_info.container():
        fetch_and_display_info()

    # Update graph
    with placeholder.container():
        st.subheader("Graph of Operation Timings")
        fetch_and_update_data()
        # st.scatter_chart(
        #     st.session_state.chart_data.set_index("x"),
        #     use_container_width=True
        # )
        # st.markdown("<style>.big-font {font-size: 12px; color: gray; margin: 0;}</style>", unsafe_allow_html=True)
        # st.markdown("<p class='big-font'><b>X-values</b> represent the number of operations performed.</p>", unsafe_allow_html=True)
        # st.markdown("<p class='big-font'><b>Y-values</b> represent time in milliseconds.</p>", unsafe_allow_html=True)
        # st.divider()

    # Update table
    with placeholder_table.container():
        fetch_and_update_table()

    time.sleep(5)  # Wait for 5 seconds before fetching again

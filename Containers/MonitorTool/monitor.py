import streamlit as st
import os
import pandas as pd
import time
from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING

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
def get_processing_time(step_name):
    record = db[STATUS_UPDATES].find_one({"step": step_name})
    return record["duration"] if record else 0

def get_collection_count(collection_name):
    return db[collection_name].count_documents({})

def get_latest_documents(limit=100):
    return list(db[STATUS_UPDATES].find().sort("timestamp", DESCENDING).limit(limit))

def get_table_data():
    data = [
        {
            "Processing Step": "Reading and Processing Files",
            "Collection Count": 0,
            "Processing Time": get_processing_time("total-file-processing-time"),
        },
        {
            "Processing Step": "- Storing Files",
            "Collection Count": get_collection_count("files"),
            "Processing Time": get_processing_time("storing-files"),
        },
        {
            "Processing Step": "- Storing Chunks",
            "Collection Count": get_collection_count("chunks"),
            "Processing Time": get_processing_time("storing-chunks"),
        },
        {
            "Processing Step": "Identifying Clone Candidates",
            "Collection Count": get_collection_count("candidates"),
            "Processing Time": get_processing_time("identify-candidates"),
        },
        {
            "Processing Step": "Expanding Candidate (clone count)",
            "Collection Count": get_collection_count("clones"),
            "Processing Time": get_processing_time("expanding-candidates"),
        },
    ]

    table_data = [
        [item["Processing Step"], item["Collection Count"], item["Processing Time"]]
        for item in data
    ]
    return table_data

def get_timers_data():
    """Fetch and format timing data for display in a scatter graph."""
    BATCH_SIZE = 1000

    # Initialize session state if not already done
    if "pd_data" not in st.session_state:
        st.session_state["pd_data"] = pd.DataFrame(columns=["timestamp", "duration", "step"])
        st.session_state["last_timestamp"] = None

    # Build the query based on the last fetched timestamp
    match_query = {"step": {"$in": ["chunkify-file", "expand-single-candidate"]}}
    if st.session_state["last_timestamp"] is not None:
        match_query["timestamp"] = {"$gt": st.session_state["last_timestamp"]}

    pipeline = [
        {"$match": match_query},
        {"$sort": {"timestamp": ASCENDING}},  # Sort by timestamp
    ]

    # Perform aggregation or find query
    new_data = list(db[STATUS_UPDATES].aggregate(pipeline))

    # If new data is found, process it
    if new_data:
        # Convert to DataFrame
        new_df = pd.DataFrame(new_data)

        # Update session_state["pd_data"]
        st.session_state["pd_data"] = pd.concat([st.session_state["pd_data"], new_df], ignore_index=True)

        # Update last fetched timestamp to the last document's timestamp
        st.session_state["last_timestamp"] = new_df["timestamp"].iloc[-1]

    # Process data for scatter plot
    data = st.session_state["pd_data"]

    # Separate and process "chunkify-file"
    chunkify_data = data[data["step"] == "chunkify-file"].copy()
    if not chunkify_data.empty:
        chunkify_data["batch"] = chunkify_data.index // BATCH_SIZE
        aggregated_chunkify = chunkify_data.groupby("batch").agg(
            timestamp=("timestamp", "first"),  # First timestamp in the batch
            average_duration=("duration", "mean"),  # Average duration in the batch
        )
        chunkify_scatter_data = [
            {"x": row["timestamp"], "y": row["average_duration"], "step": "chunkify-file"}
            for _, row in aggregated_chunkify.iterrows()
        ]
    else:
        chunkify_scatter_data = []

    # Process "expand-single-candidate" without batching
    expand_single_data = data[data["step"] == "expand-single-candidate"]
    expand_scatter_data = [
        {"x": row["timestamp"], "y": row["duration"], "step": "expand-single-candidate"}
        for _, row in expand_single_data.iterrows()
    ]

    # Combine both datasets
    combined_data = chunkify_scatter_data + expand_scatter_data

    return combined_data


def get_info_data():
    """Fetch summary statistics."""
    total_files_processed = db["files"].count_documents({})
    total_clones_found = db["clones"].count_documents({})
    total_chunks = db["chunks"].count_documents({})
    total_candidates = db["candidates"].count_documents({})
    return {
        "total_files_processed": total_files_processed,
        "total_chunks": total_chunks,
        "total_candidates": total_candidates,
        "total_clones": total_clones_found,
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
        df = pd.DataFrame(data, columns=["x", "y"])
        

        df["x"] = pd.to_datetime(df["x"])  # Ensure it's a datetime object
        df.set_index("x", inplace=True)
 
        # st.write(df)
        # # Create the scatter plot
        st.scatter_chart(df, x_label="represent time of operation (12-hour clock)", y_label="represent time (nano seconds)", use_container_width=True)

def fetch_and_display_info():
    data = get_info_data()

    if data:
        st.subheader("Database Statistics")
        
        clones_difference = data["total_clones"] - st.session_state.last_clones_found

        st.metric(label="Number of files processed", value=data["total_files_processed"])
        st.metric(label="Number of chunks", value=data["total_chunks"])
        st.metric(label="Number of candidates", value=data["total_candidates"])
        st.metric(label="Number of clones", value=data["total_clones"], delta=clones_difference)

        st.session_state.last_clones_found = data["total_clones"]

def fetch_and_update_table():
    table_data = get_table_data()
    st.subheader("Processing Steps")
    st.dataframe({
        "Processing Step": [row[0] for row in table_data],
        "Collection Count": [row[1] for row in table_data],
        "Processing Time (minutes)": [
            round(float(row[2]) / 1e9 / 60, 2) if row[2] not in (None, "") else None for row in table_data
        ],
    })

def fetch_and_update_latest_doc():
    latest_docs = get_latest_documents(limit=100)
    processed_docs = [
        {
            key: (
                os.path.basename(value) if key == "fileName" else
                # For timestamp, include milliseconds
                datetime.strptime(value.split(".")[0], "%Y-%m-%dT%H:%M:%S").strftime("%H:%M:%S") + "." + value.split(".")[1][:3]
                if key == "timestamp" and isinstance(value, str) else
                value
            )
            for key, value in doc.items() if key != "_id"
        }
        for doc in latest_docs
    ]
    st.dataframe(processed_docs)

# Real-time fetching
st.write("Fetching data every 5 seconds...")
placeholder = st.empty()
placeholder_table = st.empty()
placeholder_latest_doc = st.empty()

while True:
    # Update graph
    with placeholder.container():
        st.subheader("Graph of Operation Timings")
        fetch_and_update_data()

    # Update table
    with placeholder_table.container():
        fetch_and_update_table()
    
    # Update table
    with placeholder_latest_doc.container():
        st.subheader("Last 100 Operations")
        fetch_and_update_latest_doc()

    time.sleep(5)  # Wait for 5 seconds before fetching again

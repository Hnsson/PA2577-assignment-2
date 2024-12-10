import streamlit as st
import pandas as pd
import time
from helpers import get_data, get_timers_data, get_info_data

# Title
st.title("Real-Time Statistics Interface")

# Initialize session state for data storage
if "chart_data" not in st.session_state:
    st.session_state.chart_data = pd.DataFrame(
        columns=["x", "Last 100 files", "Last 1000 files", "Overall files"]
    )
if "last_cones_found" not in st.session_state:
    st.session_state.last_clones_found = 0

# Function to fetch and append new data
def fetch_and_update_data():
    # Fetch new data
    average_last_100 = get_data("100")
    average_last_1000 = get_data("1000")
    average_last_overall = get_data()

    # Prepare new data row
    new_data = {
        "x": int(average_last_overall["x"]),  # x-values shared across all lines
        "Last 100 files": int(average_last_100["y"]["total"]),
        "Last 1000 files": int(average_last_1000["y"]["total"]),
        "Overall files": int(average_last_overall["y"]["total"]),
    }

    # Append new data to the DataFrame
    st.session_state.chart_data = pd.concat(
        [st.session_state.chart_data, pd.DataFrame([new_data])],
        ignore_index=True
    )

def fetch_and_display_info():
    data = get_info_data()

    if data:
        st.subheader("File Statistics")
        
        clones_difference = data["clones_found"] - st.session_state.last_clones_found

        col1, col2 = st.columns(2)
        col1.metric(":gray[Number of files processed]", data["total_files_processed"])
        col2.metric(":gray[Number of clones found]", data["clones_found"], clones_difference)

        st.session_state.last_clones_found = data["clones_found"]

def fetch_and_update_table():
    data = get_timers_data()

    if data:
        st.subheader("Timer Statistics")
        st.write(":gray[Time taken to process the last 1000 files]")
        df = pd.DataFrame(data['files'])
        st.dataframe(data=df, use_container_width=True)


st.write(":gray[Fetching data every 5 seconds...]")
placeholder = st.empty()  # Placeholder for the chart
placeholder_info = st.empty()
placeholder_table = st.empty()

while True:
    with placeholder_info.container():
        fetch_and_display_info()  # Fetch and display the table

    fetch_and_update_data()  # Fetch and update the data
    with placeholder.container():
        st.line_chart(
            st.session_state.chart_data.set_index("x"),
            use_container_width=True
        )
        st.markdown("<style>.big-font {font-size: 12px; color: gray; margin: 0;}</style>", unsafe_allow_html=True)
        st.markdown("<p class='big-font'><b>X-values</b> represent the number of processed files.</p>", unsafe_allow_html=True)
        st.markdown("<p class='big-font'><b>Y-values</b> represent time in microseconds.</p>", unsafe_allow_html=True)
        st.divider()
    
    with placeholder_table.container():
        fetch_and_update_table()

    time.sleep(5)  # Wait for 5 seconds before fetching again

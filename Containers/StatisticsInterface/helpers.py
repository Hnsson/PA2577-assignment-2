# Api CALLS

import streamlit as st
import requests
import os

from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("TARGET")

def get_data(last_files = "overall"):
    url = (
        f"http://{BACKEND_URL}/average/{last_files}"
    )
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        st.error(f"Error while fetching data: {e}")
    else:
        if response.ok:
            return response.json()
        else:
            return None

def get_info_data():
    url = (
        f"http://{BACKEND_URL}/info"
    )
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        st.error(f"Error while fetching data: {e}")
    else:
        if response.ok:
            return response.json()
        else:
            return None

def get_timers_data():
    url = (
        f"http://{BACKEND_URL}/timers"
    )
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        st.error(f"Error while fetching data: {e}")
    else:
        if response.ok:
            return response.json()
        else:
            return None
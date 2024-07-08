import streamlit as st
import requests
import json
from streamlit.logger import get_logger

LOGGER = get_logger(__name__)

def load_api_keys():
    try:
        return {
            "openrouter": st.secrets["secrets"]["openrouter_api_key"],
            "rapidapi": st.secrets["secrets"]["rapidapi_key"]
        }
    except KeyError as e:
        st.error(f"{e} API key not found in secrets.toml. Please add it.")
        return None

def load_users():
    return st.secrets["users"]

def login(username, password):
    users = load_users()
    if username in users and users[username] == password:
        return True
    return False

def get_company_posts(company_url, rapidapi_key):
    url = "https://linkedin-data-scraper.p.rapidapi.com/company_updates"
    payload = {
        "company_url": company_url,
        "posts": 10,
        "comments": 10,
        "reposts": 10
    }
    headers = {
        "x-rapidapi-key": rapidapi_key,
        "x-rapidapi-host": "linkedin-data-scraper.p.rapidapi.com",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        LOGGER.error(f"Company posts API request failed: {e}")
        st.error("Failed to fetch company posts. Please try again later.")
    return None

def analyze_posts(posts, openrouter_key):
    if not posts:
        return "No posts available for analysis."

    post_texts = [post.get('postText', '') for post in posts]
    combined_text = "\n\n".join(post_texts)

    if not combined_text:
        return "No post content available for analysis."

    prompt = f"""Analyze the following LinkedIn posts and provide insights on:
    1. Content style (formal, casual, professional, etc.)
    2. Tone (informative, persuasive, inspirational, etc.)
    3. Common themes or topics
    4. Use of hashtags or mentions
    5. Length and structure of posts

    Posts:
    {combined_text}

    Based on this analysis, provide a prompt that would generate posts in a similar style, along with an example post.
    """

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {openrouter_key}"},
            json={
                "model": "anthropic/claude-3-sonnet-20240229",
                "messages": [
                    {"role": "system", "content": "You are an expert in content analysis and creation."},
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.RequestException as e:
        LOGGER.error(f"OpenRouter API request failed: {e}")
        st.error("Failed to generate content analysis. Please try again later.")
    except (KeyError, IndexError, ValueError) as e:
        LOGGER.error(f"Error processing OpenRouter API response: {e}")
        st.error("Error processing the generated content. Please try again.")
    return None

def main_app():
    api_keys = load_api_keys()
    if not api_keys:
        return

    company_url = st.text_input("Enter LinkedIn Company URL:")

    if company_url:
        if 'company_data' not in st.session_state:
            st.session_state.company_data = None
        
        if 'analysis_result' not in st.session_state:
            st.session_state.analysis_result = None

        if st.button("Fetch Company Data"):
            with st.spinner("Fetching company posts..."):
                company_data = get_company_posts(company_url, api_keys["rapidapi"])
                if company_data:
                    st.session_state.company_data = company_data
                    st.success("Company data fetched successfully!")
                else:
                    st.error("Failed to fetch company data. Please try again.")

        if st.session_state.company_data:
            st.subheader("Company Posts")
            posts = st.session_state.company_data.get('response', [])
            for i, post in enumerate(posts, 1):
                st.write(f"Post {i}:")
                st.write(post.get('postText', 'No text available'))
                st.write("---")

            if st.button("Analyze Posts"):
                with st.spinner("Analyzing company posts..."):
                    analysis = analyze_posts(posts, api_keys["openrouter"])
                    if analysis:
                        st.session_state.analysis_result = analysis
                        st.success("Analysis completed successfully!")
                    else:
                        st.error("Failed to analyze posts. Please try again.")

        if st.session_state.analysis_result:
            st.subheader("Content Analysis and Prompt Generation")
            st.write(st.session_state.analysis_result)

def login_page():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if login(username, password):
            st.session_state.logged_in = True
            st.success("Logged in successfully!")
            st.rerun()
        else:
            st.error("Invalid username or password")

def display():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_page()
    else:
        st.title("LinkedIn Company Analysis")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
        else:
            main_app()

    st.caption("Note: This app uses RapidAPI's LinkedIn Data Scraper and OpenRouter for AI model access. Make sure you have valid API keys for both services.")

if __name__ == "__main__":
    display()

import streamlit as st
import requests
import time
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

def get_company_info(company_url, rapidapi_key):
    url = "https://linkedin-profile-data.p.rapidapi.com/company-profile"
    querystring = {"url": company_url}
    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "linkedin-profile-data.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.RequestException as e:
        LOGGER.error(f"Company info API request failed: {e}")
        st.error("Failed to fetch company information. Please try again later.")
    return {}

def get_company_posts(company_url, rapidapi_key):
    url = "https://linkedin-profile-data.p.rapidapi.com/company-posts"
    querystring = {"url": company_url, "limit": "10"}
    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "linkedin-profile-data.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        data = response.json()
        return data.get('posts', [])
    except requests.RequestException as e:
        LOGGER.error(f"Company posts API request failed: {e}")
        if response.status_code == 429:
            st.warning("Rate limit exceeded. Please wait a moment before trying again.")
        else:
            st.error("Failed to fetch company posts. Please try again later.")
    return []

def analyze_posts(posts, openrouter_key):
    if not posts:
        return "No posts available for analysis."

    post_texts = [post.get('content', '') for post in posts if post.get('content')]
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
        with st.spinner("Fetching company information..."):
            company_info = get_company_info(company_url, api_keys["rapidapi"])
            st.subheader("Company Information")
            st.write(f"Name: {company_info.get('name', 'N/A')}")
            st.write(f"Industry: {company_info.get('industry', 'N/A')}")
            st.write(f"Description: {company_info.get('description', 'N/A')}")

        with st.spinner("Fetching and analyzing company posts..."):
            company_posts = get_company_posts(company_url, api_keys["rapidapi"])
            if company_posts:
                analysis = analyze_posts(company_posts, api_keys["openrouter"])
                if analysis:
                    st.subheader("Content Analysis and Prompt Generation")
                    st.write(analysis)
            else:
                st.warning("No posts available for analysis. Please try again later.")

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

    st.caption("Note: This app uses RapidAPI's LinkedIn Profile Data API and OpenRouter for AI model access. Make sure you have valid API keys for both services.")

if __name__ == "__main__":
    display()

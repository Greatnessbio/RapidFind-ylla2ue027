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

def get_company_info(company_url, rapidapi_key):
    url = "https://linkedin-data-scraper.p.rapidapi.com/company_pro"
    payload = {"link": company_url}
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
        LOGGER.error(f"Company info API request failed: {e}")
        st.error("Failed to fetch company information. Please try again later.")
    return None

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

def summarize_company_info(company_info):
    summary = ""
    if 'data' in company_info:
        data = company_info['data']
        summary += f"Company Name: {data.get('companyName', 'N/A')}\n"
        summary += f"Industry: {data.get('industry', 'N/A')}\n"
        summary += f"Company Size: {data.get('employeeCount', 'N/A')} employees\n"
        summary += f"Headquarters: {data.get('headquarter', {}).get('city', 'N/A')}, {data.get('headquarter', {}).get('country', 'N/A')}\n"
        
        # Handle 'foundedOn' more flexibly
        founded_on = data.get('foundedOn', 'N/A')
        if isinstance(founded_on, dict):
            founded_year = founded_on.get('year', 'N/A')
        elif isinstance(founded_on, str):
            founded_year = founded_on
        else:
            founded_year = 'N/A'
        summary += f"Founded: {founded_year}\n"
        
        summary += f"Specialties: {', '.join(data.get('specialities', ['N/A']))}\n"
        summary += f"\nDescription: {data.get('description', 'N/A')}\n"
    else:
        summary = "No company information available."
    return summary

def summarize_company_posts(company_posts):
    summary = ""
    if 'response' in company_posts:
        posts = company_posts['response']
        summary += f"Analyzed {len(posts)} recent posts:\n\n"
        for i, post in enumerate(posts, 1):
            summary += f"Post {i}:\n"
            summary += f"Text: {post.get('postText', 'N/A')[:100]}...\n"
            summary += f"Likes: {post.get('socialCount', {}).get('numLikes', 'N/A')}\n"
            summary += f"Comments: {post.get('socialCount', {}).get('numComments', 'N/A')}\n"
            summary += f"Shares: {post.get('socialCount', {}).get('numShares', 'N/A')}\n\n"
    else:
        summary = "No company posts available."
    return summary

def analyze_text(text, prompt, openrouter_key):
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {openrouter_key}"},
            json={
                "model": "anthropic/claude-3-sonnet-20240229",
                "messages": [
                    {"role": "system", "content": "You are an expert in content analysis and creation."},
                    {"role": "user", "content": prompt + "\n\n" + text}
                ]
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.RequestException as e:
        LOGGER.error(f"OpenRouter API request failed: {e}")
        st.error("Failed to generate analysis. Please try again later.")
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
        with st.spinner("Fetching company information and posts..."):
            company_info = get_company_info(company_url, api_keys["rapidapi"])
            company_posts = get_company_posts(company_url, api_keys["rapidapi"])

            if company_info and company_posts:
                st.success("Data fetched successfully!")

                st.subheader("Company Summary")
                company_summary = summarize_company_info(company_info)
                st.text_area("Company Information", company_summary, height=300)

                st.subheader("Recent Posts Summary")
                posts_summary = summarize_company_posts(company_posts)
                st.text_area("Recent Posts", posts_summary, height=300)

                if st.button("Analyze Company Profile and Posts"):
                    analysis_prompt = """
                    Based on the company information and recent posts, provide an analysis covering:
                    1. The company's main focus and industry position
                    2. Their communication style on LinkedIn
                    3. Key themes or topics they frequently discuss
                    4. The level of engagement they receive on their posts
                    5. Suggestions for improving their LinkedIn presence
                    """
                    with st.spinner("Analyzing company profile and posts..."):
                        analysis = analyze_text(company_summary + "\n\n" + posts_summary, analysis_prompt, api_keys["openrouter"])
                        if analysis:
                            st.subheader("Analysis")
                            st.write(analysis)
                        else:
                            st.error("Failed to generate analysis. Please try again.")

            else:
                st.error("Failed to fetch company data. Please check the URL and try again.")

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

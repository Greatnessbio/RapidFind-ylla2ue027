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

def store_data(key, value):
    st.session_state[key] = value
    LOGGER.info(f"Stored data for key: {key}")

def get_stored_data(key):
    if key in st.session_state:
        LOGGER.info(f"Retrieved data for key: {key}")
        return st.session_state[key]
    else:
        LOGGER.warning(f"No data found for key: {key}")
        return None

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
        "posts": 20,
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

def display_company_info(company_info):
    st.subheader("Company Information")
    col1, col2 = st.columns(2)
    
    with col1:
        st.image(company_info['data']['logoResolutionResult'], width=200)
        st.write(f"**{company_info['data']['companyName']}**")
        st.write(f"Industry: {company_info['data']['industry']}")
        st.write(f"Founded: {company_info['data']['foundedOn']['year']}")
        st.write(f"Employees: {company_info['data']['employeeCount']}")
    
    with col2:
        st.write(f"Tagline: {company_info['data']['tagline']}")
        st.write(f"Followers: {company_info['data']['followerCount']}")
        st.write(f"Website: {company_info['data']['websiteUrl']}")
        st.write(f"Headquarters: {company_info['data']['headquarter']['city']}, {company_info['data']['headquarter']['country']}")

    st.write("**Description:**")
    st.write(company_info['data']['description'])

def display_competitors(company_info):
    st.subheader("Similar Companies")
    for company in company_info['data']['similarOrganizations'][:5]:  # Display top 5 competitors
        st.write(f"**{company['name']}**")
        st.write(f"Industry: {company['industry']}")
        st.write(f"Followers: {company['followerCount']}")
        st.write("---")

def main_app():
    api_keys = load_api_keys()
    if not api_keys:
        return

    company_url = st.text_input("Enter LinkedIn Company URL:")

    if company_url:
        if st.button("Fetch Company Data"):
            with st.spinner("Fetching company information and posts..."):
                company_info = get_company_info(company_url, api_keys["rapidapi"])
                company_posts = get_company_posts(company_url, api_keys["rapidapi"])
                if company_info and company_posts:
                    store_data('company_info', company_info)
                    store_data('company_posts', company_posts)
                    st.success("Company data fetched and stored successfully!")
                else:
                    st.error("Failed to fetch company data. Please try again.")

        stored_company_info = get_stored_data('company_info')
        if stored_company_info:
            display_company_info(stored_company_info)
            display_competitors(stored_company_info)

            st.write("---")
            st.subheader("Analyze Company Posts")
            st.write("""
            Press the button below to analyze the company's LinkedIn posts. 
            This will provide insights on:
            - Content style (formal, casual, professional, etc.)
            - Tone (informative, persuasive, inspirational, etc.)
            - Common themes or topics
            - Use of hashtags and mentions
            - Length and structure of posts
            """)

            if st.button("Analyze Posts"):
                stored_company_posts = get_stored_data('company_posts')
                if stored_company_posts:
                    with st.spinner("Analyzing company posts..."):
                        posts_text = "\n\n".join([post.get('postText', '') for post in stored_company_posts.get('response', [])])
                        posts_prompt = """Analyze the following LinkedIn posts and provide insights on:
                        1. Content style (formal, casual, professional, etc.)
                        2. Tone (informative, persuasive, inspirational, etc.)
                        3. Common themes or topics
                        4. Use of hashtags or mentions
                        5. Length and structure of posts
                        
                        Provide a summary of your analysis."""
                        
                        posts_analysis = analyze_text(posts_text, posts_prompt, api_keys["openrouter"])
                        
                        if posts_analysis:
                            store_data('posts_analysis', posts_analysis)
                            st.success("Analysis completed and stored successfully!")
                        else:
                            st.error("Failed to complete analysis. Please try again.")
                else:
                    st.error("No stored company posts found. Please fetch company data first.")

            stored_posts_analysis = get_stored_data('posts_analysis')
            if stored_posts_analysis:
                st.subheader("Posts Analysis")
                st.write(stored_posts_analysis)

                st.write("---")
                st.subheader("Generate Example Post")
                st.write("""
                Press the button below to generate an example post based on the analysis.
                This will:
                - Create a prompt that captures the company's posting style
                - Generate a sample post using that prompt
                """)

                if st.button("Generate Example Post"):
                    with st.spinner("Generating example post..."):
                        example_prompt = "Based on the analysis of the LinkedIn posts, provide a prompt that would generate posts in a similar style, along with an example post."
                        example_post = analyze_text(stored_posts_analysis, example_prompt, api_keys["openrouter"])
                        
                        if example_post:
                            store_data('example_post', example_post)
                            st.subheader("Generated Post")
                            st.write(example_post)
                        else:
                            st.error("Failed to generate example post. Please try again.")
        else:
            st.warning("No company data stored. Please fetch company data first.")

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

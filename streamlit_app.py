import streamlit as st
import requests
import json
from streamlit.logger import get_logger

LOGGER = get_logger(__name__)

# ... [All previous functions remain the same] ...

def main_app():
    api_keys = load_api_keys()
    if not api_keys:
        return

    company_url = st.text_input("Enter LinkedIn Company URL:")

    if company_url:
        # Automatically fetch data when URL is entered
        with st.spinner("Fetching company information and posts..."):
            company_info = get_company_info(company_url, api_keys["rapidapi"])
            company_posts = get_company_posts(company_url, api_keys["rapidapi"])
            if company_info and company_posts:
                store_data('company_info', company_info)
                store_data('company_posts', company_posts)
                st.success("Company data fetched and stored successfully!")
            else:
                st.error("Failed to fetch company data. Please check the URL and try again.")

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
                if stored_company_posts and 'response' in stored_company_posts:
                    with st.spinner("Analyzing company posts..."):
                        posts_text = "\n\n".join([post.get('postText', '') for post in stored_company_posts['response']])
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
                    st.error("No stored company posts found or invalid data structure. Please check the URL and try again.")

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
            st.warning("No company data stored. Please enter a valid LinkedIn company URL.")

# ... [The rest of the code (login_page, display, etc.) remains the same] ...

if __name__ == "__main__":
    display()

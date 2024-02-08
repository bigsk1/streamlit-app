import streamlit as st

# Set the title of the app
st.title('My First Streamlit App')

# Display a simple text
st.write('Hello, Streamlit!')

# Ask for user input and display it
user_input = st.text_input("Enter your name", "")
st.write(f'Hello, {user_input}!')

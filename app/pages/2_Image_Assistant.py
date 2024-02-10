import os
import base64
from io import BytesIO
from typing import List
import streamlit as st
from PIL import Image
from phi.assistant import Assistant
from phi.tools.streamlit.components import (
    get_openai_key_sidebar,
    check_password,
    reload_button_sidebar,
    get_username_sidebar,
)

from ai.assistants.image import get_image_assistant
from utils.log import logger
from urllib.parse import urlparse
import requests

st.set_page_config(
    page_title="Image AI",
    page_icon=":camera:",
)
st.title("Image Assistant")
st.markdown("##### Artistic Revolution :camera: AI Empowered")


def encode_image(image_file):
    image = Image.open(image_file)
    
    # Convert image to RGB if it has an alpha channel (transparency)
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        # Create a white background
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
        image = background
    
    buffer = BytesIO()
    image.save(buffer, format="JPEG")  # Now saving as JPEG should not raise an error
    encoding = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoding}"


def restart_assistant():
    st.session_state["image_assistant"] = None
    st.session_state["image_assistant_run_id"] = None
    st.session_state["file_uploader_key"] += 1
    st.session_state["uploaded_image"] = None
    st.rerun()


    # https only 
def is_valid_url(url):
    parsed_url = urlparse(url)
    return bool(parsed_url.scheme == "https" and parsed_url.netloc)

    # security for images
def is_image_content_type(response_headers):
    content_type = response_headers.get('Content-Type', '')
    return content_type.startswith('image/')


    # Function to download and save image from URL
def download_image_from_url(image_url, output_dir="downloaded_images"):
    # Validate URL
    if not is_valid_url(image_url):
        return None, "Invalid URL format."
    
    try:
        # Perform the request
        response = requests.get(image_url, stream=True, timeout=10)
        response.raise_for_status()  # Check for HTTP errors

        # Validate content type
        if not is_image_content_type(response.headers):
            return None, "The URL does not point to a valid image content type."

        # Process and save the image
        file_name = os.path.basename(image_url)
        file_extension = os.path.splitext(file_name)[1].lower()
        allowed_formats = ['.jpg', '.jpeg', '.png', '.webp']
        if file_extension not in allowed_formats:
            error_message = "Unsupported image format. Please upload an image in one of the following formats: " + ", ".join(allowed_formats)
            return None, error_message

        # Save the image
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        file_path = os.path.join(output_dir, file_name)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)

        return file_path, None
    except requests.exceptions.RequestException as e:
        return None, f"Error downloading the image: {e}"



def main() -> None:
    # Get OpenAI key from environment variable or user input
    get_openai_key_sidebar()

    # Get username
    username = get_username_sidebar()
    if username:
        st.sidebar.info(f":technologist: User: {username}")
    else:
        st.markdown("---")
        st.markdown("#### :technologist: Enter a username, upload an Image and start chatting")
        return

    # Get the assistant
    image_assistant: Assistant
    if "image_assistant" not in st.session_state or st.session_state["image_assistant"] is None:
        logger.info("---*--- Creating Vision Assistant ---*---")
        image_assistant = get_image_assistant(
            user_id=username,
            debug_mode=False,
        )
        st.session_state["image_assistant"] = image_assistant
    else:
        image_assistant = st.session_state["image_assistant"]

    # Sidebar for image URL input
    image_url = st.sidebar.text_input("Enter an Image URL", "")


    # Download and process image from URL if provided
    if image_url:
        downloaded_image_path, error_message = download_image_from_url(image_url)
        if downloaded_image_path:
            st.sidebar.success("Image downloaded successfully.")
            # Encode the downloaded image for use in the application
            with open(downloaded_image_path, "rb") as image_file:
                encoded_downloaded_image = encode_image(image_file)
            # Optionally set the uploaded_image state to the encoded image
            st.session_state["uploaded_image"] = encoded_downloaded_image
        elif error_message:
            st.sidebar.error(error_message)
        else:
            st.sidebar.error("Failed to download the image.")
                             
     
    # Create assistant run (i.e. log to database) and save run_id in session state
    st.session_state["image_assistant_run_id"] = image_assistant.create_run()

    # Store uploaded image in session state
    uploaded_image = None
    if "uploaded_image" in st.session_state:
        uploaded_image = st.session_state["uploaded_image"]

    # Load messages for existing assistant
    assistant_chat_history = image_assistant.memory.get_chat_history()
    if len(assistant_chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = assistant_chat_history
        # Search for uploaded image
        if uploaded_image is None:
            for message in assistant_chat_history:
                if message["role"] == "user":
                    for item in message["content"]:
                        if item["type"] == "image_url":
                            uploaded_image = item["image_url"]["url"]
                            st.session_state["uploaded_image"] = uploaded_image
                            break
    else:
        logger.debug("No chat history found")
        st.session_state["messages"] = [{"role": "assistant", "content": "Ask me about the image..."}]

    # Upload Image if not available
    if uploaded_image is None:
        if "file_uploader_key" not in st.session_state:
            st.session_state["file_uploader_key"] = 0
        uploaded_file = st.sidebar.file_uploader(
            "Upload Image",
            key=st.session_state["file_uploader_key"],
        )
        if uploaded_file is not None:
            alert = st.sidebar.info("Processing Image...", icon="ℹ️")
            image_file_name = uploaded_file.name.split(".")[0]
            if f"{image_file_name}_uploaded" not in st.session_state:
                logger.info(f"Encoding {image_file_name}")
                uploaded_image = encode_image(uploaded_file)
                st.session_state["uploaded_image"] = uploaded_image
                st.session_state[f"{image_file_name}_uploaded"] = True
            alert.empty()

    # Prompt for user input
    if uploaded_image:
        st.image(uploaded_image, use_column_width=True)
        if prompt := st.chat_input():
            vision_message = [
                {
                    "type": "text",
                    "text": prompt,
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": uploaded_image,
                        "detail": "low",
                    },
                },
            ]
            st.session_state["messages"].append({"role": "user", "content": vision_message})

    if st.sidebar.button("New Run"):
        restart_assistant()

    if uploaded_image:
        if st.sidebar.button("Generate Caption"):
            caption_message = [
                {
                    "type": "text",
                    "text": "Generate a caption for this image",
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": uploaded_image,
                        "detail": "low",
                    },
                },
            ]
            st.session_state["messages"].append({"role": "user", "content": caption_message})

        if st.sidebar.button("Describe Image"):
            caption_message = [
                {
                    "type": "text",
                    "text": "Describe this image in 2 sentences",
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": uploaded_image,
                        "detail": "low",
                    },
                },
            ]
            st.session_state["messages"].append({"role": "user", "content": caption_message})

        if st.sidebar.button("Identify Brands"):
            brands_message = [
                {
                    "type": "text",
                    "text": "List the brands in this image. This is only for demo and testing purposes.",
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": uploaded_image,
                        "detail": "low",
                    },
                },
            ]
            st.session_state["messages"].append({"role": "user", "content": brands_message})

        if st.sidebar.button("Identify Items"):
            items_message = [
                {
                    "type": "text",
                    "text": "List the items in this image",
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": uploaded_image,
                        "detail": "low",
                    },
                },
            ]
            st.session_state["messages"].append({"role": "user", "content": items_message})

    # Display existing chat messages
    for message in st.session_state["messages"]:
        if message["role"] == "system":
            continue
        with st.chat_message(message["role"]):
            content = message.get("content")
            if isinstance(content, list):
                for item in content:
                    if item["type"] == "text":
                        st.write(item["text"])
                    # elif item["type"] == "image_url":
                    #     st.image(item["image_url"]["url"], use_column_width=True)
            else:
                st.write(content)

    # If last message is from a user, generate a new response
    last_message = st.session_state["messages"][-1]
    if last_message.get("role") == "user":
        question = last_message["content"]
        with st.chat_message("assistant"):
            with st.spinner("Working..."):
                response = ""
                resp_container = st.empty()
                for delta in image_assistant.run(question):
                    response += delta  # type: ignore
                    resp_container.markdown(response)
            st.session_state["messages"].append({"role": "assistant", "content": response})

    if image_assistant.storage:
        image_assistant_run_ids: List[str] = image_assistant.storage.get_all_run_ids(user_id=username)
        new_image_assistant_run_id = st.sidebar.selectbox("Run ID", options=image_assistant_run_ids)
        if st.session_state["image_assistant_run_id"] != new_image_assistant_run_id:
            logger.debug(f"Loading run {new_image_assistant_run_id}")
            logger.info("---*--- Loading Vision Assistant ---*---")
            st.session_state["image_assistant"] = get_image_assistant(
                user_id=username,
                run_id=new_image_assistant_run_id,
                debug_mode=False,
            )
            st.rerun()

    # Show reload button
    reload_button_sidebar()


if check_password():
    main()

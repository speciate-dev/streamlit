import asyncio
import json

import requests
import websockets

import streamlit as st
from python_lib.secrets import get_secret

class Config:
    BASE_URL = (
        "api.speciate.com"
        if get_secret("ENV", "prod") == "prod"
        else "dev.api.speciate.com"
    )
    CONFIG_URL = f"https://{BASE_URL}/v1/configs/"
    CHAT_URL = f"wss://{BASE_URL}/v1/chat-agents/chat-message"

class StreamlitApp:
    def __init__(self):
        self.user_id = st.query_params.get("user_id")
        self.chat_id = st.query_params.get("chat_id")
        self.stream_response_flag = True
        self.connection_url = f"{Config.CHAT_URL}?user_id={self.user_id}&chat_id={self.chat_id}&stream_response={self.stream_response_flag}"
        
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "user", "content": ""},
                {"role": "assistant", "content": "Understood"},
            ]

    def display_title(self):
        st.title("Chat with Speciate Agent")
        hide_decoration_bar_style = """
            <style>
                header {visibility: hidden;}
            </style>
        """
        st.markdown(hide_decoration_bar_style, unsafe_allow_html=True)

    def display_config(self):
        response = requests.get(Config.CONFIG_URL)
        if response.ok:
            config_parent = json.loads(response.content)
            config = config_parent["config"]
            container = st.container(border=True)
            container.write("Model: " + ":blue[" + config["LLM.MODEL_NAME"] + "]")
            if self.user_id and self.chat_id:
                container.write(f"Reading :blue[{str(config['LLM.CONTEXT_LOG_COUNT'])}] most recent logs and :blue[{str(config['LLM.CONTEXT_CHAT_COUNT'])}] most recent chats")
            else:
                container.write("No user context available")

    def display_chat(self):
        # Display user and assistant messages skipping the first two
        for message in st.session_state.messages[2:]:
            # ignore tool use blocks
            if isinstance(message["content"], str):
                st.chat_message(message["role"]).markdown(message["content"])

    async def handle_chat_response(self, chat_request, chat_response_placeholder):
        try:
            async with websockets.connect(self.connection_url) as websocket:
                await websocket.send(chat_request)

                full_chat_response = ""
                while True:
                    chat_response = await websocket.recv()
                    if chat_response == "END_OF_STREAM_RESPONSE":
                        break
                    full_chat_response += chat_response
                    chat_response_placeholder.markdown(full_chat_response)
                    if self.stream_response_flag == False:
                        break
                return full_chat_response
        except Exception as e:
            print(str(e))

    async def handle_chat(self):
        if chat_request := st.chat_input("How can I help you today?"):
            st.chat_message("user").markdown(chat_request)
            st.session_state.messages.append({"role": "user", "content": chat_request})

            with st.chat_message("assistant"):
                with st.spinner("Thinking aloud..."):
                    chat_response_placeholder = st.empty()
                    full_chat_response = await self.handle_chat_response(chat_request, chat_response_placeholder)
                    st.session_state.messages.append({"role": "assistant", "content": full_chat_response})
                    
if __name__ == "__main__":
    app = StreamlitApp()
    app.display_title()
    app.display_config()
    if app.user_id and app.chat_id:
        app.display_chat()
        asyncio.run(app.handle_chat())

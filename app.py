import os
from collections import namedtuple
from time import sleep

import openai
import streamlit as st


st.title("AI Chat Room")


ss = st.session_state

with st.sidebar:
    ss.openai_api_key = st.text_input("OpenAI API key", placeholder="sk-xxxx", type="password")

if key := (ss.openai_api_key or os.getenv("OPENAI_API_KEY")):
    oai = openai.OpenAI(api_key=key)
else:
    st.warning("Please set your OpenAI API key")

class Bot:
    def __init__(
        self,
        name: str,
        instructions: str,
        avatar: str = "🤖",
        tools: list[dict] = [],
        model: str = "gpt-3.5-turbo-1106",
    ) -> None:
        self.name = name
        self.avatar = avatar
        self.assistant = oai.beta.assistants.create(
            name=name,
            instructions=instructions,
            tools=tools,
            model=model,
        )
        self.thread = oai.beta.threads.create()

Message = namedtuple("Message", ["index", "content"])


st.info("This is an AI chat room for two bots, which you can configure below:")


with st.form("config"):
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Bot A")
        col1, col2 = st.columns([3, 1])
        with col1:
            bot_a_name = st.text_input("Name", value="Alice")
        with col2:
            bot_a_avatar = st.text_input("Avatar", value="👩")
        bot_a_instruct = st.text_area("Instructions", value="You are Alice. You are talking with Bob.")
    with col_b:
        st.subheader("Bot B")
        col1, col2 = st.columns([3, 1])
        with col1:
            bot_b_name = st.text_input("Name", value="Bob")
        with col2:
            bot_b_avatar = st.text_input("Avatar", value="👨")
        bot_b_instruct = st.text_area("Instructions", value="You are Bob. You are talking with Alice.")
    init_message = st.text_input("Initial message", value="Hi! I'm Alice. How are you?")
    if st.form_submit_button("Submit"):
        ss.bots = [
            Bot(bot_a_name, bot_a_instruct, bot_a_avatar),
            Bot(bot_b_name, bot_b_instruct, bot_b_avatar),
        ]


box = st.container()
chat = st.button("Continue")


if "bots" in ss:

    if "messages" not in ss:
        ss.turn = 0
        ss.messages = [Message(0, init_message)]

    for message in ss.messages:
        with box.chat_message(
            name=ss.bots[message.index].name,
            avatar=ss.bots[message.index].avatar
        ):
            st.markdown(message.content)

    if chat:
        ss.turn += 1
        index = ss.turn % len(ss.bots)
        bot = ss.bots[index]
        _ = oai.beta.threads.messages.create(
            thread_id=bot.thread.id,
            role="user",
            content=ss.messages[-1].content,
        )
        run = oai.beta.threads.runs.create(
            thread_id=bot.thread.id,
            assistant_id=bot.assistant.id
        )
        while (
            status := oai.beta.threads.runs.retrieve(run.id, thread_id=bot.thread.id).status
        ) not in ("completed", "failed"):
            sleep(2)
        
        if status == "completed":
            messages = oai.beta.threads.messages.list(bot.thread.id, order="asc")
            new_messages = [msg for msg in messages if msg.run_id == run.id]
            answer = [
                msg_content for msg in new_messages for msg_content in msg.content
            ]
            if all(
                isinstance(content, openai.types.beta.threads.MessageContentText)
                for content in answer
            ):
                answer = "\n".join(content.text.value for content in answer)
        else:
            answer = f"Error: {run}"
        with box.chat_message(name=bot.name, avatar=bot.avatar):
            st.markdown(answer)
        
        ss.messages.append(Message(index, answer))

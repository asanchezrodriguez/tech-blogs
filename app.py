# This is the simplest example of AI Foundry Agent

import os
import chainlit as cl
import logging
from dotenv import load_dotenv
from azure.ai.agents import AgentsClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import (
    MessageRole,
    AgentStreamEvent,
    MessageDeltaChunk,
    ThreadRun,
)

# Load environment variables
load_dotenv()

# Disable verbose connection logs
logger = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
logger.setLevel(logging.WARNING)

# Create an instance of the AgentsClient using DefaultAzureCredential
agents_client = AgentsClient(
    endpoint=os.getenv("AZURE_FOUNDRY_PROJECT_ENDPOINT"),
    credential=DefaultAzureCredential()
)


# Chainlit setup
@cl.on_chat_start
async def on_chat_start():
    # Create a thread for the agent
    if not cl.user_session.get("thread_id"):
        thread = agents_client.threads.create()

        cl.user_session.set("thread_id", thread.id)
        print(f"New Thread ID: {thread.id}")

@cl.on_message
async def on_message(message: cl.Message):
    thread_id = cl.user_session.get("thread_id")
    
    try:
        # Show thinking message to user
        msg = await cl.Message("thinking...", author="agent").send()

        agents_client.messages.create(
            thread_id=thread_id,
            role="user",
            content=message.content,
        )
        
        is_thinking = True        # Run the agent to process tne message in the thread
        with agents_client.runs.stream(thread_id=thread_id, agent_id=os.getenv("AGENT_ID")) as stream:
            msg.content = ""
            for event_type, event_data, _ in stream:
                if isinstance(event_data, MessageDeltaChunk):
                    msg.content += event_data.text
                    if msg:
                        await msg.update()
                    if is_thinking:
                        is_thinking = False

                elif isinstance(event_data, ThreadRun):
                    if event_data.status == "failed":
                        logger.error(f"Run failed. Error: {event_data.last_error}")
                        raise Exception(event_data.last_error)

                elif event_type == AgentStreamEvent.ERROR:
                    logger.error(f"An error occurred. Data: {event_data}")
                    raise Exception(event_data)

        # Get the last message from the agent
        response_message = agents_client.messages.get_last_message_text_by_role(thread_id=thread_id, role=MessageRole.AGENT)
        if not response_message:
            raise Exception("No response from the model.")

        msg.content = response_message.text.value
        await msg.update()

    except Exception as e:
        await cl.Message(content=f"Error: {str(e)}").send()

if __name__ == "__main__":
    # Chainlit will automatically run the application
    pass
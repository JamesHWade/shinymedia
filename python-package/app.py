from shiny import reactive, req
from shiny.express import input, render, ui, session
from shinymedia import input_audio_clip, audio_spinner
from query import chat
from faicons import icon_svg
from htmltools import css

# This will hold the chat history for the current session, allowing us to chat
# with GPT-4o across multiple audio clips.
messages = []

# Add the audio clip input control onto the page.
input_audio_clip(
    "clip",
    reset_on_record=True,
    class_="mt-3 mx-auto",
    style=css(width="600px", max_width="100%"),
    audio_bits_per_second=64000,
)

# A long-running task that actually does the chat with GPT-4o. It takes the
# audio clip and a list of existing messages as input, and returns the chat
# response as a data URL of an audio file.
@reactive.extended_task
async def chat_task(audio_clip, messages, session):
    with ui.Progress(session=session) as p:
        chat_output = await chat(audio_clip, messages, p)
        return chat_output, messages

# When a new audio clip is recorded, we start a chat operation with GPT-4o by
# invoking the chat_task.
@reactive.effect
@reactive.event(input.clip, ignore_none=False)
def start_chat():
    chat_task.cancel()
    req(input.clip())
    print(input.clip())
    chat_task(input.clip(), messages[:], session)

# Show the chat response
@render.express
def response():
    # If the user hasn't started recording their first audio clip, show the
    # instructions.
    if chat_task.status() == "initial":
        with ui.card(class_="mt-3 mx-auto", style=css(width="600px", max_width="100%")):
            ui.markdown(
                """
                **Instructions:** Record a short audio clip to start chatting with GPT-4o.
                After it responds, you can record another clip to continue the conversation.
                Reload the browser to start a new conversation.

                Some ideas to get you started:

                * "What's the weather like today?"
                * "Tell me a joke."
                * "What's your favorite book and why?"
                """
            )
        return

    # If there is no audio clip or if the chat task is still running, show nothing.
    if input.clip() is None or chat_task.status() == "running":
        return

    # This next line will return values if the chat task completed successfully.
    # If the chat task failed with an error, that error will be raised instead.
    chat_result_audio, chat_result_messages = chat_task.result()

    # Update the global messages variable with the new chat history after this
    # interaction.
    global messages
    messages = chat_result_messages[:]

    # Play the chat response audio, with a cool spinner visualization
    audio_spinner(src=chat_result_audio, autodismiss=False)

# Footer with credits and source code link
with ui.panel_fixed(bottom=0, left=0, right=0, height="auto", id="footer"):
    with ui.div(class_="mx-auto", style=css(width="600px", max_width="100%")):
        with ui.div(class_="float-left"):
            "Built in Python with "
            ui.a("Shiny", href="https://shiny.posit.co/py/")
        with ui.div(class_="float-right"):
            with ui.a(href="https://github.com/jcheng5/multimodal"):
                icon_svg("github", margin_right="0.5em")
                "View source code"

# Bit of CSS to make the footer look okay
ui.head_content(
    ui.tags.style(
        """
        #footer {
            padding: 0.5em 0.7em;
            background-color: var(--bs-primary);
            color: white;
        }
        #footer a {
            color: white;
        }
        """
    )
)
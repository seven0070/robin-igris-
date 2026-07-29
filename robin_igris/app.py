"""Gradio chat UI for Robin Igris."""

from __future__ import annotations

import os

import gradio as gr
from dotenv import load_dotenv

from robin_igris.agent import Agent


def create_app() -> gr.Blocks:
    load_dotenv()
    name = os.getenv("AGENT_NAME", "Robin Igris")

    with gr.Blocks(title=name) as demo:
        gr.Markdown(
            f"""
# {name}
Tool-using AI agent — calculator, web search, time, and session notes.

Set OmniRoute running on `:20128` (see `docs/OMNIROUTE.md`). `.env` defaults point there.
"""
        )
        chatbot = gr.Chatbot(height=480, label=name)
        msg = gr.Textbox(placeholder="Ask anything…", label="Message")
        with gr.Row():
            send = gr.Button("Send", variant="primary")
            clear = gr.Button("Clear")

        # Serializable transcript: list of {role, content} for user/assistant only
        transcript = gr.State([])

        def respond(user_text: str, history: list, past: list):
            user_text = (user_text or "").strip()
            history = list(history or [])
            past = list(past or [])
            if not user_text:
                return "", history, past

            agent = Agent()
            for turn in past:
                agent.history.append(
                    {"role": turn["role"], "content": turn["content"]}
                )

            try:
                reply = agent.chat(user_text)
            except Exception as exc:  # noqa: BLE001
                reply = f"Error: {exc}"

            past = past + [
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": reply},
            ]
            history = history + [
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": reply},
            ]
            return "", history, past

        send.click(respond, [msg, chatbot, transcript], [msg, chatbot, transcript])
        msg.submit(respond, [msg, chatbot, transcript], [msg, chatbot, transcript])
        clear.click(lambda: ("", [], []), None, [msg, chatbot, transcript])

    return demo


def main() -> None:
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", "7860")),
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    main()

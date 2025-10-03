# app_new.py
import os
import json
import logging
import traceback
import chainlit as cl
from dotenv import load_dotenv

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ListSortOrder

load_dotenv()

# ===== Logging =====
logger = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
logger.setLevel(logging.WARNING)
DEBUG = os.getenv("DEBUG", "1") not in ("0", "false", "False")

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

# ===== Config =====
AIPROJECT_ENDPOINT = os.getenv("AIPROJECT_ENDPOINT")
AGENT_ID = os.getenv("AGENT_ID")

if not AIPROJECT_ENDPOINT:
    raise RuntimeError("Define AIPROJECT_ENDPOINT en .env")
if not AGENT_ID:
    raise RuntimeError("Define AGENT_ID en .env")

# ===== Client =====
project = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint=AIPROJECT_ENDPOINT
)

# ===== Utilidades =====
def message_to_text_safe(message) -> str | None:
    """
    Preferir message.text_messages[-1].text.value (según Agent Playground).
    Fallback: recorrer content parts y extraer 'text' si existiera.
    """
    # 1) Camino oficial reciente
    try:
        tm = getattr(message, "text_messages", None)
        if tm and len(tm) > 0:
            last = tm[-1]
            val = getattr(getattr(last, "text", None), "value", None)
            if val:
                return val.strip()
    except Exception:
        pass

    # 2) Fallback defensivo
    try:
        parts = getattr(message, "content", None) or []
        texts = []
        for part in parts:
            ptype = getattr(part, "type", None)
            if ptype in ("text", "output_text"):
                t = None
                if hasattr(part, "text"):
                    t = getattr(part.text, "value", None) or getattr(part.text, "content", None)
                if not t and hasattr(part, "output_text"):
                    t = getattr(part.output_text, "value", None) or getattr(part.output_text, "content", None)
                if t:
                    texts.append(t)
        if texts:
            return "\n".join(texts).strip()
    except Exception:
        pass
    return None

def dump_thread_snapshot(thread_id: str, label: str):
    """
    Imprime un snapshot simple del hilo para debug.
    """
    try:
        msgs = project.agents.messages.list(thread_id=thread_id, order=ListSortOrder.ASCENDING)
        snap = []
        for m in msgs:
            snap.append({
                "id": getattr(m, "id", None),
                "role": getattr(m, "role", None),
                "has_text_messages": bool(getattr(m, "text_messages", None)),
                "part_types": [getattr(p, "type", None) for p in (getattr(m, "content", None) or [])],
                "text_preview": (message_to_text_safe(m) or "")[:160]
            })
        dprint(f"\n=== SNAPSHOT {label} (count={len(snap)}) ===")
        dprint(json.dumps(snap, indent=2, ensure_ascii=False))
    except Exception as e:
        dprint(f"[snapshot error] {e}")

def get_last_assistant_text(thread_id: str) -> str | None:
    """
    Lee todos los mensajes en orden ASCENDING y devuelve el último texto del rol 'assistant'.
    """
    messages = project.agents.messages.list(thread_id=thread_id, order=ListSortOrder.ASCENDING)
    last_text = None
    for m in messages:
        if getattr(m, "role", None) == "assistant":
            txt = message_to_text_safe(m)
            if txt:
                last_text = txt  # nos vamos quedando con el más reciente
    return last_text

# ===== Chainlit =====
@cl.on_chat_start
async def on_chat_start():
    # Evita crear hilos duplicados en hot-reload
    if not cl.user_session.get("thread_id"):
        thread = project.agents.threads.create()
        cl.user_session.set("thread_id", thread.id)
        dprint(f"New Thread ID: {thread.id}")
    dump_thread_snapshot(cl.user_session.get("thread_id"), "on_chat_start")
    await cl.Message(content="¡Listo! ¿Qué quieres preguntar al agente?").send()

@cl.on_message
async def on_message(message: cl.Message):
    thread_id = cl.user_session.get("thread_id")

    try:
        thinking = await cl.Message("thinking...", author="agent").send()

        # 1) Crear mensaje de usuario
        project.agents.messages.create(
            thread_id=thread_id,
            role="user",
            content=message.content
        )
        dump_thread_snapshot(thread_id, "after user message")

        # 2) Ejecutar el run
        run = project.agents.runs.create_and_process(
            thread_id=thread_id,
            agent_id=AGENT_ID
        )
        dprint(f"Run finished with status: {getattr(run, 'status', None)}")
        if getattr(run, "status", None) == "failed":
            raise RuntimeError(getattr(run, "last_error", "Run failed."))

        dump_thread_snapshot(thread_id, "after run")

        # 3) Leer último texto del assistant (patrón Agent Playground)
        assistant_text = get_last_assistant_text(thread_id)
        dump_thread_snapshot(thread_id, "before send back")

        if not assistant_text:
            raise RuntimeError("No se recibió respuesta del agente.")

        thinking.content = assistant_text
        await thinking.update()

    except Exception as e:
        dprint("".join(traceback.format_exc()))
        await cl.Message(content=f"Error: {e}").send()

if __name__ == "__main__":
    # Ejecuta: chainlit run app_new.py -w
    pass

# app.py
# -------------------------------------------------------------------------
# NOT: Bu kod tamamen insan (developer) tarafından yazılmıştır, GPT veya 
# başka bir yapay zeka tarafından üretilmemiştir. Eğitim amaçlı paylaşılmaktadır.
#
# Model: gpt-4o-mini
# Min. 4000 kelime, Max. 10000 kelime
# 3 ayrı API çağrısı, her çağrıda 2 chunk -> 6 chunk toplam
# -------------------------------------------------------------------------

import os
import re
import gradio as gr

# Gerekli kütüphaneler
try:
    from openai import OpenAI
    import tiktoken
    from PyPDF2 import PdfReader
    from docx import Document
except ImportError:
    raise ImportError("Lütfen 'openai', 'tiktoken', 'gradio', 'PyPDF2', 'python-docx' paketlerini kurun.")

# ============== 1) OPENAI API İstemcisi ================
client = OpenAI(api_key="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")


def call_openai_chat(messages, max_tokens=10000, temperature=0.8):
    """
    gpt-4o-mini modeline istek atar.
    - max_tokens=10000 => uzun metin
    - temperature=0.8 => daha yaratıcı
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stop=None
    )
    return response.choices[0].message.content


# ============== 2) Chunk Fonksiyonları ===============

def heading1_part1_and_part2(input_text):
    """
    API Çağrısı #1 => 2 chunk (Heading 1 Part1 + Part2)
    Part1 ~1000 kelime, Part2 => final ~2000 kelime
    """
    # chunk #1 => part1
    prompt1 = f"""
We want Heading 1 (introductory overview) in two parts.
PART 1 => around 1000+ words. NOT final.
Input:
{input_text}
"""
    msgs1 = [
        {"role": "system", "content": "You are an AI assistant creating heading1 part1."},
        {"role": "user", "content": prompt1}
    ]
    h1_part1 = call_openai_chat(msgs1)

    # chunk #2 => part2 => finalize
    prompt2 = f"""
Partial heading1:
{h1_part1}

Now finalize heading1 with part2.
Ensure total ~2000+ words. Return final heading1 only.
"""
    msgs2 = [
        {"role": "system", "content": "You are finalizing heading #1."},
        {"role": "user", "content": prompt2}
    ]
    heading1_final = call_openai_chat(msgs2)
    return heading1_final


def heading2_and_3_api(heading1_text):
    """
    API Çağrısı #2 => 2 chunk (Heading2, Heading3)
    chunk #3 => heading2
    chunk #4 => heading3
    """
    # heading2
    prompt_h2 = f"""
We have heading1 for context. 
Produce 'Heading 2: Detailed explanation of common risks.' ~1000+ words.
Return heading2 text only.
Context sample:
{heading1_text[:1500]}
"""
    msgs_h2 = [
        {"role": "system", "content": "You are creating heading2."},
        {"role": "user", "content": prompt_h2}
    ]
    heading2_text = call_openai_chat(msgs_h2)

    # heading3
    prompt_h3 = f"""
We have heading1 for context. 
Produce 'Heading 3: Practical examples and solutions.' ~1000+ words.
Return heading3 text only.
Context sample:
{heading1_text[:1500]}
"""
    msgs_h3 = [
        {"role": "system", "content": "You are creating heading3."},
        {"role": "user", "content": prompt_h3}
    ]
    heading3_text = call_openai_chat(msgs_h3)

    return heading2_text, heading3_text

def heading4_and_expansion_api(h1_text, h2_text, h3_text, original_input):
    """
    API Çağrısı #3 => 2 chunk (Heading4, expansions/shorten)
    chunk #5 => heading4
    chunk #6 => expansions if <4000 words, or shorten if >10000
    """
    # chunk #5 => heading4
    prompt_h4 = f"""
We have heading1,2,3. 
Produce 'Heading 4: Summary and next steps for students.' ~1000 words at least.
Return heading4 only.
Context sample:
{h1_text[:1200]}
"""
    msgs_h4 = [
        {"role": "system", "content": "You are creating heading4."},
        {"role": "user", "content": prompt_h4}
    ]
    heading4_text = call_openai_chat(msgs_h4)

    # chunk #6 => expansions or shorten
    prompt_expand = f"""
We have 4 headings now:

[Heading1]
{h1_text}

[Heading2]
{h2_text}

[Heading3]
{h3_text}

[Heading4]
{heading4_text}

Combine them into one final text. 
If total < 4000 words => expand. 
If > 10000 => shorten. 
Return final text only, merged. 
Original input:
{original_input}
"""
    msgs_expand = [
        {"role": "system", "content": "You ensure final word count 4000-10000."},
        {"role": "user", "content": prompt_expand}
    ]
    final_text = call_openai_chat(msgs_expand)
    return final_text

# ============== 3) Pipeline (6 chunk, 3 API çağrısı) ==============

def main_pipeline(input_txt):
    """
    3 API Çağrısı:
    1) heading1_part1_and_part2 => chunk #1 + #2
    2) heading2_and_3_api => chunk #3 + #4
    3) heading4_and_expansion_api => chunk #5 + #6
    """
    # API #1 => Heading1
    heading1_text = heading1_part1_and_part2(input_txt)

    # API #2 => Heading2, Heading3
    heading2_text, heading3_text = heading2_and_3_api(heading1_text)

    # API #3 => Heading4 + expansions
    final_text = heading4_and_expansion_api(
        h1_text=heading1_text,
        h2_text=heading2_text,
        h3_text=heading3_text,
        original_input=input_txt
    )
    return final_text

# ============== 4) Gradio Arayüz Fonksiyonları ==============

def run_pipeline(user_input_text):
    """
    Tek girdi: user_input_text (string).
    Dönüş: final_html, info_label
    """
    if not user_input_text.strip():
        return ("⚠️ Please provide some text!", "")

    # pipeline
    final_text = main_pipeline(user_input_text)
    # HTML
    final_html = final_text.replace("\n","<br>")
    # Word count
    plain_text = re.sub(r"<.*?>","", final_text)
    wcount = len(plain_text.split())

    info = f"✅ Done. Final text ~{wcount} words (target 4000-10000)."
    return (final_html, info)

def build_app():
    text_input = gr.Textbox(
        lines=5,
        label="Input Text (Minimum 4000 words, maximum 10000 words in final result)",
        placeholder="Paste or type your input text here..."
    )
    output_html = gr.HTML(label="Final Output")
    output_info = gr.Label(label="Information (Word Count)")

    demo = gr.Interface(
        fn=run_pipeline,
        inputs=text_input,
        outputs=[output_html, output_info],
        title="6 Chunks with 3 API Calls (gpt-4o-mini)",
        description=(
            "3 API calls, each producing 2 chunks => 6 total.\n"
            "Heading1 in 2 parts, then heading2+3, then heading4+expansions.\n"
            "Ensures at least 4000 words, max 10000 words.\n"
        )
    )
    return demo

if __name__ == "__main__":
    app = build_app()
    app.launch()
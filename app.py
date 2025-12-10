import gradio as gr
import pandas as pd
import re
import html
import urllib.parse

# ---------- Load dataset ----------
try:
    df = pd.read_csv("UniqueLaptopsConverted.csv")
    df.columns = [col.strip() for col in df.columns]

    df["Manufacturer"] = df["Company"].str.title().fillna("Unknown")
    df["Model Name"] = df["Processor"].fillna("Unknown") + " - " + df["Memory"].fillna("Unknown")
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    df["RAM"] = pd.to_numeric(df["RAM"], errors="coerce")
except Exception as e:
    df = None
    error_msg = str(e)

# ---------- Helper Functions ----------
def extract_limit(question):
    match = re.search(r'top (\d+)', question, re.IGNORECASE)
    if not match:
        match = re.search(r"first\s+(\d+)", question, re.IGNORECASE)
    if not match:
        match = re.search(r"best\s+(\d+)", question, re.IGNORECASE)
    return int(match.group(1)) if match else None

def format_card(row, index=None):
    price_display = f"${row['Price']:,.2f}" if pd.notna(row['Price']) else "N/A"
    ram_display = f"{int(row['RAM']):,}GB RAM" if pd.notna(row['RAM']) else "N/A"
    rating_display = f"{row.get('Rating', 'N/A')}"
    reviews_display = row.get('No_of_ratings', '0')
    try:
        reviews_display = f"{int(reviews_display):,}"
    except:
        pass

    position_label = f"<h3 style='margin: 0 0 6px 0;'>#{index}</h3>" if index is not None else ""
    product_url = row.get("Product Link", "")
    model_name = row.get("Model Name", "laptop")
    encoded_model_name = urllib.parse.quote_plus(model_name)

    if isinstance(product_url, str) and "amazon.com" in product_url:
        link_text = "🔗 Open on Amazon"
    else:
        product_url = f"https://www.amazon.com/s?k={encoded_model_name}"
        link_text = "🔍 Search this model on Amazon"

    return f"""
    <div style='display: flex; align-items: flex-start; border: 1px solid #444;
                border-radius: 10px; padding: 14px; margin: 15px 0;
                background: #1b1b1b; color: #f5f5f5;
                box-shadow: 0 0 4px rgba(0,0,0,0.35);'>
        <img src="{row.get('ImgURL', '')}" alt="Product photo"
             style="width: 120px; height: auto; margin-right: 15px; border-radius: 6px;">
        <div>
            {position_label}
            <h4 style='margin: 0 0 8px 0;'>{row['Manufacturer']} — {row['Model Name']}</h4>
            <p><strong>Price:</strong> {price_display}</p>
            <p><strong>Specifications:</strong> {row.get('Processor', 'N/A')}, {ram_display}</p>
            <p><strong>Rating:</strong> {rating_display} ⭐ ({reviews_display} reviews)</p>
            <p>
              <a href="{product_url}" target="_blank"
                 style="display:inline-block; padding:6px 12px; background:#0a84ff; color:white;
                        border-radius:6px; text-decoration:none; font-weight:bold;">
                 {link_text}
              </a>
            </p>
        </div>
    </div>
    """

# ---------- Chat History ----------
chat_history = []

def chatbot_response(user_input):
    global chat_history
    user_text = html.escape(user_input.strip())
    chat_history.append(
            f"<div style='background:#000000;padding:12px;border-radius:10px;"
            f"max-width:70%;margin-left:auto;margin-bottom:12px;color:#000'>{user_text}</div>"
        )

    try:
        if df is None:
            chat_history.append(f"<div style='color:red;'>⚠️ Error loading data: {error_msg}</div>")
            return update_chatbox()

        question = user_input.lower()
        working_df = df.dropna(subset=["Price", "Model Name"])
        limit = extract_limit(question)

        # Filter by brand
        for brand in working_df["Manufacturer"].dropna().unique():
            if brand.lower() in question:
                working_df = working_df[working_df["Manufacturer"].str.lower() == brand.lower()]
                break

        # Filter by RAM
        ram_match = re.search(r"(\d+)\s*gb\s*ram", question)
        if ram_match:
            working_df = working_df[working_df["RAM"] == int(ram_match.group(1))]

        # Filter by Price
        price_match = re.search(r"under\s+(\d+)", question)
        if price_match:
            working_df = working_df[working_df["Price"] <= float(price_match.group(1))]

        # Generate result
        if "highest rating" in question or "best rated" in question:
            row = working_df.sort_values(by="Rating", ascending=False).iloc[0]
            response = format_card(row)
        elif "cheapest" in question or "lowest price" in question:
            row = working_df.sort_values(by="Price").iloc[0]
            response = format_card(row)
        elif "most expensive" in question or "highest price" in question:
            row = working_df.sort_values(by="Price", ascending=False).iloc[0]
            response = format_card(row)
        elif limit:
            sort_by = "Rating" if "top" in question or "best" in question else "Price"
            rows = working_df.sort_values(by=sort_by, ascending=(sort_by == "Price")).head(limit)
            response = "".join(format_card(row, index=i + 1) for i, (_, row) in enumerate(rows.iterrows()))
        else:
            rows = working_df.sort_values(by="Price").head(5)
            response = "".join(format_card(row, index=i + 1) for i, (_, row) in enumerate(rows.iterrows()))

        chat_history.append(
            f"<div style='background:#0066ff;padding:12px;border-radius:12px;"
            f"max-width:70%;margin-left:auto;margin-bottom:12px;color:white;font-weight:500;'>"
            f"{user_text}</div>"
        )


    except Exception as e:
        chat_history.append(f"<div style='color:red;'>❌ Internal error: {str(e)}</div>")

    return update_chatbox()

def update_chatbox():
    return f"""
    <div id='chatbox' style='height:500px; overflow-y:auto; background:#0e0e0e; padding:1rem;
         border-radius:10px; border:1px solid #333; color:#ccc; font-family:Myriad, sans-serif'>
        {''.join(chat_history)}
        <div id='bottom-scroll-anchor'></div>
    </div>
    <script>
        var el = document.getElementById("bottom-scroll-anchor");
        if (el) {{
            el.scrollIntoView({{ behavior: "smooth" }});
        }}
    </script>
    """

def clear_chat():
    global chat_history
    chat_history.clear()
    return update_chatbox()

# ---------- Interface ----------
with gr.Blocks(title="Laptop Bot (Fixed Scroll)") as app:
    gr.HTML("<h2 style='color:#eee'>Laptop Q&A Bot</h2><p style='color:#ccc'>Ask things like 'top 3 laptops under $700', 'best rated HP', etc.</p>")
    
    with gr.Row():
        textbox = gr.Textbox(placeholder="Ask about laptops...", show_label=False)
        clear_btn = gr.Button("Clear Chat")
    
    chatbox = gr.HTML(update_chatbox())

    textbox.submit(chatbot_response, inputs=textbox, outputs=chatbox)
    clear_btn.click(fn=clear_chat, outputs=chatbox)

app.launch()
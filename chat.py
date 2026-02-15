import streamlit as st
import google.generativeai as genai
from lk20_data import hent_kunnskapsprofil 

# ==========================================
# 1. API OG KONFIGURASJON (RETTET)
# ==========================================
try:
    # Sjekker om nøkkelen finnes i secrets.toml
    if "GOOGLE_API_KEY" in st.secrets:
        # Henter nøkkelen sikkert
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    else:
        st.error("Fant ikke GOOGLE_API_KEY. Har du husket secrets.toml?")
        
except FileNotFoundError:
    st.error("Finner ikke .streamlit/secrets.toml-filen. Sjekk mappen!")
except Exception as e:
    st.error(f"En uventet feil oppstod: {e}")

st.set_page_config(page_title="LK20-Simulator", layout="wide")

# ==========================================
# 2. SIDEBAR
# ==========================================
with st.sidebar:
    st.header("Innstillinger")
    alle_trinn = [f"{i}. trinn" for i in range(1, 11)]
    trinn = st.selectbox("Velg klassetrinn:", alle_trinn, index=4) 
    
    begrep = st.text_input("Tema:", "Brøk")
    
    if st.button("Nullstill", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    with st.expander("Se elevens hjerne"):
        data = hent_kunnskapsprofil(trinn)
        st.caption(f"**Kan fra før:** {data['kjent']}")
        st.caption(f"**Lærer nå:** {data['laerer_naa']}")

# ==========================================
# 3. ELEV-PERSONA
# ==========================================
profil = hent_kunnskapsprofil(trinn)

system_instruks = f"""
DU ER EN ELEV PÅ {trinn}.
Læreren prøver å forklare deg '{begrep}'.

DIN KUNNSKAPSBANK:
1. DETTE KAN DU GODT: {profil['kjent']}
2. DETTE ER NYTT OG VANSKELIG: {profil['laerer_naa']}
3. DETTE KAN DU IKKE: Alt over {trinn}.

REGLER:
- Du vet IKKE hva '{begrep}' er med mindre det står under "DETTE KAN DU GODT".
- ALDRI forklar begrepet tilbake til læreren.
- Still spørsmål. Vær litt usikker.
- Snakk norsk som en elev på {trinn}.
"""

# ==========================================
# 4. CHAT
# ==========================================
# HER ER ENDRINGEN DU BA OM:
st.title(f"Forklar '{begrep}' til en elev på {trinn}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    icon = "🧑‍🏫" if m["role"] == "user" else "🧒"
    with st.chat_message(m["role"], avatar=icon):
        st.markdown(m["content"])

if prompt := st.chat_input("Skriv din forklaring..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍🏫"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🧒"):
        try:
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash", 
                system_instruction=system_instruks
            )
            
            history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                       for m in st.session_state.messages[:-1]]
            
            chat = model.start_chat(history=history)
            response = chat.send_message(prompt)
            
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            st.error(f"Feil: {e}")
import streamlit as st
import google.generativeai as genai
from lk20_data import hent_kunnskapsprofil 

# ==========================================
# 1. API OG KONFIGURASJON
# ==========================================
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    else:
        st.error("Mangler API-nøkkel i .streamlit/secrets.toml")
except Exception as e:
    st.error(f"Feil ved oppstart: {e}")

st.set_page_config(page_title="LK20-Simulator", layout="wide")

# ==========================================
# 2. SIDEBAR MED VEILEDER
# ==========================================
with st.sidebar:
    st.header("Innstillinger")
    alle_trinn = [f"{i}. trinn" for i in range(1, 11)]
    trinn = st.selectbox("Velg klassetrinn:", alle_trinn, index=4) 
    
    begrep = st.text_input("Tema:", "Brøk")
    
    if st.button("Nullstill samtale", use_container_width=True):
        st.session_state.messages = []
        st.session_state.veiledning = None # Nullstiller veilederen også
        st.rerun()

    st.divider()
    
    # --- HER ER VEILEDEREN TILBAKE ---
    st.subheader("👩‍🏫 Pedagogisk Veileder")
    st.info("Når du er ferdig med forklaringen, trykk her for å få en vurdering.")
    
    if st.button("Gi meg tilbakemelding", type="primary", use_container_width=True):
        st.session_state.be_om_veiledning = True

    # Vis kunnskapsdata (for debugging/info)
    with st.expander("Se elevens forutsetninger"):
        data = hent_kunnskapsprofil(trinn)
        st.caption(f"**Kan fra før:** {data['kjent']}")
        st.caption(f"**Lærer nå:** {data['laerer_naa']}")

# ==========================================
# 3. ELEV-PERSONA
# ==========================================
profil = hent_kunnskapsprofil(trinn)

system_instruks_elev = f"""
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
# 4. CHAT-GRENSESNITT
# ==========================================
st.title(f"Forklar '{begrep}' til en elev på {trinn}")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Vis historikk
for m in st.session_state.messages:
    icon = "🧑‍🏫" if m["role"] == "user" else "🧒"
    with st.chat_message(m["role"], avatar=icon):
        st.markdown(m["content"])

# Input-felt
if prompt := st.chat_input("Skriv din forklaring..."):
    # Lagre og vis lærers melding
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍🏫"):
        st.markdown(prompt)

    # Generer elevens svar
    with st.chat_message("assistant", avatar="🧒"):
        try:
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash", 
                system_instruction=system_instruks_elev
            )
            
            # Konverter historikk
            history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                       for m in st.session_state.messages[:-1]]
            
            chat = model.start_chat(history=history)
            response = chat.send_message(prompt)
            
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            st.error(f"Feil: {e}")

# ==========================================
# 5. VEILEDER-LOGIKK (KJØRER ETTER KNAPPETRYKK)
# ==========================================
if st.session_state.get("be_om_veiledning", False):
    st.divider()
    with st.chat_message("assistant", avatar="📝"):
        st.subheader("Pedagogisk Vurdering")
        with st.spinner("Analyserer samtalen din..."):
            
            # Vi lager en ny instruks for "sensoren"
            veileder_instruks = f"""
            Du er en erfaren praksisveileder i lærerutdanningen.
            Analyser samtalen over mellom en lærerstudent og en simulert elev på {trinn}.
            Temaet var: {begrep}.

            Vurder følgende (vær konkret og konstruktiv):
            1. **Språkbruk:** Var det tilpasset {trinn}? Unngikk studenten for vanskelige ord?
            2. **Forståelse:** Sjekket studenten om eleven faktisk forstod underveis?
            3. **Elevaktivitet:** Fikk eleven lov til å tenke selv, eller ble det bare forelesning?
            
            Gi en kort oppsummering og et tips til neste gang.
            """
            
            # Samler hele samtalen i én tekststreng
            samtale_tekst = "\n".join([f"{m['role']}: {

import streamlit as st
import google.generativeai as genai

# ==========================================
# 1. API OG KONFIGURASJON
# ==========================================
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    else:
        st.error("Mangler API-nøkkel! Sjekk secrets.")
        st.stop()
except Exception as e:
    st.error(f"Feil ved tilkobling: {e}")
    st.stop()

st.set_page_config(page_title="LK20-Simulator", layout="wide", page_icon="🎓")

# ==========================================
# 2. HENT FAKTISKE MODELLER (INGEN FILTRERING)
# ==========================================
@st.cache_data
def hent_alle_modeller():
    """Henter absolutt alt nøkkelen din har tilgang til."""
    try:
        alle = genai.list_models()
        # Vi tar med alt som støtter 'generateContent'
        tilgjengelige = [m.name for m in alle if 'generateContent' in m.supported_generation_methods]
        
        # Hvis listen er tom, legger vi til gammel klassiker som backup
        if not tilgjengelige:
            return ["models/gemini-pro"] 
            
        return tilgjengelige
    except Exception as e:
        st.error(f"Klarte ikke hente liste: {e}")
        return ["models/gemini-pro"]

mine_modeller = hent_alle_modeller()

# ==========================================
# 3. SIDEBAR
# ==========================================
with st.sidebar:
    st.header("🔧 Teknisk")
    
    # VISER ALT RÅTT - Velg det som ser ut som "flash" eller "pro"
    valgt_modell = st.selectbox("Velg modell (Din liste):", mine_modeller)
    
    st.info(f"Du bruker nå: **{valgt_modell}**")
    st.caption("Tips: Prøv en annen i listen hvis du får feilmelding.")

    st.divider()
    st.header("🎓 Pedagogisk (LK20)")
    
    trinn_valg = st.slider("Velg klassetrinn:", min_value=1, max_value=10, value=5)
    trinn_tekst = f"{trinn_valg}. trinn"
    begrep = st.text_input("Tema:", "Brøk")
    
    if st.button("Nullstill samtale", use_container_width=True):
        st.session_state.messages = []
        st.session_state.veiledning = None
        st.session_state.be_om_veiledning = False
        st.rerun()

    st.divider()
    st.subheader("👩‍🏫 Veileder")
    if st.button("Gi meg tilbakemelding", type="primary", use_container_width=True):
        st.session_state.be_om_veiledning = True

# ==========================================
# 4. HJERNE (LK20-SIMULERING)
# ==========================================
system_instruks_elev = f"""
DIN ROLLE:
Du er en elev i norsk grunnskole på {trinn_tekst}.
Tema: '{begrep}'.

DIN KUNNSKAP (LK20):
Du baserer alt du kan på **Læreplan i matematikk (MAT01-05)**.
- Du KAN kompetansemål opp til {trinn_valg - 1}. trinn.
- Du LÆRER kompetansemål for {trinn_tekst} (vær litt usikker her).
- Du KAN IKKE stoff fra {trinn_valg + 1}. trinn eller oppover.

DINE INSTRUKSJONER:
- Du vet IKKE hva '{begrep}' er med mindre det er pensum på lavere trinn.
- **Vær passiv:** Ikke driv samtalen.
- **Ikke still "sosiale" spørsmål** ("Hva synes du?", "Liker du matte?").
- **Ikke forklar tilbake.**
- Hvis læreren bruker ord fra høyere trinn, spør: "Hva betyr det?".
- Snakk som en på {trinn_valg}. trinn.
"""

# ==========================================
# 5. CHAT
# ==========================================
st.title(f"Undervisning: {begrep} ({trinn_tekst})")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    icon = "🧑‍🏫" if m["role"] == "user" else "🧒"
    with st.chat_message(m["role"], avatar=icon):
        st.markdown(m["content"])

if prompt := st.chat_input("Start undervisningen..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍🏫"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🧒"):
        try:
            model = genai.GenerativeModel(
                model_name=valgt_modell, 
                system_instruction=system_instruks_elev
            )
            
            history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                       for m in st.session_state.messages[:-1]]
            
            chat = model.start_chat(history=history)
            response = chat.send_message(prompt)
            
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            feil = str(e)
            st.error(f"Feil med {valgt_modell}:")
            if "429" in feil:
                st.warning("⚠️ Kvote full. Prøv en annen modell i menyen.")
            elif "404" in feil:
                st.warning("⚠️ Modellen finnes ikke. Prøv en annen.")
            else:
                st.warning(feil)

# ==========================================
# 6. VEILEDER
# ==========================================
if st.session_state.get("be_om_veiledning", False):
    st.divider()
    with st.chat_message("assistant", avatar="📝"):
        st.subheader("Pedagogisk Vurdering (LK20)")
        with st.spinner("Sjekker mot læreplanen..."):
            
            veileder_instruks = f"""
            Du er praksisveileder. Analyser samtalen basert på **LK20**.
            Eleven går på {trinn_tekst}. Tema: {begrep}.
            Vurder nivåtilpasning og progresjon. Vær kort.
            """
            
            logg = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            
            try:
                veileder_model = genai.GenerativeModel(model_name=valgt_modell, system_instruction=veileder_instruks)
                analyse = veileder_model.generate_content(f"Logg:\n{logg}")
                st.markdown(analyse.text)
            except Exception as e:
                st.warning("Kunne ikke kjøre veileder.")
    
    st.session_state.be_om_veiledning = False

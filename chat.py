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
# 2. SMARTERE MODELL-VELGER
# ==========================================
@st.cache_data
def finn_beste_modeller():
    """Finner modeller og sorterer dem etter kvote-størrelse."""
    try:
        alle = genai.list_models()
        chat_modeller = [m.name for m in alle if 'generateContent' in m.supported_generation_methods]
        
        # --- SORTERINGSLOGIKK (VIKTIG!) ---
        # Vi vil ha modellene i denne rekkefølgen:
        # 1. gemini-1.5-flash (Mest stabil, høyest kvote)
        # 2. gemini-1.5-flash-latest (Nyere, men også bra)
        # 3. Andre "flash"-modeller
        # 4. Alt annet (Pro, 2.0, exp - disse har lav kvote)
        
        def sorterings_nokkel(navn):
            if "gemini-1.5-flash" in navn and "latest" not in navn: return 0  # Gullmedalje
            if "gemini-1.5-flash" in navn: return 1                           # Sølv
            if "flash" in navn: return 2                                      # Bronse
            return 3                                                          # Resten

        chat_modeller.sort(key=sorterings_nokkel)
        return chat_modeller
    except Exception as e:
        # Hvis vi ikke får hentet listen, tvinger vi fram arbeidshesten
        return ["models/gemini-1.5-flash", "models/gemini-1.5-pro"]

mine_modeller = finn_beste_modeller()

# ==========================================
# 3. SIDEBAR
# ==========================================
with st.sidebar:
    st.header("🔧 Teknisk")
    # Den øverste i listen er nå den med høyest kvote!
    valgt_modell = st.selectbox("Aktiv AI-modell:", mine_modeller, index=0)
    
    st.info(f"Valgt modell: **{valgt_modell.split('/')[-1]}**\n\nHvis denne går tom, velg nr 2 i listen.")

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
# 4. HJERNE (LK20)
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
- Hvis læreren bruker ord fra høyere trinn (f.eks algebra på barneskolen), spør: "Hva betyr det?".
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
            # Her fanger vi opp kvote-feil og gir en tydelig beskjed
            feil = str(e)
            if "429" in feil:
                st.error("🛑 STOPP! Dagskvoten for denne modellen er oppbrukt.")
                st.info("👉 Gå til menyen til venstre og bytt til en annen modell (prøv den neste på listen).")
            elif "404" in feil:
                st.error("Denne modellen er ikke tilgjengelig. Prøv en annen i menyen.")
            else:
                st.error(f"En feil oppstod: {e}")

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
                # Veilederen bruker også den valgte modellen
                veileder_model = genai.GenerativeModel(model_name=valgt_modell, system_instruction=veileder_instruks)
                analyse = veileder_model.generate_content(f"Logg:\n{logg}")
                st.markdown(analyse.text)
            except Exception as e:
                st.warning("Kunne ikke kjøre veileder (sannsynligvis pga kvote).")
    
    st.session_state.be_om_veiledning = False

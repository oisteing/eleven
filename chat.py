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
# 2. AUTO-PILOT (Modellvelger)
# ==========================================
@st.cache_data
def finn_tilgjengelige_modeller():
    try:
        alle = genai.list_models()
        chat_modeller = [m.name for m in alle if 'generateContent' in m.supported_generation_methods]
        # Sorterer slik at Flash (rask/gratis) kommer først
        chat_modeller.sort(key=lambda x: "flash" not in x) 
        return chat_modeller
    except Exception as e:
        return ["models/gemini-1.5-flash"]

mine_modeller = finn_tilgjengelige_modeller()

# ==========================================
# 3. SIDEBAR
# ==========================================
with st.sidebar:
    st.header("🔧 Teknisk")
    valgt_modell = st.selectbox("Aktiv AI-modell:", mine_modeller, index=0)

    st.divider()
    st.header("🎓 Pedagogisk (LK20)")
    
    # Vi bruker tallverdier for trinnet for å kunne regne med dem
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
    
    st.info(f"Eleven simuleres nå basert på LK20 kompetansemål for {trinn_tekst}.")

# ==========================================
# 4. GENERER "HJERNE" BASERT PÅ LK20
# ==========================================
# Her ber vi AI-en definere eleven basert på sin egen kunnskap om LK20
system_instruks_elev = f"""
DIN ROLLE:
Du er en elev i norsk grunnskole som går på {trinn_tekst}.
Vi simulerer en undervisningssituasjon om temaet '{begrep}'.

DIN KUNNSKAPSBASIS (VIKTIG):
Du skal basere din kunnskap og forståelse STRENGT på **Læreplan i matematikk fellesfag (MAT01-05) fra LK20**.

1. **Hva du kan:** Du behersker kompetansemålene for alle trinn opp til og med {trinn_valg - 1}. trinn.
2. **Hva du lærer nå:** Du jobber med kompetansemålene for {trinn_tekst}. Dette er din "sone for den nærmeste utvikling". Du kan dette litt, men er usikker.
3. **Hva du IKKE kan:** Du kjenner IKKE til begreper eller metoder som tilhører kompetansemålene for {trinn_valg + 1}. trinn eller høyere. Hvis læreren bruker slike begreper, må du bli forvirret.

DINE INSTRUKSJONER FOR OPPFØRSEL:
- Du vet IKKE hva '{begrep}' er med mindre det er tydelig dekket i kompetansemålene for lavere trinn.
- **Vær passiv:** Ikke driv samtalen. Læreren må lede.
- **Ikke vær "flinkis":** Ikke still pedagogiske spørsmål tilbake til læreren (f.eks. "Hva synes du om brøk?").
- **Reager:** Hvis læreren forklarer bra (tilpasset ditt LK20-nivå), vis forståelse. Hvis læreren bruker ord fra høyere trinn, spør "Hva betyr det?".
- Språk: Snakk naturlig norsk tilpasset en alder av {trinn_valg + 6} år.

Eksempel på nivå-sjekk:
Hvis du går på 5. trinn og læreren snakker om "ukjent x" (algebra), skal du si "Hva er x? Det har vi ikke lært". (Fordi algebra kommer senere i LK20).
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
            st.error(f"Feilmelding: {e}")
            if "429" in str(e):
                st.warning("⚠️ Kvote full. Bytt modell i menyen!")

# ==========================================
# 6. VEILEDER (MED LK20-FOKUS)
# ==========================================
if st.session_state.get("be_om_veiledning", False):
    st.divider()
    with st.chat_message("assistant", avatar="📝"):
        st.subheader("Pedagogisk Vurdering (LK20)")
        with st.spinner("Sjekker mot læreplanen..."):
            
            veileder_instruks = f"""
            Du er en streng praksisveileder. 
            Analyser samtalen basert på **LK20 (Læreplan i matematikk)**.
            
            Eleven går på {trinn_tekst}.
            Tema: {begrep}.

            Sjekk spesielt:
            1. **Nivå:** Traff studenten riktig kompetansemål for {trinn_tekst}? (Eller ble det for vanskelig/lett?)
            2. **Progresjon:** Bygget studenten på kunnskap fra lavere trinn?
            
            Gi en kort, faglig tilbakemelding.
            """
            
            logg = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            
            try:
                veileder_model = genai.GenerativeModel(model_name=valgt_modell, system_instruction=veileder_instruks)
                analyse = veileder_model.generate_content(f"Logg:\n{logg}")
                st.markdown(analyse.text)
            except Exception as e:
                st.error(f"Veileder feilet: {e}")
    
    st.session_state.be_om_veiledning = False

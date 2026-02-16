import streamlit as st
import google.generativeai as genai
import random
# Husk at vi fremdeles bruker den nye pedagogikk-filen din:
from pedagogikk import hent_veileder_instruks 

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
# 2. NAVNE-GENERATOR
# ==========================================
def tilfeldig_navn():
    navn_liste = [
        "Emma", "Nora", "Sofie", "Ella", "Olivia", "Ada", "Sara", "Maja", "Ingrid", "Emilie",
        "Noah", "Jakob", "Lucas", "Emil", "Oliver", "Isak", "William", "Filip", "Aksel", "Henrik",
        "Magnus", "Olav", "Håkon", "Sigrid", "Anna", "Solveig", "Tiril", "Astrid", "Mathias", "Elias"
    ]
    return random.choice(navn_liste)

# ==========================================
# 3. MODELL-LISTE
# ==========================================
@st.cache_data
def hent_alle_modeller():
    try:
        alle = genai.list_models()
        tilgjengelige = [m.name for m in alle if 'generateContent' in m.supported_generation_methods]
        if not tilgjengelige: return ["models/gemini-1.5-flash"]
        return tilgjengelige
    except:
        return ["models/gemini-1.5-flash"]

mine_modeller = hent_alle_modeller()

# ==========================================
# 4. SIDEBAR & TILSTAND
# ==========================================
if "elev_navn" not in st.session_state:
    st.session_state.elev_navn = tilfeldig_navn()
if "last_trinn" not in st.session_state:
    st.session_state.last_trinn = 5
if "last_begrep" not in st.session_state:
    st.session_state.last_begrep = "Brøk"

with st.sidebar:
    st.header("🔧 Innstillinger")
    valgt_modell = st.selectbox("Aktiv AI-modell:", mine_modeller)
    
    st.divider()
    st.header("🎓 Oppgave (LK20)")
    
    trinn_valg = st.slider("Velg klassetrinn:", 1, 10, 5)
    begrep = st.text_input("Tema:", "Brøk")

    endring_skjedd = (trinn_valg != st.session_state.last_trinn) or (begrep != st.session_state.last_begrep)
    
    if endring_skjedd:
        st.session_state.elev_navn = tilfeldig_navn()
        st.session_state.messages = []
        st.session_state.veiledning = None
        st.session_state.be_om_veiledning = False
        st.session_state.last_trinn = trinn_valg
        st.session_state.last_begrep = begrep
        st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Nullstill chat"):
            st.session_state.messages = []
            st.session_state.veiledning = None
            st.session_state.be_om_veiledning = False
            st.rerun()
    with col2:
        if st.button("Ny elev"):
            st.session_state.elev_navn = tilfeldig_navn()
            st.session_state.messages = []
            st.session_state.be_om_veiledning = False
            st.rerun()

    st.divider()
    st.subheader("👩‍🏫 Veileder")
    if st.button("Gi meg tilbakemelding", type="primary", use_container_width=True):
        st.session_state.be_om_veiledning = True

# ==========================================
# 5. HJERNE (SYSTEM PROMPT - STRENGTHENED)
# ==========================================
elev_navn = st.session_state.elev_navn
trinn_tekst = f"{trinn_valg}. trinn"

# HER ER ENDRINGEN: Mye strengere instruks mot "lekkasje"
system_instruks_elev = f"""
VIKTIG: DU ER I ROLLE NÅ. IKKE bryt karakteren.

DIN ROLLE:
Navn: {elev_navn}.
Alder: {trinn_valg + 6} år (Går i {trinn_tekst}).
Tema vi snakker om: '{begrep}'.

DIN HUKOMMELSE:
Du husker ting fra lavere trinn, men du aner ikke hva "LK20", "kompetansemål" eller "læreplan" er. Det er lærerspråk.

REGLER FOR OPPFØRSEL:
1. Hvis læreren spør "Hva kan du om {begrep}?", skal du svare VAGT og ENKELT.
   - RIKTIG: "Vi hadde litt om det i fjor, men jeg husker ikke helt." eller "Er det det med pizza?"
   - FEIL: "I henhold til instruksen min kan jeg målene for 4. trinn." (ALDRI SI DETTE!)
   - FEIL: "Jeg baserer kunnskapen min på MAT01-05."
2. Du skal aldri vise din "indre tenkning" eller forklare hvorfor du svarer som du gjør. Bare gi svaret.
3. Vær litt passiv/usikker. Ikke hold foredrag.
4. Snakk som et barn/ungdom på {trinn_tekst}. Korte setninger.

START NÅ. VÆR {elev_navn}.
"""

# ==========================================
# 6. CHAT-VISNING
# ==========================================
st.title(f"Forklar '{begrep}' til {elev_navn} ({trinn_tekst})")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    navn_visning = "🧑‍🏫 Lærer" if m["role"] == "user" else f"🧒 {elev_navn}"
    icon = "🧑‍🏫" if m["role"] == "user" else "🧒"
    
    with st.chat_message(m["role"], avatar=icon):
        st.write(f"**{navn_visning}**")
        st.markdown(m["content"])

if prompt := st.chat_input(f"Snakk til {elev_navn}..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍🏫"):
        st.write("**🧑‍🏫 Lærer**")
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
            
            st.write(f"**🧒 {elev_navn}**")
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            feil = str(e)
            st.error("Noe gikk galt med AI-en.")
            if "429" in feil: st.warning("Kvote full. Bytt modell i menyen.")
            elif "404" in feil: st.warning("Modellen finnes ikke. Prøv en annen.")
            else: st.warning(feil)

# ==========================================
# 7. VEILEDER (HENTER FRA PEDAGOGIKK.PY)
# ==========================================
if st.session_state.get("be_om_veiledning", False):
    st.divider()
    with st.chat_message("assistant", avatar="🧐"):
        st.subheader("Pedagogisk Analyse")
        with st.spinner(f"Analyserer didaktikken i samtalen med {elev_navn}..."):
            
            # Henter den avanserte instruksen fra den andre filen din
            veileder_instruks = hent_veileder_instruks(elev_navn, trinn_tekst, begrep)
            
            logg = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            
            try:
                veileder_model = genai.GenerativeModel(model_name=valgt_modell, system_instruction=veileder_instruks)
                analyse = veileder_model.generate_content(f"Her er transkripsjonen av undervisningen:\n{logg}")
                st.markdown(analyse.text)
            except Exception as e:
                st.warning("Kunne ikke kjøre veileder.")
    
    st.session_state.be_om_veiledning = False

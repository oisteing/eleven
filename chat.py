import streamlit as st
import google.generativeai as genai
import random
import time
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
# 3. SMART MODELL-VELGER (RESERVEMOTOR)
# ==========================================
def generer_svar_med_fallback(prompt, history, system_instruks):
    """
    Prøver en liste med modeller etter tur. 
    Hvis én er full eller nede, prøver den neste automatisk.
    """
    # Dette er prioriteringslisten over modeller med best kvote akkurat nå:
    modeller_aa_prove = [
        "gemini-2.0-flash-lite-preview-02-05", # Ny, rask og høy kvote
        "gemini-2.0-flash",                    # Standard ny modell
        "gemini-1.5-flash",                    # Den gamle arbeidshesten
        "gemini-1.5-flash-8b",                 # Super-lettvekter (backup)
    ]

    siste_feil = ""

    for modell_navn in modeller_aa_prove:
        try:
            # Prøver å koble til modellen
            model = genai.GenerativeModel(
                model_name=modell_navn, 
                system_instruction=system_instruks
            )
            
            chat = model.start_chat(history=history)
            response = chat.send_message(prompt)
            
            # Hvis vi kommer hit, virket det! Returner svaret.
            return response.text, modell_navn
            
        except Exception as e:
            # Hvis det feilet, lagre feilen og prøv neste i listen
            siste_feil = str(e)
            time.sleep(1) # Vent litt før neste forsøk
            continue
    
    # Hvis ALLE feilet:
    return f"Beklager, alle AI-modellene er opptatt akkurat nå. Feil: {siste_feil}", "Ingen"

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
    st.caption("Systemet velger automatisk den beste tilgjengelige modellen (Flash Lite / Flash 1.5).")
    
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
# 5. HJERNE (SYSTEM PROMPT)
# ==========================================
elev_navn = st.session_state.elev_navn
trinn_tekst = f"{trinn_valg}. trinn"

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
   - FEIL: "I henhold til instruksen min kan jeg målene for 4. trinn."
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
        # Konverter historikk
        history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                   for m in st.session_state.messages[:-1]]
        
        # --- HER BRUKER VI DEN NYE FALLBACK-FUNKSJONEN ---
        with st.spinner(f"{elev_navn} tenker..."):
            svar_tekst, brukt_modell = generer_svar_med_fallback(prompt, history, system_instruks_elev)
        
        # (Valgfritt: Vis hvilken modell som ble brukt i en liten notis for debugging)
        # st.caption(f"Teknisk info: Svar generert av {brukt_modell}")

        st.write(f"**🧒 {elev_navn}**")
        st.markdown(svar_tekst)
        st.session_state.messages.append({"role": "assistant", "content": svar_tekst})

# ==========================================
# 7. VEILEDER (MED FALLBACK)
# ==========================================
if st.session_state.get("be_om_veiledning", False):
    st.divider()
    with st.chat_message("assistant", avatar="🧐"):
        st.subheader("Pedagogisk Analyse")
        with st.spinner(f"Analyserer didaktikken i samtalen med {elev_navn}..."):
            
            veileder_instruks = hent_veileder_instruks(elev_navn, trinn_tekst, begrep)
            logg = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            
            # Bruker også fallback-funksjonen for veilederen!
            analyse, _ = generer_svar_med_fallback(f"Her er loggen:\n{logg}", [], veileder_instruks)
            
            st.markdown(analyse)
    
    st.session_state.be_om_veiledning = False

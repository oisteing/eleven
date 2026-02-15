import streamlit as st
import google.generativeai as genai
from lk20_data import hent_kunnskapsprofil 

# ==========================================
# 1. API OG KONFIGURASJON
# ==========================================
try:
    # Sjekker både secrets.toml (lokalt) og Streamlit Cloud secrets
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
# 2. FINN TILGJENGELIGE MODELLER (AUTO-PILOT)
# ==========================================
@st.cache_data
def finn_tilgjengelige_modeller():
    """Spør Google: Hvilke modeller har jeg lov til å bruke?"""
    try:
        alle = genai.list_models()
        # Vi vil bare ha de som kan chatte (generateContent)
        chat_modeller = [m.name for m in alle if 'generateContent' in m.supported_generation_methods]
        
        # Sorter slik at "flash" (rask/gratis) kommer øverst
        chat_modeller.sort(key=lambda x: "flash" not in x) 
        return chat_modeller
    except Exception as e:
        return ["models/gemini-1.5-flash"] # Fallback hvis listen feiler

# Hent listen én gang
mine_modeller = finn_tilgjengelige_modeller()

# ==========================================
# 3. SIDEBAR MED INNSTILLINGER
# ==========================================
with st.sidebar:
    st.header("🔧 Teknisk")
    # Her kan du velge modell selv hvis den automatiske feiler!
    valgt_modell = st.selectbox("Aktiv AI-modell:", mine_modeller, index=0)
    st.caption("Tips: Bytt modell her hvis du får 404 eller 429 feil.")

    st.divider()
    st.header("🎓 Pedagogisk")
    alle_trinn = [f"{i}. trinn" for i in range(1, 11)]
    trinn = st.selectbox("Velg klassetrinn:", alle_trinn, index=4) 
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

    # Debug-info
    with st.expander("Se elevens hjerne"):
        data = hent_kunnskapsprofil(trinn)
        st.write(f"**Kan:** {data['kjent']}")
        st.write(f"**Lærer:** {data['laerer_naa']}")

# ==========================================
# 4. ELEV-PERSONA
# ==========================================
profil = hent_kunnskapsprofil(trinn)

system_instruks_elev = f"""
DU ER EN ELEV PÅ {trinn}.
Tema: '{begrep}'.

DIN KUNNSKAP:
1. DU KAN: {profil['kjent']}
2. DU LÆRER NÅ: {profil['laerer_naa']}
3. UKJENT: Alt annet.

REGLER:
- Du vet IKKE hva '{begrep}' er (med mindre det står under "DU KAN").
- ALDRI undervis læreren.
- Vær nysgjerrig, still spørsmål.
- Snakk norsk.
"""

# ==========================================
# 5. CHAT
# ==========================================
st.title(f"Forklar '{begrep}' til en elev på {trinn}")

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
            # Bruker modellen du valgte i menyen!
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
                st.warning("⚠️ Kvote full for denne modellen. Prøv å bytte modell i menyen til venstre!")
            elif "404" in str(e):
                st.warning("⚠️ Denne modellen finnes ikke. Velg en annen i menyen.")

# ==========================================
# 6. VEILEDER
# ==========================================
if st.session_state.get("be_om_veiledning", False):
    st.divider()
    with st.chat_message("assistant", avatar="📝"):
        st.subheader("Pedagogisk Vurdering")
        with st.spinner("Analyserer..."):
            
            veileder_instruks = f"""
            Du er praksisveileder. Analyser samtalen om '{begrep}' for {trinn}.
            Vurder språkbruk, elevinvolvering og forståelse. Vær kort og konkret.
            """
            
            logg = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            
            try:
                # Bruker samme modell som chatten
                veileder_model = genai.GenerativeModel(model_name=valgt_modell, system_instruction=veileder_instruks)
                analyse = veileder_model.generate_content(f"Logg:\n{logg}")
                st.markdown(analyse.text)
            except Exception as e:
                st.error(f"Veileder feilet: {e}")
    
    st.session_state.be_om_veiledning = False

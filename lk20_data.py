# lk20_data.py

# Kunnskapsbank for matematikk (LK20)
# Her legger du inn stikkord for hva elevene skal kunne etter hvert trinn.
LK20_MAAL = {
    1: "Telle til 20, sortere ting, begrepene over/under/størst/minst, enkel addisjon med fingre.",
    2: "Telle til 100, addisjon og subtraksjon med tierovergang, måle lengde, kjenne igjen mynter.",
    3: "Gangetabellen (2, 3, 5, 10), deling i like grupper, måle med linjal, speiling og symmetri.",
    4: "Hele gangetabellen, tall opp til 1000, enkle brøker (1/2, 1/4), finne areal ved å telle ruter.",
    5: "Brøk og desimaltall, tekstoppgaver, regne med penger, målestokk, negative tall (intro).",
    6: "Prosent, vinkler (gradskive), gjennomsnitt og typetall, regne med tid.",
    7: "Algebra (x og y), ligninger, volum av bokser, koordinatsystem, regneark.",
    8: "Potenser, kvadratrot, lineære funksjoner (y=ax+b), Pytagoras, sannsynlighet.",
    9: "Formlikhet, valuta og økonomi, volum av sylinder/kjegle, vitenskapelig notasjon.",
    10: "Andregradsfunksjoner, matematisk bevisføring, komplekse figurer, modellering."
}

def hent_kunnskapsprofil(trinn_tekst):
    """
    Summerer opp alt eleven kan fra tidligere år.
    """
    try:
        # Finner tallet i "5. trinn" -> 5
        trinn_tall = int(trinn_tekst.split(".")[0])
    except:
        trinn_tall = 5  # Fallback

    # 1. Hva kan eleven GODT? (Alt fra trinn 1 opp til trinnet før)
    kjent_stoff = []
    for i in range(1, trinn_tall):
        if i in LK20_MAAL:
            kjent_stoff.append(f"{i}. trinn: {LK20_MAAL[i]}")
    
    # 2. Hva lærer eleven NÅ?
    laerer_naa = LK20_MAAL.get(trinn_tall, "Ukjent pensum")

    return {
        "kjent": " | ".join(kjent_stoff),
        "laerer_naa": laerer_naa
    }
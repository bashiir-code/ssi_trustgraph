"""LAYER 4 — Synthesis & Presentation (analyst + writer).

Two-stage, runs ONCE over all questions' fact sheets:

  1. analyst (V4-Pro): reasons ACROSS all topics — builds a cross-cutting
     model (regulation x technology x labour x pricing), base/alternative
     scenarios with explicit confidence + assumptions, source tensions, and
     "so what" implications. Reasoning, not summary.
  2. writer (V4-Flash): renders one coherent expert report from the analyst
     brief + the fact sheets, with a synthesis lede, varied structure and
     inline citations.

Grounding is preserved: both stages use only the gathered, cited facts and
must label extrapolation vs evidence (see feedback on analytical depth).
"""

from ssi_blog_agent.clients import deepseek
from ssi_blog_agent.models import QuestionResearch

ANALYST_MODEL = "deepseek-v4-pro"
WRITER_MODEL = "deepseek-v4-flash"

ANALYST_SYSTEM_PROMPT = """Olet vanhempi markkina-analyytikko (Suomen
insinööriala). Saat usean jäsenkysymyksen tutkitut faktakoosteet lähteineen.
Tehtäväsi EI ole tiivistää vaan ANALYSOIDA. Tuota jäsennelty analyyttinen
muistio (kirjoittajan työkalu, ei lopullinen teksti):

1. RISTIINKYTKENNÄT: Rakenna YHTENÄINEN malli siitä, miten teemat (sääntely,
   teknologian käyttöönotto, työvoiman kysyntä, palkat, kustannukset)
   vaikuttavat TOISIINSA. Älä käsittele niitä erillisinä siiloina — etsi
   syy-seuraussuhteet ja toisen kierroksen vaikutukset.
2. SKENAARIOT: Keskeisille kehityskuluille perusskenaario + vähintään yksi
   vaihtoehto. Merkitse kullekin varmuustaso (korkea/keskitaso/matala) ja
   KESKEISET OLETUKSET. Mikä konkreettisesti muuttaisi ennusteen?
3. JÄNNITTEET: Nosta esiin lähteiden ristiriidat ja datan aukot. Erota
   selvästi DATAAN PERUSTUVA ja EKSTRAPOLAATIO.
4. JOHTOPÄÄTÖKSET KOHDEYLEISÖLLE: Mitä tämä tarkoittaa konkreettisesti
   pienille ja keskisuurille suomalaisille insinööritoimistoille ja alan
   ammattilaisille (the "so what").

Perusta KAIKKI annettuun dataan, älä keksi lukuja. Kun päättelet datan yli,
merkitse se ("Ekstrapolaatio:", "Arvio, matala varmuus:"). Tiivis,
analyyttinen tyyli, ei markkinointikieltä."""

WRITER_SYSTEM_PROMPT = """Olet asiantuntijatoimittaja. Saat (A) analyytikon
muistion ja (B) tutkitut faktakoosteet lähteineen. Kirjoita YKSI yhtenäinen,
asiantuntijatason markkina-analyysiraportti suomeksi (Markdown). Rakenne:

1. **Tiivistelmä & synteesi** (lede): aloita RISTIINKYTKEVÄLLÄ kokonaiskuvalla
   — miten sääntely, teknologia ja työvoima/palkat kytkeytyvät. Tämä on
   raportin tärkein osa.
2. **Skenaariot & näkymät**: perus- ja vaihtoehtoskenaariot; merkitse
   varmuustasot ja keskeiset oletukset selkeästi (esim. "(varmuus: matala)").
3. **Teemakohtaiset syvennykset**: käsittele kukin aihe, mutta VIITTAA ristiin
   muihin teemoihin äläkä toista samaa rakennetta joka osiossa — vaihtele
   esitystapaa.

Säännöt: älä keksi lukuja (vain koosteiden/muistion tiedot). Säilytä
analyytikon epävarmuus-/ekstrapolaatiomerkinnät. Upota lähdeviitteet
inline-linkkeinä keskeisten väitteiden yhteyteen. Vältä toistuvia kliseitä ja
samaa lopetuskaavaa. Skannattavat otsikot, lihavoidut avainhavainnot, taulukko
vain kun se tuo lisäarvoa."""


def _format_bundle(bundle: list[QuestionResearch]) -> str:
    blocks = []
    for i, qr in enumerate(bundle, start=1):
        lines = [f"## Kysymys {i}: {qr.question.text}"]
        for fs in qr.fact_sheets:
            tag = fs.specialist or "?"
            sources = "; ".join(fs.sources) if fs.sources else "(ei lähteitä)"
            lines.append(f"### [{tag}] {fs.sub_query}\n{fs.summary}\nLähteet: {sources}")
        blocks.append("\n\n".join(lines))
    return "\n\n---\n\n".join(blocks)


def synthesize(bundle: list[QuestionResearch]) -> str:
    """Analyst pass (V4-Pro): cross-cutting reasoning over all topics."""
    return deepseek.chat(
        [
            {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
            {"role": "user", "content": f"=== FAKTAKOOSTEET ===\n{_format_bundle(bundle)}"},
        ],
        model=ANALYST_MODEL,
        temperature=0.4,
    )


def write_report(bundle: list[QuestionResearch], analyst_brief: str) -> str:
    """Writer pass (V4-Flash): render one coherent expert report."""
    return deepseek.chat(
        [
            {"role": "system", "content": WRITER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"=== ANALYYTIKON MUISTIO ===\n{analyst_brief}\n\n"
                    f"=== FAKTAKOOSTEET (lähteet) ===\n{_format_bundle(bundle)}"
                ),
            },
        ],
        model=WRITER_MODEL,
        temperature=0.5,
    )

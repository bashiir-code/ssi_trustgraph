"""LAYER 4 — Synthesis & Presentation (analyst + writer + citations).

Two-stage, runs ONCE over all questions' fact sheets:

  1. analyst (V4-Pro): reasons ACROSS all topics — builds a cross-cutting
     model (regulation x technology x labour x pricing), base/alternative
     scenarios with explicit confidence + assumptions, source tensions, and
     "so what" implications. Reasoning, not summary.
  2. writer (V4-Flash): renders one coherent expert report from the analyst
     brief + the fact sheets, with a synthesis lede, varied structure and
     NUMBERED [n] inline citations. A deterministic ## Lähteet bibliography is
     appended from the global source index (always complete, even if the
     model's inline [n] usage is imperfect).

Grounding is preserved: both stages use only the gathered, cited facts and
must label extrapolation vs evidence.
"""

from ssi_blog_agent.clients import deepseek
from ssi_blog_agent.models import AgentStatus, QuestionResearch

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
muistion ja (B) tutkitut faktakoosteet, joiden lähteet on NUMEROITU [n].
Kirjoita YKSI yhtenäinen, asiantuntijatason markkina-analyysiraportti suomeksi
(Markdown). Rakenne:

1. **Tiivistelmä & synteesi** (lede): aloita RISTIINKYTKEVÄLLÄ kokonaiskuvalla
   — miten sääntely, teknologia ja työvoima/palkat kytkeytyvät.
2. **Skenaariot & näkymät**: perus- ja vaihtoehtoskenaariot; merkitse
   varmuustasot ja keskeiset oletukset (esim. "(varmuus: matala)").
3. **Teemakohtaiset syvennykset**: käsittele kukin aihe, viittaa ristiin
   muihin teemoihin, äläkä toista samaa rakennetta — vaihtele esitystapaa.

Säännöt: älä keksi lukuja (vain koosteiden/muistion tiedot). SIDO jokainen
keskeinen väite ja luku lähteeseen numeroidulla viitteellä [n], käyttäen
koosteissa annettuja numeroita. ÄLÄ luo omaa lähdeluetteloa — se liitetään
automaattisesti. Säilytä epävarmuus-/ekstrapolaatiomerkinnät. Vältä toistuvia
kliseitä. Skannattavat otsikot, lihavoidut avainhavainnot, taulukko vain kun
se tuo lisäarvoa."""


def build_source_index(bundle: list[QuestionResearch]) -> tuple[dict[str, int], list[str]]:
    """Assign a stable [n] to every unique source URL across all fact sheets."""
    index: dict[str, int] = {}
    ordered: list[str] = []
    for qr in bundle:
        for fs in _ok_sheets(qr):
            for url in fs.sources:
                if url not in index:
                    ordered.append(url)
                    index[url] = len(ordered)
    return index, ordered


def _ok_sheets(qr: QuestionResearch) -> list:
    return [fs for fs in qr.fact_sheets if fs.status == AgentStatus.OK]


def _format_for_analyst(bundle: list[QuestionResearch]) -> str:
    blocks = []
    for i, qr in enumerate(bundle, start=1):
        lines = [f"## Kysymys {i}: {qr.question.text}"]
        for fs in _ok_sheets(qr):
            tag = fs.specialist or "?"
            srcs = "; ".join(fs.sources) if fs.sources else "(ei lähteitä)"
            lines.append(f"### [{tag}] {fs.sub_query}\n{fs.summary}\nLähteet: {srcs}")
        failed = [fs for fs in qr.fact_sheets if fs.status == AgentStatus.FAILED]
        if failed:
            gaps = "; ".join(fs.sub_query for fs in failed)
            lines.append(f"**Huom: osa tutkimuksesta epäonnistui (tietopuute):** {gaps}")
        if qr.validation_note:
            lines.append(f"**Faktantarkistus (kattavuus {qr.coverage}%):** {qr.validation_note}")
        blocks.append("\n\n".join(lines))
    return "\n\n---\n\n".join(blocks)


def _format_for_writer(bundle: list[QuestionResearch], index: dict[str, int]) -> str:
    blocks = []
    for i, qr in enumerate(bundle, start=1):
        lines = [f"## Kysymys {i}: {qr.question.text}"]
        for fs in _ok_sheets(qr):
            tag = fs.specialist or "?"
            refs = ", ".join(f"[{index[u]}]" for u in fs.sources if u in index) or "(ei lähteitä)"
            lines.append(f"### [{tag}] {fs.sub_query}\n{fs.summary}\nLähdeviitteet: {refs}")
        blocks.append("\n\n".join(lines))
    return "\n\n---\n\n".join(blocks)


def synthesize(bundle: list[QuestionResearch]) -> str:
    """Analyst pass (V4-Pro): cross-cutting reasoning over all topics."""
    return deepseek.chat(
        [
            {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
            {"role": "user", "content": f"=== FAKTAKOOSTEET ===\n{_format_for_analyst(bundle)}"},
        ],
        model=ANALYST_MODEL,
        temperature=0.4,
    )


def write_report(bundle: list[QuestionResearch], analyst_brief: str) -> str:
    """Writer pass (V4-Flash) + deterministic numbered bibliography."""
    index, ordered = build_source_index(bundle)

    body = deepseek.chat(
        [
            {"role": "system", "content": WRITER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"=== ANALYYTIKON MUISTIO ===\n{analyst_brief}\n\n"
                    f"=== FAKTAKOOSTEET (numeroidut lähteet) ===\n"
                    f"{_format_for_writer(bundle, index)}"
                ),
            },
        ],
        model=WRITER_MODEL,
        temperature=0.5,
    )

    bibliography = "\n\n## Lähteet\n\n" + "\n".join(
        f"[{n}] {url}" for n, url in enumerate(ordered, start=1)
    )
    return body + bibliography

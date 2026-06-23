"""Chunk 5 proof: formatting guardrails + traceable citations (offline).

Stubs the writer to emit a messy draft (stray code fence, bold-only heading)
and confirms the cleanup + deterministic bibliography produce a clean report
with a numbered source list and at least one traceable [n] -> URL link.

Run: python scripts/test_presentation.py
"""

import sys

from ssi_blog_agent import layer4_presentation as pres
from ssi_blog_agent.models import FactSheet, MemberQuestion, QuestionResearch

MESSY_DRAFT = """**Tiivistelmä & synteesi**

Rakennusinsinöörien mediaanipalkka on 4 943 €/kk [1], ja sääntely kiristyy [2].

```json
{"raw": "should be stripped"}
```



Liikaa tyhjää yllä.
"""


def main() -> None:
    pres.deepseek.chat = lambda messages, **kw: MESSY_DRAFT

    bundle = [QuestionResearch(
        question=MemberQuestion(id="q1", text="Palkat ja sääntely 2026?"),
        fact_sheets=[FactSheet(
            sub_query="rakennusinsinöörien mediaanipalkka",
            summary="Mediaani 4 943 €/kk.",
            sources=["https://pxdata.stat.fi/.../15au.px", "https://finlex.fi/cpr"],
            specialist="quant",
        )],
    )]

    report = pres.write_report(bundle, analyst_brief="(muistio)")

    checks = {
        "opens with # heading": report.startswith("#"),
        "no stray code fences": "```" not in report,
        "has bibliography": "## Lähteet" in report,
        "numbered source [1]": "[1] https://pxdata.stat.fi" in report,
        "inline citation present": "[1]" in report.split("## Lähteet")[0],
        "no 3+ blank lines": "\n\n\n" not in report,
    }
    for name, ok in checks.items():
        print(f"  {name}: {'PASS' if ok else 'FAIL'}")
    if all(checks.values()):
        print("ALL PASS")
    else:
        print("FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()

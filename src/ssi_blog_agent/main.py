"""Entrypoint: ajaa koko viikoittaisen pipelinen kertaajona."""

from ssi_blog_agent.graph import build_graph


def main() -> None:
    app = build_graph()
    final_state = app.invoke({})
    print(final_state.get("report_markdown", "(ei raporttia)"))


if __name__ == "__main__":
    main()

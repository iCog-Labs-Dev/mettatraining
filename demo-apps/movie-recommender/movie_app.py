from __future__ import annotations

from movie_recommender import SymbolicMovieRecommender


recommender = SymbolicMovieRecommender()


def recommend_from_seed(seed_movie: str, limit: int) -> str:
    recommendations = recommender.recommend_like(seed_movie, limit=limit)
    if not recommendations:
        return "No recommendations found."

    lines = [f"Movies similar to {seed_movie}:"]
    for item in recommendations:
        reasons = ", ".join(item.matched_features)
        lines.append(f"- {item.title} (score {item.score}): {reasons}")
    return "\n".join(lines)


def recommend_from_query(query: str, limit: int) -> str:
    try:
        parsed_query, recommendations = recommender.recommend_from_query(query, limit=limit)
    except ValueError as error:
        return str(error)

    if not recommendations:
        return "No recommendations found."

    preference_bits = []
    for feature_type, values in sorted(parsed_query.preferences.items()):
        preference_bits.append(f"{feature_type}={', '.join(sorted(values))}")

    exclusion_bits = []
    for feature_type, values in sorted(parsed_query.exclusions.items()):
        exclusion_bits.append(f"{feature_type}!={', '.join(sorted(values))}")

    lines = [
        f"Interpreted query: {'; '.join(preference_bits)}",
    ]
    if exclusion_bits:
        lines.append(f"Exclusions: {'; '.join(exclusion_bits)}")

    for item in recommendations:
        reasons = ", ".join(item.matched_features)
        lines.append(f"- {item.title} (score {item.score}): {reasons}")
    return "\n".join(lines)


def build_demo():
    try:
        import gradio as gr
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "Gradio is not installed in the active Python environment. "
            "Install project requirements before launching the UI."
        ) from error

    with gr.Blocks() as demo:
        gr.Markdown("## Symbolic Movie Recommender")
        gr.Markdown(
            "A content-based recommender backed by MeTTa movie facts and Python scoring."
        )

        with gr.Tab("Find Similar Movies"):
            seed_movie = gr.Dropdown(
                choices=recommender.movies,
                value="Inception",
                label="Pick a movie you like",
            )
            seed_limit = gr.Slider(1, 8, value=5, step=1, label="Number of recommendations")
            seed_button = gr.Button("Recommend Similar Movies")
            seed_output = gr.Textbox(label="Recommendations", lines=10)
            seed_button.click(
                fn=recommend_from_seed,
                inputs=[seed_movie, seed_limit],
                outputs=seed_output,
            )

        with gr.Tab("Ask In Natural Language"):
            query_input = gr.Textbox(
                label="Movie request",
                value="Recommend 5 cerebral sci-fi movies with family themes but not dark ones",
                placeholder="e.g. Recommend whimsical fantasy movies with magic",
                lines=3,
            )
            query_limit = gr.Slider(1, 8, value=5, step=1, label="Number of recommendations")
            query_button = gr.Button("Interpret And Recommend")
            query_output = gr.Textbox(label="Recommendations", lines=14)
            query_button.click(
                fn=recommend_from_query,
                inputs=[query_input, query_limit],
                outputs=query_output,
            )

    return demo


if __name__ == "__main__":
    demo = build_demo()
    demo.launch()

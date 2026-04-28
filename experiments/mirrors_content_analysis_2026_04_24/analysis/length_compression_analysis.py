"""Analysis of word count, post length, etc.

To run:

PYTHONPATH=. uv run python experiments/mirrors_content_analysis_2026_04_24/analysis/length_compression_analysis.py
"""
import pandas as pd

from experiments.mirrors_content_analysis_2026_04_24.dataloader import Dataloader

class LengthCompressionAnalyzer:

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.results = {
            "original_text_analysis": None,
            "mirror_text_analysis": None,
            "pairwise_analysis": None,
            "keep_remove_analysis": None,
        }

    def original_text_analysis(self):
        """Analysis of the original post text."""
        pass

    def mirror_text_analysis(self):
        """Analysis of the mirror post text."""
        pass

    def pairwise_analysis(self):
        """Pairwise analysis comparing the original and mirrored posts."""
        pass

    def keep_remove_analysis(self):
        """Analysis of the keep/remove decisions."""
        pass

    def show_results(self):
        pass

    def save_results(self):
        pass

def main():

    # load data
    dataloader = Dataloader()
    df = dataloader.get_latest_mirrorview_run_data()
    df = dataloader.transform_latest_mirrorview_run_data(df)

    breakpoint()

    # do analysis
    analyzer = LengthCompressionAnalyzer(df)
    analyzer.original_text_analysis()
    analyzer.mirror_text_analysis()
    analyzer.pairwise_analysis()
    analyzer.keep_remove_analysis()

    # show/save results
    analyzer.show_results()
    analyzer.save_results()

if __name__ == "__main__":
    main()

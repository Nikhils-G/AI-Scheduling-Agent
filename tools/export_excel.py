import pandas as pd

class Exporter:
    def __init__(self, out_path="data/appointments_export.xlsx"):
        self.out_path = out_path

    def export(self, appointments_df):
        # minimal cleaning before export
        df = appointments_df.copy()
        # ensure consistent ordering
        cols = [c for c in df.columns]
        df.to_excel(self.out_path, index=False)
        return self.out_path

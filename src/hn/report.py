import pandas as pd
from hn.model import engine 
from hn.query import get_authors_avg_stmt
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def avg_score_report(engine, outputfilename: str):
    outputdir = BASE_DIR / "reports" / outputfilename
    outputdir.parent.mkdir(parents=True, exist_ok=True)
    stmt = get_authors_avg_stmt()
    df = pd.read_sql(stmt,engine)
    df.to_csv(outputdir, index=False)

if __name__ == "__main__":

    avg_score_report(engine=engine, outputfilename="avg.csv")
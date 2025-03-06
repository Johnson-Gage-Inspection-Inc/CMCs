import re
import pandas as pd


def parse_range(range_text):
    # Keep your existing parse_range logic
    if not range_text or not isinstance(range_text, str):
        return None, None, None

    text = re.sub(r"[^\x20-\x7E]+", " ", range_text)
    text = re.sub(r"\s+", " ", text).strip()

    pat1 = re.compile(
        r"^\(\s*([+-]?\d*\.?\d+)\s+to\s+([+-]?\d*\.?\d+)\s*\)\s+(.+)$", re.IGNORECASE
    )
    m = pat1.match(text)
    if m:
        return m.group(1), m.group(2), m.group(3).strip()

    pat2 = re.compile(r"^Up\s+to\s+([\-.\d]+)\s+(.+)$", re.IGNORECASE)
    m = pat2.match(text)
    if m:
        return None, m.group(1), m.group(2).strip()

    pat3 = re.compile(r"^([\-.\d]+)\s+to\s+([\-.\d]+)\s+(.+)$", re.IGNORECASE)
    m = pat3.match(text)
    if m:
        return m.group(1), m.group(2), m.group(3).strip()

    pat4 = re.compile(r"^([\-.\d]+)\s+(.+)$", re.IGNORECASE)
    m = pat4.match(text)
    if m:
        return None, m.group(1), m.group(2).strip()

    return None, None, text


def expand_frequency_and_cmc(df):
    expanded_data = []
    for _, row in df.iterrows():
        freq_split = row["Frequency"].split("\n") if pd.notna(row["Frequency"]) else []
        cmc_split = row["CMC (±)"].split("\n") if pd.notna(row["CMC (±)"]) else []
        range_split = row["Range"].split("\n") if pd.notna(row["Range"]) else []
        param_split = row["Parameter"].split("\n") if pd.notna(row["Parameter"]) else []

        if (
            len(freq_split) == len(cmc_split) and len(range_split) == 1 and len(param_split) == 1
        ):
            for i in range(len(freq_split)):
                expanded_data.append(
                    {
                        **row.to_dict(),
                        "Frequency": freq_split[i],
                        "CMC (±)": cmc_split[i],
                    }
                )
        else:
            expanded_data.append(row.to_dict())

    return pd.DataFrame(expanded_data)

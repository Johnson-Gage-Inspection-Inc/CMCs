import re
import json


def remove_small_chars(clust):
    for ln in clust:
        if all(c["size"] < 7.5 for c in ln["chars"]):
            return
        median_y1 = sorted([char["y1"] for char in ln["chars"]])[len(ln["chars"]) // 2]
        string = ""
        i = 0
        for char in ln["text"]:
            if char == " ":
                string += char
            elif ln["chars"][i]["size"] > 7.5 and ln["chars"][i]["y1"] < median_y1 + 1:
                string += ln["chars"][i]["text"]
                i += 1
            else:
                ln["chars"].pop(i)
        while "  " in string:
            string = string.replace("  ", " ")
        ln["text"] = string.strip()


def custom_extract_tables(
    page, table_settings=None, vertical_thresh=14, indent_thresh=4
):
    """
    Custom table extraction from a pdfplumber Page.
    """
    BEGIN_LINE_PATTERN_DEFAULT = re.compile(r"^(?:\d|\(\d|\-\d|\(-\d|[<>]\s*\d)")
    BEGIN_LINE_PATTERN_SECOND = re.compile(r"^(?:\d|\(\d|\-\d|\(-\d|[<>]\s*\d|[\(≤<>])")

    def get_first_word_width(ln):
        if "chars" not in ln or not ln["chars"]:
            return 0
        first_word_chars = []
        for c in ln["chars"]:
            if c["text"].isspace():
                if first_word_chars:
                    break
                else:
                    continue
            first_word_chars.append(c)
        if not first_word_chars:
            return 0
        return first_word_chars[-1]["x1"] - first_word_chars[0]["x0"]

    # Use pdfplumber's table finder.
    tables = page.find_tables(table_settings=table_settings)
    custom_tables = []

    for table in tables:
        table_rows = []
        for row in table.rows:
            row_cells = []
            for col_idx, cell in enumerate(row.cells):
                if not cell:
                    row_cells.append([])
                    continue
                cell_crop = page.crop(cell)
                lines = cell_crop.extract_text_lines(layout=True, return_chars=True)
                visual_rows = []
                if not lines:
                    visual_rows.append({"text": "", "top": None})
                else:
                    lines.sort(key=lambda ln: ln["top"])
                    clusters = []
                    current_cluster = [lines[0]]
                    for ln in lines[1:]:
                        vertical_gap = ln["top"] - current_cluster[-1]["top"]
                        if vertical_gap >= vertical_thresh:
                            clusters.append(current_cluster)
                            current_cluster = [ln]
                            continue
                        available_space = cell[2] - current_cluster[-1]["x1"]
                        first_word_width = get_first_word_width(ln)
                        indent_prev = current_cluster[-1]["x0"] - cell[0]
                        indent_candidate = ln["x0"] - cell[0]
                        if abs(indent_prev - indent_candidate) > indent_thresh:
                            clusters.append(current_cluster)
                            current_cluster = [ln]
                        # Use the second column pattern only for the 2nd column (col index 1)
                        elif (
                            BEGIN_LINE_PATTERN_SECOND
                            if col_idx == 1
                            else BEGIN_LINE_PATTERN_DEFAULT
                        ).search(ln["text"].strip()):
                            clusters.append(current_cluster)
                            current_cluster = [ln]
                        elif available_space >= first_word_width:
                            clusters.append(current_cluster)
                            current_cluster = [ln]
                        else:
                            current_cluster.append(ln)
                    clusters.append(current_cluster)

                    def convert_to_subscript(s):
                        mapping = json.load(open("src/subscript_mapping.json", encoding="utf-8"))
                        return "".join(mapping.get(char, char) for char in s)

                    cluster_info = []
                    for clust in clusters:
                        if not clust:
                            continue
                        remove_small_chars(clust)
                        text = " ".join(ln["text"] for ln in clust).strip()
                        min_x0 = min(ln["x0"] for ln in clust)
                        max_x1 = max(ln["x1"] for ln in clust)
                        top_val = min(ln["top"] for ln in clust)
                        sizes = [
                            c.get("size", 0)
                            for ln in clust
                            for c in ln.get("chars", [])
                            if c.get("size")
                        ]
                        avg_font_size = sum(sizes) / len(sizes) if sizes else 0
                        cluster_info.append(
                            {
                                "text": text,
                                "min_x0": min_x0,
                                "max_x1": max_x1,
                                "top": top_val,
                                "font_size": avg_font_size,
                            }
                        )

                    grouped_clusters = []
                    if cluster_info:
                        current_group = [cluster_info[0]]
                        for c in cluster_info[1:]:
                            # If the vertical difference is small, just add to the current group.
                            if abs(c["top"] - current_group[0]["top"]) < 5:
                                current_group.append(c)
                            else:
                                # Check if this new cluster is a short alphanumeric candidate (subscript)
                                trimmed = c["text"].strip()
                                if len(trimmed) <= 2 and re.fullmatch(
                                    r"[A-Za-z0-9]+", trimmed
                                ):
                                    # Merge it with the current group even though the vertical gap is larger.
                                    current_group.append(c)
                                else:
                                    grouped_clusters.append(current_group)
                                    current_group = [c]
                        grouped_clusters.append(current_group)
                    else:
                        grouped_clusters = []

                    merged_rows = []
                    tol_top = 2
                    tol_font = 1
                    for group in grouped_clusters:
                        baseline_cluster = max(group, key=lambda c: len(c["text"]))
                        baseline_top = baseline_cluster["top"]
                        baseline_font = baseline_cluster.get("font_size", 0)
                        filtered_group = [
                            c
                            for c in group
                            if not (
                                (baseline_top - c["top"]) > tol_top and (baseline_font - c["font_size"]) > tol_font
                            )
                        ]
                        if not filtered_group:
                            continue
                        filtered_group.sort(key=lambda c: c["min_x0"])
                        merged_text = filtered_group[0]["text"]
                        current_max = filtered_group[0]["max_x1"]
                        for c in filtered_group[1:]:
                            trimmed_text = c["text"].strip()
                            # If the candidate is a short alphanumeric string (one or two characters)
                            if len(trimmed_text) <= 2 and re.fullmatch(
                                r"[A-Za-z0-9]+", trimmed_text
                            ):
                                candidate = convert_to_subscript(trimmed_text)
                                # If the merged text ends with a closing parenthesis,
                                # insert the candidate before that.
                                if merged_text.endswith(")"):
                                    merged_text = (
                                        merged_text[:-1].rstrip() + candidate + ")"
                                    )
                                else:
                                    merged_text = merged_text.rstrip() + candidate
                            else:
                                gap = c["min_x0"] - current_max
                                if gap < 3:
                                    merged_text = merged_text.rstrip() + c["text"]
                                else:
                                    merged_text = merged_text + " " + c["text"]
                            current_max = max(current_max, c["max_x1"])

                        merged_text = re.sub(
                            r"([A-Za-z])\s+([A-Za-z])((?:[₀₁₂₃₄₅₆₇₈₉])\b)",
                            r"\1\3\2",
                            merged_text,
                        )
                        base_indent = lines[0]["x0"] - cell[0]
                        indent = filtered_group[0]["min_x0"] - cell[0]
                        if indent > base_indent + indent_thresh:
                            merged_text = f"\t{merged_text}"
                        merged_rows.append(
                            {"text": merged_text, "top": filtered_group[0]["top"]}
                        )
                    visual_rows.extend(merged_rows)
                row_cells.append(visual_rows)
            table_rows.append(row_cells)
        custom_tables.append(table_rows)
    return custom_tables

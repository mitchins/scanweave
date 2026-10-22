"""Geometry-derived context; no oracle line identities or font labels."""
import numpy as np


def source_lines(rows):
    groups = []
    for page in sorted({row['page'] for row in rows}):
        selected = [i for i, row in enumerate(rows) if row['page'] == page]
        current = []
        for index in sorted(selected, key=lambda i: (rows[i]['bbox'][1]+rows[i]['bbox'][3])/2):
            box = rows[index]['bbox']
            center, height = (box[1]+box[3])/2, box[3]-box[1]
            if current:
                centers = [(rows[i]['bbox'][1]+rows[i]['bbox'][3])/2 for i in current]
                heights = [rows[i]['bbox'][3]-rows[i]['bbox'][1] for i in current]
                if abs(center-float(np.median(centers))) > .65*max(height, float(np.median(heights))):
                    groups.append(current)
                    current = []
            current.append(index)
        if current:
            groups.append(current)
    return groups


def context_vectors(rows, embeddings):
    vectors = np.zeros_like(embeddings)
    dispersion, counts = np.zeros(len(rows)), np.zeros(len(rows))
    line_ids = np.full(len(rows), -1, dtype=int)
    for line, indices in enumerate(source_lines(rows)):
        for index in indices:
            other = [j for j in indices if rows[j]['character'] != rows[index]['character']]
            if len(other) < 3:
                continue
            mean = embeddings[other].mean(0)
            norm = np.linalg.norm(mean)
            vectors[index] = mean/max(norm, 1e-8)
            dispersion[index] = 1-norm
            counts[index] = len({rows[j]['character'] for j in other})
            line_ids[index] = line
    return vectors, dispersion, counts, line_ids

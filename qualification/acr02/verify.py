"""Validate actual derivative PDFs and bind evidence to input hashes."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pikepdf
import pypdfium2
sys.path.insert(0, 'qualification')
from tools_env import qpdf_bin, qpdf_env

ROOT = Path('qualification/acr02/local')


def pdfium_text(path):
    with pypdfium2.PdfDocument(str(path)) as pdf:
        return [pdf[i].get_textpage().get_text_range() for i in range(len(pdf))]


def font_hashes(path):
    rows = []
    with pikepdf.open(path) as pdf:
        for obj in pdf.objects:
            if isinstance(obj, pikepdf.Dictionary):
                for key in ('/FontFile', '/FontFile2', '/FontFile3', '/ToUnicode'):
                    if key in obj:
                        rows.append(hashlib.sha256(obj[key].read_bytes()).hexdigest())
    return sorted(rows)


def save_results(records, destination):
    destination.write_text(json.dumps(records, indent=2) + '\n')
    if not all(row['passed'] for row in records):
        raise SystemExit('Verification failed; see verification.json')


def main():
    pairs = [('prototype-acr01.pdf', 'prototype-controlled-jpeg.pdf'),
             ('prototype-acr01.pdf', 'prototype-controlled-indexed.pdf'),
             ('../..//acr01/local/product/historical.pdf', 'history-indexed16.pdf'),
             ('../..//acr01/local/product/financial.pdf', 'financial-full13-indexed16.pdf')]
    records = []
    for original, candidate in pairs:
        source, out = ROOT / original, ROOT / candidate
        # Original full-document membership stays intact in every derivative.
        before = subprocess.check_output(['pdftotext', str(source), '-'])
        after = subprocess.check_output(['pdftotext', str(out), '-'])
        q = subprocess.run([str(qpdf_bin()), '--check', str(out)], env=qpdf_env(), capture_output=True, text=True)
        row = {'source': str(source), 'candidate': str(out), 'bytes_before': source.stat().st_size,
               'bytes_after': out.stat().st_size, 'sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
               'poppler_text_equal': before == after, 'pdfium_text_equal': pdfium_text(source) == pdfium_text(out),
               'font_program_and_tounicode_hashes_equal': font_hashes(source) == font_hashes(out),
               'qpdf_exit': q.returncode, 'qpdf_log': q.stdout + q.stderr}
        row['passed'] = (row['poppler_text_equal'] and row['pdfium_text_equal']
                         and row['font_program_and_tounicode_hashes_equal'] and q.returncode == 0)
        records.append(row)
    save_results(records, ROOT / 'verification.json')
    print([(r['candidate'], r['bytes_before'], r['bytes_after']) for r in records])


if __name__ == '__main__':
    main()

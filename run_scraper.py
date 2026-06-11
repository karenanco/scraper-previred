#!/usr/bin/env python3
import subprocess
import sys
import os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_spider(name):
    print(f"\n===== Ejecutando spider: {name} =====")
    result = subprocess.run(
        [sys.executable, '-m', 'scrapy', 'crawl', name],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
    if result.returncode != 0:
        print(f"ERROR: Spider {name} falló con código {result.returncode}")
    else:
        print(f"OK: Spider {name} completado")
    return result.returncode


def main():
    print("=== Scraper Previred - Inicio ===")
    errors = 0
    errors += run_spider('previred')
    errors += run_spider('sii_utm')
    print(f"\n=== Scraper Previred - {'Completado con errores' if errors else 'Completado OK'} ===")
    return errors


if __name__ == '__main__':
    sys.exit(main())

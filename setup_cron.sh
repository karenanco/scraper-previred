#!/usr/bin/env bash
set -e

PROJECT_DIR=$(cd "$(dirname "$0")" && pwd)
CRON_JOB="0 8 * * * cd $PROJECT_DIR && python run_scraper.py >> $PROJECT_DIR/data/scraper.log 2>&1"

# Backup existing crontab
crontab -l > /tmp/crontab_backup 2>/dev/null || true

if grep -q "run_scraper.py" /tmp/crontab_backup 2>/dev/null; then
    echo "El cron job ya existe. No se hicieron cambios."
    exit 0
fi

echo "$CRON_JOB" >> /tmp/crontab_backup
crontab /tmp/crontab_backup
rm /tmp/crontab_backup

echo "Cron job instalado: diario a las 08:00"
echo "Log: $PROJECT_DIR/data/scraper.log"

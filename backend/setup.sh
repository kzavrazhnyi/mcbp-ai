#!/usr/bin/env bash
# Bootstrap venv для backend (Linux / macOS).
# Запуск з теки backend:  ./setup.sh
# Потім активація:        source .venv/bin/activate
set -euo pipefail
cd "$(dirname "$0")"

# 1. Створити venv, якщо його ще немає
if [ ! -d .venv ]; then
    echo "==> Створюю .venv ..."
    python3 -m venv .venv
else
    echo "==> .venv вже існує — пропускаю створення."
fi

PY=.venv/bin/python

# 2. Оновити pip і встановити пакет із dev-залежностями
echo "==> Оновлюю pip ..."
"$PY" -m pip install --upgrade pip
echo "==> Встановлюю залежності (editable + dev) ..."
"$PY" -m pip install -e ".[dev]"

# 3. Створити .env з шаблону, якщо відсутній
if [ ! -f .env ]; then
    cp .env.example .env
    echo "==> Створено .env з .env.example — відредагуйте за потреби."
fi

echo
echo "Готово. Активуйте venv і запустіть сервер:"
echo "  source .venv/bin/activate"
echo "  uvicorn app.main:app --reload"

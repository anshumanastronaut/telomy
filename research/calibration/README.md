# Telomy calibration workbench (dev tool)

Live dashboard to calibrate WHOOP/ring/patch raw signals against reference instruments
(fingertip oximeter, thermometer, ECG patch). Pulls + decodes WHOOP raw from the cloud,
you feed reference readings by hand, it fits SpO₂ = c0−c1·ratio, °C = a·raw+b, and the
HRV PPG→ECG factor, and plots them.

Run: `cd research/calibration && ../../backend/.venv/bin/uvicorn app:app --port 8799`
then open http://127.0.0.1:8799 . Needs `~/.ssh/telomy-oracle.key`. `readings.json` is git-ignored.

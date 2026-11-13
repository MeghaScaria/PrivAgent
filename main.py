#!/usr/bin/env python3
"""
Single entry point for PrivAgent. Run:

    python main.py

This launches the Streamlit dashboard, which starts the four MCP
servers itself on first load. If you haven't trained the models yet
(no models/*.pkl files present), this will tell you to run
models/train_models.py first.
"""
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def check_models_exist():
    required = [
        "models/action_level_model.pkl",
        "models/trajectory_level_model.pkl",
        "models/thresholds.json",
    ]
    missing = [f for f in required if not os.path.exists(os.path.join(BASE_DIR, f))]
    return missing


def check_env_file():
    env_path = os.path.join(BASE_DIR, ".env")
    example_path = os.path.join(BASE_DIR, ".env.example")
    if not os.path.exists(env_path) and os.path.exists(example_path):
        print("No .env file found.")
        print(f"   Copy {example_path} to .env and add your Gemini API key.")
        print("   (The Attack Laboratory page works without one; the Research")
        print("   Assistant page needs it.)")
        print()


def main():
    missing = check_models_exist()
    if missing:
        print("Trained models are missing:")
        for m in missing:
            print(f"   - {m}")
        print()
        print("Run this first:")
        print("   python models/train_models.py")
        print()
        sys.exit(1)

    check_env_file()

    print("Starting PrivAgent dashboard...")
    print("   The four MCP servers will start automatically on first load.")
    print()

    dashboard_path = os.path.join(BASE_DIR, "dashboard", "app.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_path])


if __name__ == "__main__":
    main()

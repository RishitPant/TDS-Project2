# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx",
#   "pandas",
#   "matplotlib",
#   "seaborn",
#   "sklearn",
#   "requests"
# ]
# ///



import os
import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib
import json
from sklearn.ensemble import IsolationForest
import warnings
import requests

matplotlib.use('Agg')

warnings.filterwarnings("ignore")

# Set the AI Proxy token from environment variable
AIPROXY_TOKEN = os.environ.get("AIPROXY_TOKEN", "")
if not AIPROXY_TOKEN:
    raise ValueError("AIPROXY_TOKEN environment variable not set.")

# API URLs
CHAT_COMPLETION_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
EMBEDDINGS_URL = "https://aiproxy.sanand.workers.dev/openai/v1/embeddings"


# Helper function for chat completion
def get_chat_response(prompt, model="gpt-4o-mini"):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AIPROXY_TOKEN}"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    }
    response = requests.post(CHAT_COMPLETION_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.status_code}, {response.text}"


# Data analysis functions
def analyze_data(data):
    """Perform basic data analysis."""
    return {
        "shape": data.shape,
        "missing_values": data.isnull().sum().to_dict(),
        "summary_statistics": data.describe(include="all").to_dict(),
        "data_types": data.dtypes.apply(str).to_dict()
    }


def detect_outliers(data):
    """Detect outliers using IsolationForest."""
    numeric_cols = data.select_dtypes(include="number").columns
    if len(numeric_cols) == 0:
        return "No numeric columns for outlier detection."
    iso = IsolationForest(contamination=0.05, random_state=42)
    outliers = iso.fit_predict(data[numeric_cols].dropna())
    return {"outliers_detected": list(outliers).count(-1)}


def generate_visualizations(data, output_dir):
    """Generate and save visualizations."""
    charts = []
    numeric_cols = data.select_dtypes(include="number").columns

    # Correlation heatmap
    if len(numeric_cols) > 1:
        plt.figure(figsize=(8, 6))
        sns.heatmap(data[numeric_cols].corr(), annot=True, cmap="coolwarm")
        plt.title("Correlation Heatmap")
        chart_file = os.path.join(output_dir, "correlation_heatmap.png")
        plt.savefig(chart_file)
        plt.close()
        charts.append(chart_file)

    # Missing values bar chart
    plt.figure(figsize=(8, 6))
    data.isnull().sum().plot(kind="bar")
    plt.title("Missing Values Count")
    plt.ylabel("Count")
    chart_file = os.path.join(output_dir, "missing_values.png")
    plt.savefig(chart_file)
    plt.close()
    charts.append(chart_file)

    return charts


# Main function
def main(csv_file):
    # Validate file
    if not os.path.isfile(csv_file):
        print(f"File '{csv_file}' not found.")
        sys.exit(1)

    # Load data
    data = pd.read_csv(csv_file, encoding='ISO-8859-1')
    output_dir = os.path.splitext(csv_file)[0]
    os.makedirs(output_dir, exist_ok=True)

    # Perform analysis
    analysis = analyze_data(data)
    outlier_info = detect_outliers(data)
    analysis["outliers"] = outlier_info

    # Generate visualizations
    charts = generate_visualizations(data, output_dir)

    # Create prompt for GPT-4o-mini
    prompt = f"""
    You are analyzing a dataset that contains various attributes. Your task is to narrate a story based on the findings from the dataset analysis.

    Dataset Overview:
    - Shape: {analysis['shape']}
    - Missing Values: {json.dumps(analysis['missing_values'], indent=2)}
    - Summary Statistics: {json.dumps(analysis['summary_statistics'], indent=2)}
    - Outlier Info: {json.dumps(outlier_info, indent=2)}

    Create a story-like narration based on these findings. Your story should:
    1. Introduce the dataset and its key features.
    2. Discuss the missing values and any notable observations.
    3. Explore the summary statistics and what they reveal about the data.
    4. Tell a story around the outliers, including their impact.
    5. Conclude with insights and lessons learned, supported by visualizations.
    
    Make it engaging and suitable for a report.
    """
    story = get_chat_response(prompt)

    # Save README and outputs
    readme_file = os.path.join(output_dir, "README.md")
    with open(readme_file, "w") as f:
        f.write("# Automated Data Analysis Report\n\n")
        f.write(story + "\n\n")
        for chart in charts:
            f.write(f"![Chart]({os.path.basename(chart)})\n")

    print(f"Analysis complete. Results saved in: {output_dir}")


# Entry point
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python autolysis.py <csv_file>")
        sys.exit(1)
    main(sys.argv[1])

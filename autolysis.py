# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx",
#   "pandas",
#   "matplotlib",
#   "seaborn",
#   "scikit-learn",
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

    # Handle CSV encoding
    try:
        data = pd.read_csv(csv_file, encoding='utf-8')
    except UnicodeDecodeError:
        # If UTF-8 fails, try ISO-8859-1 (Latin-1) encoding as a fallback
        data = pd.read_csv(csv_file, encoding='ISO-8859-1')

    # Define the output folder based on the CSV file name (without extension)
    output_dir = os.path.splitext(csv_file)[0]
    # Create folder if it does not exist
    os.makedirs(output_dir, exist_ok=True)

    # Perform analysis
    analysis = analyze_data(data)
    outlier_info = detect_outliers(data)
    analysis["outliers"] = outlier_info

    # Generate visualizations
    charts = generate_visualizations(data, output_dir)

    # Create a dynamic prompt for GPT-4o-mini to generate a story from the analysis
    prompt = f"""
    You are an expert data analyst. Below is an analysis of a dataset. Using your knowledge and analytical skills, craft a concise and insightful story about the findings.

    Dataset Overview:
    - Shape: {analysis['shape']}
    - Missing Values: {json.dumps(analysis['missing_values'], indent=2)}
    - Summary Statistics: {json.dumps(analysis['summary_statistics'], indent=2)}
    - Outlier Info: {json.dumps(outlier_info, indent=2)}

    Please write a narrative that:
    1. Introduces the dataset and highlights the most important features.
    2. Discusses the missing values and any observations regarding their impact.
    3. Explores the summary statistics and shares the most interesting insights.
    4. Tells a story about the outliers, what they might indicate, and their significance.
    5. Concludes with key insights that can be derived from the analysis and what actions should be considered going forward.
    
    Keep the story engaging and informative, with clear actionable takeaways.
    """
    
    # Get the generated story from GPT
    story = get_chat_response(prompt)

    # Save the README file with the analysis results
    readme_file = os.path.join(output_dir, "README.md")
    with open(readme_file, "w") as f:
        f.write("# Data Analysis Report\n\n")
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

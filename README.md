# Football Analytics Dashboard

## Overview

This project is an interactive football shot analytics dashboard built using Python and Streamlit.
The dashboard allows users to analyse Brighton match shot data through a variety of visualisations, as well as their opposition's data.

## Features

- Interactive match selection
- Shot maps
- Expected goals
- Team performance summary metrics
- Match statistics
- Dynamic visuals
- Data filtering (minutes)

## Technologies Used

- Python
- Streamlit
- Pandas
- NumPy
- Matplotlib
- Plotly
- Understat API

## Data Sources

Match and shot data all sourced from Understat.
Limited to shot data as Understat do not have efficient data for passes/defensive contributions etc.

## Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/football-dashboard.git
```
Navigate to project folder:

```bash
cd football-dashboard
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Dashboard

Run the streamlit application:

```bash
streamlit run Dynamic_Dashboard.py
```

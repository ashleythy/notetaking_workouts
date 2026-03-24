import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def frequency_chart(df: pd.DataFrame) -> go.Figure:
    """Bar chart: number of workout sessions per date."""
    if df.empty:
        return _empty_fig("No data yet")
    counts = df.groupby("workout_date")["entry_id"].nunique().reset_index()
    counts.columns = ["Date", "Sessions"]
    fig = px.bar(
        counts,
        x="Date",
        y="Sessions",
        labels={"Sessions": "Sessions logged"},
    )
    fig.update_xaxes(tickformat="%Y-%m-%d")
    fig.update_layout(xaxis_tickangle=-45)
    return fig


def volume_chart(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar: total reps per exercise type."""
    if df.empty:
        return _empty_fig("No data yet")
    vol = (
        df.dropna(subset=["reps"])
        .groupby("exercise_name")["reps"]
        .sum()
        .sort_values()
        .reset_index()
    )
    vol.columns = ["Exercise", "Total Reps"]
    if vol.empty:
        return _empty_fig("No rep data recorded yet")
    fig = px.bar(
        vol,
        x="Total Reps",
        y="Exercise",
        orientation="h"
    )
    return fig


def progression_chart(df: pd.DataFrame, exercise: str, metric: str = "weight_kg") -> go.Figure:
    """Line chart: chosen metric over time for a single exercise."""
    subset = df[df["exercise_name"] == exercise].dropna(subset=[metric]).copy()
    if subset.empty:
        return _empty_fig(f"No {metric.replace('_', ' ')} data for {exercise}")
    subset = subset.sort_values("workout_date")
    label = metric.replace("_", " ").title()
    fig = px.line(
        subset,
        x="workout_date",
        y=metric,
        markers=True,
        title=f"{(exercise).capitalize()} ({label})",
        labels={"workout_date": "Date", metric: f"# {label}"},
    )
    fig.update_xaxes(tickformat="%Y-%m-%d")
    fig.update_layout(xaxis_tickangle=-45)
    return fig


def _empty_fig(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font={"size": 16, "color": "gray"},
    )
    fig.update_layout(xaxis_visible=False, yaxis_visible=False)
    return fig

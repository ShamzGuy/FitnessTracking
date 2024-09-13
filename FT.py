import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Hide Streamlit style elements for a cleaner look
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Title of the dashboard
st.title("Fitness Progress Dashboard")

# URL of your Google Sheet CSV export
sheet_id = "193xV6td88gsuLRdoSipsvwjP4zQCntoqWsjTQbjaLjs"
sheet_name = "Sheet1"  # Replace with the actual name of your sheet if different
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"

# Read the data into a pandas DataFrame
df = pd.read_csv(url)

# Convert date columns to datetime
date_columns = df.columns[3:]
df_melted = df.melt(id_vars=["Name", "Goal", "Target"], value_vars=date_columns,
                    var_name="Date", value_name="Value")

# Clean and preprocess the data
df_melted['Date'] = pd.to_datetime(df_melted['Date'], format='%d-%b-%Y', errors='coerce')
# Convert 'Value' to numeric
df_melted['Value'] = pd.to_numeric(df_melted['Value'], errors='coerce')

# Extract numeric part from 'Target' column
df_melted['Target_numeric'] = df_melted['Target'].str.extract('(\d+\.?\d*)', expand=False)
df_melted['Target_numeric'] = pd.to_numeric(df_melted['Target_numeric'], errors='coerce')

# Sidebar for user selection
st.sidebar.title("Filter Options")
selected_name = st.sidebar.selectbox("Select Individual", df['Name'].unique())
selected_goal = st.sidebar.selectbox("Select Goal", df[df['Name'] == selected_name]['Goal'].unique())

# Filter data based on selection
filtered_data = df_melted[(df_melted['Name'] == selected_name) & (df_melted['Goal'] == selected_goal)]

# Display individual's progress
st.header(f"{selected_name} - {selected_goal}")

if not filtered_data.empty and filtered_data['Value'].notnull().any():
    # Prepare data for plotting
    plot_data = filtered_data[['Date', 'Value']].set_index('Date')
    # Add target value as a horizontal line
    target_value = filtered_data['Target_numeric'].iloc[0]
    plot_data['Target'] = target_value

    # Plotting using Altair for better customization
    # Reset index to have 'Date' as a column
    plot_data = plot_data.reset_index()

    # Create the chart with custom colors and improved aesthetics
    # Define color scheme
    line_chart = alt.Chart(plot_data).transform_fold(
        ['Value', 'Target'],
        as_=['Measurement', 'Value']
    ).mark_line().encode(
        x=alt.X('Date:T', axis=alt.Axis(title='Date', grid=False)),
        y=alt.Y('Value:Q', axis=alt.Axis(title='Measurement Value', grid=False)),
        color=alt.Color('Measurement:N', scale=alt.Scale(
            domain=['Value', 'Target'],
            range=['#1f77b4', 'green']  # Blue for Value, Green for Target
        )),
        strokeDash=alt.condition(
            alt.datum.Measurement == 'Target',
            alt.value([5, 5]),
            alt.value([0])
        ),
        tooltip=[alt.Tooltip('Date:T', title='Date'),
                 alt.Tooltip('Measurement:N', title='Type'),
                 alt.Tooltip('Value:Q', title='Value')]
    ).properties(
        title=f"{selected_name}'s Progress on {selected_goal}",
        width=700,
        height=400
    ).configure_title(
        fontSize=20,
        anchor='start',
        color='gray'
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    ).interactive()

    st.altair_chart(line_chart, use_container_width=True)

    # Display current status
    latest_value = filtered_data.dropna(subset=['Value']).iloc[-1]['Value']
    st.write(f"**Latest Value:** {latest_value}")
    st.write(f"**Target Value:** {filtered_data['Target'].iloc[0]}")
else:
    st.write("No data available for this selection.")

# Leaderboard Section
st.header("Leaderboard")

# Assign points for each activity
# Define a function to calculate points
def calculate_points(row):
    # Base points for participation per week
    participation_points = 1 if not pd.isnull(row['Value']) else 0

    # Points based on progress towards the target
    if pd.isnull(row['Value']) or pd.isnull(row['Target_numeric']):
        progress_points = 0
    else:
        # For goals where higher value is better (e.g., steps, workouts)
        if "Loss" not in row['Goal'] and "weight" not in row['Goal'].lower():
            progress = (row['Value'] / row['Target_numeric']) * 100
        else:  # For weight loss goals where lower value is better
            progress = ((row['Target_numeric'] / row['Value']) * 100) if row['Value'] != 0 else 0

        # Cap the progress at 100%
        progress = min(progress, 100)
        # Assign points (e.g., 1 point for every 10% progress)
        progress_points = progress / 10

    # Total points for the row
    total_points = participation_points + progress_points
    return total_points

# Apply the function to calculate points
df_melted['Points'] = df_melted.apply(calculate_points, axis=1)

# Sum points for each individual
leaderboard = df_melted.groupby('Name')['Points'].sum().reset_index()
leaderboard = leaderboard.sort_values(by='Points', ascending=False)

# Display the leaderboard with a bar chart
st.subheader("Points Leaderboard")

# Create a bar chart for the leaderboard
leaderboard_chart = alt.Chart(leaderboard).mark_bar().encode(
    x=alt.X('Points:Q', title='Total Points'),
    y=alt.Y('Name:N', sort='-x', title='Participant'),
    color=alt.Color('Name:N', legend=None),
    tooltip=[alt.Tooltip('Name:N', title='Participant'),
             alt.Tooltip('Points:Q', title='Total Points', format='.1f')]
).properties(
    width=700,
    height=400
).configure_axis(
    labelFontSize=12,
    titleFontSize=14
).configure_title(
    fontSize=20,
    anchor='start',
    color='gray'
).configure_view(
    strokeWidth=0
)

st.altair_chart(leaderboard_chart, use_container_width=True)

# Optionally, display the raw data
if st.sidebar.checkbox("Show Raw Data"):
    st.subheader("Raw Data")
    st.write(df_melted)
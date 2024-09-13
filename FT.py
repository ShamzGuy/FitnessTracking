import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Set page configuration for better mobile experience
st.set_page_config(
    page_title="Fitness Progress Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS to adjust layout for mobile devices
st.markdown("""
    <style>
        /* Hide the default Streamlit header and footer */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        /* Adjust the padding of the main block */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)

# Title of the dashboard
st.title("Fitness Progress Dashboard")

# URL of your Google Sheet CSV export
sheet_id = "193xV6td88gsuLRdoSipsvwjP4zQCntoqWsjTQbjaLjs"
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

# Assign points for each activity
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

# Sidebar for user selection
with st.sidebar:
    st.title("Filter Options")
    # Add an option to select 'View Leaderboard' or 'View Individual Progress'
    view_option = st.radio("Select View", ('Leaderboard', 'Individual Progress'))
    # Optionally, display the raw data
    show_data = st.checkbox("Show Raw Data")

if view_option == 'Leaderboard':
    # Display the leaderboard at the top
    st.header("Leaderboard")
    st.subheader("Points Leaderboard")

    # Create a bar chart for the leaderboard
    leaderboard_chart = alt.Chart(leaderboard).mark_bar().encode(
        x=alt.X('Points:Q', title='Total Points'),
        y=alt.Y('Name:N', sort='-x', title='Participant'),
        color=alt.Color('Name:N', legend=None),
        tooltip=[alt.Tooltip('Name:N', title='Participant'),
                 alt.Tooltip('Points:Q', title='Total Points', format='.1f')]
    ).properties(
        height=400
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    ).configure_title(
        fontSize=18,
        anchor='start',
        color='gray'
    ).configure_view(
        strokeWidth=0
    )

    st.altair_chart(leaderboard_chart, use_container_width=True)

    if show_data:
        st.subheader("Raw Data")
        st.write(df_melted)

else:
    # When 'Individual Progress' is selected
    selected_name = st.selectbox("Select Individual", df['Name'].unique())
    selected_goal = st.selectbox("Select Goal", df[df['Name'] == selected_name]['Goal'].unique())

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

        # Reset index to have 'Date' as a column
        plot_data = plot_data.reset_index()

        # Create the chart with custom colors and improved aesthetics
        line_chart = alt.Chart(plot_data).transform_fold(
            ['Value', 'Target'],
            as_=['Measurement', 'Value']
        ).mark_line(point=True).encode(
            x=alt.X('Date:T', axis=alt.Axis(title='Date', grid=False, labelAngle=-45)),
            y=alt.Y('Value:Q', axis=alt.Axis(title='Measurement Value', grid=False)),
            color=alt.Color('Measurement:N', scale=alt.Scale(
                domain=['Value', 'Target'],
                range=['#1f77b4', 'green']  # Blue for Value, Green for Target
            ), legend=alt.Legend(title="Legend")),
            strokeDash=alt.condition(
                alt.datum.Measurement == 'Target',
                alt.value([5, 5]),
                alt.value([0])
            ),
            tooltip=[alt.Tooltip('Date:T', title='Date'),
                     alt.Tooltip('Measurement:N', title='Type'),
                     alt.Tooltip('Value:Q', title='Value')]
        ).properties(
            height=400
        ).configure_axis(
            labelFontSize=12,
            titleFontSize=14
        ).configure_title(
            fontSize=18,
            anchor='start',
            color='gray'
        ).configure_legend(
            orient='bottom'
        ).interactive()

        st.altair_chart(line_chart, use_container_width=True)

        # Display current status
        latest_value = filtered_data.dropna(subset=['Value']).iloc[-1]['Value']
        st.markdown(f"**Latest Value:** {latest_value}")
        st.markdown(f"**Target Value:** {filtered_data['Target'].iloc[0]}")

        if show_data:
            st.subheader("Raw Data")
            st.write(filtered_data)
    else:
        st.write("No data available for this selection.")

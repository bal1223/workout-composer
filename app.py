import streamlit as st
import pandas as pd
import datetime
import logging
from database import init_db, populate_initial_data
from workout_generator import (
    generate_workout, save_workout, load_workout, 
    save_workout_feedback, get_recent_workouts
)
from components import (
    get_all_workout_components, add_workout_component, 
    update_workout_component, delete_workout_component,
    validate_component_input
)
from exercises import (
    get_all_circuit_exercises, add_exercise, 
    update_exercise, delete_exercise,
    validate_exercise_input
)
from constraints import (
    get_component_type_limits, get_duration_constraints,
    update_component_type_limit, update_duration_constraints,
    validate_constraints_input, validate_duration_constraints
)
from utils import (
    get_dashboard_stats, get_workout_history, get_workout_stats,
    format_duration, format_date, get_component_options,
    validate_database_setup, export_workout_to_dict
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)
logger = logging.getLogger("app")

# Initialize session state
if 'current_workout' not in st.session_state:
    st.session_state.current_workout = None
if 'saved_workout_id' not in st.session_state:
    st.session_state.saved_workout_id = None

def main():
    st.set_page_config(
        page_title="Workout Composer",
        page_icon="💪",
        layout="wide"
    )
    
    # Initialize database
    init_db()
    populate_initial_data()
    
    # Validate database setup
    is_valid, error_msg = validate_database_setup()
    if not is_valid:
        st.error(f"Database setup error: {error_msg}")
        st.stop()
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", 
        ["Dashboard", "Generate Workout", "Workout History", 
         "Manage Components", "Manage Exercises", "Manage Constraints", "Stats"])
    
    # Route to appropriate page
    if page == "Dashboard":
        dashboard_page()
    elif page == "Generate Workout":
        generate_workout_page()
    elif page == "Workout History":
        workout_history_page()
    elif page == "Manage Components":
        manage_components_page()
    elif page == "Manage Exercises":
        manage_exercises_page()
    elif page == "Manage Constraints":
        manage_constraints_page()
    elif page == "Stats":
        stats_page()

def dashboard_page():
    st.header("Dashboard")
    
    # Get dashboard stats
    stats = get_dashboard_stats()
    
    # Summary stats in columns
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Total Workouts", value=str(stats['total_workouts']))
    with col2:
        st.metric(label="Completion Rate", value=f"{stats['completion_rate']}%")
    with col3:
        st.metric(label="Avg Rating", value=f"{stats['avg_rating']}/3")
    
    # Quick actions
    # st.subheader("Quick Actions")
    # col1, col2 = st.columns(2)
    # with col1:
    #     if st.button("Generate New Workout"):
    #         st.switch_page("pages/generate_workout.py")
    # with col2:
    #     if st.button("View Recent Workouts"):
    #         st.switch_page("pages/workout_history.py")
    
    # Recent activity
    st.subheader("Recent Activity")
    recent_workouts = get_recent_workouts(limit=5)
    
    if recent_workouts:
        recent_df = pd.DataFrame([
            {
                "Date": format_date(workout['date']),
                "Duration": f"{workout['duration']} min",
                "Rating": '★' * (workout['rating'] or 0) if workout['rating'] else '--',
                "Status": "Completed" if workout['completed'] else "Not Completed"
            }
            for workout in recent_workouts
        ])
        st.dataframe(recent_df, hide_index=True)
    else:
        st.info("No workouts generated yet. Generate your first workout!")

def generate_workout_page():
    st.header("Generate Workout")
    
    # Generate form
    with st.form("workout_generator"):
        st.write("Generate a workout based on current constraints")
        
        # Advanced options
        advanced_options = st.expander("Advanced Options (Optional)")
        with advanced_options:
            duration_constraints = get_duration_constraints()
            min_duration = duration_constraints['min_length']
            max_duration = duration_constraints['max_length']
            default_duration = (min_duration + max_duration) // 2
            
            target_duration = st.slider(
                "Target Duration (minutes)",
                min_value=min_duration,
                max_value=max_duration,
                value=default_duration
            )
            
            component_options = get_component_options()
            
            include_components = st.multiselect(
                "Include Components",
                options=component_options
            )
            
            exclude_components = st.multiselect(
                "Exclude Components",
                options=[opt for opt in component_options if opt not in include_components]
            )
        
        generate_button = st.form_submit_button("Generate Workout")
    
    # Handle workout generation outside the form
    if generate_button:
        with st.spinner("Generating workout..."):
            # Get parameters if they exist
            params = {}
            if 'target_duration' in locals():
                params['target_duration'] = target_duration
            if 'include_components' in locals() and include_components:
                params['include_components'] = include_components
            if 'exclude_components' in locals() and exclude_components:
                params['exclude_components'] = exclude_components
            
            workout = generate_workout(**params)
            
            if workout:
                # Store in session state
                st.session_state.current_workout = workout
                st.session_state.saved_workout_id = None
                st.success("Workout Generated!")
                logger.info(f"Generated workout with {len(workout.get('components', []))} components")
            else:
                st.error("Could not generate a workout with the given constraints. Please try again or adjust constraints.")
    
    # Display the workout if it exists in session state
    if 'current_workout' in st.session_state and st.session_state.current_workout:
        display_generated_workout(st.session_state.current_workout)

def display_generated_workout(workout):
    # Get current day of week
    day_of_week = datetime.datetime.now().strftime('%A')
    today = datetime.datetime.now().strftime('%B %d, %Y')
    
    # Show workout details
    st.subheader(f"{day_of_week} Workout - {today}")
    st.write(f"Total Duration: {workout['total_duration']} minutes")
    
    # Display each component
    for component in workout['components']:
        component_header = f"{component['name']} ({component['type']} - {component['duration']} min)"
        with st.expander(component_header, expanded=True):
            # For circuit components, show exercises
            if component['exercises']:
                st.write("Circuit exercises:")
                exercises_df = pd.DataFrame(
                    [(ex['name'], ex['body_group']) for ex in component['exercises']],
                    columns=["Exercise", "Body Group"]
                )
                st.dataframe(exercises_df, hide_index=True)
            else:
                st.write(f"Follow {component['name']} routine")
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Save Workout", key="save_workout_btn"):
            if 'current_workout' in st.session_state and st.session_state.current_workout:
                try:
                    workout_id = save_workout(st.session_state.current_workout)
                    if workout_id:
                        st.session_state.saved_workout_id = workout_id
                        st.success(f"Workout saved! ID: {workout_id}")
                        logger.info(f"Workout saved successfully with ID: {workout_id}")
                    else:
                        st.error("Failed to save workout. Check app.log for details.")
                        logger.error("save_workout returned None")
                except Exception as e:
                    st.error(f"Error saving workout: {str(e)}")
                    logger.error(f"Exception in save_workout: {str(e)}", exc_info=True)
            else:
                st.warning("No workout to save. Please generate a workout first.")
    
    with col2:
        if st.button("Regenerate"):
            st.rerun()
    
    with col3:
        # Export as PDF functionality would go here
        st.download_button(
            "Export PDF",
            data="PDF export not implemented in this version",
            file_name="workout.pdf",
            mime="application/pdf",
            disabled=True
        )
    
    # Feedback section
    if st.session_state.saved_workout_id:
        st.divider()
        st.subheader("Workout Feedback")
        
        completed = st.checkbox("Mark as Completed")
        
        if completed:
            rating = st.radio("Rate this workout:", ["★", "★★", "★★★"], horizontal=True)
            rating_value = len(rating)  # Convert to numeric value
            
            notes = st.text_area("Workout Notes")
            
            if st.button("Submit Feedback"):
                success = save_workout_feedback(
                    st.session_state.saved_workout_id,
                    completed=True,
                    rating=rating_value,
                    notes=notes
                )
                if success:
                    st.success("Feedback saved!")
                else:
                    st.error("Failed to save feedback.")

def workout_history_page():
    st.header("Workout History")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    with col1:
        default_start = datetime.date.today() - datetime.timedelta(days=30)
        start_date = st.date_input("Date Range Start", default_start)
    with col2:
        end_date = st.date_input("Date Range End", datetime.date.today())
    with col3:
        status_filter = st.selectbox("Status", ["All", "Completed", "Not Completed"])
    
    # Get workout history
    workouts = get_workout_history(start_date, end_date, status_filter)
    
    if workouts:
        # Convert to DataFrame for display
        workouts_df = pd.DataFrame(workouts)
        st.dataframe(workouts_df, hide_index=True)
        
        # Add view button for each workout
        selected_workout = st.selectbox("Select a workout to view details:", [""] + [f"{w['id']} - {w['date']}" for w in workouts])
        if selected_workout:
            selected_id = int(selected_workout.split()[0])
            if st.button("View Details"):
                workout = load_workout(selected_id)
                if workout:
                    st.divider()
                    st.subheader(f"Workout Details - {format_date(workout['date'])}")
                    display_workout_details(workout)
    else:
        st.info("No workouts found for the selected filters.")

def display_workout_details(workout):
    st.write(f"**Total Duration:** {workout['total_duration']} minutes")
    st.write(f"**Status:** {'Completed' if workout['completed'] else 'Not Completed'}")
    if workout['rating']:
        st.write(f"**Rating:** {'★' * workout['rating']}")
    if workout['notes']:
        st.write(f"**Notes:** {workout['notes']}")
    
    st.subheader("Components")
    for component in workout['components']:
        with st.expander(f"{component['name']} ({component['type']} - {component['duration']} min)"):
            if component['exercises']:
                exercises_df = pd.DataFrame(
                    [(ex['name'], ex['body_group']) for ex in component['exercises']],
                    columns=["Exercise", "Body Group"]
                )
                st.dataframe(exercises_df, hide_index=True)
            else:
                st.write(f"Follow {component['name']} routine")

def manage_components_page():
    st.header("Manage Workout Components")
    
    tab1, tab2 = st.tabs(["View Components", "Add/Edit Component"])
    
    with tab1:
        components = get_all_workout_components()
        if components:
            components_df = pd.DataFrame(components)
            st.dataframe(components_df, hide_index=True)
            
            # Select component to edit/delete
            component_names = [c['name'] for c in components]
            selected_component = st.selectbox("Select a component to edit or delete:", [""] + component_names)
            
            if selected_component:
                component = next(c for c in components if c['name'] == selected_component)
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Edit Component"):
                        st.session_state.editing_component = component
                        st.rerun()
                
                with col2:
                    if st.button("Delete Component"):
                        if delete_workout_component(component['id']):
                            st.success(f"Deleted component: {component['name']}")
                            st.rerun()
                        else:
                            st.error("Cannot delete component as it is in use.")
        else:
            st.info("No workout components found.")
    
    with tab2:
        # Check if we're editing an existing component
        editing_component = st.session_state.get('editing_component', None)
        
        st.subheader("Edit Component" if editing_component else "Add New Component")
        
        with st.form("component_form"):
            name = st.text_input("Component Name", value=editing_component['name'] if editing_component else "")
            avg_duration = st.number_input(
                "Average Duration (minutes)", 
                min_value=5, 
                max_value=60, 
                value=editing_component['avg_duration'] if editing_component else 20
            )
            source = st.selectbox(
                "Source", 
                ["Circuit Exercises", "Peloton", "NA"],
                index=["Circuit Exercises", "Peloton", "NA"].index(editing_component['source']) if editing_component else 0
            )
            component_type = st.selectbox(
                "Type", 
                ["Circuit", "Core", "Cardio", "Stretching"],
                index=["Circuit", "Core", "Cardio", "Stretching"].index(editing_component['type']) if editing_component else 0
            )
            
            exercise_count = None
            if component_type == "Circuit":
                exercise_count = st.number_input(
                    "Exercise Count", 
                    min_value=1, 
                    max_value=10, 
                    value=editing_component['exercise_count'] if editing_component and editing_component['exercise_count'] else 5
                )
            
            submitted = st.form_submit_button("Save Component")
            
            if submitted:
                is_valid, error_msg = validate_component_input(name, avg_duration, source, component_type, exercise_count)
                
                if not is_valid:
                    st.error(error_msg)
                else:
                    if editing_component:
                        # Update existing component
                        if update_workout_component(editing_component['id'], name, avg_duration, source, component_type, exercise_count):
                            st.success(f"Updated component: {name}")
                            del st.session_state.editing_component
                            st.rerun()
                        else:
                            st.error("Failed to update component.")
                    else:
                        # Add new component
                        component_id = add_workout_component(name, avg_duration, source, component_type, exercise_count)
                        if component_id:
                            st.success(f"Added component: {name}")
                            st.rerun()
                        else:
                            st.error("Failed to add component.")

def manage_exercises_page():
    st.header("Manage Circuit Exercises")
    
    tab1, tab2 = st.tabs(["View Exercises", "Add/Edit Exercise"])
    
    with tab1:
        exercises = get_all_circuit_exercises()
        if exercises:
            exercises_df = pd.DataFrame(exercises)
            exercises_df['TRX'] = exercises_df['trx_flag'].apply(lambda x: 'Yes' if x else 'No')
            exercises_df = exercises_df.drop('trx_flag', axis=1)
            st.dataframe(exercises_df, hide_index=True)
            
            # Select exercise to edit/delete
            exercise_names = [e['name'] for e in exercises]
            selected_exercise = st.selectbox("Select an exercise to edit or delete:", [""] + exercise_names)
            
            if selected_exercise:
                exercise = next(e for e in exercises if e['name'] == selected_exercise)
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Edit Exercise"):
                        st.session_state.editing_exercise = exercise
                        st.rerun()
                
                with col2:
                    if st.button("Delete Exercise"):
                        if delete_exercise(exercise['id']):
                            st.success(f"Deleted exercise: {exercise['name']}")
                            st.rerun()
                        else:
                            st.error("Cannot delete exercise as it is in use.")
        else:
            st.info("No circuit exercises found.")
    
    with tab2:
        # Check if we're editing an existing exercise
        editing_exercise = st.session_state.get('editing_exercise', None)
        
        st.subheader("Edit Exercise" if editing_exercise else "Add New Exercise")
        
        with st.form("exercise_form"):
            name = st.text_input("Exercise Name", value=editing_exercise['name'] if editing_exercise else "")
            body_group = st.selectbox(
                "Body Group", 
                ["Lower Body", "Upper Body", "Core", "Full Body", "Back", "Arms"],
                index=["Lower Body", "Upper Body", "Core", "Full Body", "Back", "Arms"].index(editing_exercise['body_group']) if editing_exercise else 0
            )
            trx_flag = st.checkbox("TRX Exercise", value=editing_exercise['trx_flag'] if editing_exercise else False)
            
            submitted = st.form_submit_button("Save Exercise")
            
            if submitted:
                is_valid, error_msg = validate_exercise_input(name, body_group, trx_flag)
                
                if not is_valid:
                    st.error(error_msg)
                else:
                    if editing_exercise:
                        # Update existing exercise
                        if update_exercise(editing_exercise['id'], name, body_group, trx_flag):
                            st.success(f"Updated exercise: {name}")
                            del st.session_state.editing_exercise
                            st.rerun()
                        else:
                            st.error("Failed to update exercise.")
                    else:
                        # Add new exercise
                        exercise_id = add_exercise(name, body_group, trx_flag)
                        if exercise_id:
                            st.success(f"Added exercise: {name}")
                            st.rerun()
                        else:
                            st.error("Failed to add exercise.")

def manage_constraints_page():
    st.header("Manage Constraints")
    
    # Component type limits
    st.subheader("Component Type Limits")
    
    type_limits = get_component_type_limits()
    
    # Create a DataFrame for display
    type_limits_df = pd.DataFrame([
        {"Component Type": k, "Count Limit": v}
        for k, v in type_limits.items()
    ])
    
    # Display as editable table
    edited_data = st.data_editor(
        type_limits_df,
        num_rows="fixed",
        column_config={
            "Count Limit": st.column_config.NumberColumn(
                "Count Limit",
                min_value=0,
                max_value=10,
                step=1
            )
        },
        hide_index=True
    )
    
    # Save button for type limits
    if st.button("Save Type Limits"):
        success = True
        for _, row in edited_data.iterrows():
            if not update_component_type_limit(row['Component Type'], row['Count Limit']):
                success = False
                break
        
        if success:
            st.success("Component type limits updated successfully!")
        else:
            st.error("Failed to update some limits.")
    
    # Duration constraints
    st.subheader("Duration Constraints")
    
    duration_constraints = get_duration_constraints()
    
    col1, col2 = st.columns(2)
    with col1:
        min_length = st.number_input(
            "Minimum Total Length (minutes)",
            min_value=20,
            max_value=60,
            value=duration_constraints['min_length']
        )
    with col2:
        max_length = st.number_input(
            "Maximum Total Length (minutes)",
            min_value=30,
            max_value=120,
            value=duration_constraints['max_length']
        )
    
    if st.button("Save Duration Constraints"):
        is_valid, error_msg = validate_duration_constraints(min_length, max_length)
        
        if not is_valid:
            st.error(error_msg)
        else:
            if update_duration_constraints(min_length, max_length):
                st.success("Duration constraints updated successfully!")
            else:
                st.error("Failed to update duration constraints.")

def stats_page():
    st.header("Workout Statistics")
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        default_start = datetime.date.today() - datetime.timedelta(days=30)
        start_date = st.date_input("From Date", default_start)
    with col2:
        end_date = st.date_input("To Date", datetime.date.today())
    
    # Get statistics
    stats = get_workout_stats(start_date, end_date)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Total Workouts", value=str(stats['total_workouts']))
    with col2:
        st.metric(label="Completion Rate", value=f"{stats['completion_rate']}%")
    with col3:
        st.metric(label="Avg Workout Time", value=f"{stats['avg_duration']} min")
    with col4:
        st.metric(label="Avg Rating", value=f"{stats['avg_rating']}/3")
    
    # Component usage chart
    st.subheader("Component Usage")
    if stats['component_usage']:
        component_df = pd.DataFrame([
            {"Component Type": k, "Usage Count": v}
            for k, v in stats['component_usage'].items()
        ])
        st.bar_chart(component_df.set_index('Component Type'))
    else:
        st.info("No component usage data available for the selected date range.")
    
    # Most used exercises
    st.subheader("Most Used Circuit Exercises")
    if stats['exercise_usage']:
        exercise_df = pd.DataFrame(stats['exercise_usage'])
        exercise_df.columns = ["Exercise", "Times Used"]
        st.dataframe(exercise_df, hide_index=True)
    else:
        st.info("No exercise usage data available for the selected date range.")

if __name__ == "__main__":
    main()
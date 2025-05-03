import random
import logging
from database import get_db_connection
from constraints import get_component_type_limits, get_duration_constraints
from components import get_all_workout_components, get_workout_component
from exercises import get_all_circuit_exercises, get_exercise

logger = logging.getLogger("workout_generator")

def generate_workout(target_duration=None, include_components=None, exclude_components=None):
    """
    Generates a random workout within defined constraints
    
    Args:
        target_duration: Optional target duration in minutes
        include_components: Optional list of component names to include
        exclude_components: Optional list of component names to exclude
    
    Returns:
        A dictionary with workout details or None if generation fails
    """
    # 1. Load constraints
    type_limits = get_component_type_limits()
    duration_constraints = get_duration_constraints()
    
    # Modify target duration based on constraints if provided
    if target_duration:
        min_duration = target_duration
        max_duration = target_duration + 5  # Allow slight flexibility
    else:
        min_duration = duration_constraints['min_length']
        max_duration = duration_constraints['max_length']
    
    # 2. Initialize counters for each component type
    type_counts = {component_type: 0 for component_type in type_limits.keys()}
    
    # 3. Initialize total duration
    total_duration = 0
    
    # 4. Get all available components
    all_components = get_all_workout_components()
    
    # Filter components based on include/exclude lists
    available_components = []
    for component in all_components:
        if include_components and component['name'] not in include_components:
            continue
        if exclude_components and component['name'] in exclude_components:
            continue
        available_components.append(component)
    
    if not available_components:
        logger.warning("No available components after filtering")
        return None
    
    # 5. Randomly select components while respecting constraints
    selected_components = []
    available_components_copy = available_components.copy()
    
    # First, add all required components if specified
    if include_components:
        required_components = [c for c in available_components if c['name'] in include_components]
        for component in required_components:
            # Check if adding this component would exceed type limit
            if type_counts[component['type']] >= type_limits[component['type']]:
                logger.warning(f"Cannot include {component['name']} as it would exceed type limit for {component['type']}")
                continue
                
            # Add component to selected list
            selected_components.append(component)
            type_counts[component['type']] += 1
            total_duration += component['avg_duration']
            
            # Remove from available copy
            if component in available_components_copy:
                available_components_copy.remove(component)
    
    # Then, add random components until constraints are met
    max_attempts = 50  # Prevent infinite loops
    attempts = 0
    
    # TODO: Don't repeat components selected in the last x workouts
    while attempts < max_attempts:
        # If we've reached minimum duration, check if we're within all constraints
        if total_duration >= min_duration and total_duration <= max_duration:
            all_constraints_met = True
            for component_type, limit in type_limits.items():
                if limit > 0 and type_counts.get(component_type, 0) == 0:
                    all_constraints_met = False
                    break
            
            if all_constraints_met:
                break
        
        # If no more components are available or we've exceeded max duration, break
        if not available_components_copy or total_duration > max_duration:
            break
            
        # Randomly select a component
        component = random.choice(available_components_copy)
        available_components_copy.remove(component)
        
        # Check if adding this component would exceed type limit
        if type_counts.get(component['type'], 0) >= type_limits.get(component['type'], 0):
            continue
            
        # Check if adding this component would exceed duration limit
        if total_duration + component['avg_duration'] > max_duration:
            continue
            
        # Add component to selected list
        selected_components.append(component)
        type_counts[component['type']] = type_counts.get(component['type'], 0) + 1
        total_duration += component['avg_duration']
        
        attempts += 1
    
    # Check if we have a valid workout
    if total_duration < min_duration:
        logger.warning(f"Could not generate workout with minimum duration of {min_duration} minutes")
        return None
    
    # 6. For circuit components, randomly select appropriate exercises
    workout = {
        'components': [],
        'total_duration': total_duration
    }
    
    for position, component in enumerate(selected_components):
        component_data = {
            'id': component['id'],
            'name': component['name'],
            'type': component['type'],
            'duration': component['avg_duration'],
            'position': position,
            'exercises': []
        }
        
        # If component is a circuit, select exercises
        if component['type'] == 'Circuit' and component['exercise_count'] is not None:
            exercises = select_exercises_for_circuit(component)
            component_data['exercises'] = exercises
        
        workout['components'].append(component_data)
    
    return workout

# TODO: Don't repeat exercises selected in the last x workouts
def select_exercises_for_circuit(component):
    """
    Selects appropriate exercises for a circuit component
    
    Args:
        component: Component dictionary with type and exercise_count
        
    Returns:
        List of exercise dictionaries
    """
    # Get all exercises
    all_exercises = get_all_circuit_exercises()
    
    # Filter for TRX if needed
    if 'TRX' in component['name'].upper():
        filtered_exercises = [e for e in all_exercises if e['trx_flag']]
    else:
        filtered_exercises = all_exercises
    
    # If exercise_count specified, select that many exercises
    exercise_count = component['exercise_count'] or 5  # Default to 5 if None
    
    # Ensure we have enough exercises
    if len(filtered_exercises) < exercise_count:
        logger.warning(f"Not enough exercises available for {component['name']}. Using all {len(filtered_exercises)} available exercises.")
        exercise_count = len(filtered_exercises)
    
    if exercise_count == 0:
        return []
    
    # Randomly select exercises
    # TODO: Possibly add logic to ensure variety in body groups
    # For now, just sample without replacement
    selected_exercises = random.sample(filtered_exercises, exercise_count)
    
    # Format for return
    return [{'id': e['id'], 'name': e['name'], 'body_group': e['body_group']} 
            for e in selected_exercises]

def save_workout(workout):
    """
    Saves a generated workout to the database
    
    Args:
        workout: Workout dictionary to save
        
    Returns:
        Workout ID if successful, None otherwise
    """
    # Begin transaction
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Insert workout
        cursor.execute('''
            INSERT INTO generated_workouts (total_duration)
            VALUES (?)
        ''', (workout['total_duration'],))
        
        workout_id = cursor.lastrowid
        
        # Insert components
        for component in workout['components']:
            cursor.execute('''
                INSERT INTO workout_components_used 
                (workout_id, component_id, position_in_workout)
                VALUES (?, ?, ?)
            ''', (workout_id, component['id'], component['position']))
            
            # Insert circuit exercises if any
            if component['exercises']:
                for pos, exercise in enumerate(component['exercises']):
                    cursor.execute('''
                        INSERT INTO circuit_exercises_used
                        (workout_id, component_id, exercise_id, position_in_circuit)
                        VALUES (?, ?, ?, ?)
                    ''', (workout_id, component['id'], exercise['id'], pos))
        
        # Commit transaction
        conn.commit()
        logger.info(f"Saved workout ID {workout_id} with {len(workout['components'])} components")
        return workout_id
    
    except Exception as e:
        # Rollback in case of error
        conn.rollback()
        logger.error(f"Error saving workout: {e}")
        return None
    
    finally:
        conn.close()

def load_workout(workout_id):
    """
    Loads a workout from the database
    
    Args:
        workout_id: ID of the workout to load
        
    Returns:
        Workout dictionary if found, None otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get workout details
        cursor.execute('''
            SELECT id, date_generated, total_duration, completed, rating, notes
            FROM generated_workouts
            WHERE id = ?
        ''', (workout_id,))
        
        workout_data = cursor.fetchone()
        
        if not workout_data:
            logger.warning(f"No workout found with ID {workout_id}")
            return None
        
        # Format workout
        workout = {
            'id': workout_data['id'],
            'date': workout_data['date_generated'],
            'total_duration': workout_data['total_duration'],
            'completed': bool(workout_data['completed']),
            'rating': workout_data['rating'],
            'notes': workout_data['notes'],
            'components': []
        }
        
        # Get components
        cursor.execute('''
            SELECT wcu.component_id, wcu.position_in_workout, 
                   wc.name, wc.avg_duration, wc.type
            FROM workout_components_used wcu
            JOIN workout_components wc ON wcu.component_id = wc.id
            WHERE wcu.workout_id = ?
            ORDER BY wcu.position_in_workout
        ''', (workout_id,))
        
        components_data = cursor.fetchall()
        
        for comp_data in components_data:
            component = {
                'id': comp_data['component_id'],
                'position': comp_data['position_in_workout'],
                'name': comp_data['name'],
                'duration': comp_data['avg_duration'],
                'type': comp_data['type'],
                'exercises': []
            }
            
            # Get exercises if it's a circuit
            if component['type'] == 'Circuit':
                cursor.execute('''
                    SELECT ce.id, ce.name, ce.body_group
                    FROM circuit_exercises_used ceu
                    JOIN circuit_exercises ce ON ceu.exercise_id = ce.id
                    WHERE ceu.workout_id = ? AND ceu.component_id = ?
                    ORDER BY ceu.position_in_circuit
                ''', (workout_id, component['id']))
                
                exercises_data = cursor.fetchall()
                
                for ex_data in exercises_data:
                    exercise = {
                        'id': ex_data['id'],
                        'name': ex_data['name'],
                        'body_group': ex_data['body_group']
                    }
                    component['exercises'].append(exercise)
            
            workout['components'].append(component)
        
        logger.info(f"Loaded workout ID {workout_id} with {len(workout['components'])} components")
        return workout
    
    except Exception as e:
        logger.error(f"Error loading workout {workout_id}: {e}")
        return None
    
    finally:
        conn.close()

def save_workout_feedback(workout_id, completed=False, rating=None, notes=None):
    """
    Saves feedback for a workout
    
    Args:
        workout_id: ID of the workout
        completed: Whether the workout was completed
        rating: Optional rating (1-3)
        notes: Optional notes
        
    Returns:
        True if successful, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE generated_workouts
            SET completed = ?, rating = ?, notes = ?
            WHERE id = ?
        ''', (completed, rating, notes, workout_id))
        
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"Updated feedback for workout ID {workout_id}")
            return True
        else:
            logger.warning(f"No workout found with ID {workout_id}")
            return False
    
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving workout feedback for ID {workout_id}: {e}")
        return False
    
    finally:
        conn.close()

def get_recent_workouts(limit=5):
    """
    Retrieves recent workouts
    
    Args:
        limit: Maximum number of workouts to retrieve
        
    Returns:
        List of workout dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, date_generated, total_duration, completed, rating
            FROM generated_workouts
            ORDER BY date_generated DESC
            LIMIT ?
        ''', (limit,))
        
        result = []
        for row in cursor.fetchall():
            # Get component names for this workout
            cursor.execute('''
                SELECT wc.name
                FROM workout_components_used wcu
                JOIN workout_components wc ON wcu.component_id = wc.id
                WHERE wcu.workout_id = ?
                ORDER BY wcu.position_in_workout
            ''', (row['id'],))
            
            component_names = [comp_row['name'] for comp_row in cursor.fetchall()]
            
            result.append({
                'id': row['id'],
                'date': row['date_generated'],
                'duration': row['total_duration'],
                'components': component_names,
                'completed': bool(row['completed']),
                'rating': row['rating']
            })
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting recent workouts: {e}")
        return []
    
    finally:
        conn.close()
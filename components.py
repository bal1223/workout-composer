import logging
from database import get_db_connection, safe_db_operation

logger = logging.getLogger("components")

def get_all_workout_components():
    """
    Retrieves all workout components from the database.
    Returns a list of dictionaries.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT id, name, avg_duration, source, type, exercise_count
        FROM workout_components
        ORDER BY name
        ''')
        
        result = []
        for row in cursor.fetchall():
            result.append({
                'id': row['id'],
                'name': row['name'],
                'avg_duration': row['avg_duration'],
                'source': row['source'],
                'type': row['type'],
                'exercise_count': row['exercise_count']
            })
        
        return result
    except Exception as e:
        logger.error(f"Error getting workout components: {e}")
        return []
    finally:
        conn.close()

def get_workout_component(component_id):
    """
    Retrieves a specific workout component by ID.
    Returns the component as a dictionary or None if not found.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT id, name, avg_duration, source, type, exercise_count
        FROM workout_components
        WHERE id = ?
        ''', (component_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'id': row['id'],
                'name': row['name'],
                'avg_duration': row['avg_duration'],
                'source': row['source'],
                'type': row['type'],
                'exercise_count': row['exercise_count']
            }
        else:
            return None
    except Exception as e:
        logger.error(f"Error getting workout component {component_id}: {e}")
        return None
    finally:
        conn.close()

def add_workout_component(name, avg_duration, source, type, exercise_count=None):
    """
    Add a new workout component.
    Returns the ID of the newly created component or None if an error occurred.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        INSERT INTO workout_components (name, avg_duration, source, type, exercise_count)
        VALUES (?, ?, ?, ?, ?)
        ''', (name, avg_duration, source, type, exercise_count))
        
        component_id = cursor.lastrowid
        conn.commit()
        logger.info(f"Added workout component: {name} (ID: {component_id})")
        return component_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Error adding workout component {name}: {e}")
        return None
    finally:
        conn.close()

def update_workout_component(component_id, name, avg_duration, source, type, exercise_count=None):
    """
    Update an existing workout component.
    Returns True if successful, False otherwise.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        UPDATE workout_components
        SET name = ?, avg_duration = ?, source = ?, type = ?, exercise_count = ?
        WHERE id = ?
        ''', (name, avg_duration, source, type, exercise_count, component_id))
        
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"Updated workout component ID {component_id}: {name}")
            return True
        else:
            logger.warning(f"No workout component found with ID {component_id}")
            return False
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating workout component {component_id}: {e}")
        return False
    finally:
        conn.close()

def delete_workout_component(component_id):
    """
    Delete a workout component.
    Returns True if successful, False otherwise.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if component is used in any workouts
        cursor.execute('''
        SELECT COUNT(*) FROM workout_components_used
        WHERE component_id = ?
        ''', (component_id,))
        
        if cursor.fetchone()[0] > 0:
            logger.warning(f"Cannot delete component ID {component_id} as it is in use")
            return False
        
        # Get the name for logging
        cursor.execute('SELECT name FROM workout_components WHERE id = ?', (component_id,))
        name_row = cursor.fetchone()
        component_name = name_row['name'] if name_row else "Unknown"
        
        # Delete component
        cursor.execute('''
        DELETE FROM workout_components
        WHERE id = ?
        ''', (component_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"Deleted workout component ID {component_id}: {component_name}")
            return True
        else:
            logger.warning(f"No workout component found with ID {component_id}")
            return False
    except Exception as e:
        conn.rollback()
        logger.error(f"Error deleting workout component {component_id}: {e}")
        return False
    finally:
        conn.close()
        
def validate_component_input(name, avg_duration, source, type, exercise_count=None):
    """
    Validates input for a workout component.
    Returns (is_valid, error_message)
    """
    if not name or len(name.strip()) == 0:
        return False, "Component name cannot be empty"
    
    if avg_duration <= 0:
        return False, "Duration must be greater than 0"
    
    if not source:
        return False, "Source cannot be empty"
    
    valid_types = ["Circuit", "Core", "Cardio", "Stretching"]
    if type not in valid_types:
        return False, f"Type must be one of: {', '.join(valid_types)}"
    
    if type == "Circuit" and (exercise_count is None or exercise_count <= 0):
        return False, "Circuit components must have at least 1 exercise"
    
    return True, ""
import logging
from database import get_db_connection

logger = logging.getLogger("exercises")

def get_all_circuit_exercises():
    """
    Retrieves all circuit exercises from the database.
    Returns a list of dictionaries.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT id, name, body_group, trx_flag
        FROM circuit_exercises
        ORDER BY name
        ''')
        
        result = []
        for row in cursor.fetchall():
            result.append({
                'id': row['id'],
                'name': row['name'],
                'body_group': row['body_group'],
                'trx_flag': bool(row['trx_flag'])
            })
        
        return result
    except Exception as e:
        logger.error(f"Error getting circuit exercises: {e}")
        return []
    finally:
        conn.close()

def get_exercise(exercise_id):
    """
    Retrieves a specific exercise by ID.
    Returns the exercise as a dictionary or None if not found.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT id, name, body_group, trx_flag
        FROM circuit_exercises
        WHERE id = ?
        ''', (exercise_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'id': row['id'],
                'name': row['name'],
                'body_group': row['body_group'],
                'trx_flag': bool(row['trx_flag'])
            }
        else:
            return None
    except Exception as e:
        logger.error(f"Error getting exercise {exercise_id}: {e}")
        return None
    finally:
        conn.close()

def add_exercise(name, body_group, trx_flag=False):
    """
    Add a new circuit exercise.
    Returns the ID of the newly created exercise or None if an error occurred.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        INSERT INTO circuit_exercises (name, body_group, trx_flag)
        VALUES (?, ?, ?)
        ''', (name, body_group, trx_flag))
        
        exercise_id = cursor.lastrowid
        conn.commit()
        logger.info(f"Added exercise: {name} (ID: {exercise_id})")
        return exercise_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Error adding exercise {name}: {e}")
        return None
    finally:
        conn.close()

def update_exercise(exercise_id, name, body_group, trx_flag=False):
    """
    Update an existing circuit exercise.
    Returns True if successful, False otherwise.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        UPDATE circuit_exercises
        SET name = ?, body_group = ?, trx_flag = ?
        WHERE id = ?
        ''', (name, body_group, trx_flag, exercise_id))
        
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"Updated exercise ID {exercise_id}: {name}")
            return True
        else:
            logger.warning(f"No exercise found with ID {exercise_id}")
            return False
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating exercise {exercise_id}: {e}")
        return False
    finally:
        conn.close()

def delete_exercise(exercise_id):
    """
    Delete a circuit exercise.
    Returns True if successful, False otherwise.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if exercise is used in any workouts
        cursor.execute('''
        SELECT COUNT(*) FROM circuit_exercises_used
        WHERE exercise_id = ?
        ''', (exercise_id,))
        
        if cursor.fetchone()[0] > 0:
            logger.warning(f"Cannot delete exercise ID {exercise_id} as it is in use")
            return False
        
        # Get the name for logging
        cursor.execute('SELECT name FROM circuit_exercises WHERE id = ?', (exercise_id,))
        name_row = cursor.fetchone()
        exercise_name = name_row['name'] if name_row else "Unknown"
        
        # Delete exercise
        cursor.execute('''
        DELETE FROM circuit_exercises
        WHERE id = ?
        ''', (exercise_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"Deleted exercise ID {exercise_id}: {exercise_name}")
            return True
        else:
            logger.warning(f"No exercise found with ID {exercise_id}")
            return False
    except Exception as e:
        conn.rollback()
        logger.error(f"Error deleting exercise {exercise_id}: {e}")
        return False
    finally:
        conn.close()

def validate_exercise_input(name, body_group, trx_flag=False):
    """
    Validates input for a circuit exercise.
    Returns (is_valid, error_message)
    """
    if not name or len(name.strip()) == 0:
        return False, "Exercise name cannot be empty"
    
    valid_body_groups = ["Lower Body", "Upper Body", "Core", "Full Body", "Back", "Arms"]
    if body_group not in valid_body_groups:
        return False, f"Body group must be one of: {', '.join(valid_body_groups)}"
    
    return True, ""
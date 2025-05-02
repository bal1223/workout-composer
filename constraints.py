import logging
from database import get_db_connection

logger = logging.getLogger("constraints")

def get_component_type_limits():
    """
    Retrieves the component type limits from the database.
    Returns a dictionary of {component_type: count_limit}.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT component_type, count_limit
        FROM constraints
        ''')
        
        result = {}
        for row in cursor.fetchall():
            result[row['component_type']] = row['count_limit']
        
        return result
    except Exception as e:
        logger.error(f"Error getting component type limits: {e}")
        return {}
    finally:
        conn.close()

def get_duration_constraints():
    """
    Retrieves the duration constraints from the database.
    Returns a dictionary with 'min_length' and 'max_length' keys.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT min_length, max_length
        FROM duration_constraints
        LIMIT 1
        ''')
        
        row = cursor.fetchone()
        if row:
            return {
                'min_length': row['min_length'],
                'max_length': row['max_length']
            }
        else:
            # Default values if no constraints are found
            return {
                'min_length': 40,
                'max_length': 50
            }
    except Exception as e:
        logger.error(f"Error getting duration constraints: {e}")
        # Default values if there's an error
        return {
            'min_length': 40,
            'max_length': 50
        }
    finally:
        conn.close()

def update_component_type_limit(component_type, count_limit):
    """
    Update the maximum allowed count for a component type.
    Returns True if successful, False otherwise.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if constraint exists
        cursor.execute('''
        SELECT COUNT(*) FROM constraints
        WHERE component_type = ?
        ''', (component_type,))
        
        if cursor.fetchone()[0] > 0:
            # Update existing constraint
            cursor.execute('''
            UPDATE constraints
            SET count_limit = ?
            WHERE component_type = ?
            ''', (count_limit, component_type))
        else:
            # Insert new constraint
            cursor.execute('''
            INSERT INTO constraints (component_type, count_limit)
            VALUES (?, ?)
            ''', (component_type, count_limit))
        
        conn.commit()
        logger.info(f"Updated constraint for {component_type}: {count_limit}")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating constraint for {component_type}: {e}")
        return False
    finally:
        conn.close()

def update_duration_constraints(min_length, max_length):
    """
    Update the min/max duration constraints.
    Returns True if successful, False otherwise.
    """
    if min_length > max_length:
        logger.error("Min length cannot be greater than max length")
        return False
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if any constraints exist
        cursor.execute('SELECT COUNT(*) FROM duration_constraints')
        
        if cursor.fetchone()[0] > 0:
            # Update existing constraints
            cursor.execute('''
            UPDATE duration_constraints
            SET min_length = ?, max_length = ?
            WHERE id = (SELECT id FROM duration_constraints LIMIT 1)
            ''', (min_length, max_length))
        else:
            # Insert new constraints
            cursor.execute('''
            INSERT INTO duration_constraints (min_length, max_length)
            VALUES (?, ?)
            ''', (min_length, max_length))
        
        conn.commit()
        logger.info(f"Updated duration constraints: min={min_length}, max={max_length}")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating duration constraints: {e}")
        return False
    finally:
        conn.close()

def validate_constraints_input(component_type, count_limit):
    """
    Validates input for component type constraints.
    Returns (is_valid, error_message)
    """
    valid_types = ["Circuit", "Core", "Cardio", "Stretching"]
    if component_type not in valid_types:
        return False, f"Component type must be one of: {', '.join(valid_types)}"
    
    if count_limit < 0:
        return False, "Count limit must be 0 or greater"
    
    return True, ""

def validate_duration_constraints(min_length, max_length):
    """
    Validates input for duration constraints.
    Returns (is_valid, error_message)
    """
    if min_length <= 0:
        return False, "Minimum duration must be greater than 0"
    
    if max_length <= 0:
        return False, "Maximum duration must be greater than 0"
    
    if min_length > max_length:
        return False, "Minimum duration cannot be greater than maximum duration"
    
    if max_length > 120:
        return False, "Maximum duration cannot exceed 120 minutes"
    
    return True, ""
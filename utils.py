import datetime
import logging
import pandas as pd
from database import get_db_connection

logger = logging.getLogger("utils")

def get_dashboard_stats():
    """
    Get statistics for the dashboard
    
    Returns:
        Dictionary with dashboard metrics
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # TODO: Add distribution of workout types and durations
    try:
        # Total workouts
        cursor.execute('SELECT COUNT(*) FROM generated_workouts')
        total_workouts = cursor.fetchone()[0]
        
        # Completion rate
        cursor.execute('SELECT COUNT(*) FROM generated_workouts WHERE completed = 1')
        completed_workouts = cursor.fetchone()[0]
        completion_rate = (completed_workouts / total_workouts * 100) if total_workouts > 0 else 0
        
        # Average rating
        cursor.execute('SELECT AVG(rating) FROM generated_workouts WHERE rating IS NOT NULL')
        avg_rating = cursor.fetchone()[0] or 0
        
        return {
            'total_workouts': total_workouts,
            'completion_rate': round(completion_rate, 1),
            'avg_rating': round(avg_rating, 1)
        }
    
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return {
            'total_workouts': 0,
            'completion_rate': 0,
            'avg_rating': 0
        }
    finally:
        conn.close()

def get_workout_history(start_date=None, end_date=None, status_filter='All'):
    """
    Get workout history with optional filters
    
    Args:
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        status_filter: 'All', 'Completed', or 'Not Completed'
    
    Returns:
        List of workout dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = '''
            SELECT id, date_generated, total_duration, completed, rating
            FROM generated_workouts
            WHERE 1=1
        '''
        params = []
        
        if start_date:
            query += ' AND date_generated >= ?'
            params.append(start_date.strftime('%Y-%m-%d'))
        
        if end_date:
            query += ' AND date_generated <= ?'
            params.append(end_date.strftime('%Y-%m-%d'))
        
        if status_filter == 'Completed':
            query += ' AND completed = 1'
        elif status_filter == 'Not Completed':
            query += ' AND completed = 0'
        
        query += ' ORDER BY date_generated DESC'
        
        cursor.execute(query, params)
        
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
            
            # Format date for display
            date_obj = datetime.datetime.strptime(row['date_generated'], '%Y-%m-%d')
            formatted_date = date_obj.strftime('%B %d, %Y')
            
            # Format rating for display
            rating_display = '★' * (row['rating'] or 0) if row['rating'] else '--'
            
            result.append({
                'id': row['id'],
                'date': formatted_date,
                'components': ', '.join(component_names),
                'duration': f"{row['total_duration']} min",
                'rating': rating_display,
                'status': 'Completed' if row['completed'] else 'Not Completed'
            })
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting workout history: {e}")
        return []
    finally:
        conn.close()

def get_workout_stats(start_date=None, end_date=None):
    """
    Get workout statistics for the stats page
    
    Args:
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
    
    Returns:
        Dictionary with various statistics
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Build base query with date filtering
        date_condition = "WHERE 1=1"
        params = []
        
        if start_date:
            date_condition += " AND date_generated >= ?"
            params.append(start_date.strftime('%Y-%m-%d'))
        
        if end_date:
            date_condition += " AND date_generated <= ?"
            params.append(end_date.strftime('%Y-%m-%d'))
        
        # Basic stats
        cursor.execute(f'''
            SELECT 
                COUNT(*) as total_workouts,
                COUNT(CASE WHEN completed = 1 THEN 1 END) as completed_workouts,
                AVG(total_duration) as avg_duration,
                AVG(CASE WHEN rating IS NOT NULL THEN rating END) as avg_rating
            FROM generated_workouts
            {date_condition}
        ''', params)
        
        row = cursor.fetchone()
        total_workouts = row['total_workouts'] or 0
        completed_workouts = row['completed_workouts'] or 0
        avg_duration = row['avg_duration'] or 0
        avg_rating = row['avg_rating'] or 0
        
        completion_rate = (completed_workouts / total_workouts * 100) if total_workouts > 0 else 0
        
        # Component usage stats
        cursor.execute(f'''
            SELECT wc.type, COUNT(*) as count
            FROM workout_components_used wcu
            JOIN workout_components wc ON wcu.component_id = wc.id
            JOIN generated_workouts gw ON wcu.workout_id = gw.id
            {date_condition}
            GROUP BY wc.type
        ''', params)
        
        component_usage = {row['type']: row['count'] for row in cursor.fetchall()}
        
        # Most used exercises
        cursor.execute(f'''
            SELECT ce.name, COUNT(*) as times_used
            FROM circuit_exercises_used ceu
            JOIN circuit_exercises ce ON ceu.exercise_id = ce.id
            JOIN generated_workouts gw ON ceu.workout_id = gw.id
            {date_condition}
            GROUP BY ce.id, ce.name
            ORDER BY times_used DESC
            LIMIT 10
        ''', params)
        
        exercise_usage = [{'exercise': row['name'], 'times_used': row['times_used']} 
                         for row in cursor.fetchall()]
        
        return {
            'total_workouts': total_workouts,
            'completion_rate': round(completion_rate, 1),
            'avg_duration': round(avg_duration, 1),
            'avg_rating': round(avg_rating, 1),
            'component_usage': component_usage,
            'exercise_usage': exercise_usage
        }
    
    except Exception as e:
        logger.error(f"Error getting workout stats: {e}")
        return {
            'total_workouts': 0,
            'completion_rate': 0,
            'avg_duration': 0,
            'avg_rating': 0,
            'component_usage': {},
            'exercise_usage': []
        }
    finally:
        conn.close()

def format_duration(minutes):
    """
    Format duration from minutes to human-readable string
    
    Args:
        minutes: Duration in minutes
    
    Returns:
        Formatted string (e.g., "45 min", "1 hr 30 min")
    """
    if minutes < 60:
        return f"{minutes} min"
    else:
        hours = minutes // 60
        mins = minutes % 60
        if mins == 0:
            return f"{hours} hr"
        else:
            return f"{hours} hr {mins} min"

def format_date(date):
    """
    Format date to a consistent string format
    
    Args:
        date: datetime object or string
    
    Returns:
        Formatted date string
    """
    if isinstance(date, str):
        try:
            date = datetime.datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return date
    
    return date.strftime('%B %d, %Y')

def get_component_options():
    """
    Get all component names for UI selection
    
    Returns:
        List of component names
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT name FROM workout_components ORDER BY name')
        return [row['name'] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting component options: {e}")
        return []
    finally:
        conn.close()

def validate_database_setup():
    """
    Validates that the database is properly set up with initial data
    
    Returns:
        (is_valid, error_message)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if all tables exist
        required_tables = [
            'workout_components', 'circuit_exercises', 'constraints',
            'duration_constraints', 'generated_workouts', 'workout_components_used',
            'circuit_exercises_used'
        ]
        
        for table in required_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cursor.fetchone():
                return False, f"Table '{table}' is missing"
        
        # Check if we have initial data
        cursor.execute('SELECT COUNT(*) FROM workout_components')
        if cursor.fetchone()[0] == 0:
            return False, "No workout components found in database"
        
        cursor.execute('SELECT COUNT(*) FROM circuit_exercises')
        if cursor.fetchone()[0] == 0:
            return False, "No circuit exercises found in database"
        
        cursor.execute('SELECT COUNT(*) FROM constraints')
        if cursor.fetchone()[0] == 0:
            return False, "No constraints found in database"
        
        cursor.execute('SELECT COUNT(*) FROM duration_constraints')
        if cursor.fetchone()[0] == 0:
            return False, "No duration constraints found in database"
        
        return True, ""
    
    except Exception as e:
        logger.error(f"Error validating database setup: {e}")
        return False, f"Database validation error: {str(e)}"
    finally:
        conn.close()

def export_workout_to_dict(workout_id):
    """
    Export a workout to a dictionary format for PDF generation or other uses
    
    Args:
        workout_id: ID of the workout to export
    
    Returns:
        Dictionary containing all workout information
    """
    from workout_generator import load_workout
    
    workout = load_workout(workout_id)
    if not workout:
        return None
    
    # Format for export
    export_data = {
        'id': workout['id'],
        'date': format_date(workout['date']),
        'total_duration': format_duration(workout['total_duration']),
        'components': []
    }
    
    for component in workout['components']:
        comp_data = {
            'name': component['name'],
            'type': component['type'],
            'duration': format_duration(component['duration']),
            'exercises': []
        }
        
        if component['exercises']:
            for exercise in component['exercises']:
                comp_data['exercises'].append({
                    'name': exercise['name'],
                    'body_group': exercise['body_group']
                })
        
        export_data['components'].append(comp_data)
    
    return export_data
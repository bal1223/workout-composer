import sqlite3
import os
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)
logger = logging.getLogger("database")

DB_FILE = 'workout_composer.db'

def get_db_connection():
    """
    Creates a connection to the SQLite database.
    Returns the connection object.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

def init_db():
    """
    Initializes the database by creating all necessary tables.
    Should be called when the application starts.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Create workout_components table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            avg_duration INTEGER NOT NULL,
            source TEXT NOT NULL,
            type TEXT NOT NULL,
            exercise_count INTEGER
        )
        ''')
        
        # Create circuit_exercises table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS circuit_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            body_group TEXT NOT NULL,
            trx_flag BOOLEAN NOT NULL DEFAULT 0
        )
        ''')
        
        # Create constraints table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS constraints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component_type TEXT NOT NULL,
            count_limit INTEGER NOT NULL
        )
        ''')
        
        # Create duration_constraints table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS duration_constraints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            min_length INTEGER NOT NULL,
            max_length INTEGER NOT NULL
        )
        ''')
        
        # Create generated_workouts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS generated_workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_generated DATE NOT NULL DEFAULT CURRENT_DATE,
            total_duration INTEGER NOT NULL,
            completed BOOLEAN NOT NULL DEFAULT 0,
            rating INTEGER,
            notes TEXT
        )
        ''')
        
        # Create workout_components_used table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_components_used (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER NOT NULL,
            component_id INTEGER NOT NULL,
            position_in_workout INTEGER NOT NULL,
            FOREIGN KEY (workout_id) REFERENCES generated_workouts (id),
            FOREIGN KEY (component_id) REFERENCES workout_components (id)
        )
        ''')
        
        # Create circuit_exercises_used table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS circuit_exercises_used (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER NOT NULL,
            component_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,
            position_in_circuit INTEGER NOT NULL,
            FOREIGN KEY (workout_id) REFERENCES generated_workouts (id),
            FOREIGN KEY (component_id) REFERENCES workout_components (id),
            FOREIGN KEY (exercise_id) REFERENCES circuit_exercises (id)
        )
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully")
        
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database initialization error: {e}")
        raise
    finally:
        conn.close()

def populate_initial_data():
    """
    Populates the database with initial data if tables are empty.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if we need to populate workout_components
        cursor.execute("SELECT COUNT(*) FROM workout_components")
        if cursor.fetchone()[0] == 0:
            # Initial workout components
            initial_components = [
                {"name": "21-Ladder", "avg_duration": 40, "source": "Circuit Exercises", "type": "Circuit", "exercise_count": 5},
                {"name": "15-Ladder", "avg_duration": 20, "source": "Circuit Exercises", "type": "Circuit", "exercise_count": 5},
                {"name": "Peloton Core - 10 min", "avg_duration": 10, "source": "Peloton", "type": "Core", "exercise_count": None},
                {"name": "Peloton Core - 15 min", "avg_duration": 15, "source": "Peloton", "type": "Core", "exercise_count": None},
                {"name": "Peloton Core - 20 min", "avg_duration": 20, "source": "Peloton", "type": "Core", "exercise_count": None},
                {"name": "Bootcamp Circuit", "avg_duration": 30, "source": "Circuit Exercises", "type": "Circuit", "exercise_count": 8},
                {"name": "Peloton Ride - 10 min", "avg_duration": 10, "source": "Peloton", "type": "Cardio", "exercise_count": None},
                {"name": "TRX Circuit", "avg_duration": 20, "source": "Circuit Exercises", "type": "Circuit", "exercise_count": 4},
                {"name": "Peloton Strength - 10 min", "avg_duration": 10, "source": "Peloton", "type": "Circuit", "exercise_count": None},
                {"name": "Peloton Strength - 30 min", "avg_duration": 30, "source": "Peloton", "type": "Circuit", "exercise_count": None},
                {"name": "Peloton Strength - 45 min", "avg_duration": 45, "source": "Peloton", "type": "Circuit", "exercise_count": None},
                {"name": "Peloton Stretching - 10 min", "avg_duration": 10, "source": "Peloton", "type": "Stretching", "exercise_count": None},
                {"name": "55 Finisher", "avg_duration": 5, "source": "NA", "type": "Cardio", "exercise_count": None},
                {"name": "6th Street Hill Run", "avg_duration": 10, "source": "NA", "type": "Cardio", "exercise_count": None}
            ]
            
            for component in initial_components:
                cursor.execute('''
                INSERT INTO workout_components (name, avg_duration, source, type, exercise_count)
                VALUES (?, ?, ?, ?, ?)
                ''', (component["name"], component["avg_duration"], component["source"], 
                      component["type"], component["exercise_count"]))
            
            logger.info(f"Populated {len(initial_components)} initial workout components")
        
        # Check if we need to populate circuit_exercises
        cursor.execute("SELECT COUNT(*) FROM circuit_exercises")
        if cursor.fetchone()[0] == 0:
            # Initial circuit exercises
            initial_exercises = [
                {"name":"Jumping Lunges", "body_group":"Lower Body", "trx_flag":False},
                {"name":"Push Ups - TRX", "body_group":"Upper Body", "trx_flag":True},
                {"name":"Squat + Shoulder Press", "body_group":"Full body", "trx_flag":False},
                {"name":"Sit Ups", "body_group":"Core", "trx_flag":False},
                {"name":"Dumbell Row", "body_group":"Back", "trx_flag":False},
                {"name":"Burpee", "body_group":"Full body", "trx_flag":False},
                {"name":"Sumo Squats", "body_group":"Lower Body", "trx_flag":False},
                {"name":"Good Mornings", "body_group":"Lower Body", "trx_flag":False},
                {"name":"Deadlift", "body_group":"Lower Body", "trx_flag":False},
                {"name":"One-leg Deadlift", "body_group":"Lower Body", "trx_flag":False},
                {"name":"Pistol Squat - TRX", "body_group":"Lower Body", "trx_flag":True},
                {"name":"Reverse Crunches", "body_group":"Core", "trx_flag":False},
                {"name":"Jump Squat", "body_group":"Lower Body", "trx_flag":False},
                {"name":"Plank", "body_group":"Core", "trx_flag":False},
                {"name":"Push Ups + Dumbell Twist", "body_group":"Upper Body", "trx_flag":False},
                {"name":"Bicep Curl", "body_group":"Arms", "trx_flag":False},
                {"name":"Hammer Curl", "body_group":"Arms", "trx_flag":False},
                {"name":"Tricep Extension", "body_group":"Arms", "trx_flag":False},
                {"name":"Shoulder Press - Wide", "body_group":"Upper Body", "trx_flag":False},
                {"name":"Shoulder Press - Narrow", "body_group":"Upper Body", "trx_flag":False},
                {"name":"Arnold Press", "body_group":"Upper Body", "trx_flag":False},
                {"name":"Lunge + Twist", "body_group":"Lower Body", "trx_flag":False},
                {"name":"Scissor Kicks", "body_group":"Core", "trx_flag":False},
                {"name":"Dead Bug", "body_group":"Core", "trx_flag":False},
                {"name":"Superman", "body_group":"Core", "trx_flag":False},
                {"name":"Push Up + Row", "body_group":"Upper Body", "trx_flag":False},
                {"name":"Slow Squat", "body_group":"Lower Body", "trx_flag":False},
                {"name":"Shoulder Raises", "body_group":"Arms", "trx_flag":False},
                {"name":"Russian Twists", "body_group":"Core", "trx_flag":False},
                {"name":"Dumbell Clean", "body_group":"Upper Body", "trx_flag":False},
                {"name":"Rows Combo - TRX", "body_group":"Upper Body", "trx_flag":True},
                {"name":"Around the World - TRX", "body_group":"Upper Body", "trx_flag":True},
                {"name":"One-leg lunge - TRX", "body_group":"Lower Body", "trx_flag":True},
                {"name":"One-arm row - TRX", "body_group":"Upper Body", "trx_flag":True},
                {"name":"Chest press - TRX", "body_group":"Upper Body", "trx_flag":True},
                {"name":"Biceps Curl - TRX", "body_group":"Upper Body", "trx_flag":True},
                {"name":"Tricep Extension - TRX", "body_group":"Upper Body", "trx_flag":True},
                {"name":"Plank+Pike+Leg Spread+Push Up", "body_group":"Full body", "trx_flag":True},
                {"name":"Hamstring Curl - TRX", "body_group":"Lower Body", "trx_flag":True}
            ]
            
            for exercise in initial_exercises:
                cursor.execute('''
                INSERT INTO circuit_exercises (name, body_group, trx_flag)
                VALUES (?, ?, ?)
                ''', (exercise["name"], exercise["body_group"], exercise["trx_flag"]))
            
            logger.info(f"Populated {len(initial_exercises)} initial circuit exercises")
            
        # Check if we need to populate constraints
        cursor.execute("SELECT COUNT(*) FROM constraints")
        if cursor.fetchone()[0] == 0:
            # Initial constraints
            initial_type_limits = [
                {"component_type": "Circuit", "count_limit": 2},
                {"component_type": "Core", "count_limit": 1},
                {"component_type": "Cardio", "count_limit": 1},
                {"component_type": "Stretching", "count_limit": 1}
            ]
            
            for constraint in initial_type_limits:
                cursor.execute('''
                INSERT INTO constraints (component_type, count_limit)
                VALUES (?, ?)
                ''', (constraint["component_type"], constraint["count_limit"]))
            
            logger.info(f"Populated {len(initial_type_limits)} initial constraints")
            
        # Check if we need to populate duration_constraints
        cursor.execute("SELECT COUNT(*) FROM duration_constraints")
        if cursor.fetchone()[0] == 0:
            # Initial duration constraints
            cursor.execute('''
            INSERT INTO duration_constraints (min_length, max_length)
            VALUES (?, ?)
            ''', (40, 50))
            
            logger.info("Populated initial duration constraints")
        
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Error populating initial data: {e}")
        raise
    finally:
        conn.close()

def safe_db_operation(operation_func, *args, **kwargs):
    """
    Wrapper for safely executing database operations
    """
    try:
        return operation_func(*args, **kwargs)
    except sqlite3.Error as e:
        logger.error(f"Database error in {operation_func.__name__}: {str(e)}")
        return None
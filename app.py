import uuid
from datetime import datetime
import json
import pandas as pd
import sqlite3
from collections import Counter
from datetime import datetime, timedelta
import os
from flask import g 
from flask import send_file
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from werkzeug.utils import secure_filename
import io
import base64


from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_file

# --- Word Cloud Imports ---
from wordcloud import WordCloud
import matplotlib.pyplot as plt
# --- End Word Cloud Imports ---

# --- Supabase Client Imports (Needed for Supabase functionality) ---
from supabase import create_client, Client

# --- HARDCODED VALUES (NOT RECOMMENDED FOR PRODUCTION - REPLACE WITH YOUR ACTUAL KEYS) ---
# You MUST replace these with your actual keys for the app to work.
# IMPORTANT: Change 'your_hardcoded_flask_secret_key_here_for_testing' to a strong, unique key.
FLASK_SECRET_KEY_HARDCODED = '3100ecda3dfe52805aaf2d8ad2474cd2'
SUPABASE_URL_HARDCODED = "https://qbpbonlmftcfjkmqzhhf.supabase.co"
SUPABASE_KEY_HARDCODED = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFicGJvbmxtZnRjZmprbXF6aGhmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTI0MzUxODcsImV4cCI6MjA2ODkxMTE4N30.aWDZhhwQ56uDb8SnMr_t4sTb0yPT4hHpGwBsmsETFhg"
# --- END HARDCODED VALUES ---


app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY_HARDCODED # Using the hardcoded key


# --- SUPABASE CLIENT INITIALIZATION (using hardcoded values) ---
try:
    # Use the hardcoded global variables for Supabase client creation
    supabase: Client = create_client(SUPABASE_URL_HARDCODED, SUPABASE_KEY_HARDCODED)
    print("Supabase client initialized successfully using hardcoded credentials.")
except Exception as e:
    print(f"ERROR: Failed to initialize Supabase client: {e}")
    supabase = None


# --- Configuration for File Uploads and Database ---
UPLOAD_FOLDER = 'temp_uploads' # Temporary folder for uploaded images before they go to cloud storage
ALLOWED_CSV_XLSX_EXTENSIONS = {'csv', 'xlsx'} # Allowed extensions for manual CSV/XLSX uploads
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'} # Allowed extensions for direct image uploads in the survey form
DATABASE = 'survey_data.db' # Define DATABASE globally here!

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB max file size for all uploads

# Ensure UPLOAD_FOLDER exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# --- SQLite Database Functions ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS survey_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                age INTEGER,
                gender TEXT,
                department TEXT,
                likes TEXT,
                rating INTEGER,
                suggestions TEXT,
                recommendation TEXT,
                image_url TEXT,              -- Column for image URL (from Supabase Storage)
                image_analytics_results TEXT, -- Column for analytics results (e.g., JSON string)
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

init_db() # Initialize SQLite database on app startup

def generate_word_cloud(text_list, filename="wordcloud.png"):
    clean_text_list = [str(item) for item in text_list if item is not None]

    if not clean_text_list:
        print("No valid text data provided for word cloud generation.")
        # You should have a default "no data" image or handle this gracefully
        # For demonstration, we'll return None and handle it in the route
        return None

    combined_text = " ".join(clean_text_list)
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(combined_text)

    output_dir = os.path.join(app.static_folder, 'generated_images') # Use app.static_folder
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    wordcloud.to_file(filepath)
    return filepath

# --- FLASK ROUTES ---

@app.route('/')
def index():
    """Renders the homepage."""
    return render_template('index.html')

@app.route('/take_survey')
def take_survey():
    """Renders the survey form page."""
    return render_template('take_survey.html')

@app.route('/submit_survey', methods=['POST'])
def submit_survey():
    """Handles the submission of the survey form."""
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        email = request.form.get('email')
        age = request.form.get('age')
        gender = request.form.get('gender')
        department = request.form.get('department')
        most_liked = request.form.get('most_liked')
        rating = request.form.get('rating')
        suggestions = request.form.get('suggestions')
        recommend = request.form.get('recommend')

        if not all([first_name, email, age, gender, department, most_liked, rating, recommend]):
            flash('Please fill out all required fields.', 'danger')
            return redirect(url_for('take_survey'))

        try:
            age = int(age) if age else None
            rating = int(rating) if rating else None
        except ValueError:
            flash('Invalid age or rating provided. Please enter numbers.', 'danger')
            return redirect(url_for('take_survey'))

        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO survey_responses (name, email, age, gender, department, likes, rating, suggestions, recommendation) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (first_name, email, age, gender, department, most_liked, rating, suggestions, recommend)
            )
            conn.commit()
            flash('Survey response submitted successfully!', 'success')
        except sqlite3.IntegrityError:
            flash('An entry with this email already exists. Please use a different email or update.', 'danger')
            conn.rollback()
        except Exception as e:
            flash(f'Database error occurred during submission: {e}', 'danger')
            conn.rollback()
        finally:
            conn.close()

        # --- IMPORTANT CHANGE HERE: Redirect to thank_you_page ---
        return redirect(url_for('thank_you_page'))

    return redirect(url_for('take_survey'))

@app.route('/thank_you')
def thank_you_page():
    """Renders the styled thank you page after survey submission."""
    return render_template('thank_you.html') # This is the HTML file that will contain the "Back to Home Page" link

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serves uploaded files (e.g., images) from the UPLOAD_FOLDER."""
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))


@app.route('/results')
def view_results():
    # Get filter parameters from the URL query string
    selected_gender = request.args.get('gender_filter')
    selected_department = request.args.get('department_filter')
    min_age = request.args.get('min_age', type=int)
    max_age = request.args.get('max_age', type=int)

    combined_responses = [] # This will hold all responses after filtering from both sources

    # --- Fetch from SQLite and apply filters ---
    conn = get_db_connection()
    sqlite_query = 'SELECT * FROM survey_responses WHERE 1=1' # Start with a true condition
    sqlite_params = []

    if selected_gender:
        sqlite_query += ' AND gender = ?'
        sqlite_params.append(selected_gender)
    if selected_department:
        sqlite_query += ' AND department = ?'
        sqlite_params.append(selected_department)
    if min_age is not None:
        sqlite_query += ' AND age >= ?'
        sqlite_params.append(min_age)
    if max_age is not None:
        sqlite_query += ' AND age <= ?'
        sqlite_params.append(max_age)

    try:
        sqlite_responses = conn.execute(sqlite_query, sqlite_params).fetchall()
        for row in sqlite_responses:
            # Convert SQLite Row objects to dictionaries
            response_dict = dict(row)
            # Ensure timestamp is string for JSON
            if 'timestamp' in response_dict and isinstance(response_dict['timestamp'], datetime):
                 response_dict['timestamp'] = response_dict['timestamp'].isoformat()
            combined_responses.append(response_dict)
    except Exception as e:
        print(f"Error fetching data from SQLite: {e}")
    finally:
        conn.close()

    # --- Fetch from Supabase and apply filters ---
    if supabase:
        try:
            supabase_query = supabase.table('responses').select('*')

            if selected_gender:
                supabase_query = supabase_query.eq('gender', selected_gender)
            if selected_department:
                supabase_query = supabase_query.eq('department', selected_department)
            if min_age is not None:
                supabase_query = supabase_query.gte('age', min_age)
            if max_age is not None:
                supabase_query = supabase_query.lte('age', max_age)

            response_data, count = supabase_query.execute()
            if response_data and response_data[1]: # Supabase client usually returns (data, count)
                # Supabase returns dictionaries, so no Row-to-dict conversion needed
                # Just ensure timestamp is handled if it's not already string (Supabase usually is)
                for res in response_data[1]:
                    if 'timestamp' in res and isinstance(res['timestamp'], datetime):
                        res['timestamp'] = res['timestamp'].isoformat()
                    combined_responses.append(res)

        except Exception as e:
            print(f"Error fetching data from Supabase: {e}")
    else:
        print("Supabase client not initialized, skipping Supabase data fetch.")


    # --- Aggregation and KPI calculations (based on combined and filtered responses) ---
    all_likes_suggestions = []
    all_ages = []
    all_genders = []
    all_departments = []
    all_ratings = []
    all_recommendations = []

    department_counts = Counter()

    for response_dict in combined_responses:
        # Data aggregation for KPIs and initial charts
        if response_dict.get('likes'):
            all_likes_suggestions.append(response_dict['likes'])
        if response_dict.get('suggestions'):
            all_likes_suggestions.append(response_dict['suggestions'])
        if response_dict.get('age') is not None:
            all_ages.append(response_dict['age'])
        if response_dict.get('gender'):
            all_genders.append(response_dict['gender'])
        if response_dict.get('department'):
            all_departments.append(response_dict['department'])
            department_counts[response_dict['department']] += 1
        if response_dict.get('rating') is not None:
            all_ratings.append(response_dict['rating'])
        if response_dict.get('recommendation'):
            all_recommendations.append(response_dict['recommendation'])

    # Calculate initial KPIs based on aggregated data
    total_responses = len(combined_responses)
    most_common_department = department_counts.most_common(1)[0][0] if department_counts else 'N/A'

    # Prepare data for initial chart rendering
    gender_data = [{'label': k, 'value': v} for k, v in Counter(all_genders).items()]
    department_data = [{'label': k, 'value': v} for k, v in Counter(all_departments).items()]
    rating_data = [{'label': str(k), 'value': v} for k, v in Counter(all_ratings).items()]
    
    # Ensure recommendation order: Yes, No, Maybe (explicitly count them)
    positive_recommendations_count = Counter(all_recommendations).get('yes', 0)
    negative_recommendations_count = Counter(all_recommendations).get('no', 0)
    maybe_recommendations_count = Counter(all_recommendations).get('maybe', 0)
    recommendation_data = [
        {'label': 'Yes', 'value': positive_recommendations_count},
        {'label': 'No', 'value': negative_recommendations_count},
        {'label': 'Maybe', 'value': maybe_recommendations_count}
    ]

    # Get unique values for dropdowns
    unique_genders = sorted(list(set(all_genders)))
    unique_departments = sorted(list(set(all_departments)))


    return render_template('view_results.html',
                           responses=combined_responses, # Pass the filtered list of dictionaries
                           total_responses=total_responses,
                           positive_recommendations=positive_recommendations_count,
                           negative_recommendations=negative_recommendations_count,
                           maybe_recommendations=maybe_recommendations_count,
                           most_common_department=most_common_department,
                           gender_data=gender_data,
                           department_data=department_data,
                           rating_data=rating_data,
                           recommendation_data=recommendation_data,
                           ages=all_ages, # This is the list of ages from filtered data
                           
                           # Pass filter options back to the template to pre-select dropdowns
                           selected_gender=selected_gender,
                           selected_department=selected_department,
                           min_age=min_age,
                           max_age=max_age,
                           unique_genders=unique_genders,
                           unique_departments=unique_departments
                          )
    
@app.route('/live_analytics')
def live_analytics():
    # You might pass initial data or just render the template
    return render_template('live_analytics.html')

# --- NEW: API Endpoint for Live Data ---
@app.route('/api/live_data')
def get_live_data():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Total Responses
        cur.execute("SELECT COUNT(*) FROM survey_responses")
        total_responses = cur.fetchone()[0]

        # 2. Recommendation Breakdown
        cur.execute("SELECT recommendation, COUNT(*) FROM survey_responses GROUP BY recommendation")
        recommendation_breakdown_raw = cur.fetchall()
        recommendation_breakdown = [{'label': item[0] if item[0] else 'N/A', 'value': item[1]} for item in recommendation_breakdown_raw]

        # 3. Gender Distribution
        cur.execute("SELECT gender, COUNT(*) FROM survey_responses GROUP BY gender")
        gender_distribution_raw = cur.fetchall()
        gender_distribution = [{'label': item[0] if item[0] else 'N/A', 'value': item[1]} for item in gender_distribution_raw]

        # 4. Department Distribution
        cur.execute("SELECT department, COUNT(*) FROM survey_responses GROUP BY department")
        department_distribution_raw = cur.fetchall()
        department_distribution = [{'label': item[0] if item[0] else 'N/A', 'value': item[1]} for item in department_distribution_raw]

        # 5. Rating Distribution
        cur.execute("SELECT rating, COUNT(*) FROM survey_responses GROUP BY rating ORDER BY rating")
        rating_distribution_raw = cur.fetchall()
        rating_distribution = [{'label': str(item[0]) if item[0] is not None else 'N/A', 'value': item[1]} for item in rating_distribution_raw]

        # 6. Age Distribution
        cur.execute("""
            SELECT
                CASE
                    WHEN age IS NULL THEN 'N/A'
                    WHEN age < 18 THEN '<18'
                    WHEN age BETWEEN 18 AND 24 THEN '18-24'
                    WHEN age BETWEEN 25 AND 34 THEN '25-34'
                    WHEN age BETWEEN 35 AND 44 THEN '35-44'
                    WHEN age BETWEEN 45 AND 54 THEN '45-54'
                    ELSE '55+'
                END as age_group,
                COUNT(*)
            FROM survey_responses
            GROUP BY age_group
            ORDER BY
                CASE
                    WHEN age_group = '<18' THEN 1
                    WHEN age_group = '18-24' THEN 2
                    WHEN age_group = '25-34' THEN 3
                    WHEN age_group = '35-44' THEN 4
                    WHEN age_group = '45-54' THEN 5
                    WHEN age_group = '55+' THEN 6
                    ELSE 7 -- for 'N/A'
                END;
        """)
        age_distribution_raw = cur.fetchall()
        age_distribution = [{'label': item[0], 'value': item[1]} for item in age_distribution_raw]


        # --- TREND DATA FOR KPIs (Corrected for SQLite syntax and 'timestamp' column) ---

        # SQLite stores DATETIME as TEXT, so comparisons need to be string-based.
        # Ensure your 'timestamp' column is indeed DATETIME DEFAULT CURRENT_TIMESTAMP.

        end_date = datetime.now()
        # For daily trends, it's safer to use date objects, then convert to string for query.
        # Start of today (midnight)
        current_day_start = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        # End of today (midnight of next day)
        current_day_end = current_day_start + timedelta(days=1)


        # 7. Total Responses Trend (e.g., daily count for last 7 days)
        # Use a loop to get data for each of the last 7 days
        total_responses_trend_data = []
        for i in range(7):
            date_to_check = end_date - timedelta(days=6-i) # Calculates dates for current day, then yesterday, etc.
            day_start_str = date_to_check.strftime('%Y-%m-%d 00:00:00')
            day_end_str = (date_to_check + timedelta(days=1)).strftime('%Y-%m-%d 00:00:00')

            cur.execute(
                "SELECT COUNT(*) FROM survey_responses WHERE timestamp >= ? AND timestamp < ?",
                (day_start_str, day_end_str)
            )
            count = cur.fetchone()[0]
            total_responses_trend_data.append({'label': date_to_check.strftime('%m-%d'), 'value': count})

        # Get current day's total for trend comparison
        cur.execute(
            "SELECT COUNT(*) FROM survey_responses WHERE timestamp >= ? AND timestamp < ?",
            (current_day_start.strftime('%Y-%m-%d %H:%M:%S'), current_day_end.strftime('%Y-%m-%d %H:%M:%S'))
        )
        current_day_responses = cur.fetchone()[0]

        # Get previous day's total for trend comparison
        previous_day_start = current_day_start - timedelta(days=1)
        previous_day_end = current_day_start
        cur.execute(
            "SELECT COUNT(*) FROM survey_responses WHERE timestamp >= ? AND timestamp < ?",
            (previous_day_start.strftime('%Y-%m-%d %H:%M:%S'), previous_day_end.strftime('%Y-%m-%d %H:%M:%S'))
        )
        previous_day_responses = cur.fetchone()[0]

        total_responses_trend_status = 'neutral'
        if current_day_responses > previous_day_responses:
            total_responses_trend_status = 'positive'
        elif current_day_responses < previous_day_responses:
            total_responses_trend_status = 'negative'


        # 8. Average Rating Trend (e.g., daily average for last 7 days)
        avg_rating_trend_data = []
        for i in range(7):
            date_to_check = end_date - timedelta(days=6-i)
            day_start_str = date_to_check.strftime('%Y-%m-%d 00:00:00')
            day_end_str = (date_to_check + timedelta(days=1)).strftime('%Y-%m-%d 00:00:00')

            cur.execute(
                "SELECT AVG(rating) FROM survey_responses WHERE timestamp >= ? AND timestamp < ? AND rating IS NOT NULL",
                (day_start_str, day_end_str)
            )
            avg = cur.fetchone()[0]
            avg_rating_trend_data.append({'label': date_to_check.strftime('%m-%d'), 'value': round(float(avg), 2) if avg else 0})

        # Get current and previous day's average for trend comparison
        cur.execute(
            "SELECT AVG(rating) FROM survey_responses WHERE timestamp >= ? AND timestamp < ? AND rating IS NOT NULL",
            (current_day_start.strftime('%Y-%m-%d %H:%M:%S'), current_day_end.strftime('%Y-%m-%d %H:%M:%S'))
        )
        current_day_avg_rating = cur.fetchone()[0]
        current_day_avg_rating = round(float(current_day_avg_rating), 2) if current_day_avg_rating else 0

        cur.execute(
            "SELECT AVG(rating) FROM survey_responses WHERE timestamp >= ? AND timestamp < ? AND rating IS NOT NULL",
            (previous_day_start.strftime('%Y-%m-%d %H:%M:%S'), previous_day_end.strftime('%Y-%m-%d %H:%M:%S'))
        )
        previous_day_avg_rating = cur.fetchone()[0]
        previous_day_avg_rating = round(float(previous_day_avg_rating), 2) if previous_day_avg_rating else 0

        avg_rating_trend_status = 'neutral'
        if current_day_avg_rating > previous_day_avg_rating:
            avg_rating_trend_status = 'positive'
        elif current_day_avg_rating < previous_day_avg_rating:
            avg_rating_trend_status = 'negative'


        # You'll need to decide how you define "positive" and "negative" for recommendations.
        # For simplicity, let's compare current positive vs. previous positive counts.
        cur.execute(
            "SELECT COUNT(*) FROM survey_responses WHERE recommendation = 'yes' AND timestamp >= ? AND timestamp < ?",
            (current_day_start.strftime('%Y-%m-%d %H:%M:%S'), current_day_end.strftime('%Y-%m-%d %H:%M:%S'))
        )
        current_day_positive_recommendations = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM survey_responses WHERE recommendation = 'yes' AND timestamp >= ? AND timestamp < ?",
            (previous_day_start.strftime('%Y-%m-%d %H:%M:%S'), previous_day_end.strftime('%Y-%m-%d %H:%M:%S'))
        )
        previous_day_positive_recommendations = cur.fetchone()[0]

        positive_recommendations_trend_status = 'neutral'
        if current_day_positive_recommendations > previous_day_positive_recommendations:
            positive_recommendations_trend_status = 'positive'
        elif current_day_positive_recommendations < previous_day_positive_recommendations:
            positive_recommendations_trend_status = 'negative'


        cur.close()

        return jsonify({
            "totalResponses": total_responses,
            "recommendationBreakdown": recommendation_breakdown,
            "genderDistribution": gender_distribution,
            "departmentDistribution": department_distribution,
            "ratingDistribution": rating_distribution,
            "ageDistribution": age_distribution,
            # KPI Trend Data
            "totalResponsesTrend": {
                "data": total_responses_trend_data,
                "status": total_responses_trend_status
            },
            "avgRatingTrend": {
                "data": avg_rating_trend_data,
                "status": avg_rating_trend_status
            },
            "positiveRecommendationsTrendStatus": positive_recommendations_trend_status
        })

    except Exception as e:
        print(f"Error fetching live data: {e}")
        return jsonify({"message": "Error fetching live data", "error": str(e)}), 500
    finally:
        if conn:
            conn.close()
            
            
@app.route('/wordcloud_image')
def wordcloud_image():
    try:
        # Placeholder for your database interaction.
        # Replace this with your actual database query logic to fetch suggestions and likes.
        # Example:
        # from your_database_module import execute_query
        # results = execute_query('SELECT suggestions, likes FROM survey_responses')

        # For demonstration, let's use dummy data or assume 'execute' works
        # If 'execute' is your custom function, make sure it's available here.
        # Replace 'execute' with your actual database query mechanism
        # Assuming `execute` is defined elsewhere and works
        # You mentioned `conn = execute('SELECT ...').fetchall()` earlier.
        # Make sure `execute` is available in this scope.
        # For a simple example, let's assume `app.db_conn` exists or you have a global `execute`
        
        # Mock database fetching for demonstration. Replace with your actual database logic.
        # You'll need to adapt this based on how your 'execute' function is set up.
        # From your previous code, it looked like this:
        # conn = execute('SELECT suggestions, likes FROM survey_responses').fetchall()
        # results = conn # Assuming conn is the fetched results
        # conn.close() # if conn is a database connection

        # *** IMPORTANT: Replace the following with your actual database call ***
        # Example using a mock:
        dummy_responses = [
            {'suggestions': 'Great experience', 'likes': 'Friendly staff'},
            {'suggestions': 'Improve UI', 'likes': 'Quick service'},
            {'suggestions': 'Good insights', 'likes': 'Easy to use'},
            {'suggestions': None, 'likes': 'Very helpful'} # Example with missing data
        ]
        results = dummy_responses # Replace with your `results` from actual DB query

        all_text = []
        for res in results:
            if res and 'suggestions' in res and res['suggestions']:
                all_text.append(res['suggestions'])
            if res and 'likes' in res and res['likes']:
                all_text.append(res['likes'])

        wordcloud_path = generate_word_cloud(all_text, "live_wordcloud.png")

        if wordcloud_path and os.path.exists(wordcloud_path):
            return send_file(wordcloud_path, mimetype='image/png')
        else:
            # If no word cloud could be generated (e.g., no text data), return a placeholder or error
            # You might want to serve a default "no word cloud" image from your static folder
            return "Error: Word cloud image could not be generated or found.", 500

    except Exception as e:
        print(f"Error generating or serving word cloud: {e}")
        return "Error generating word cloud.", 500

# Your other routes like /upload_manual etc.

# --- Word Cloud route (from your old app.py if needed elsewhere, it was removed from view_results) ---
# If you want to serve the word cloud image on live_analytics page
# you might reuse or adapt this route to generate it on demand.
# For example, by calling generate_word_cloud with all data for wordcloud_image()

@app.route('/upload_manual', methods=['GET', 'POST'])
def upload_manual():
    """Handles manual CSV/XLSX file uploads for survey data."""
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'error') # Added 'error' category for flashing
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                if filename.endswith('.csv'):
                    df = pd.read_csv(filepath)
                elif filename.endswith('.xlsx'):
                    df = pd.read_excel(filepath)
                else:
                    flash('Unsupported file type. Please upload a CSV or XLSX file.', 'error')
                    os.remove(filepath)
                    return redirect(request.url)

                # --- Your Database Insertion Logic Here ---
                # Example:
                # for index, row in df.iterrows():
                #     # Insert row data into your database
                #     pass
                # --- End Database Insertion Logic ---

                os.remove(filepath) # Clean up the uploaded file
                flash('File successfully uploaded and processed!', 'success') # Added 'success' category
                return redirect(url_for('home')) # Redirect to the home page

            except Exception as e:
                flash(f'An error occurred during file processing: {e}', 'error')
                if os.path.exists(filepath):
                    os.remove(filepath)
                return redirect(request.url)
        else:
            flash('Allowed file types are CSV and XLSX', 'error')
            return redirect(request.url)

    # For GET request, render the upload form
    return render_template('upload_manual.html')


if __name__ == "__main__":
    app.run(debug=True)
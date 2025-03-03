from flask import Flask, render_template, jsonify, request
import gitlab
import datetime
from collections import defaultdict

app = Flask(__name__)

def fetch_pipeline_data(project_id=None, access_token=None, days=7, max_pages=100):
    """Fetch pipeline data with configurable parameters"""
    GITLAB_URL = "https://gitlab.com"
    PROJECT_ID = project_id
    ACCESS_TOKEN = access_token

    gl = gitlab.Gitlab(GITLAB_URL, private_token=ACCESS_TOKEN)
    project = gl.projects.get(PROJECT_ID)

    # Get data for specified days
    today = datetime.datetime.now(datetime.timezone.utc)
    start_date = today - datetime.timedelta(days=days)
    updated_after = start_date.isoformat()

    print(f"Fetching pipelines updated after {updated_after}")

    pipelines = project.pipelines.list(
        updated_after=updated_after,
        as_list=False,
        per_page=100
    )

    # Collect all pipelines with pagination handling (built into python-gitlab)
    all_pipelines = []
    page_count = 0

    for pipeline in pipelines:
        page_count = (page_count + 1) // 100 + 1  # Increment page counter
        if page_count > max_pages:
            print(f"Warning: Reached maximum page limit of {max_pages}")
            break
        all_pipelines.append(pipeline)
        print(f"Fetched pipeline {pipeline.id}")

    print(f"Total pipelines fetched: {len(all_pipelines)}")

    # Step 2: Get jobs for each pipeline and compute execution times
    job_times = defaultdict(list)

    for pipeline in all_pipelines:
        print(f"Fetching jobs for pipeline {pipeline.id}")
        jobs = pipeline.jobs.list(all=True)  # all=True gets all jobs regardless of status
        print(f"Fetched {len(jobs)} jobs")

        for job in jobs:
            job_name = job.name
            duration = job.duration  # None if job hasn't finished
            print(f"Job: {job_name}, Duration: {duration}")
            if duration:
                job_times[job_name].append(duration)

    # Step 3: Calculate average execution time
    job_avg_times = {job: sum(times) / len(times) for job, times in job_times.items()}

    # Print results
    for job, avg_time in job_avg_times.items():
        print(f"Job: {job}, Average Execution Time: {avg_time:.2f} seconds")

    return job_avg_times, job_times

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/job-stats')
def job_stats():
    # Get parameters from request
    project_id = request.args.get('project_id')
    access_token = request.args.get('access_token')
    days = int(request.args.get('days', 7))
    max_pages = int(request.args.get('max_pages', 100))

    job_avg_times, job_times = fetch_pipeline_data(
        project_id=project_id,
        access_token=access_token,
        days=days,
        max_pages=max_pages
    )

    # Prepare data for charts
    data = {
        'averages': {
            'labels': list(job_avg_times.keys()),
            'values': [float(f"{t:.2f}") for t in job_avg_times.values()]
        },
        'raw_data': {
            name: times for name, times in job_times.items()
        }
    }
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
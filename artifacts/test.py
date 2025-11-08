import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "project"))
from database_helpers import *

conn = setup_db()


add_job(conn, "test job 1", "test description")
add_job(conn, "test job 2", "test description")

add_skill_to_job(conn, "test skill 1", job_id=1)
add_skill_to_job(conn, "test skill 1", job_id=2)
add_skill_to_job(conn, "test skill 2", job_id=1)
add_skill_to_job(conn, "test skill 3", job_id=1)

add_skill_to_job(conn, "test skill 4", job_id=1)
add_skill_to_job(conn, "test skill 5", job_id=2)
add_skill_to_job(conn, "test skill 6", job_id=1)

add_skill_to_job(conn, "test skill 7", job_id=1)
add_skill_to_job(conn, "test skill 8", job_id=2)
add_skill_to_job(conn, "test skill 9", job_id=1)

print("all jobs = ", "\n".join([str(job) for job in get_jobs(conn)]), "\n")
print("skills for job 1 = ", "\n".join([str(skill) for skill in get_skills_for_job(conn, 1)]), "\n")
print("jobs for skill 1 = ", "\n".join([str(job) for job in get_job_for_skill(conn, "test skill 1")]), "\n")

close_db(conn)
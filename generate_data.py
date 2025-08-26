from faker import Faker
import random
from datetime import timedelta

fake = Faker()


def esc(s):
    return str(s).replace("'", "''")


def generate_departments(num_departments):
    departments = []
    for _ in range(num_departments):
        departments.append(fake.unique.job() + ' Department')
    return departments


def generate_employees(num_employees, department_ids):
    employees = []
    for i in range(num_employees):
        first_name = fake.first_name()
        last_name = fake.last_name()
        # Make email unique by appending an index
        email = f"{first_name.lower()}.{last_name.lower()}{i}@{fake.free_email_domain()}"
        phone_number = fake.phone_number()
        hire_date = fake.date_between(start_date='-5y', end_date='today')
        job_id = fake.job()
        salary = round(random.uniform(30000, 120000), 2)
        dept_id = random.choice(department_ids) if department_ids else 'NULL'
        employees.append((first_name, last_name, email, phone_number, hire_date, job_id, salary, dept_id))
    return employees


def generate_projects(num_projects):
    projects = []
    for _ in range(num_projects):
        project_name = fake.catch_phrase()
        start_date = fake.date_between(start_date='-2y', end_date='today')
        if random.random() > 0.2:
            end_date = start_date + timedelta(days=random.randint(30, 365))
        else:
            end_date = None
        projects.append((project_name, start_date, end_date))
    return projects


def generate_assignments(num_assignments, employee_ids, project_ids):
    assignments = []
    for _ in range(num_assignments):
        emp_id = random.choice(employee_ids)
        project_id = random.choice(project_ids)
        assignment_date = fake.date_between(start_date='-1y', end_date='today')
        assignments.append((emp_id, project_id, assignment_date))
    return assignments


num_departments = 10
num_employees = 150
num_projects = 30
num_assignments = 220

# Generate data
departments_data = generate_departments(num_departments)

# Write department data to SQL
with open('insert_departments.sql', 'w') as f:
    for dept_name in departments_data:
        line = "INSERT INTO departments (dept_name) VALUES ('{}');\n".format(esc(dept_name))
        f.write(line)

# Department IDs will be 1..num_departments after insertion
department_ids = list(range(1, num_departments + 1))

employees_data = generate_employees(num_employees, department_ids)

# Write employee data to SQL
with open('insert_employees.sql', 'w') as f:
    for emp in employees_data:
        first_name, last_name, email, phone, hire_date, job_id, salary, dept_id = emp
        line = (
            "INSERT INTO employees (first_name, last_name, email, phone_number, hire_date, job_id, salary, dept_id) "
            "VALUES ('{}', '{}', '{}', '{}', '{}', '{}', {}, {});\n".format(
                esc(first_name), esc(last_name), esc(email), esc(phone), hire_date, esc(job_id), salary, dept_id
            )
        )
        f.write(line)

# Employee IDs will be 1..num_employees after insertion
employee_ids = list(range(1, num_employees + 1))

projects_data = generate_projects(num_projects)

# Write project data to SQL
with open('insert_projects.sql', 'w') as f:
    for proj in projects_data:
        project_name, start_date, end_date = proj
        end_date_str = "'{}'".format(end_date) if end_date is not None else 'NULL'
        line = (
            "INSERT INTO projects (project_name, start_date, end_date) VALUES ('{}', '{}', {});\n".format(
                esc(project_name), start_date, end_date_str
            )
        )
        f.write(line)

# Project IDs will be 1..num_projects after insertion
project_ids = list(range(1, num_projects + 1))

assignments_data = generate_assignments(num_assignments, employee_ids, project_ids)

# Write assignment data to SQL
with open('insert_assignments.sql', 'w') as f:
    for assign in assignments_data:
        emp_id, project_id, assignment_date = assign
        line = "INSERT INTO assignments (emp_id, project_id, assignment_date) VALUES ({}, {}, '{}');\n".format(
            emp_id, project_id, assignment_date
        )
        f.write(line)



import re

def extract_job_info(job_desc_path):
	with open(job_desc_path, 'r') as f:
		text = f.read()

	# Extract job title (first line)
	job_title = text.splitlines()[0].strip()

	# Extract company (second line)
	company = text.splitlines()[1].strip()

	# Experience level (look for 'Experience' section)
	exp_match = re.search(r'Experience\n([A-Za-z]+)', text)
	experience = exp_match.group(1) if exp_match else ""

	# Technical skills (look for technologies listed)
	tech_skills = []
	tech_section = re.search(r'traditional technologies such as: ([^\n]*)', text)
	if tech_section:
		tech_skills = [skill.strip() for skill in tech_section.group(1).split(',')]
	else:
		# Fallback: look for lines with 'skills' or similar
		tech_skills = []

	# Soft skills (look for lines with 'mentor', 'teamwork', 'innovation', etc.)
	soft_skills = []
	soft_keywords = ['mentor', 'guide', 'teamwork', 'innovation', 'inclusion', 'diversity', 'self-organization', 'communities']
	for line in text.splitlines():
		for word in soft_keywords:
			if word in line.lower():
				soft_skills.append(line.strip())
				break

	return {
		'Job title': job_title,
		'Company': company,
		'Experience level': experience,
		'Technical skills': ', '.join(tech_skills),
		'Soft skills': '; '.join(soft_skills)
	}

def write_template(info, output_path):
	with open(output_path, 'w') as f:
		f.write(f"Job title\n{info['Job title']}\n")
		f.write(f"Company\n{info['Company']}\n")
		f.write(f"Experenice level\n{info['Experience level']}\n")
		f.write(f"Techinal skills\n{info['Technical skills']}\n")
		f.write(f"Soft skills\n{info['Soft skills']}\n")

if __name__ == "__main__":
	job_desc_path = "Job_desc"
	output_path = "Generated_Template.txt"
	info = extract_job_info(job_desc_path)
	write_template(info, output_path)

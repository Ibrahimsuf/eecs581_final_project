import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class JobInfo:
	job_title: str = ''
	company: str = ''
	experience_level: str = ''
	technical_skills: List[str] = field(default_factory=list)
	soft_skills: List[str] = field(default_factory=list)


class JobDescriptionParser:
	"""Parse a free-form job description file and produce a template file.

	This class wraps the previous procedural functions into a single reusable
	parser with a small public surface:

	- extract_job_info() -> JobInfo
	- write_template(info: JobInfo)
	- process() -> JobInfo (parse + write)
	"""

	def __init__(self, job_desc_path: str, output_path: str = "Generated_Template.txt"):
		self.job_desc_path = job_desc_path
		self.output_path = output_path

	def extract_job_info(self) -> JobInfo:
		# Read file and delegate to text-based parser
		with open(self.job_desc_path, 'r') as f:
			text = f.read()
		return self.extract_job_info_from_text(text)

	def extract_job_info_from_text(self, text: str) -> JobInfo:
		"""Parse a job description from raw text (not from a file).

		This lets other scripts (e.g. scrapers) fetch HTML, convert to text,
		and parse without writing to disk first.
		"""

		# Normalize and prepare lines
		lines = [l for l in text.splitlines() if l.strip()]
		job_title = lines[0].strip() if lines else ''
		company = lines[1].strip() if len(lines) > 1 else ''

		# Experience level (look for 'Experience' section)
		exp_match = re.search(r'Experience\s*\n\s*([A-Za-z0-9+\-/ ]+)', text, re.IGNORECASE)
		experience = exp_match.group(1).strip() if exp_match else ''

		# Technical skills: try to parse the 'traditional technologies such as:' line
		tech_skills: List[str] = []
		tech_section = re.search(r'traditional technologies such as:\s*([^\n]*)', text, re.IGNORECASE)
		if tech_section:
			tech_skills = [s.strip() for s in tech_section.group(1).split(',') if s.strip()]
		else:
			# Fallback: look for common technology keywords in the body
			tech_keywords = ['node.js', 'Java', 'GO', 'AngularJS', 'React', 'Python', 'REST', 'JSON', 'XML', 'Ruby', 'Perl', 'NoSQL', 'relational', 'PySpark', 'AWS', 'iOS', 'Android']
			for kw in tech_keywords:
				if kw.lower() in text.lower() and kw not in tech_skills:
					tech_skills.append(kw)

		# Soft skills: capture lines that mention mentoring, teamwork, innovation, etc.
		soft_skills: List[str] = []
		soft_keywords = ['mentor', 'guide', 'teamwork', 'innovation', 'inclusion', 'diversity', 'self-organization', 'community', 'collaborat']
		for line in text.splitlines():
			for word in soft_keywords:
				if word in line.lower():
					soft_skills.append(line.strip())
					break

		return JobInfo(
			job_title=job_title,
			company=company,
			experience_level=experience,
			technical_skills=tech_skills,
			soft_skills=soft_skills,
		)

	def write_template(self, info: JobInfo):
		with open(self.output_path, 'w') as f:
			f.write(f"Job title\n{info.job_title}\n")
			f.write(f"Company\n{info.company}\n")
			f.write(f"Experenice level\n{info.experience_level}\n")
			f.write(f"Techinal skills\n{', '.join(info.technical_skills)}\n")
			f.write(f"Soft skills\n{'; '.join(info.soft_skills)}\n")

	def process(self) -> JobInfo:
		"""Convenience method: parse and write the template to disk."""
		info = self.extract_job_info()
		self.write_template(info)
		return info


if __name__ == "__main__":
	parser = JobDescriptionParser("Job_desc", "Generated_Template.txt")
	info = parser.process()
	print(f"Wrote template to {parser.output_path}")

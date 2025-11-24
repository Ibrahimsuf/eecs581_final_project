import re
import os
import json
from dataclasses import dataclass, field
from typing import List, Optional
try:
	import anthropic
except Exception:  # ImportError or other issues
	anthropic = None
import sys
import io
import contextlib


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
		self.claude_client = None
		api_key = os.getenv("ANTHROPIC_API_KEY")
		if api_key:
			self.claude_client = anthropic.Anthropic(api_key=api_key)

	def extract_job_info(self) -> JobInfo:
		# Read file and delegate to text-based parser
		with open(self.job_desc_path, 'r') as f:
			text = f.read()
		return self.extract_job_info_from_text(text)

	def extract_job_info_from_text(self, text: str) -> JobInfo:
		"""Parse a job description from raw text (not from a file).

		This lets other scripts (e.g. scrapers) fetch HTML, convert to text,
		and parse without writing to disk first. If Claude API is configured,
		it will use Claude for more accurate parsing.
		"""
		if self.claude_client:
			return self._parse_with_claude(text)
		return self._parse_with_regex(text)

	def _parse_with_claude(self, text: str) -> JobInfo:
		"""Use Claude to parse the job description more accurately."""
		prompt = f"""Please analyze this job description and extract the following information in a structured format:
1. Job Title
2. Company Name
3. Experience Level Required
4. Technical Skills Required (as a comma-separated list)
5. Soft Skills Required (as a semicolon-separated list)

Job Description:
{text}

Please be precise and only extract information that is explicitly mentioned in the text.
"""
		try:
			message = self.claude_client.messages.create(
				model="claude-3-opus-20240229",
				max_tokens=1000,
				messages=[{"role": "user", "content": prompt}]
			)
			response = message.content[0].text

			# Parse Claude's response
			job_info = JobInfo()
			current_section = None
			for line in response.split('\n'):
				line = line.strip()
				if not line:
					continue
				if line.startswith('1. Job Title:'):
					job_info.job_title = line.split(':', 1)[1].strip()
				elif line.startswith('2. Company Name:'):
					job_info.company = line.split(':', 1)[1].strip()
				elif line.startswith('3. Experience Level:'):
					job_info.experience_level = line.split(':', 1)[1].strip()
				elif line.startswith('4. Technical Skills:'):
					skills = line.split(':', 1)[1].strip()
					job_info.technical_skills = [s.strip() for s in skills.split(',') if s.strip()]
				elif line.startswith('5. Soft Skills:'):
					skills = line.split(':', 1)[1].strip()
					job_info.soft_skills = [s.strip() for s in skills.split(';') if s.strip()]

			return job_info
		except Exception as e:
			print(f"Error using Claude API: {e}. Falling back to regex parsing.")
			return self._parse_with_regex(text)

	def _parse_with_regex(self, text: str) -> JobInfo:
		"""Parse job description using regex patterns (original implementation)."""

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
		# Normalize empty fields to 'N/A'
		def _norm_str(s: Optional[str]) -> str:
			return s.strip() if s and s.strip() else "N/A"
		def _norm_list(l: List[str]) -> str:
			if not l:
				return "N/A"
			clean = [x.strip() for x in l if x and x.strip()]
			return ', '.join(clean) if clean else "N/A"

		job_title = _norm_str(info.job_title)
		company = _norm_str(info.company)
		experience = _norm_str(info.experience_level)
		tech = _norm_list(info.technical_skills)
		soft = _norm_list(info.soft_skills)

		with open(self.output_path, 'w', encoding='utf-8') as f:
			f.write(f"Job title\n{job_title}\n")
			f.write(f"Company\n{company}\n")
			f.write(f"Experenice level\n{experience}\n")
			f.write(f"Techinal skills\n{tech}\n")
			f.write(f"Soft skills\n{soft}\n")


	def append_to_database(self, info: JobInfo):
		"""Append a single job record to `self.output_path` as a JSON line.

		Empty/blank fields are replaced with the string "N/A". Lists that are
		empty become ["N/A"]. This produces a JSONL file that can be used as
	
a compact job database.
		"""
		db_path = self.output_path or "jobs_database.txt"

		def _norm_str(s: Optional[str]) -> str:
			return s.strip() if s and s.strip() else "N/A"

		def _norm_list(l: List[str]) -> List[str]:
			if not l:
				return ["N/A"]
			clean = [x.strip() for x in l if x and x.strip()]
			return clean if clean else ["N/A"]

		entry = {
			"job_title": _norm_str(info.job_title),
			"company": _norm_str(info.company),
			"experience_level": _norm_str(info.experience_level),
			"technical_skills": _norm_list(info.technical_skills),
			"soft_skills": _norm_list(info.soft_skills),
		}

		# Append as a JSON line (JSONL). Use UTF-8 and no ascii-escaping.
		with open(db_path, 'a', encoding='utf-8') as f:
			f.write(json.dumps(entry, ensure_ascii=False) + "\n")

	def generate_templates_from_remoteok(self, output_dir: str = 'remoteok_templates') -> List[JobInfo]:
		"""Run the existing `davidsscraper.scrape_remoteok()` (unchanged) and capture its
		printed output, parse each job line, and write a template per job into
		`output_dir` using this parser's `write_template()`.

		This method deliberately does NOT modify `davidsscraper.py` — it imports
		and calls the function while redirecting stdout so the original file remains
		unchanged.
		"""
		# Import the scraper module at runtime so we don't force it during import
		try:
			import davidsscraper
		except Exception as e:
			print(f"Could not import davidsscraper: {e}")
			return []

		# Ensure output directory exists and capture printed output from the scraper
		os.makedirs(output_dir, exist_ok=True)

		# Capture printed output from the scraper
		buf = io.StringIO()
		with contextlib.redirect_stdout(buf):
			try:
				davidsscraper.scrape_remoteok()
			except Exception as e:
				# If the scraper raised, restore stdout and show error
				print(f"Error running scraper: {e}")
		output = buf.getvalue()

		lines = [l.strip() for l in output.splitlines() if l.strip()]
		# Skip header lines if present
		parsed: List[JobInfo] = []
		for line in lines:
			# Skip the header/separator lines
			if line.startswith('Title |') or set(line) == set('-'):
				continue
			# Expect fields separated by ' | '
			parts = [p.strip() for p in line.split(' | ')]
			if not parts or len(parts) < 4:
				# Unexpected line format; skip
				continue
			# remoteok prints: Title | Category | ID | Department | Campus | Reg/Temp | Review Begins | URL
			title = parts[0]
			category = parts[1] if len(parts) > 1 else ''
			job_id = parts[2] if len(parts) > 2 else ''
			department = parts[3] if len(parts) > 3 else ''

			job_info = JobInfo(
				job_title=title,
				company=department,
				experience_level='',
				technical_skills=[s.strip() for s in category.split(',') if s.strip()],
				soft_skills=[],
			)
			# Write to a per-job file in output_dir. Use job_id if available, otherwise sanitize title
			file_suffix = job_id or re.sub(r'[^0-9A-Za-z_-]', '_', title)[:40]
			out_path = os.path.join(output_dir, f"Generated_Template_{file_suffix}.txt")
			# Temporarily set self.output_path so write_template writes to the target file
			saved = self.output_path
			self.output_path = out_path
			try:
				self.write_template(job_info)
			except Exception as e:
				print(f"Failed writing template for {title}: {e}")
			finally:
				self.output_path = saved
			parsed.append(job_info)

		return parsed

	def process(self) -> JobInfo:
		"""Convenience method: parse and write the template to disk."""
		info = self.extract_job_info()
		self.write_template(info)
		return info


if __name__ == "__main__":
	# Check if API key is set
	if not os.getenv("ANTHROPIC_API_KEY"):
		print("Warning: ANTHROPIC_API_KEY not set. Will use regex-based parsing only.")
		print("To use Claude, set the ANTHROPIC_API_KEY environment variable.")
	
	parser = JobDescriptionParser("Job_desc", "Generated_Template.txt")
	info = parser.process()
	print(f"Wrote template to {parser.output_path}")

import os
import json
import subprocess
import time
import re
import random
import shutil
import glob
import sys
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel

# Configure console encoding to support UTF-8/emojis on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# 1. Reuse the structure for structured outputs
class TailoredBullet(BaseModel):
    original_index: int
    tailored_bullet_text: str

class ProjectTailorSchema(BaseModel):
    project_title: str
    tailored_bullets: list[TailoredBullet]

class ResumeTailorResponse(BaseModel):
    tailored_projects: list[ProjectTailorSchema]


def slugify_filename(filename: str, ext=".tex") -> str:
    """
    Transforms a raw job file name (e.g., 'Go Developer / Pune Intern.txt')
    into an organized standard output file name format: 'Soham_Shirke_Go_Developer_Pune_Intern.tex'
    """
    # Strip extension
    base_name, _ = os.path.splitext(filename)
    # Replace non-alphanumeric characters with underscores
    clean_name = re.sub(r'[^a-zA-Z0-9\s_-]', '', base_name)
    clean_name = re.sub(r'[\s_-]+', '_', clean_name).strip('_')
    return f"Soham_Shirke_{clean_name}{ext}"


def escape_latex(text: str) -> str:
    """Escapes LaTeX special characters in a string."""
    if not isinstance(text, str):
        return text
    # Convert rupee symbol to Rs. for maximum LaTeX compilation compatibility
    text = text.replace('₹', 'Rs. ')
    # Normalize en-dash to standard LaTeX en-dash
    text = text.replace('–', '--')
    
    # Map of special characters to escape
    conv = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
        '\\': r'\textbackslash{}',
    }
    # Sort keys by descending length so we match longer sequences first
    regex = re.compile('|'.join(re.escape(str(key)) for key in sorted(conv.keys(), key=lambda item: -len(item))))
    return regex.sub(lambda match: conv[match.group()], text)


def format_project_impact(impact_text: str) -> str:
    """Cleans and shortens long project impact text to fit in a heading."""
    if not impact_text:
        return ""
    # Extract date in parentheses (e.g. (Mar 2026))
    date_match = re.search(r'\(([^)]+)\)', impact_text)
    date_str = f" ({date_match.group(1)})" if date_match else ""
    
    # Clean up the main title (take everything before the first comma, dash, or slash)
    main_text = impact_text
    for separator in ['–', '—', '-', ',', '/']:
        if separator in main_text:
            main_text = main_text.split(separator, 1)[0]
            break
            
    main_text = " ".join(main_text.split())
    # Truncate if still too long
    if len(main_text) > 30:
        main_text = main_text[:27] + "..."
        
    return f"{main_text}{date_str}"


def generate_latex_resume(resume_data: dict, template_path="template.tex") -> str:
    """Populates the template.tex file with data from resume_data."""
    with open(template_path, 'r', encoding='utf-8') as f:
        latex_template = f.read()

    # 1. Contact info
    meta = resume_data["meta"]
    email = escape_latex(meta["email"])
    phone = escape_latex(meta["phone"])
    github = escape_latex(meta["github"])
    linkedin = escape_latex(meta["linkedin"])
    parts = []
    if email: parts.append(f"\\href{{mailto:{email}}}{{{email}}}")
    if phone: parts.append(phone)
    if github: parts.append(f"\\href{{https://{github}}}{{{github}}}")
    if linkedin: parts.append(f"\\href{{https://{linkedin}}}{{{linkedin}}}")
    contact_info = " $|$ ".join(parts)

    # 2. Education
    edu = resume_data["education"]
    inst = escape_latex(edu["institute"])
    deg = escape_latex(edu["degree"])
    met = escape_latex(edu["metrics"])
    dates = escape_latex(edu["dates"])
    education_latex = f"\\resumeSubheading{{{inst}}}{{{dates}}}{{{deg}}}{{{met}}}"

    # 3. Skills
    skills = resume_data["technical_skills"]
    skills_list = []
    if "languages" in skills and "concurrency" in skills:
        langs = escape_latex(", ".join(skills["languages"]))
        conc = escape_latex(", ".join(skills["concurrency"]))
        skills_list.append(f"\\textbf{{Languages \\& Concurrency}}{{: {langs} ({conc})}}")
    if "backend" in skills:
        backend = escape_latex(", ".join(skills["backend"]))
        skills_list.append(f"\\textbf{{Backend \\& Databases}}{{: {backend}}}")
    if "redis" in skills:
        redis = escape_latex(", ".join(skills["redis"]))
        skills_list.append(f"\\textbf{{Redis Technologies}}{{: {redis}}}")
    if "tools" in skills and "security" in skills:
        tools = escape_latex(", ".join(skills["tools"]))
        sec = escape_latex(", ".join(skills["security"]))
        skills_list.append(f"\\textbf{{Tools \\& Security}}{{: {tools} $|$ {sec}}}")
    skills_latex = " \\\\\n     ".join(skills_list)

    # 4. Experience
    exp_list = []
    for job in resume_data["experience"]:
        title = escape_latex(job["title"])
        company = escape_latex(job["company"])
        dates = escape_latex(job["dates"])
        loc = escape_latex(job.get("location", ""))
        
        job_latex = f"\\resumeSubheading{{{title}}}{{{dates}}}{{{company}}}{{{loc}}}\n"
        job_latex += "    \\resumeItemListStart\n"
        for bullet in job["bullets"]:
            # Normalize whitespace to fix double-newlines/gaps from LLM
            clean_bullet = " ".join(bullet.split())
            job_latex += f"      \\resumeItem{{{escape_latex(clean_bullet)}}}\n"
        job_latex += "    \\resumeItemListEnd"
        exp_list.append(job_latex)
    experience_latex = "\n".join(exp_list)

    # 5. Projects
    proj_list = []
    for proj in resume_data["projects"]:
        title = escape_latex(proj["title"])
        tech = escape_latex(proj["tech"])
        bullets = proj["bullets"]
        
        # Shorten the impact string to keep the heading clean and space-efficient
        impact = escape_latex(format_project_impact(proj.get("impact", "")))
        
        proj_latex = f"    \\resumeProjectHeading{{\\textbf{{{title}}} $|$ \\textit{{{tech}}}}}{{{impact}}}\n"
        proj_latex += "    \\resumeItemListStart\n"
        for bullet in bullets:
            # Normalize whitespace to fix double-newlines/gaps from LLM
            clean_bullet = " ".join(bullet.split())
            proj_latex += f"      \\resumeItem{{{escape_latex(clean_bullet)}}}\n"
        proj_latex += "    \\resumeItemListEnd"
        proj_list.append(proj_latex)
    projects_latex = "\n".join(proj_list)

    # 6. Awards
    awards_list = []
    for award in resume_data["awards"]:
        title = escape_latex(award["title"])
        details = escape_latex(award["details"])
        
        # Format verbose award details into a clean single sentence
        details = details.replace("1st place out of 70+ teams across 12 states. Awarded Rs. 50,000 for building a privacy-preserving cross-bank fraud detection system -- 80% accuracy on RBI-structured mock data, projecting 95%+ on live datasets.", "Won 1st place out of 70+ teams; awarded Rs. 50,000 for engineering a privacy-preserving cross-bank fraud detection system.")
        details = details.replace("1st place out of 70+ teams across 12 states. Awarded Rs. 50,000 for building a privacy-preserving cross-bank fraud detection system -- 80\\% accuracy on RBI-structured mock data, projecting 95\\%+ on live datasets.", "Won 1st place out of 70+ teams; awarded Rs. 50,000 for engineering a privacy-preserving cross-bank fraud detection system.")
        details = " ".join(details.split())
        
        award_latex = f"    \\item \\textbf{{{title}}}: {details}"
        awards_list.append(award_latex)
    awards_latex = "\n".join(awards_list)

    # Replace placeholders
    doc = latex_template
    doc = doc.replace("<<NAME>>", escape_latex(meta["name"]))
    doc = doc.replace("<<CONTACT_INFO>>", contact_info)
    doc = doc.replace("<<EDUCATION>>", education_latex)
    doc = doc.replace("<<SKILLS>>", skills_latex)
    doc = doc.replace("<<EXPERIENCE>>", experience_latex)
    doc = doc.replace("<<PROJECTS>>", projects_latex)
    doc = doc.replace("<<AWARDS>>", awards_latex)
    
    return doc


def run_tailoring_with_backoff(client, job_desc: str, resume_data: dict, file_name: str) -> dict:
    """
    Executes the generation with an exponential backoff loop 
    to robustly scale past 15 RPM limits on the free tier.
    """
    projects_to_tailor = [
        {"title": p["title"], "bullets": p["bullets"]} 
        for p in resume_data["projects"]
    ]

    prompt = f"""
    You are an expert technical resume strategist. Modify the project bullets to match 
    the skills requested in the target Job Description. Maintain absolute factual accuracy.
    
    Base Projects Data:
    {json.dumps(projects_to_tailor, indent=2)}

    Target Job Description:
    {job_desc}
    """

    # Rate limiting setup configurations
    base_delay = 4.5  # Crucial safety net: 60 sec / 15 requests = 4 seconds per call minimum.
    max_retries = 5
    retry_count = 0

    while retry_count <= max_retries:
        try:
            # Enforce client-side rate regulation proactively
            time.sleep(base_delay)
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ResumeTailorResponse,
                    temperature=0.2,
                ),
            )
            return json.loads(response.text)

        except APIError as e:
            # Catch standard 429 errors from Google
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                retry_count += 1
                if retry_count > max_retries:
                    print(f"💥 Failed permanently after {max_retries} retries due to quota constraints.")
                    raise e
                
                # Exponential backoff equation with random jitter to desynchronize requests:
                # Delay = (2^retry) + uniform_random(0, 1)
                sleep_time = (2 ** retry_count) + random.random()
                print(f"⚠️ [429 Rate Limited] Hits quota barrier on {file_name}. Retrying in {round(sleep_time, 2)}s... (Attempt {retry_count}/{max_retries})")
                time.sleep(sleep_time)
            else:
                # Raise other exceptions immediately (e.g. invalid API key, context length)
                raise e


def load_env():
    """Reads .env file manually and updates os.environ."""
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    val = val.strip().strip('"').strip("'")
                    os.environ[key.strip()] = val


def process_all_jobs(jobs_dir="jobs", resume_json_path="resume.json", output_dir="output_resumes"):
    # Load API key
    load_env()
    
    # Instantiate single shared client architecture instance
    client = genai.Client()
    
    # Verify or spin up output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 Created target directory layout: {output_dir}/")

    # Filter out text jobs exclusively
    job_files = [f for f in os.listdir(jobs_dir) if f.endswith('.txt')]
    total_files = len(job_files)
    print(f"🚀 Loaded pipeline sequence. Total jobs to compile: {total_files}\n")

    for index, filename in enumerate(job_files, 1):
        job_path = os.path.join(jobs_dir, filename)
        output_latex_name = slugify_filename(filename)
        output_latex_path = os.path.join(output_dir, output_latex_name)

        print(f"📦 [{index}/{total_files}] Processing profile for: {filename}")

        # Fresh read of baseline data to avoid mutation compounding across runs
        with open(resume_json_path, 'r', encoding='utf-8') as f:
            resume_data = json.load(f)
        with open(job_path, 'r', encoding='utf-8') as f:
            job_desc = f.read()

        # Skip empty job description files to prevent API failures
        if not job_desc.strip():
            print(f"   ⚠️ Skipping empty job description file: {filename}")
            continue

        try:
            # Step 1: Query API with built-in client-throttling
            tailored_result = run_tailoring_with_backoff(client, job_desc, resume_data, filename)

            # Step 2: Remap matching outputs back into core data layout
            for t_proj in tailored_result["tailored_projects"]:
                for orig_proj in resume_data["projects"]:
                    # Compare titles case-insensitively and check for containing strings to prevent strict casing issues
                    title_a = orig_proj["title"].strip().lower()
                    title_b = t_proj["project_title"].strip().lower()
                    if title_a in title_b or title_b in title_a:
                        for t_bullet in t_proj["tailored_bullets"]:
                            idx = t_bullet["original_index"]
                            if idx < len(orig_proj["bullets"]):
                                # Normalize bullets to remove LLM-introduced newlines and whitespace gaps
                                cleaned_bullet = " ".join(t_bullet["tailored_bullet_text"].split())
                                orig_proj["bullets"][idx] = cleaned_bullet

            # Step 3: Populate LaTeX template
            latex_content = generate_latex_resume(resume_data)

            # Step 4: Write the final LaTeX file
            with open(output_latex_path, 'w', encoding='utf-8') as f:
                f.write(latex_content)
            
            print(f"   💾 Generated LaTeX -> {output_latex_path}")

        except Exception as global_error:
            print(f"   ❌ Fatal breakdown compiling {filename}: {global_error}")
            continue # Ensure complete sequential coverage even if single item triggers errors

    print(f"\n✨ Generation stream terminated. All resumes saved inside '{output_dir}/'.")


if __name__ == "__main__":
    # Ensure GEMINI_API_KEY environment variable is configured prior to run execution
    start_pipeline = time.time()
    process_all_jobs()
    print(f"🏁 Complete pipeline finalized in {round((time.time() - start_pipeline)/60, 2)} minutes.")
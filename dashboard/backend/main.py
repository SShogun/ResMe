from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os
import json
import logging

# Ensure root workspace directory and local backend directory are in the path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, "..", ".."))
sys.path.append(ROOT_DIR)
sys.path.append(BACKEND_DIR)

import engine
import database
from redis_cache import cache

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DashboardBackend")

app = FastAPI(title="ResMe Dashboard API")

# Enable CORS for Vite React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RESUME_JSON_PATH = os.path.join(ROOT_DIR, "resume.json")

# Pydantic schemas for request validation
class ResumeUpdate(BaseModel):
    meta: dict
    education: dict
    technical_skills: dict
    experience: list
    projects: list
    awards: list

class TailorRequest(BaseModel):
    job_description: str
    selected_projects: list[str] = []

class ApplicationCreate(BaseModel):
    company: str
    title: str
    status: str
    date_applied: str
    jd_text: str = ""
    latex_content: str = ""
    notes: str = ""

class ApplicationUpdate(BaseModel):
    company: str
    title: str
    status: str
    date_applied: str
    jd_text: str = ""
    latex_content: str = ""
    notes: str = ""

@app.get("/api/resume")
def get_resume():
    # Try loading from DB first
    try:
        db_resume = database.get_resume_profile()
        if db_resume:
            return db_resume
    except Exception as e:
        logger.warning(f"Failed to read resume from database: {e}")

    # Fallback to local resume.json file and bootstrap the DB
    if not os.path.exists(RESUME_JSON_PATH):
        raise HTTPException(status_code=404, detail="resume.json not found.")
    try:
        with open(RESUME_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Bootstrap DB with the file contents
        try:
            database.save_resume_profile(data)
        except Exception as e:
            logger.warning(f"Failed to bootstrap database with resume data: {e}")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read resume: {e}")

@app.post("/api/resume")
def update_resume(updated_resume: ResumeUpdate):
    try:
        resume_dict = updated_resume.dict()
        # Save to DB first
        database.save_resume_profile(resume_dict)
        
        # Save to local file if it exists/writable (best effort)
        try:
            with open(RESUME_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(resume_dict, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Could not update local backup resume.json: {e}")

        # Invalidate cache if there's any active caches
        try:
            cache.delete("dashboard_stats")
        except Exception:
            pass
        return {"status": "success", "message": "Resume updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update resume: {e}")

@app.post("/api/tailor")
def tailor_resume(req: TailorRequest):
    if not req.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")
    
    try:
        # Load copy of resume (DB first, then file)
        resume_data = None
        try:
            resume_data = database.get_resume_profile()
        except Exception as e:
            logger.warning(f"Could not load resume from DB for tailoring: {e}")
            
        if not resume_data:
            with open(RESUME_JSON_PATH, "r", encoding="utf-8") as f:
                resume_data = json.load(f)
            
        # Ensure env is loaded
        engine.load_env()
        
        # Instantiate Gemini Client
        from google import genai
        client = genai.Client()
        
        # Run tailoring backend query
        # Since run_tailoring_with_backoff accepts (client, job_desc, resume_data, file_name)
        tailored_result = engine.run_tailoring_with_backoff(
            client, 
            req.job_description, 
            resume_data, 
            "api_tailor_request"
        )
        
        # We track modifications side-by-side to show the user in the UI diff
        modifications = []
        
        # Step 2: Remap matching outputs back into core data layout
        for t_proj in tailored_result["tailored_projects"]:
            for orig_proj in resume_data["projects"]:
                # Compare titles case-insensitively/partially
                title_a = orig_proj["title"].strip().lower()
                title_b = t_proj["project_title"].strip().lower()
                
                # Check if we should tailor this project (or if it was selected)
                is_selected = True
                if req.selected_projects:
                    is_selected = any(p.lower() in title_a or title_a in p.lower() for p in req.selected_projects)
                
                if (title_a in title_b or title_b in title_a) and is_selected:
                    project_mods = {
                        "project_title": orig_proj["title"],
                        "bullets": []
                    }
                    for t_bullet in t_proj["tailored_bullets"]:
                        idx = t_bullet["original_index"]
                        if idx < len(orig_proj["bullets"]):
                            # Normalize bullets to remove LLM-introduced newlines and whitespace gaps
                            cleaned_bullet = " ".join(t_bullet["tailored_bullet_text"].split())
                            old_bullet = orig_proj["bullets"][idx]
                            orig_proj["bullets"][idx] = cleaned_bullet
                            
                            if old_bullet.strip() != cleaned_bullet.strip():
                                project_mods["bullets"].append({
                                    "original_index": idx,
                                    "old": old_bullet,
                                    "new": cleaned_bullet
                                })
                    if project_mods["bullets"]:
                        modifications.append(project_mods)

        # Generate LaTeX code using the template and the tailored data
        template_abs_path = os.path.join(ROOT_DIR, "template.tex")
        latex_content = engine.generate_latex_resume(resume_data, template_path=template_abs_path)
        
        return {
            "status": "success",
            "modifications": modifications,
            "tailored_resume_data": resume_data,
            "latex_content": latex_content
        }
        
    except Exception as e:
        logger.error(f"Error tailoring resume: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/applications")
def get_applications():
    # Attempt to retrieve from Redis cache first
    cache_key = "all_applications"
    try:
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("⚡ Serving applications list from cache.")
            return json.loads(cached_data)
    except Exception as e:
        logger.warning(f"Cache get error: {e}")

    # Fallback to Database
    try:
        apps = database.get_all_applications()
        # Set cache with expiration of 30 seconds
        try:
            cache.set(cache_key, json.dumps(apps), ex=30)
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
        return apps
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/applications")
def create_application(app_data: ApplicationCreate):
    try:
        new_id = database.create_application(
            company=app_data.company,
            title=app_data.title,
            status=app_data.status,
            date_applied=app_data.date_applied,
            jd_text=app_data.jd_text,
            latex_content=app_data.latex_content,
            notes=app_data.notes
        )
        # Clear cache
        try:
            cache.delete("all_applications")
            cache.delete("dashboard_stats")
        except Exception:
            pass
        return {"id": new_id, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/applications/{app_id}")
def update_application(app_id: int, app_data: ApplicationUpdate):
    try:
        database.update_application(
            app_id=app_id,
            company=app_data.company,
            title=app_data.title,
            status=app_data.status,
            date_applied=app_data.date_applied,
            jd_text=app_data.jd_text,
            latex_content=app_data.latex_content,
            notes=app_data.notes
        )
        # Clear cache
        try:
            cache.delete("all_applications")
            cache.delete("dashboard_stats")
        except Exception:
            pass
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/applications/{app_id}")
def delete_application(app_id: int):
    try:
        database.delete_application(app_id)
        # Clear cache
        try:
            cache.delete("all_applications")
            cache.delete("dashboard_stats")
        except Exception:
            pass
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
def get_stats():
    cache_key = "dashboard_stats"
    try:
        cached_stats = cache.get(cache_key)
        if cached_stats:
            logger.info("⚡ Serving stats from cache.")
            return json.loads(cached_stats)
    except Exception:
        pass

    try:
        apps = database.get_all_applications()
        total = len(apps)
        
        status_counts = {
            "Wishlist": 0,
            "Applied": 0,
            "Interviewing": 0,
            "Offer": 0,
            "Rejected": 0
        }
        for a in apps:
            status_counts[a["status"]] = status_counts.get(a["status"], 0) + 1
            
        stats = {
            "total_applications": total,
            "by_status": status_counts,
            "interview_rate": round((status_counts["Interviewing"] + status_counts["Offer"]) / total * 100, 1) if total > 0 else 0.0,
            "offer_rate": round(status_counts["Offer"] / total * 100, 1) if total > 0 else 0.0
        }
        
        try:
            cache.set(cache_key, json.dumps(stats), ex=60)
        except Exception:
            pass
            
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
